from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv
import google.generativeai as generativeai
import os

# 載入環境變數
load_dotenv()

# 設定 LINE API
line_bot_api = LineBotApi(os.getenv('line_bot_api'))
handler = WebhookHandler(os.getenv('handler'))

# 設定 Generative AI API
generativeai.configure(api_key=os.getenv('key'))

# 初始化 Flask
app = Flask(__name__)

@app.route("/callback", methods=['POST'])
def callback():
    # 確認 LINE 的簽名
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# 處理用戶訊息事件
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text  # 用戶傳送的訊息
    try:
        # 使用 Generative AI 生成回應
        response = generativeai.GenerativeModel("gemini-2.0-flash-exp").generate_content(user_message)
        reply = response.text
    except Exception as e:
        reply = f"抱歉，無法生成回應: {e}"

    # 回應用戶
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
