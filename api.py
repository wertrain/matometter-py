# coding:utf-8
from bottle import Bottle, request, redirect
import cPickle
from my.db import datastore
import common
from my.twitter import api
from google.appengine.api import memcache
from google.appengine.api import mail

from datetime import datetime, timedelta
import time
import re
import urllib

apis = Bottle()

#@apis.route('/latest_tweets_to_datastore')
#def add_latest_tweets_to_datastore():
#    u""" ツイートを取得し、更新（デバッグ用） """
#    #datastore.remove_all()
#    debug.add_latest_tweets_to_datastore()
#    return 'Updated.'

def tweet_model_to_object(tweet, with_history=False):
    u"""
        ツイートデータモデルを辞書オブジェクトに変換する
        （ツイートデータモデルに変更があった場合、この関数で差を吸収しやすくする）
        @param tweet ツイートデータモデル
    """
    text = tweet.text
    urls = []
    videoinfo = None
    for media in tweet.media.run():
        # ツイート本文から URL を除去
        for url in media.urls:
            text = text.replace(url, '')
        # 表示用に https の Media URL を保存
        for url in media.media_urls_https:
            urls.append(url)
        if media.video_type is not None and media.video_url is not None:
            videoinfo = {'type': media.video_type, 'url':media.video_url}
    data = {
        'id':tweet.id,
        'text':text,
        'created_at':tweet.created_at,
        'lang':tweet.lang,
        'retweet_count': tweet.retweet_count,
        'favorite_count': tweet.favorite_count,
        'user':{
            'id':tweet.user.id,
            'name':tweet.user.name,
            'screen_name':tweet.user.screen_name,
            'profile_image_url':tweet.user.profile_image_url_https,
        }
    }
    # @note このあたりリファクタしたい
    if len(urls) > 0:
        data['media'] = {'url': urls[0], 'urls':urls}
    if videoinfo is not None:
        if not 'media' in data:
            data['media'] = {}
        data['media']['video'] = videoinfo
    if with_history:
        history = tweet.history.get()
        # 過去 HISTORY_COUNT 番目のデータまで渡す
        HISTORY_COUNT = 5
        counts = []
        timestamps = datastore.get_timestamps(history.timestamp_indexes[-HISTORY_COUNT:])
        tslen = len(timestamps)
        for i, v in enumerate(timestamps):
            counts.append({
                'timestamp': v,
                'favorite': history.favorite_counts[-tslen+i],
                'retweet': history.retweet_counts[-tslen+i]
            })
            data['history'] = {
              'counts': counts
            }
    return data

def user_model_to_object(user):
    return {
        'id': user.id,
        'name': user.name,
        'screen_name': user.screen_name,
        'profile_image_url': user.profile_image_url_https
    }

def linkURLs(str):
    return re.sub(r'([^"]|^)(https?|ftp)(://[\w:;/.?%#&=+-]+)', r'\1<a href="\2\3">\2\3</a>', str)

def tweet_with_history(id):
    tweet = datastore.get_tweet(id)
    tweet.text = linkURLs(tweet.text)
    return tweet_model_to_object(tweet, with_history=True)

def tweet_user(id):
    user = datastore.get_tweetuser(id)
    return user_model_to_object(user)

def count_from_cache(key_base, q):
    u"""
        カウント数をキャッシュから取得する
        @param key_base memcacheに指定するベースとなるキー
        @param q データストアのクエリ
    """
    memcache_key = key_base + '_count'
    data = memcache.get(memcache_key)
    if data is None:
        count = q.count()
        memcache.add(memcache_key, str(count), 60 * 60 * 24)
        return count
    return int(data)

def newer(offset=0, limit=20):
    u"""
        最新のツイート（最近投稿されたもの順）を取得する
        @param limit いくつ取得するか
    """
    memcache_base_key = 'newer_tweet_cache'
    memcache_key = memcache_base_key + '_offset_' + str(offset) + '_limit_' + str(limit)
    data = memcache.get(memcache_key)
    if data is None:
        tweets = []
        q = datastore.get_tweets()
        q.order("-created_at")
        for tweet in q.run(offset=offset, limit=limit):
            tweets.append(tweet_model_to_object(tweet))
        data = cPickle.dumps((tweets, count_from_cache(memcache_base_key, q)))
        memcache.add(memcache_key, data, 60 * 30)
    return cPickle.loads(data)

