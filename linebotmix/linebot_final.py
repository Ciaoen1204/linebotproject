import os
import requests
import random
import csv
import threading
from bs4 import BeautifulSoup
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, AudioMessage, ImageMessage, QuickReply, QuickReplyButton, MessageAction
import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
from googletrans import Translator
import schedule
import time
from io import BytesIO
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import re

# Load environment variables
load_dotenv()

# Flask initialization
app = Flask(__name__)

# LINE Bot configuration
line_bot_api = LineBotApi(os.getenv('LineBotApi'))
handler = WebhookHandler(os.getenv('secret'))

# Translator and Speech-to-Text configuration
translator = Translator()
speech_config = speechsdk.SpeechConfig(
    subscription=os.getenv("SPEECH_KEY"),
    region=os.getenv("SPEECH_REGION")
)
speech_config.speech_recognition_language = "zh-CN"

# Azure Computer Vision initialization
computervision_client = ComputerVisionClient(
    os.getenv('COMPUTER_VISION_ENDPOINT'),
    CognitiveServicesCredentials(os.getenv('COMPUTER_VISION_SUBSCRIPTION_KEY'))
)

# 使用全域變數來儲存用戶的狀態和提醒事項
user_status = {}
reminders = {}

# 初始化 scheduler
scheduler = BackgroundScheduler()

def check_reminders():
    current_time = datetime.now().strftime("%H:%M")
    
    # 檢查是否有提醒時間符合現在時間
    for user_id, user_reminders in reminders.items():
        for reminder, reminder_time in user_reminders:
            if reminder_time == current_time:
                line_bot_api.push_message(
                    user_id,
                    TextSendMessage(text=f"提醒：{reminder}，現在是 {current_time}，該行動了！")
                )

# 啟動定時任務，每分鐘檢查一次
scheduler.add_job(check_reminders, 'interval', minutes=1)

# 啟動定時器
scheduler.start()

# Function to fetch BBC news article links
def get_bbc_news_articles():
    url = 'https://www.bbc.com/news'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if href.startswith('/news/articles/'):
            full_url = 'https://www.bbc.com' + href
            return full_url

# Function to fetch BBC news video links
def get_bbc_news_videos():
    url = 'https://www.bbc.com/news'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if href.startswith('/news/videos/'):
            full_url = 'https://www.bbc.com' + href
            return full_url

# Function to send daily news article
def send_daily_article():
    article_link = get_bbc_news_articles()
    if article_link:
        reply = f"\u4eca\u65e5\u65b0\u805e\u6587\u7ae0\uff1a\n{article_link}"
    else:
        reply = "\u672a\u80fd\u7372\u53d6\u4eca\u65e5\u65b0\u805e\u6587\u7ae0\u3002"
    
    user_ids = os.getenv("USER_IDS").split(',')
    for user_id in user_ids:
        line_bot_api.push_message(user_id, TextSendMessage(text=reply))

# Function to send daily news video
def send_daily_video():
    video_link = get_bbc_news_videos()
    if video_link:
        reply = f"\u4eca\u65e5\u65b0\u805e\u5f71\u7247\uff1a\n{video_link}"
    else:
        reply = "\u672a\u80fd\u7372\u53d6\u4eca\u65e5\u65b0\u805e\u5f71\u7247\u3002"
    
    user_ids = os.getenv("USER_IDS").split(',')
    for user_id in user_ids:
        line_bot_api.push_message(user_id, TextSendMessage(text=reply))

# Vocabulary quiz setup
def load_words_from_csv(filepath):
    words, translations = [], {}
    with open(filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            word, translation = row
            words.append(word)
            translations[word] = translation
    return words, translations

def generate_cloze(word):
    hidden = list(word)
    for i in range(1, len(word) - 1):
        hidden[i] = '_'
    return ''.join(hidden)

csv_filepath = os.path.join(os.path.dirname(__file__), 'vocabulary.csv')
words, translations = load_words_from_csv(csv_filepath)
correct_answer = None
error_count = 0

#--- 爬取單字資料功能 ---
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

# Audio processing
ffmpeg_path =r"C:\Users\User\OneDrive\桌面\113-1程式\ffmpeg-master-latest-win64-gpl\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"

def recognize_from_audio_file(file_path):
    audio_config = speechsdk.audio.AudioConfig(filename=file_path)
    speech_recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config, audio_config=audio_config
    )
    result = speech_recognizer.recognize_once_async().get()
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        return "No speech could be recognized."
    elif result.reason == speechsdk.ResultReason.Canceled:
        return f"Recognition canceled: {result.cancellation_details.error_details}"
    return "Unknown error."

# OCR from images
def image_to_text(image_data):
    try:
        ocr_result = computervision_client.recognize_printed_text_in_stream(image_data)
        text = ""
        for region in ocr_result.regions:
            for line in region.lines:
                text += " ".join([word.text for word in line.words]) + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error: {e}")
        return None

