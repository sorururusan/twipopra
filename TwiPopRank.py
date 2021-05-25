from flask import Flask, request,render_template,send_from_directory
from flask_paginate import Pagination, get_page_parameter
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
import os
import twitter
import tweepy
import sqlite3

#Twitter APIのキーとトークン
consumer_key='D6OPHpSUEAOOnsCzxQ0y01aHH'
consumer_secret='5AkQwsYKTpuy6ZIzqnk5bzjZKX5HnIjDeQQnSUfXHK93ucGhP6'
access_token_key='209906590-Psr5JSXhFlMqvPH1ktoKDrjDquRvF0C9r1MuXufJ'
access_token_secret='HWEBXuqc7Agil7YENZbspbzzN4SB1RZCTEgYkQwSlF7Qi'

app = Flask(__name__)

#DB作成or接続
dbname = 'tweets.db'
conn = sqlite3.connect(dbname)
#カーソルオブジェクト作成
cur = conn.cursor()

#accountsテーブル作成
#項目は自動で振られるidとtwiidとname
cur.execute('CREATE TABLE IF NOT EXISTS tweets(id STRING,\
                                                name STRING,\
                                                screen_name STRING,\
                                                retweet INTEGER,\
                                                favorite INTEGER,\
                                                profile_image_url STRING,\
                                                text STRING,\
                                                time String,\
                                                img_url STRING )')


#ツイートボタン作成
def createTweetbtn(string):
    tweet = string
    tweetbtn = "\
    <div class='twitter'>\
    <a href='//twitter.com/share' class='twitter-share-button' data-text='" + tweet + "'  data-lang='ja'>\
        入力内容を呟く\
    </a>\
    </div>\
    <script async src='https://platform.twitter.com/widgets.js' charset='utf-8'></script>" 
    return tweetbtn

#css反映のための関数
@app.context_processor
def add_staticfile():
    def staticfile_cp(fname):
        path = os.path.join(app.root_path, 'static', fname)
        mtime =  str(int(os.stat(path).st_mtime))
        return './static/' + fname + '?v=' + str(mtime)
    return dict(staticfile=staticfile_cp)

#twitterモジュールでの接続
def getTwitterAPI():
    api = twitter.Api(consumer_key=consumer_key,
                  consumer_secret=consumer_secret,
                  access_token_key=access_token_key,
                  access_token_secret=access_token_secret
                 )
    return api

#tweepyモジュールでの接続
def authTwitter():
  auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
  auth.set_access_token(access_token_key, access_token_secret)
  api = tweepy.API(auth, wait_on_rate_limit = True) # API利用制限にかかった場合、解除まで待機する
  return(api)

