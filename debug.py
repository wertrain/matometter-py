# coding:utf-8

from my.db import datastore
from my.twitter import api
from google.appengine.ext import db

def add_latest_tweets_to_datastore():
    result = api.home_timeline(count=200)
    timestamp_count = datastore.get_timestamp_count()
    ids = {}
    if result['status_code'] == 200:
        for tweet in result['timeline']:
            t = tweet
            # retweeted_status があれば誰かのリツイートであるので、元のツイートを取得する
            if 'retweeted_status' in tweet:
                t = tweet['retweeted_status']
            # id を保存して、一回の呼び出しでは同じ投稿は一度しか書き込まないようにする
            id = str(t['id'])
            if not ids.has_key(id):
                ids[id] = True
                datastore.entry_tweet(tweet, timestamp_count)
        datastore.timestamp()
    else:
        write_tmp(str(result['status_code']))

def add_popular_tweets_to_datastore():
    result = api.search_tweets(q='RT', count=100, result_type='popular')
    if result['status_code'] == 200:
        for tweet in result['timeline']:
            datastore.entry_tweet(tweet)

class Tmp(db.Model):
    text = db.TextProperty()
    
def write_tmp(text):
    for tmp in Tmp.all():
        tmp.delete()
    tmp = Tmp()
    tmp.text = text
    tmp.put()