# coding:utf-8
u"""
    Google App Engine Datastore ラッパー

    このモジュールは Google App Engine Datastore をラップして使いやすくしたものです。

    ===========================================================================
          このモジュールで扱うデータモデル図式
    ---------------------------------------------------------------------------

        [TweetUser] ... 一人のユーザーを表す（Tweetとは一対多の関係）
            └ [Tweet] ... 一つのツイートを表す
                ├ [TweetTag]     ... ツイートに付属する複数のタグデータ
                ├ [TweetMedia]   ... ツイートに含まれる複数のメディアを取り出したい時に参照する
                └ [TweetHistory] ... ツイートの過去のRT数などを調べたい時に参照する
           
        [CallHistory] ... Tweet/TweetHistory は時刻のインデックスしか持っていないので、実際の時刻を知りたい時に参照する

    ===========================================================================

    __author__ = 'T.Miyata'
    __version__ = '0.1'
"""
from datetime import datetime
import calendar
from google.appengine.ext import db

class TweetUser(db.Model):
    u"""
        ツイートをしたユーザーのデータモデル
    """
    id = db.IntegerProperty()
    name = db.StringProperty()
    screen_name = db.StringProperty()
    profile_image_url_https = db.StringProperty()

class Tweet(db.Model):
    u"""
        一つのツイートを表すデータモデル
    """
    id = db.IntegerProperty()
    text = db.StringProperty(multiline=True)
    created_at = db.DateTimeProperty(auto_now_add=False)
    lang = db.StringProperty()
    retweet_count = db.IntegerProperty()
    favorite_count = db.IntegerProperty()
    timestamp_index = db.IntegerProperty()
    user = db.ReferenceProperty(TweetUser)
    tags = db.ListProperty(db.Key)

class TweetMedia(db.Model):
    u"""
        一つのツイートに含まれる media データモデル
    """
    urls = db.StringListProperty()
    media_urls_https = db.StringListProperty()
    types = db.StringListProperty()
    # 他の実装に合わせるならば、以下二つも複数持つべきだけどまぁいいか
    video_url = db.StringProperty()
    video_type = db.StringProperty()
    tweet = db.ReferenceProperty(Tweet, collection_name = 'media')
    
class TweetHistory(db.Model):
    u"""
        一つのツイートの歴史データモデル
        
        例えば、 retweet_counts[2] が記録された時間が知りたい場合
        timestamp_indexes[2] から取得したインデックスを使って
        CallHistory.unixtimestamps から調べる。
        
        つまり、 CallHistory.unixtimestamps[timestamp_indexes[2]] というような調べ方になる
    """
    retweet_counts = db.ListProperty(int, default=[])
    favorite_counts = db.ListProperty(int, default=[])
    timestamp_indexes = db.ListProperty(int, default=[])
    tweet = db.ReferenceProperty(Tweet, collection_name = 'history')

class TweetTag(db.Model):
    u"""
        ツイートに付属するタグのデータモデル
        
    """
    name = db.StringProperty()
    @property
    def tweets(self): #実体を持つのではなく、毎回クエリを実行する。
        return Tweet.all().filter('tags', self.key())

class CallHistory(db.Model):
    u"""
        呼び出し履歴データモデル
    """
    # unixtime で時刻を保持する
    unixtimestamps = db.ListProperty(long, default=[])
    # timestamps の長さをカウントすれば出せるはずなので冗長？
    # 現状はカウントの手間を節約する程度の意味しかない
    timestamp_count = db.IntegerProperty(default=0)

class StoreTrendsTweet(db.Model):
    u"""
        トレンドツイートを保持する文字列を保存するデータモデル
    """
    text = db.TextProperty(default='')

def get_timestamp_count():
    u"""
        現在の呼び出し回数を取得する
    """
    callhistory = None
    for c in CallHistory.all():
        callhistory = c
    if callhistory == None:
        callhistory = CallHistory()
    return callhistory.timestamp_count

def timestamp():
    u"""
        現在時刻を呼び出し時刻に登録し、カウンターを進める
    """
    callhistory = None
    for c in CallHistory.all():
        callhistory = c
    if callhistory == None:
        callhistory = CallHistory()
    callhistory.unixtimestamps.append(calendar.timegm(datetime.utcnow().timetuple()))
    callhistory.timestamp_count = callhistory.timestamp_count + 1
    callhistory.put()

def entry_tweet(tweet_json, timestamp_count):
    u"""
        Datastore にツイートを登録、または更新する
        @param tweet_json 保存する JSON 形式ツイートデータ（APIから取得した JSON をパースして、そのまま渡してください）
    """
    t = tweet_json
    # retweeted_status があれば誰かのリツイートであるので、元のツイートを取得する
    if 'retweeted_status' in tweet_json:
        t = tweet_json['retweeted_status']
    
    user = update_user(t)
    tweet = update_tweet(user, t, timestamp_count)
    media = update_media(tweet, t)
    history = update_history(tweet, t, timestamp_count)

def update_tweet(user, tweet_json, timestamp_count):
    u"""
        ツイートを Datastore に保存する
        @param tweet_json 保存する JSON 形式ツイートデータ（APIから取得した JSON をパースして、そのまま渡してください）
    """
    tweet = get_tweet(tweet_json['id'])
    if tweet == None:
        tweet = Tweet()
    tweet.id = tweet_json['id']
    tweet.text = tweet_json['text']
    # "Wed Nov 19 12:05:40 +0000 2014" -> '%a %b %d %H:%M:%S %z %Y'
    # http://docs.python.jp/2/library/datetime.html#strftime-strptime
    # %z は環境により対応していないことがあるようなので、カットする
    # カットした後、捨てるのではなくタイムゾーンの値を計算した方がいいかも？
    l = tweet_json['created_at'].split()
    tweet.created_at = datetime.strptime((' '.join(l[0:4]) + ' ' + l[5]), '%a %b %d %H:%M:%S %Y')
    tweet.lang = tweet_json['lang']
    tweet.retweet_count = tweet_json['retweet_count']
    tweet.favorite_count = tweet_json['favorite_count']
    tweet.timestamp_index = timestamp_count
    tweet.user = user
    tweet.put()
    return tweet

