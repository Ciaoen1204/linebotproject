import os
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import schedule
import time
import threading
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# 設定你的 Line Bot API 和 Webhook Handler
line_bot_api = LineBotApi(os.getenv('LineBotApi'))
handler = WebhookHandler(os.getenv('secret'))

def get_bbc_news_links():
    url = 'https://www.bbc.com/news'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if href.startswith('/news/articles/'):
            full_url = 'https://www.bbc.com' + href
            return full_url

def send_daily_article():
    news_link = get_bbc_news_links()
    if news_link:
        reply = news_link
    else:
        reply = "No articles found."
    line_bot_api.push_message(os.getenv("user_id"), TextSendMessage(text=reply))

@app.route("/callback", methods=['POST'])
def callback():
    # 獲取請求標頭中的簽名
    signature = request.headers['X-Line-Signature']

    # 獲取請求正文
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # 驗證簽名
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text)
    )

def schedule_daily_message():
    schedule.every().day.at("17:47").do(send_daily_article)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # 啟動排程執行緒
    threading.Thread(target=schedule_daily_message).start()
    # 啟動 Flask 伺服器
    app.run()