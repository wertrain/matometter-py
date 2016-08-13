# coding:utf-8
u"""
    Twitter API ラッパー

    このモジュールは Twitter API をラップして使いやすくしたものです。
    現状は、コンシューマーキーなどはソースコードに埋め込まれています。

    __author__ = 'wertrain'
    __version__ = '0.1'
"""
# import Python standard lib
import json
import pprint
#import the requests_oauthlib
#from requests_oauthlib import OAuth1Session
from appengine_oauth import oauth
import secret

def get_friends(**others):
    u"""
        フォロー中のユーザーを取得
        @param others それ以外のパラメータ
        @return 取得結果（辞書型）
        ['status_code']: ステータスコード
        ['text']: レスポンステキスト（取得に失敗すれば空）
    """
    URL = "https://api.twitter.com/1.1/friends/ids.json"
    params = {}
    params.update(others)

    client = oauth.TwitterClient(secret.CONSUMER_KEY, secret.CONSUMER_SECRET, None)

    result = client.make_request(
                    URL,
                    token=secret.ACCESS_TOKEN,
                    secret=secret.ACCESSS_TOKEN_SECERT)
                    #additional_params=params
                    #protected=True,
                    #method='GET')
    response = []
    if result.status_code == 200:
        # レスポンスはJSON形式なので parse する
        response = json.loads(result.content)
    return { 'status_code':result.status_code, 'text':response }

def home_timeline(count=20, **others):
    u"""
        タイムラインを取得
        @param count 取得するツイート数(デフォルト:20)
        @param others それ以外のパラメータ
        @return 取得結果（辞書型）
            ['status_code']: ステータスコード
            ['timeline']: ツイートリスト（取得に失敗すれば空）
    """
    URL = "https://api.twitter.com/1.1/statuses/home_timeline.json"
    params = {'count':count}
    params.update(others)

    client = oauth.TwitterClient(secret.CONSUMER_KEY, secret.CONSUMER_SECRET, None)

    result = client.make_request(
                    URL,
                    token=secret.ACCESS_TOKEN,
                    secret=secret.ACCESSS_TOKEN_SECERT,
                    additional_params=params)

    timeline = []
    if result.status_code == 200:
        # レスポンスはJSON形式なので parse する
        timeline = json.loads(result.content)
    return { 'status_code':result.status_code, 'timeline':timeline }

def search_tweets(q='', count=50, lang='ja', result_type='mixed', **others):
    u"""
        ツイートを検索
        @param q クエリ[必須]
        @param count 取得するツイート数(デフォルト:50)
        @param lang 取得対象言語(デフォルト:ja)
        @param result_type タイプ mixed,recent,popular のいずれか(デフォルト:mixed)
        @param others それ以外のパラメータ
        @return 取得結果（辞書型）
            ['status_code']: ステータスコード
            ['timeline']: ツイートリスト（取得に失敗すれば空）
    """
    URL = "https://api.twitter.com/1.1/search/tweets.json"
    params = {'q':q, 'count':count, 'lang':lang, 'result_type':result_type}
    params.update(others)

    client = oauth.TwitterClient(secret.CONSUMER_KEY, secret.CONSUMER_SECRET, None)

    result = client.make_request(
                    URL,
                    token=secret.ACCESS_TOKEN,
                    secret=secret.ACCESSS_TOKEN_SECERT,
                    additional_params=params)

    timeline = []
    if result.status_code == 200:
       # レスポンスはJSON形式なので parse する
       timeline = json.loads(result.content)
    return { 'status_code':result.status_code, 'timeline':timeline['statuses'] }

def trends_from(woeid=23424856):
    u"""
        指定された WOEID 地域のトレンドワードを取得する
        @param woeid 地域ID（デフォルト：23424856<日本>）
        @return 取得結果（辞書型）
            ['status_code']: ステータスコード
            ['trends']: トレンドワードリスト（取得に失敗すれば空）
    """
    URL = "https://api.twitter.com/1.1/trends/place.json"
    params = {'id':woeid}

    client = oauth.TwitterClient(secret.CONSUMER_KEY, secret.CONSUMER_SECRET, None)

    result = client.make_request(
                    URL,
                    token=secret.ACCESS_TOKEN,
                    secret=secret.ACCESSS_TOKEN_SECERT,
                    additional_params=params)

    trends = []
    if result.status_code == 200:
        # レスポンスはJSON形式なので parse する
        trends = json.loads(result.content)
    return { 'status_code':result.status_code, 'trends':trends }

def lookup_tweets(ids, **others):
    u"""
        複数のツイートを取得
        @param ids 取得するツイートのID配列(最大:100個)
        @param others それ以外のパラメータ
        @return 取得結果（辞書型）
            ['status_code']: ステータスコード
            ['statuses']: ツイートリスト（取得に失敗すれば空）
    """
    URL = "https://api.twitter.com/1.1/statuses/lookup.json"
    params = {'id':','.join(ids)}
    params.update(others)

    client = oauth.TwitterClient(secret.CONSUMER_KEY, secret.CONSUMER_SECRET, None)

    result = client.make_request(
                    URL,
                    token=secret.ACCESS_TOKEN,
                    secret=secret.ACCESSS_TOKEN_SECERT,
                    additional_params=params)

    statuses = []
    if result.status_code == 200:
        # レスポンスはJSON形式なので parse する
        statuses = json.loads(result.content)
    return { 'status_code':result.status_code, 'statuses':statuses }