def latest(limit=20):
    u"""
        最新のツイート（最近取得されたもの順）を取得する
        @param limit いくつ取得するか
    """
    memcache_base_key = 'latest_tweet_cache'
    memcache_key = memcache_base_key + '_limit_' + str(limit)
    data = memcache.get(memcache_key)
    if data is None:
        tweets = []
        q = datastore.get_tweets()
        q.order("-timestamp_index")
        for tweet in q.run(offset=0, limit=limit):
            tweets.append(tweet_model_to_object(tweet))
        data = cPickle.dumps((tweets, count_from_cache(memcache_base_key, q)))
        memcache.add(memcache_key, data, 60 * 30)
    return cPickle.loads(data)

def most_popular(days=1, limit=10):
    u"""
        人気のツイートを取得する
        @param days 何日前までの投稿を取得するか
        
        @note 現在の実装では、「何日前まで」の対象は作られた日ではなく
              取得された日になっている。つまり、一年前のツイートでも
              最近リツイートされれば、また取得対象に含まれることになる
    """
    memcache_key = 'most_popular_tweet_cache_days_' + str(days) + '_limit_' + str(limit)
    data = memcache.get(memcache_key)
    if data is None:
        # 対象の日付を unixtime に変換する
        target_timestamp = int(time.mktime((datetime.now() + timedelta(days=-days)).timetuple()))
        # 呼び出し履歴を取得して、対象の日付までのカウントを取得
        callhistory = datastore.get_call_history()
        count = 0
        for timestamp in reversed(callhistory.unixtimestamps):
            if timestamp < target_timestamp:
                break
            count = count + 1
        # timestamp_count は取得後、一つふえているはずなのでここで -1
        target_count = callhistory.timestamp_count - count - 1

        tweets = []
        q = datastore.get_tweets_query()
        # カウント位置までの投稿を取得する
        q.order("-retweet_count")
        q.order("-favorite_count")
        q.order("-created_at")
        for tweet in q.run():
            if tweet.timestamp_index >= target_count:
                tweets.append(tweet_model_to_object(tweet))
                if len(tweets) >= limit:
                    break
        data = cPickle.dumps(tweets)
        memcache.add(memcache_key, data, 60 * 30)
    return cPickle.loads(data)

def user_newer(id, offset=0, limit=10):
    memcache_base_key = 'user_newer_tweet_cache_id_' + str(id)
    memcache_key = memcache_base_key + '_offset_' + str(offset) + '_limit_' + str(limit)
    data = memcache.get(memcache_key)
    if data is None:
        user = datastore.get_tweetuser(id)
        q = datastore.get_tweets_from_user(user)
        q.order("-created_at")
        tweets = []
        for tweet in q.run(offset=offset, limit=limit):
            tweets.append(tweet_model_to_object(tweet))
        data = cPickle.dumps((tweets, count_from_cache(memcache_base_key, q)))
        memcache.add(memcache_key, data, 60 * 30)
    return cPickle.loads(data)

def most_popular_users(days=7, limit=10):
    memcache_key = 'most_popular_users_cache_days_' + str(days) + '_limit_' + str(limit)
    data = memcache.get(memcache_key)
    if data is None:
        tweets = most_popular(days, limit=100)
        users = {}
        for tweet in tweets:
            user = None
            id = str(tweet['user']['id'])
            # ハッシュテーブル代わりの辞書型
            if not users.has_key(id):
                user = {
                    'user': tweet['user'],
                    'retweet_count': 0,
                    'favorite_count': 0
                }
            else:
                user = users[id]
            # リツイート数とお気に入り数総数を計算
            user['retweet_count'] += tweet['retweet_count']
            user['favorite_count'] += tweet['favorite_count']
            users[id] = user
        # 指定されたサイズに切り出しつつ配列化
        users = users.values()[:limit]
        # リツイート数とお気に入り数の合計値でソートする
        users = sorted(users, key=lambda x:(x['retweet_count'] + x['favorite_count']),reverse=True)
        # 配列を pickle 化
        data = cPickle.dumps(users)
        memcache.add(memcache_key, data, 60 * 30)
    return cPickle.loads(data)

def should_entry(tweet):
    # ある程度人気のツイートに限る
    if tweet['favorite_count'] < common.FAVORITE_COUNT_REGISTERED_THRESHOLD:
        return False
    if tweet['retweet_count'] < common.RETWEET_COUNT_REGISTERED_THRESHOLD:
        return False
    # 画像があるエントリーか判定
    # extended_entities がある？ entities がある？ entities の中に media がある？
    if not 'extended_entities' in tweet and ((not 'entities' in tweet) or (not 'media' in tweet['entities'])):
        return False
    return True
    
