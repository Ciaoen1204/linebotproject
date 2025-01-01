import requests
from bs4 import BeautifulSoup
import random
import csv
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
from dotenv import load_dotenv
load_dotenv()

# Flask 應用初始化
app = Flask(__name__)

# Line Bot 設定
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 從 CSV 檔案讀取單字題庫和翻譯
def load_words_from_csv(filepath):
    words = []
    translations = {}
    with open(filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            word, translation = row
            words.append(word)
            translations[word] = translation
    return words, translations

# 確保檔案路徑正確
csv_filepath = os.path.join(os.path.dirname(__file__), 'vocabulary.csv')
words, translations = load_words_from_csv(csv_filepath)

# 全域變數儲存正確答案
correct_answer = None

# 隨機生成克漏字題目
def generate_cloze(word):
    hidden = list(word)
    # 只隱藏中間部分的字母，首尾保留
    for i in range(1, len(word) - 1):
        hidden[i] = '_'
    return ''.join(hidden)

# 處理 Line Bot 訊息
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global correct_answer
    user_message = event.message.text.lower()

    if user_message == "開始遊戲":
        correct_answer = random.choice(words)
        cloze = generate_cloze(correct_answer)
        translation = translations[correct_answer]
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"請猜這個單字: {cloze} ({translation})")
        )
    elif user_message == correct_answer:
        translation = translations[correct_answer]
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"答對了！這個單字是：{correct_answer}，中文是：{translation}")
        )
        correct_answer = None
    elif correct_answer is None:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請先輸入「開始遊戲」來開始遊戲！")
        )
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="答錯了，再試一次。")
        )
    

if __name__ == "__main__":
    app.run()