def user_timeline(user_id, count=30, **others):
    u"""
        指定ユーザーのタイムラインを取得
        @param user_id 取得するユーザーのID
        @param others それ以外のパラメータ
        @return 取得結果（辞書型）
            ['status_code']: ステータスコード
            ['timeline']: ツイートリスト（取得に失敗すれば空）
    """
    URL = "https://api.twitter.com/1.1/statuses/user_timeline.json"
    params = {'user_id': user_id, 'count': count}
    params.update(others)

    client = oauth.TwitterClient(secret.CONSUMER_KEY, secret.CONSUMER_SECRET, None)

    result = client.make_request(
                    URL,
                    token=secret.ACCESS_TOKEN,
                    secret=secret.ACCESSS_TOKEN_SECERT,
                    additional_params=params)

    timeline = []
    if result.status_code == 200:
        # レスポンスはJSON形式なので parse する
        timeline = json.loads(result.content)
    return { 'status_code':result.status_code, 'timeline':timeline }

def retweet(id, **others):
    u"""
        リツイート
        @param id リツイートするツイートのID
        @param others それ以外のパラメータ
        @return 取得結果（辞書型）
            ['status_code']: ステータスコード
    """
    URL = "https://api.twitter.com/1.1/statuses/retweet/" + str(id) + ".json"
    params = {}
    params.update(others)

    client = oauth.TwitterClient(secret.CONSUMER_KEY, secret.CONSUMER_SECRET, None)

    result = client.make_request(
                    URL,
                    token=secret.ACCESS_TOKEN,
                    secret=secret.ACCESSS_TOKEN_SECERT,
                    additional_params=params,
                    protected=True,
                    method='POST')

    return { 'status_code':result.status_code }

#def home_timeline_ex(count = 20):
#    u"""
#        タイムラインを取得
#        @param count 取得するツイート数
#        @return 取得結果（辞書型）
#            ['status_code']: ステータスコード
#            ['timeline']: ツイートリスト（取得に失敗すれば空）
#    """
#    URL = "https://api.twitter.com/1.1/statuses/home_timeline.json"
#    MAX_COUNT = 200 # 一度に取得できる最大
#    MAX_TWEET_NUM = 800 # 取得できる数の最大
#    
#    amount = count
#    while amount >= 0:
#        param_count = amount
#        if amount > MAX_COUNT:
#            param_count = MAX_COUNT
#        params = { 'count':param_count }
#        
#        session = OAuth1Session(secret.CONSUMER_KEY, secret.CONSUMER_SECRET, secret.ACCESS_TOKEN, secret.ACCESSS_TOKEN_SECERT)
#        req = session.get(URL, params = params)
#
#        timeline = []
#        if req.status_code == 200:
#            # レスポンスはJSON形式なので parse する
#            timeline = json.loads(req.text)
#            
#        return { 'status_code':req.status_code, 'timeline':timeline }

#def home_timeline(count=20, **others):
#    u"""
#        タイムラインを取得
#        @param count 取得するツイート数(デフォルト:20)
#        @param others それ以外のパラメータ
#        @return 取得結果（辞書型）
#            ['status_code']: ステータスコード
#            ['timeline']: ツイートリスト（取得に失敗すれば空）
#    """
#    URL = "https://api.twitter.com/1.1/statuses/home_timeline.json"
#    params = {'count':count}
#    params.update(others)
#
#    session = OAuth1Session(secret.CONSUMER_KEY, secret.CONSUMER_SECRET, secret.ACCESS_TOKEN, secret.ACCESSS_TOKEN_SECERT)
#    req = session.get(URL, params = params)
#
#    timeline = []
#    if req.status_code == 200:
#        # レスポンスはJSON形式なので parse する
#        timeline = json.loads(req.text)
#    return { 'status_code':req.status_code, 'timeline':timeline }

#def search_tweets(q='', count=50, lang='ja', result_type='mixed', **others):
#    u"""
#        ツイートを検索
#        @param q クエリ[必須]
#        @param count 取得するツイート数(デフォルト:50)
#        @param lang 取得対象言語(デフォルト:ja)
#        @param result_type タイプ mixed,recent,popular のいずれか(デフォルト:mixed)
#        @param others それ以外のパラメータ
#        @return 取得結果（辞書型）
#            ['status_code']: ステータスコード
#            ['timeline']: ツイートリスト（取得に失敗すれば空）
#    """
#    URL = "https://api.twitter.com/1.1/search/tweets.json"
#    params = {'q':q, 'count':count, 'lang':lang, 'result_type':result_type}
#    params.update(others)
#
#    session = OAuth1Session(secret.CONSUMER_KEY, secret.CONSUMER_SECRET, secret.ACCESS_TOKEN, secret.ACCESSS_TOKEN_SECERT)
#    req = session.get(URL, params = params)
#
#    timeline = []
#    if req.status_code == 200:
#        # レスポンスはJSON形式なので parse する
#        timeline = json.loads(req.text)
#    return { 'status_code':req.status_code, 'timeline':timeline['statuses'] }

#def get_friends(**others):
#    u"""
#        フォロー中のユーザーを取得
#        @param others それ以外のパラメータ
#        @return 取得結果（辞書型）
#            ['status_code']: ステータスコード
#            ['text']: レスポンステキスト（取得に失敗すれば空）
#    """
#    URL = "https://api.twitter.com/1.1/friends/ids.json"
#    params = {}
#    params.update(others)
#    
#    session = OAuth1Session(secret.CONSUMER_KEY, secret.CONSUMER_SECRET, secret.ACCESS_TOKEN, secret.ACCESSS_TOKEN_SECERT)
#    req = session.get(URL, params = params)
#
#    response = []
#    if req.status_code == 200:
#        # レスポンスはJSON形式なので parse する
#        response = json.loads(req.text)
#    return { 'status_code':req.status_code, 'text':response }