#公式アカウント集積
def colectTweets():
    #1時間ごとに取得
    file = open('timelog.txt', 'rt')
    year,month,day,hour,min = file.read().split()
    file.close()
    today = datetime.now()

    #DB接続
    conn = sqlite3.connect(dbname)
    #カーソルオブジェクト作成
    cur = conn.cursor()

    #TwitterAPIオブジェクト取得
    #api = getTwitterAPI() #twitterモジュール
    api = authTwitter() #tweepyモジュール
    table = ""
    if today.year > int(year) or today.month > int(month) or today.day > int(day) or today.hour > int(hour) or today.minute > int(min)+30:    
        #テーブル初期化
        cur.execute("DELETE FROM tweets")

        #日本語の公式アカウントかつ1000ファボ以上のアカウントを検索
        search_str = "filter:verified lang:ja min_faves:1000 since:" + str(today.year) + "-" + str(today.month) + "-" + str(today.day-1)
        #api.GetSearch #tweetモジュール
        #found = api.GetSearch(term=search_str,count=100,result_type='popular') #tweetモジュール
        found = tweepy.Cursor(api.search, q = search_str,  # APIの種類と検索文字列
                         include_entities = True,         # 省略されたリンクを全て取得
                         tweet_mode = 'extended',         # 省略されたツイートを全て取得
                         lang = 'ja').items(100)          # 日本のツイートのみ100件取得

        table = ""
        maxid = 0
        maxcount = 100

        for f in found:
            if maxid > f.id or maxid == 0:
                maxid = f.id
                img_url = ""
            if "media" in f.entities:
                for media in f.extended_entities['media']:
                    media_url = media['media_url']
                    filename = os.path.basename(urlparse(media_url).path)
                    img_url = img_url + " " + media_url
                cur.execute( "INSERT INTO tweets(id,name,screen_name,retweet,favorite,profile_image_url,text,time,img_url) VALUES (?,?,?,?,?,?,?,?,?)",  (f.id,f.user.name,f.user.screen_name,f.retweet_count,f.favorite_count,f.user.profile_image_url,f.full_text,f.created_at,img_url) ) #full_text
            else:
                #↓上段：text 下段：full_text
                #cur.execute( "INSERT INTO tweets(id,name,screen_name,retweet,favorite,profile_image_url,text,time) VALUES (?,?,?,?,?,?,?,?)",  (f.id,f.user.name,f.user.screen_name,f.retweet_count,f.favorite_count,f.user.profile_image_url,f.text,f.created_at ) )
                cur.execute( "INSERT INTO tweets(id,name,screen_name,retweet,favorite,profile_image_url,text,time) VALUES (?,?,?,?,?,?,?,?)",  (f.id,f.user.name,f.user.screen_name,f.retweet_count,f.favorite_count,f.user.profile_image_url,f.full_text,f.created_at ) ) #full_text
            
        conn.commit()
        #ファイルに時間記録
        file = open('timelog.txt', 'wt')
        file.write(datetime.now().strftime("%Y %m %d %H %M"))
        file.close
    #DBの内容取得
    cur.execute("SELECT * FROM tweets order by favorite desc")
    tweets = cur.fetchall()
    file = open('timelog.txt', 'rt')
    year,month,day,hour,min = file.read().split()
    file.close()
    update = year + "年" + month + "月" + day + "日" + hour + ":" + min + "更新"
    return tweets,update
    
#tweetsのデータ形式は[(),(),(),...()]
#tweetsリスト要素のタプルのデータの並びは[0]id [1]name [2]screen_name [3]retweet [4]favorite [5]profile_image_url [6]text [7]time [8]img_url
def createTweetHtml(tweets,page):
    npp = 25 #1ページ当たりの表示件数
    #tweets_html = "<div class='tweet'><table class='table  table-borderless' width='100%'>"
    tweets_html = ""
    t8 = ""
    for t in tweets:
        t8=""
        if (page-1)*npp <= tweets.index(t) and tweets.index(t) < page*npp:
            text = t[6].replace("\n","<br>")
            if t[8] is None:
                t8 = ""
            else:
                text = trimurl(text)
                for url in t[8].split():
                    t8 = t8 + "<img src='" + url + "' width='100%'>"
                t8=t8.replace("http://","https://")
            text = convertTags(convertURL(text))
            #このツイートへリンク作成
            link = "<a href='https://twitter.com/" + t[2] + "/status/" + str(t[0]) +"'>このツイートへ</a>"
            # tweets_html = tweets_html + \
            #     "<tr class='back-white'><td class='rank'>" + str(tweets.index(t)+1) + "<td/><td></td></tr>" + \
            #     "<tr><td rowspan='3'><img src='" + t[5].replace("http://","https://") + "'></td><td>" + t[1] + "<a href='https://twitter.com/" + t[2] + "'> @" + t[2] + "</a></td></tr>" + \
            #     "<tr><td><span class='back-white'>" + text + "</span></td></tr>" + \
            #     "<tr><td><span class='small'>" + str(t[3]) + "リツイート　" + str(t[4]) + "いいね " + t[7] + " " + link + t8 + " </span></td></tr>"

            tweets_html = tweets_html + \
                "<span class='rank'>" + str(tweets.index(t)+1) + "</span>" + \
                "<div class='tweet'>" + \
                "<h2 class='standard'><img src='" + t[5].replace("http://","https://") + "' class='icon_img'>" + t[1] + "<a href='https://twitter.com/" + t[2] + "'> @" + t[2] + "</a></h2>" + \
                "<span class='back-white'>" + text + "</span>" + \
                "<span class='small'>" + str(t[3]) + "リツイート　" + str(t[4]) + "いいね " + t[7] + " " + link + "</span>" + t8 + \
                "</div>" + \
                "<span></span>" 


    #tweets_html = tweets_html + "</table></div>"  
    return tweets_html

