from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import schedule
import time
import threading
import re

app = Flask(__name__)

# 設定你的 LINE Bot 的 Channel Access Token 和 Channel Secret
line_bot_api = LineBotApi('JAIpBs7Lx2UxUm/RlmO6vMOlKb3GeYbgj9YTjPdD8Ythb4G9Uwz384KuURyJxHHfIVg/gmiZW7myjvVX+DV9nliTvHxqHXpr5zZ3E+OeymmPuijw2Yh7bdRm/nZCh9T7+4linADxhOp1MlnuX6Ms+wdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('ea1e57cc2f7e7f996f63c09502340b51')

# 使用全域變數來儲存用戶的狀態和提醒事項
user_status = {}
reminders = {}
scheduled_reminders = {}

@app.route("/callback", methods=['POST'])
def callback():
    # 確認請求來自 LINE 平台
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text

    match = re.match(r'(\d{1,2})點(\d{1,2})分提醒我(.+)', text)
    if match:
        hour, minute, reminder = match.groups()
        reminder_time = f"{int(hour):02}:{int(minute):02}"
        if user_id not in reminders:
            reminders[user_id] = []
        reminders[user_id].append((reminder, reminder_time))
        reminder_id = len(reminders[user_id])
        if user_id not in scheduled_reminders:
            scheduled_reminders[user_id] = []
        scheduled_reminders[user_id].append((reminder, reminder_time))
        schedule.every().day.at(reminder_time).do(send_reminder, user_id=user_id, reminder=reminder)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"已新增提醒{reminder_id}: {reminder}，時間：{reminder_time}"))
    elif text == '查詢提醒':
        if user_id in reminders and reminders[user_id]:
            reminders_text = "\n".join([f"{i+1}. {reminder}，時間：{time}" for i, (reminder, time) in enumerate(reminders[user_id])])
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reminders_text))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="目前沒有提醒。"))
    elif text.startswith('刪除提醒'):
        try:
            reminder_id = int(text[4:].strip())
            if user_id in reminders and 0 < reminder_id <= len(reminders[user_id]):
                reminders[user_id].pop(reminder_id - 1)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"提醒{reminder_id}已刪除。"))
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="提醒編號不存在。")
                )
        except ValueError:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="請輸入正確的提醒編號，例如：刪除提醒1")
            )
    elif text.startswith('修改提醒'):
        try:
            reminder_id = int(text[4:].strip())
            if user_id in reminders and 0 < reminder_id <= len(reminders[user_id]):
                user_status[user_id] = f'waiting_for_new_reminder_{reminder_id}'
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"請輸入新的提醒事項來替換提醒{reminder_id}"))
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="提醒編號不存在。")
                )
        except ValueError:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="請輸入正確的提醒編號，例如：修改提醒1")
            )
    elif user_id in user_status and user_status[user_id].startswith('waiting_for_new_reminder_'):
        reminder_id = int(user_status[user_id].split('_')[-1])
        new_reminder = text.strip()
        reminders[user_id][reminder_id - 1] = (new_reminder, reminders[user_id][reminder_id - 1][1])
        user_status.pop(user_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"提醒{reminder_id}已修改為：{new_reminder}"))
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請依照格式輸入，例如：17點5分提醒我吃晚餐"))

def send_reminder(user_id, reminder):
    line_bot_api.push_message(user_id, TextSendMessage(text=f"提醒：{reminder}"))

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    schedule_thread = threading.Thread(target=run_schedule)
    schedule_thread.start()
    app.run()