import os
from dotenv import load_dotenv
load_dotenv()
import ffmpeg
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, AudioMessage, TextSendMessage
import azure.cognitiveservices.speech as speechsdk
from googletrans import Translator

app = Flask(__name__)

# LINE Bot 配置
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 設定 ffmpeg 路徑
ffmpeg_path = r"C:\Users\User\OneDrive\桌面\113-1程式\ffmpeg-master-latest-win64-gpl\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"  # 替換為您自己的 ffmpeg 路徑

# 初始化翻譯工具
translator = Translator()

# 語音識別功能
def recognize_from_audio_file(file_path):
    speech_config = speechsdk.SpeechConfig(subscription=(os.getenv("SPEECH_KEY")), region=(os.getenv("SPEECH_REGION")))
    speech_config.speech_recognition_language = "zh-CN" 

    audio_config = speechsdk.audio.AudioConfig(filename=file_path)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    result = speech_recognizer.recognize_once_async().get()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        return "No speech could be recognized."
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            return f"Error: {cancellation_details.error_details}"
        return "Speech recognition canceled."
    return "Unknown error."

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=AudioMessage)
def handle_audio_message(event):
    # 暫存檔案名稱
    audio_file_path = f"{event.message.id}.m4a"
    wav_file_path = f"{event.message.id}.wav"

    try:
        # 下載用戶語音訊息
        message_content = line_bot_api.get_message_content(event.message.id)
        with open(audio_file_path, 'wb') as fd:
            for chunk in message_content.iter_content():
                fd.write(chunk)

        # 檢查檔案是否成功下載
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"下載的音訊檔案不存在：{audio_file_path}")

        # 使用 ffmpeg 進行轉換
        try:
            ffmpeg.input(audio_file_path).output(wav_file_path).run(cmd=ffmpeg_path)
        except ffmpeg.Error as e:
            raise Exception(f"轉換檔案失敗: {e}")

        # 語音轉文字 (中文語音識別)
        recognized_text = recognize_from_audio_file(wav_file_path)

        # 翻譯文字 (將中文翻譯成英文)
        translated_text = translator.translate(recognized_text, src='zh-tw', dest='en').text

        # 回傳翻譯結果
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"中文內容: {recognized_text}\n翻譯: {translated_text}")
        )
    except Exception as e:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"處理語音時發生錯誤: {str(e)}")
        )
    finally:
        # 清理暫存檔案
        if os.path.exists(audio_file_path):
            os.remove(audio_file_path)
        if os.path.exists(wav_file_path):
            os.remove(wav_file_path)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