def easy_memcashe():
    u""" 何度も API を呼び出すと規制されるのでキャッシュを使う """
    memcache_key = 'home_timeline_cache'
    result = memcache.get(memcache_key)
    if result is None:
       result = api.home_timeline(count=200)
       memcache.add(memcache_key, cPickle.dumps(result), 60 * 30)
    else:
       result = cPickle.loads(result)
    return result

@apis.route('/update_tweet')
def update_tweet():
    u""" ツイートを取得し、更新 """
    result = api.home_timeline(count=200)
    timestamp_count = datastore.get_timestamp_count()
    ids = {}
    if result['status_code'] == 200:
        for tweet in result['timeline']:
            t = tweet
            # retweeted_status があれば誰かのリツイートであるので、元のツイートを取得する
            if 'retweeted_status' in tweet:
                t = tweet['retweeted_status']
            # エントリーすべきツイートか判定
            if not should_entry(t):
                continue
            # id を保存して、一回の呼び出しでは同じ投稿は一度しか書き込まないようにする
            id = str(t['id'])
            if not ids.has_key(id):
                ids[id] = True
                datastore.entry_tweet(tweet, timestamp_count)
        datastore.timestamp()
        # memcache をすべて削除してしまう
        memcache.flush_all()
    else:
        return 'Error. status_code:' + str(result['status_code'])
    return 'Updated.'

@apis.route('/update_popular_tweet')
def update_popular_tweet():
    u""" ツイートを取得し、更新 """
    result = api.search_tweets(q='RT', result_type='popular', include_entities='true')
    timestamp_count = datastore.get_timestamp_count()
    ids = {}
    if result['status_code'] == 200:
        for tweet in result['timeline']:
            t = tweet
            # retweeted_status があれば誰かのリツイートであるので、元のツイートを取得する
            if 'retweeted_status' in tweet:
                t = tweet['retweeted_status']
            # エントリーすべきツイートか判定
            if not should_entry(t):
                continue
            # id を保存して、一回の呼び出しでは同じ投稿は一度しか書き込まないようにする
            id = str(t['id'])
            if not ids.has_key(id):
                ids[id] = True
                datastore.entry_tweet(tweet, timestamp_count)
        datastore.timestamp()
    else:
        return 'Error. status_code:' + str(result['status_code'])
    return 'Updated.'

@apis.route('/update_trends_tweet')
def update_trends_tweet():
    u"""
         人気のワードからツイートを取得、更新
         search_tweets を使用する都合上、ツイートに含まれる画像は一つしか取得できない
    """
    result = api.trends_from()
    # 人気のワードを展開
    words = []
    if result['status_code'] == 200:
        for word in result['trends'][0]['trends']:
            words.append(word['name'])

    timestamp_count = datastore.get_timestamp_count()
    # 人気のワードをクエリーにしてツイートを取得
    ids = {}
    for word in words:
        #result = api.search_tweets(q=word + u' filter:images', result_type='popular', count=100)
        result = api.search_tweets(q=word + u' filter:images', result_type='mixed', count=100)
        if result['status_code'] == 200:
            for tweet in result['timeline']:
                t = tweet
                # retweeted_status があれば誰かのリツイートであるので、元のツイートを取得する
                if 'retweeted_status' in tweet:
                    t = tweet['retweeted_status']
                # エントリーすべきツイートか判定
                if not should_entry(t):
                    continue
                # id を保存して、一回の呼び出しでは同じ投稿は一度しか書き込まないようにする
                id = str(t['id'])
                if not ids.has_key(id):
                    ids[id] = True
                    datastore.entry_tweet(t, timestamp_count)
        time.sleep(0.1)

    if ids:
        datastore.timestamp()
        # memcache をすべて削除
        memcache.flush_all()
        return 'Updated.'
    else:
        return 'No update.'

@apis.route('/store_trends_tweet')
def store_trends_tweet():
    u""" 
         人気のワードからツイートを取得し保存する
         保存されたツイートを別途取得する必要がある
    """
    result = api.trends_from()
    # 人気のワードを展開
    words = []
    if result['status_code'] == 200:
        for word in result['trends'][0]['trends']:
            words.append(word['name'])

    ids = []
    pickle_text = str(datastore.get_stored_trends_text())
    if (len(pickle_text) != 0):
        ids = cPickle.loads(pickle_text)

    # 人気のワードをクエリーにしてツイートを取得
    for word in words:
        #result = api.search_tweets(q=word + u' filter:images', result_type='popular', count=100)
        result = api.search_tweets(q=word + u' filter:images', result_type='mixed', count=100)
        if result['status_code'] == 200:
            for tweet in result['timeline']:
                t = tweet
                # retweeted_status があれば誰かのリツイートであるので、元のツイートを取得する
                if 'retweeted_status' in tweet:
                    t = tweet['retweeted_status']
                # エントリーすべきツイートか判定
                if not should_entry(t):
                    continue
                # id を保存して、一回の呼び出しでは同じ投稿は一度しか書き込まないようにする
                id = str(t['id'])
                if id not in ids:
                    ids.append(id)
        time.sleep(0.05)
    datastore.update_stored_trends_text(cPickle.dumps(ids))
    return str(len(ids))

