import random
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# Flask 應用初始化
app = Flask(__name__)

# Line Bot 設定
line_bot_api = LineBotApi(channel_access_token='JAIpBs7Lx2UxUm/RlmO6vMOlKb3GeYbgj9YTjPdD8Ythb4G9Uwz384KuURyJxHHfIVg/gmiZW7myjvVX+DV9nliTvHxqHXpr5zZ3E+OeymmPuijw2Yh7bdRm/nZCh9T7+4linADxhOp1MlnuX6Ms+wdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler(channel_secret='ea1e57cc2f7e7f996f63c09502340b51')

# 單字題庫
words = ["apple", "orange", "banana", "grape", "cherry"]

# 全域變數儲存正確答案
correct_answer = None

# 隨機生成克漏字題目
def generate_cloze(word):
    hidden = list(word)
    # 只隱藏中間部分的字母，首尾保留
    for i in range(1, len(word) - 1):
        hidden[i] = "_"
    return "".join(hidden)

# 設置 /callback 路徑
@app.route("/callback", methods=["POST"])
def callback():
    # 確保來自 LINE 平台的請求
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# 處理用戶訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    global correct_answer  # 使用全域變數來儲存答案
    user_message = event.message.text.strip().lower()

    if user_message == "開始遊戲":
        correct_answer = random.choice(words)  # 隨機選擇一個單字
        cloze = generate_cloze(correct_answer)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"請填寫完整單字：{cloze}")
        )

    elif correct_answer:
        if user_message == correct_answer:
            response = "正確！恭喜你！"
            correct_answer = None  # 重置答案
        else:
            response = f"錯誤！正確答案是：{correct_answer}"
            correct_answer = None  # 重置答案

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response)
        )
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請先輸入「開始遊戲」來開始遊戲！")
        )

if __name__ == "__main__":
    app.run(debug=True)
