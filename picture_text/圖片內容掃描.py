from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, ImageMessage, TextMessage
import requests
from io import BytesIO
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# LINE Bot 配置
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))


# 初始化 Azure 服務
computervision_client = ComputerVisionClient(os.getenv('COMPUTER_VISION_ENDPOINT'), CognitiveServicesCredentials(os.getenv('COMPUTER_VISION_SUBSCRIPTION_KEY')))

@app.route("/callback", methods=["POST"])
def callback():
    """處理 LINE Webhook 回調"""
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    """處理用戶發送的圖片"""
    try:
        # 獲取圖片内容
        message_content = line_bot_api.get_message_content(event.message.id)
        image_data = BytesIO(message_content.content)

        # 使用 Azure OCR 提取圖片中的文字
        text = image_to_text(image_data)
        if text:
            # 返回提取的文字
            line_bot_api.reply_message(event.reply_token, TextMessage(text=text))
        else:
            line_bot_api.reply_message(event.reply_token, TextMessage(text="未能提取圖片中的文字"))

    except Exception as e:
        print(f"處理圖片時時出错: {e}")
        line_bot_api.reply_message(event.reply_token, TextMessage(text="發生錯誤，請稍後再試"))

def image_to_text(image_data):
    """從圖片中提取文字"""
    try:
        # 使用 Azure Computer Vision API 進行 OCR 識別
        ocr_result = computervision_client.recognize_printed_text_in_stream(image_data)

        # 處理结果
        text = ""
        for region in ocr_result.regions:
            for line in region.lines:
                text += " ".join([word.text for word in line.words]) + "\n"
        
        return text.strip()
    except Exception as e:
        print(f"錯誤: {e}")
        return None

if __name__ == "__main__":
    app.run(port=5000)
