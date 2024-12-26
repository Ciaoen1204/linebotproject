import requests
from bs4 import BeautifulSoup
import random
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# 設定你的 Channel Access Token 和 Channel Secret
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 爬取單字資料
def fetch_vocabulary():
    url = "https://wecan.tw/index.php/2018-12-02-08-34-31/2019-01-03-18-18-31/2000-basic-vocabulary"
    response = requests.get(url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    words = []
    for row in table.find_all('tr')[1:]:  # 跳過表頭
        cols = row.find_all('td')
        word = cols[0].text.strip()
        meaning = cols[1].text.strip()
        # 去除單字前面的數字和點
        word = ''.join([i for i in word if not i.isdigit() and i != '.']).strip()
        words.append(f"{word} ({meaning})")
    return words

# 定義單字列表
words = fetch_vocabulary()

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if event.message.text == "抽單字":
        selected_words = random.sample(words, 3)
        reply_text = "今日單字:\n" + "\n".join(selected_words)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )

if __name__ == "__main__":
    app.run()