@apis.route('/get_tweets_by_stored')
def get_tweets_by_stored():
    ids = []
    pickle_text = str(datastore.get_stored_trends_text())
    if (len(pickle_text) != 0):
        ids = cPickle.loads(pickle_text)
    
    if (len(ids) == 0):
        return 'Completed.'
    
    # 50 件を取得する
    result = api.lookup_tweets(ids[:50])

    if result['status_code'] == 200:
        timestamp_count = datastore.get_timestamp_count()
        for tweet in result['statuses']:
            # もうすでに登録してよいか判定済みなので直接書き込む
            datastore.entry_tweet(tweet, timestamp_count)
        del ids[:50]
        datastore.timestamp()
        memcache.flush_all()

    datastore.update_stored_trends_text(cPickle.dumps(ids))
    return str(ids)

@apis.route('/retweet')
def retweet():
    u""" 最近人気のツイートをリツイートする """
    populars = most_popular(days=1, limit=10)
    
    # 自分のタイムラインから投稿を取得
    result = api.user_timeline('2952115826', count=30) # 2952115826 は自分のID
    if not result['status_code'] == 200:
        return 'error'
    
    # 過去にリツイートしてないないか調べる
    retweet_result = None
    for i in xrange(10):
        retweet_target = populars[i]
        for tweet in result['timeline']:
            if not 'retweeted_status' in tweet:
                continue
            if tweet['retweeted_status']['id'] == str(retweet_target['id']):
                retweet_target = None
                break
        # リツイート
        if retweet_target is not None:
            retweet_result = api.retweet(retweet_target['id'])
            if retweet_result['status_code'] == 200:
                break
    return str(retweet_result)

@apis.post('/send_mail')
def send_mail():
    u""" メールを送信する """
    name = 'anonymous'
    if (len(str(request.forms.get('name'))) != 0):
        name = request.forms.get('name')
    email = 'admin <toratsugumi.sing@gmail.com>'
    if (len(str(request.forms.get('email'))) != 0):
        email = name + ' <' + request.forms.get('email') + '>'
    message = ''
    if (request.forms.get('message') is not None):
        message = urllib.unquote(request.forms.get('message')).decode('utf-8')
    message = message + '; email:' + email
    mail.send_mail_to_admins(sender='admin <toratsugumi.sing@gmail.com>',
                  subject="matometter",
                  body=message)
    redirect("/contact/OK")


@apis.route('/delete_all_datastore')
def delete_all_datastore():
    u""" datastore をすべて削除 """
    datastore.remove_all()
    return 'Updated.'

# def most_popular(days=1, limit=10):
    # u"""
        # 人気のツイートを取得する
        # @param days 何日前までの投稿を取得するか
        
        # @note 現在の実装では、「何日前まで」の対象は作られた日ではなく
              # 取得された日になっている。つまり、一年前のツイートでも
              # 最近リツイートされれば、また取得対象に含まれることになる
    # """
    # memcache_key = 'most_popular_tweet_cache_days_' + str(days) + '_limit_' + str(limit)
    # data = memcache.get(memcache_key)
    # if data is None:
        # # 対象の日付を unixtime に変換する
        # target_timestamp = int(time.mktime((datetime.now() + timedelta(days=-days)).timetuple()))
        # # 呼び出し履歴を取得して、対象の日付までのカウントを取得
        # callhistory = datastore.get_call_history()
        # count = 0
        # for timestamp in reversed(callhistory.unixtimestamps):
            # if timestamp < target_timestamp:
                # break
            # count = count + 1
        # # timestamp_count は取得後、一つふえているはずなのでここで -1
        # target_count = callhistory.timestamp_count - count - 1

        # tweets = []
        # q = datastore.get_tweets_query()
        # #カウント位置までの投稿を取得する
        # q.order("-timestamp_index")
        # q.filter('timestamp_index >=', target_count)
        # q.order("-retweet_count")
        # q.order("-favorite_count")
        # for tweet in q.run(offset=0, limit=limit):
            # tweets.append(tweet_model_to_object(tweet))
        # data = cPickle.dumps(tweets)
        # memcache.add(memcache_key, data, 60 * 30)
    #return cPickle.loads(data)