#APIで取得した時間をわかりやすい形に変換する関数
def convertCreated(created_at):
    created_at = datetime.strptime(created_at, '%a %b %d %H:%M:%S %z %Y')
    created_at = created_at.astimezone(timezone(timedelta(hours=+9)))
    created_at = datetime.strftime(created_at, '%Y-%m-%d %H:%M:%S')
    return created_at

#text中のハッシュタグにリンクを付ける関数
def convertTags(text):
    s = text
    taglist=[]
    tag = ""
    while s.find("#") != -1:
        ts = s.find("#")
        s = s[ts::]
        if "<br>" in s and " " in s:
            te = min(s.find(" "),s.find("<br>"))
            tag = s[0:te]
        elif "<br>" in s:
            te = s.find("<br>")
            tag = s[0:te]
        elif " " in s:
            te = s.find(" ")
            tag = s[0:te]
        else:
            te = len(s)
            tag = s
        s = s[te::]
        taglist.append(tag)

    s = text
    ret_str=""
    for tag in taglist:
        ts = s.find(tag)
        ret_str = ret_str + s[0:ts]
        s = s[ts::]
        if "<br>" in s and " " in s:
            te = min(s.find(" "),s.find("<br>"))
        elif "<br>" in s:
            te = s.find("<br>")
        elif " " in s:
            te = s.find(" ")
        else:
            te = len(s)
        s = s[te::]
        ret_str = ret_str + tag.replace(tag,"<a href='https://twitter.com/hashtag/" + tag[1::] + "?src=hashtag_click'>" + tag + "</a>")

    ret_str = ret_str + s
    if "#" not in text:
        ret_str = text

    return ret_str

#text中のURLをリンクに変換する関数
def convertURL(text):
    s = text
    urllist=[]
    url = ""
    while s.rfind("http") != -1:
        ts = s.rfind("http")
        s = s[ts::]
        if "<br>" in s and " " in s:
            te = min(s.find(" "),s.find("<br>"))
            url = s[0:te]
        elif "<br>" in s:
            te = s.find("<br>")
            url = s[0:te]
        elif " " in s:
            te = s.find(" ")
            url = s[0:te]
        else:
            te = len(s)
            url = s
        s = s[te::]
        urllist.append(url)

    s = text
    ret_str=""
    for url in urllist:
        ts = s.rfind(url)
        ret_str = ret_str + s[0:ts]
        s = s[ts::]
        if "<br>" in s and " " in s:
            te = min(s.find(" "),s.find("<br>"))
        elif "<br>" in s:
            te = s.find("<br>")
        elif " " in s:
            te = s.find(" ")
        else:
            te = len(s)
        s = s[te::]
        ret_str = ret_str + url.replace(url,"<a href='" + url + "'>" + url + "</a>")

    ret_str = ret_str + s
    if "http" not in text:
        ret_str = text

    return ret_str

#本文末尾のURLを削除する関数
def trimurl(text):
    p = text.rfind("http")
    return text[0:p]

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static/'), 'favicon.ico', )

#500エラーハンドル
@app.errorhandler(500)
def system_error(error):    # error.descriptionでエラー時の文字列取得
    return render_template('main.html', title='500 System Error', \
                                                tweets=str(error)),500

@app.route('/')
def main():
    tweets,update = colectTweets()

    page = request.args.get(get_page_parameter(), type=int, default=1)    #ページ数（初期値：1）

    tweets_html = createTweetHtml(tweets,page)

    pagination = Pagination(page=page, total=len(tweets),  per_page=25, css_framework='bootstrap4')

    tweetbtn = createTweetbtn("")
    return render_template('main.html', title="ついぽぷら - 公式認証アカウントの人気ツイートランキング",
                                        tweetbtn=tweetbtn,
                                        tweets=tweets_html,
                                        pagination=pagination,
                                        update=update)

## おまじない
if __name__ == "__main__":
    #app.run(debug=True)
    app.run()
