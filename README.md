まとめったー
======================
Twitter の人気投稿を自動収集し、表示する Web サービス。  
URL: [まとめった](http://matometter.com) 

開発について
------------------

### 開発環境
* Google App Engine (Python)

### 使用しているライブラリ

* bottle(0.11.6)
* jinja(2-2.7.3)
* oauthlib
* requests
* requests_oauthlib

使用しているライブラリはリポジトリ内に含まれています。  
別途 Python SDK にインストールが必要です。  
インストールが必要なライブラリは下記を参照してください。

### 必要なライブラリのインストール方法

インストールには `` pip `` を使用するのが便利です。

    pip install oauthlib
    pip install requests
    pip install requests_oauthlib
    
### ローカルで実行する際の注意点 (最新版では不要)

このアプリをローカル環境で実行する際、SSLに関するエラーが表示されます。
この問題については下記のページを参考にしてください。

[“ImportError: No module named _ssl” with dev_appserver.py from Google App Engine](http://stackoverflow.com/questions/16192916/importerror-no-module-named-ssl-with-dev-appserver-py-from-google-app-engine)

> add "_ssl" and "_socket" keys to the dictionary _WHITE_LIST_C_MODULES in /path-to-gae-sdk/google/appengine/tools/devappserver2/python/sandbox.py
> Replace the socket.py file provided by google in /path-to-gae-sdk/google/appengine/dis27 from the socket.py file from your Python framework.

以下の手順を行います。
1. google/appengine/tools/devappserver2/python/sandbox.py の _WHITE_LIST_C_MODULES に _ssl と _socket の記述を追加する
2. google/appengine/dis27 の socket.py を Python SDK の socket.py で置き換える

