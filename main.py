# coding:utf-8
"""`main` is the top level module for your Bottle application."""
# import the Bottle framework
from bottle import Bottle, static_file, url, request
from bottle import jinja2_template, Jinja2Template
# import user files
from my.db import datastore
import common
import api
# import debug code
import debug

# Create the Bottle WSGI application.
bottle = Bottle()
# 別ファイルの API 部分をマージ
bottle.merge(api.apis)

# static なファイルのルーティングを行う
# 以下の URL を参考に、必要なページ一つ一つを書いておく方法を取った
# http://nullege.com/codes/show/src@a@s@assessment-HEAD@engine@engine.py/35/bottle.jinja2_template
# url (旧 get_url) を使用して上手くルーティングする方法もあるようだけど
# http://symfoware.blog68.fc2.com/blog-entry-1069.html
# 上手く動作しなかった
@bottle.route('/static/<filepath:path>')
@bottle.route('/tweet/static/<filepath:path>')
@bottle.route('/user/static/<filepath:path>')
@bottle.route('/ranking/static/<filepath:path>')
@bottle.route('/users/static/<filepath:path>')
@bottle.route('/contact/static/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root='static')
@bottle.route('/user/<id>/static/<filepath:path>')
def server_static(id, filepath):
    return static_file(filepath, root='static')
    
Jinja2Template.defaults = {
    'title': u'まとめったー',
}

def paginate(page, count, per_page):
    u""" ページネーション処理 """
    num_page = page
    if num_page <= 0:
        num_page = 1
    max_page = count / per_page
    if (count % per_page != 0):
        max_page += 1
    # ページネーション用の設定
    PAGINATION_NUM = 5
    pages = []
    start_page = num_page - 2
    if num_page + (PAGINATION_NUM-1) > max_page:
        start_page = max_page - (PAGINATION_NUM-1)
    while len(pages) <= PAGINATION_NUM:
        if start_page > 0:
            pages.append(start_page)
        if start_page > max_page:
            break
        start_page = start_page + 1
    previous_page = max(pages[0] - 2, 1)
    next_page = min(pages.pop(), max_page)
    
    return {'pages':pages, 'current_page':num_page - 1, 'previous_page':previous_page, 'next_page':next_page }

@bottle.route('/')
def home():
    u""" HOME 画面を表示 """
    tags = []
    tags.append({'name':u'これはすごい', 'point':100})
    tags.append({'name':u'猫', 'point':80})
    tags.append({'name':u'かわいい', 'point':60})
    tags.append({'name':u'ひどい', 'point':90})
    tags.append({'name':u'ワロタｗｗｗ', 'point':60})

    recommend_tweet = api.most_popular(days=1, limit=1)[0]
    tweets, count = api.newer(limit=12)
    return jinja2_template('html/main.html', {'tags':tags, 'recommend_tweet':recommend_tweet, 'tweets':tweets})

@bottle.route('/<page:int>')
def newer_page(page):
    u""" 新着ツイートをもっと見る 画面を表示 """
    PAGE_MAX = 12
    tweets, count = api.newer(offset=(PAGE_MAX * page), limit=PAGE_MAX)
    # HOME 画面で PAGE_MAX 個表示しているので、数を引いておく
    pagination = paginate(page, count - PAGE_MAX, PAGE_MAX)
    return jinja2_template('html/newer.html', {'tweets':tweets, 'pagination':pagination})
    return str(count / PAGE_MAX)

@bottle.route('/tweet/<id:int>')
def tweet_page(id):
    u""" 個別ツイート画面を表示 """
    # ID からツイートを取得する
    tweet = api.tweet_with_history(id)
    tweets, count = api.user_newer(tweet['user']['id'], limit=4)
    # 表示中のツイートと一致するものは消す
    for other_tweet in tweets[:]: 
        if other_tweet['id'] == tweet['id']:
            tweets.remove(other_tweet)
    # 一致しない場合、一つ多くなっているので削除
    if len(tweets) == 4:
        del tweets[3]
    return jinja2_template('html/tweet.html', {'tweet':tweet, 'tweets': tweets})

@bottle.route('/user/<id:int>')
@bottle.route('/user/<id:int>/<page:int>')
def user_page(id, page = 1):
    u""" ユーザーツイート一覧画面を表示 """
    PAGE_MAX = 12
    user = api.tweet_user(id)
    tweets, count = api.user_newer(id, offset=(PAGE_MAX * (page - 1)), limit=PAGE_MAX)
    pagination = paginate(page, count, PAGE_MAX)
    return jinja2_template('html/user.html', {'tweets':tweets, 'user':user, 'pagination':pagination})

@bottle.route('/ranking/today')
def ranking_today_page():
    u""" 今日の人気ツイートを表示 """
    tweets = api.most_popular(days=1, limit=10)
    return jinja2_template('html/ranking.html', {'type': 0, 'tweets':tweets})

@bottle.route('/ranking/week')
def ranking_week_page():
    u""" 今週の人気ツイートを表示 """
    tweets = api.most_popular(days=7, limit=10)
    return jinja2_template('html/ranking.html', {'type': 1, 'tweets':tweets})

@bottle.route('/ranking/month')
def ranking_month_page():
    u""" 今月の人気ツイートを表示 """
    tweets = api.most_popular(days=30, limit=10)
    return jinja2_template('html/ranking.html', {'type': 2, 'tweets':tweets})

@bottle.route('/users/today')
def ranking_users_today_page():
    u""" 今日の人気ユーザーを表示 """
    users = api.most_popular_users(days=1, limit=10)
    return jinja2_template('html/users.html', {'type': 0, 'users':users})

@bottle.route('/users/week')
def ranking_users_week_page():
    u""" 今週の人気ユーザーを表示 """
    users = api.most_popular_users(days=7, limit=10)
    return jinja2_template('html/users.html', {'type': 1, 'users':users})

@bottle.route('/users/month')
def ranking_users_month_page():
    u""" 今月の人気ユーザーを表示 """
    users = api.most_popular_users(days=30, limit=10)
    return jinja2_template('html/users.html', {'type': 2, 'users':users})

@bottle.route('/about')
def about_page():
    u""" このサイトについてを表示 """
    return jinja2_template('html/about.html')

@bottle.route('/contact')
@bottle.route('/contact/<message>')
def contact_page(message=''):
    u""" お問い合わせページを表示 """
    return jinja2_template('html/contact.html', {'message': message})

# Define an handler for 404 errors.
@bottle.error(404)
def error_404(error):
    """Return a custom 404 error."""
    return jinja2_template('html/error/404.html')

# Define an handler for 500 errors.
@bottle.error(500)
def error_500(error):
    """Return a custom 500 error."""
    return jinja2_template('html/error/500.html')