def update_user(tweet_json):
    u"""
        ツイートに含まれるユーザー情報を Datastore に保存する
        @param tweet 紐付けるツイートデータモデル
        @param tweet_json 保存する JSON 形式ツイートデータ（APIから取得した JSON をパースして、そのまま渡してください）
    """
    user = db.Query(TweetUser).filter('id =', tweet_json['user']['id']).get()
    if user == None:
        user = TweetUser()
    else:
        # 変更されていないなら再書き込みを行わない
        if not is_modify_user(user, tweet_json):
            return user
    user.id = tweet_json['user']['id']
    user.name = tweet_json['user']['name']
    user.screen_name = tweet_json['user']['screen_name']
    user.profile_image_url_https = tweet_json['user']['profile_image_url_https']
    user.put()
    return user

def is_modify_user(user, tweet_json):
    u""" 変更されているかを判定する """
    if user.id != tweet_json['user']['id']:
        return True
    if user.name != tweet_json['user']['name']:
        return True
    if user.screen_name == tweet_json['user']['screen_name']:
        return True
    if user.profile_image_url_https == tweet_json['user']['profile_image_url_https']:
        return True
    return False

def update_media(tweet, tweet_json):
    u"""
        ツイートに含まれる media を Datastore に保存する
        @param tweet 紐付けるツイートデータモデル
        @param tweet_json 保存する JSON 形式ツイートデータ（APIから取得した JSON をパースして、そのまま渡してください）
    """
    entities = None
    if 'extended_entities' in tweet_json:
        entities = tweet_json['extended_entities']
    elif 'entities' in tweet_json:
        entities = tweet_json['entities']
    else:
        return None
    
    if not 'media' in entities:
        return None
    
    media = tweet.media.get()
    if media == None:
        media = TweetMedia()
    else:
        # media は新規作成時以外変更されないと思うので
        # 再更新処理は行わない
        return media
    urls = []
    media_urls_https = []
    types = []
    video_type = None
    video_url = None
    for m in entities['media']:
        urls.append(m['url'])
        media_urls_https.append(m['media_url_https'])
        types.append(m['type'])
        # 以下の実装は video_url, video_type が上書きされ続けて
        # 最後の値が入ることになるが、おそらく video_info はひとつしかないし
        # variants もひとつだろうから、この実装で十分
        if 'video_info' in m:
            video_types = []
            video_urls = []
            for v in m['video_info']['variants']:
                video_url = v['url']
                video_type = v['content_type']
    media.urls = urls
    media.media_urls_https = media_urls_https
    media.types = types
    media.video_type = video_type
    media.video_url = video_url
    media.tweet = tweet
    media.put()
    return media

def update_history(tweet, tweet_json, timestamp_count):
    u"""
        ツイートの歴史を Datastore に保存する
        @param tweet 紐付けるツイートデータモデル
        @param tweet_json 保存する JSON 形式ツイートデータ（APIから取得した JSON をパースして、そのまま渡してください）
    """
    history = tweet.history.get()
    if history == None:
        history = TweetHistory()
    history.retweet_counts.append(tweet_json['retweet_count'])
    history.favorite_counts.append(tweet_json['favorite_count'])
    history.timestamp_indexes.append(timestamp_count)
    history.tweet = tweet
    history.put()
    return history

def get_from_key(key):
    return db.get(key)

def get_tweet(id):
    u"""
        Datastore からツイートを取得する
        @param id 取得するツイートの ID
    """
    return db.Query(Tweet).filter('id =', id).get()

def get_tweetuser(id):
    u"""
        Datastore からユーザーを取得する
        @param id 取得するユーザーの ID
    """
    return db.Query(TweetUser).filter('id =', id).get()

def get_tweets():
    return Tweet.all()
    
def get_tweets_query():
    return db.Query(Tweet)

def get_tweets_key():
    return db.Query(Tweet).count()
    
def get_call_history():
    return db.Query(CallHistory).get()

def get_tweets_from_user(user):
    u"""
        指定されたユーザーのツイートを取得する
        @param user ツイートを取得するユーザー
    """
    return db.Query(Tweet).filter('user =', user)

def get_timestamps(indexes):
    u"""
        渡されたインデックスリストに対応する時刻を取得する
        @param indexes インデックスリスト
    """
    timestamps = []
    callhistory = db.Query(CallHistory).get()
    for index in indexes:
        if callhistory.timestamp_count > index:
            timestamps.append(callhistory.unixtimestamps[index])
    return timestamps
    
def get_stored_trends_text():
    trends = db.Query(StoreTrendsTweet).get()
    if trends is None:
        trends = StoreTrendsTweet()
    return trends.text

def update_stored_trends_text(text):
    trends = db.Query(StoreTrendsTweet).get()
    if trends is None:
        trends = StoreTrendsTweet()
    trends.text = text
    trends.put()

def remove_all():
    for tweet in Tweet.all():
        tweet.delete()
    for user in TweetUser.all():
        user.delete()
    for media in TweetMedia.all():
        media.delete()
    for history in TweetHistory.all():
        history.delete()
    for callhistory in CallHistory.all():
        callhistory.delete()