# LINE Webhook
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

def create_quick_reply():
    return QuickReply(items=[
        QuickReplyButton(action=MessageAction(label="建立提醒", text="建立提醒")),
        QuickReplyButton(action=MessageAction(label="查詢提醒", text="查詢提醒")),
        QuickReplyButton(action=MessageAction(label="修改提醒", text="修改提醒")),
        QuickReplyButton(action=MessageAction(label="刪除提醒", text="刪除提醒")),
        QuickReplyButton(action=MessageAction(label="退出提醒功能", text="退出提醒功能"))
    ])

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    global correct_answer, error_count
    user_id = event.source.user_id
    user_message = event.message.text.lower()
    text = event.message.text

    # 進入提醒模式並顯示多頁選單
    if text == '提醒功能':
        user_status[user_id] = 'reminder_mode'
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="請選擇提醒功能操作：",
                quick_reply=create_quick_reply()
            )
        )
    # 退出提醒模式
    elif text == '退出提醒功能':
        if user_status.get(user_id) == 'reminder_mode':
            user_status.pop(user_id, None)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="已退出提醒功能模式。"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="目前未處於提醒功能模式。"))
    # 檢查是否在提醒模式
    elif user_status.get(user_id) == 'reminder_mode':
        if text == '建立提醒':
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="請輸入提醒的時間和內容，例如：17點5分提醒我讀英文",
                    quick_reply=create_quick_reply()
                )
            )
        elif text == '查詢提醒':
            if user_id in reminders and reminders[user_id]:
                reminders_text = "\n".join([f"{i+1}. {reminder}，時間：{time}" for i, (reminder, time) in enumerate(reminders[user_id])])
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(
                        text=reminders_text,
                        quick_reply=create_quick_reply()
                    )
                )
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(
                        text="目前沒有提醒。",
                        quick_reply=create_quick_reply()
                    )
                )
        elif text.startswith('刪除提醒'):
            match = re.match(r'刪除提醒(\d+)', text)
            if match:
                reminder_index = int(match.group(1)) - 1  # 用戶輸入的是從1開始的編號
                if user_id in reminders and 0 <= reminder_index < len(reminders[user_id]):
                    removed_reminder, reminder_time = reminders[user_id].pop(reminder_index)
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(
                            text=f"已刪除提醒：{removed_reminder}，時間：{reminder_time}",
                            quick_reply=create_quick_reply()
                        )
                    )
                else:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(
                            text="提醒編號無效，請檢查並重新輸入。",
                            quick_reply=create_quick_reply()
                        )
                    )
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(
                        text="請輸入正確的刪除提醒編號，例如：刪除提醒1",
                        quick_reply=create_quick_reply()
                    )
                )
        elif text.startswith('修改提醒'):
            match = re.match(r'修改提醒(\d+)', text)
            if match:
                reminder_index = int(match.group(1)) - 1  # 用戶輸入的是從1開始的編號
                if user_id in reminders and 0 <= reminder_index < len(reminders[user_id]):
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(
                            text=f"請輸入新的提醒內容：{reminders[user_id][reminder_index][0]}，目前時間：{reminders[user_id][reminder_index][1]}。",
                            quick_reply=create_quick_reply()
                        )
                    )
                    user_status[user_id] = 'modifying_reminder'
                    user_status[user_id + '_reminder_index'] = reminder_index  # 記錄正在修改的提醒編號
                else:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(
                            text="提醒編號無效，請檢查並重新輸入。",
                            quick_reply=create_quick_reply()
                        )
                    )
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(
                        text="請輸入正確的修改提醒編號，例如：修改提醒1",
                        quick_reply=create_quick_reply()
                    )
                )
        elif re.match(r'(\d{1,2})點(\d{1,2})分提醒我(.+)', text):
            match = re.match(r'(\d{1,2})點(\d{1,2})分提醒我(.+)', text)
            hour, minute, reminder = match.groups()
            reminder_time = f"{int(hour):02}:{int(minute):02}"
            if user_id not in reminders:
                reminders[user_id] = []
            reminders[user_id].append((reminder, reminder_time))
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"已新增提醒：{reminder}，時間：{reminder_time}",
                    quick_reply=create_quick_reply()
                )
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="請依照格式輸入正確的指令。",
                    quick_reply=create_quick_reply()
                )
            )

    # 處理修改提醒內容的輸入
    elif user_status.get(user_id) == 'modifying_reminder':
        reminder_index = user_status.get(user_id + '_reminder_index')
        if reminder_index is not None and user_id in reminders and 0 <= reminder_index < len(reminders[user_id]):
            # 修改提醒內容或時間
            new_text = text.strip()
            current_reminder, current_time = reminders[user_id][reminder_index]
            reminders[user_id][reminder_index] = (new_text, current_time)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"提醒已更新：新內容是「{new_text}」，時間保持不變：{current_time}",
                    quick_reply=create_quick_reply()
                )
            )
            user_status.pop(user_id, None)
            user_status.pop(user_id + '_reminder_index', None)
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="修改失敗，無效的提醒編號。",
                    quick_reply=create_quick_reply()
                )
            )
    else:
        if user_message == "開始遊戲":
            correct_answer = random.choice(words)
            cloze = generate_cloze(correct_answer)
            translation = translations[correct_answer]
            error_count = 0
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"請猜這個單字: {cloze} ({translation})"))
        elif user_message == correct_answer:
            translation = translations[correct_answer]
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"答對了！這個單字是：{correct_answer}，中文是：{translation}"))
            correct_answer = None
            error_count = 0
        elif correct_answer is not None:
            error_count += 1
            if error_count >= 3:
                translation = translations[correct_answer]
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"錯誤次數過多！正確答案是：{correct_answer}，中文是：{translation}")
                )
                correct_answer = None
                error_count = 0
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"答錯了，再試一次。你已經錯了 {error_count} 次。")
                )
        elif user_message == "每日單字":
            vocabulary_words = fetch_vocabulary()
            selected_words = random.sample(vocabulary_words, 3)
            reply_text = "今日單字:\n" + "\n".join(selected_words)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

@handler.add(MessageEvent, message=AudioMessage)
def handle_audio_message(event):
    audio_file_path = f"{event.message.id}.m4a"
    wav_file_path = f"{event.message.id}.wav"
    try:
        # \u4e0b\u8f09\u97f3\u8a0a\u6a94\u6848
        message_content = line_bot_api.get_message_content(event.message.id)
        with open(audio_file_path, 'wb') as fd:
            for chunk in message_content.iter_content():
                fd.write(chunk)
        
        # \u5c07\u97f3\u6a94\u8f49\u63db\u70ba WAV \u683c\u5f0f
        os.system(f"{ffmpeg_path} -i {audio_file_path} {wav_file_path}")
        
        # \u4f7f\u7528 Azure \u8a9e\u97f3\u8fa8\u8b58
        recognized_text = recognize_from_audio_file(wav_file_path)
        
        # \u6aa2\u6e2c\u8a9e\u8a00\u4e26\u7ffb\u8b6f
        detected_language = translator.detect(recognized_text).lang  # \u6aa2\u6e2c\u8a9e\u8a00
        if detected_language == 'zh-CN':  # \u5982\u679c\u662f\u4e2d\u6587\uff0c\u7ffb\u8b6f\u6210\u82f1\u6587
            translated_text = translator.translate(recognized_text, src='zh-CN', dest='en').text
        elif detected_language == 'en':  # \u5982\u679c\u662f\u82f1\u6587\uff0c\u7ffb\u8b6f\u6210\u4e2d\u6587
            translated_text = translator.translate(recognized_text, src='en', dest='zh-CN').text
        else:  # \u5982\u679c\u8a9e\u8a00\u4e0d\u652f\u63f4\uff0c\u8fd4\u56de\u539f\u6587
            translated_text = "\u7121\u6cd5\u7ffb\u8b6f\uff0c\u539f\u6587\u70ba\uff1a" + recognized_text

        # \u56de\u8986\u8fa8\u8b58\u8207\u7ffb\u8b6f\u7d50\u679c
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"\u539f\u6587: {recognized_text}\n\u7ffb\u8b6f: {translated_text}")
        )
    except Exception as e:
        # \u932f\u8aa4\u8655\u7406
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"\u8655\u7406\u8a9e\u97f3\u6642\u767c\u751f\u932f\u8aa4: {str(e)}")
        )
    finally:
        # \u6e05\u7406\u66ab\u5b58\u6a94\u6848
        if os.path.exists(audio_file_path):
            os.remove(audio_file_path)
        if os.path.exists(wav_file_path):
            os.remove(wav_file_path)

@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    try:
        message_content = line_bot_api.get_message_content(event.message.id)
        image_data = BytesIO(message_content.content)
        text = image_to_text(image_data)
        if text:
            line_bot_api.reply_message(event.reply_token, TextMessage(text=text))
        else:
            line_bot_api.reply_message(event.reply_token, TextMessage(text="未能提取圖片中的文字"))
    except Exception as e:
        print(f"Error processing image: {e}")
        line_bot_api.reply_message(event.reply_token, TextMessage(text="發生錯誤，請稍後再試"))

# Schedule daily tasks
def schedule_jobs():
    # Schedule article push at 8:00 AM
    schedule.every().day.at("21:08").do(send_daily_article)
    # Schedule video push at 12:00 PM
    schedule.every().day.at("21:09").do(send_daily_video)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=schedule_jobs).start()
    app.run(host='0.0.0.0', port=5000)
