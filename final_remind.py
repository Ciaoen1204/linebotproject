from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, QuickReply, QuickReplyButton, MessageAction
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import re

app = Flask(__name__)

# 設定你的 LINE Bot 的 Channel Access Token 和 Channel Secret
line_bot_api = LineBotApi('fr9wkUlGTpylZs2CAGUqJHhjk/KUkcpPnBmzoM4rRT3KEGbDWB5AxbBaRMwBTVmlY5utKY2AKOISLuvWKGcLG5cz+vyFZqG1HXgoePZvxy/aS8QBHEUr/bJw6BRhxD0WEscbtJWC4ujVP309vHd0jwdB04t89/1O/w1cDnyilFU=')  # 這裡替換為您的 Channel Access Token
handler = WebhookHandler('9c9b977b5a2e4c287ad5506a64431aba')  # 這裡替換為您的 Channel Secret

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

# 建立 Quick Reply 選單
def create_quick_reply():
    return QuickReply(items=[
        QuickReplyButton(action=MessageAction(label="建立提醒", text="建立提醒")),
        QuickReplyButton(action=MessageAction(label="查詢提醒", text="查詢提醒")),
        QuickReplyButton(action=MessageAction(label="修改提醒", text="修改提醒")),
        QuickReplyButton(action=MessageAction(label="刪除提醒", text="刪除提醒")),
        QuickReplyButton(action=MessageAction(label="退出提醒功能", text="退出提醒功能"))
    ])

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
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
                    text="請輸入提醒的時間和內容，例如：17點5分提醒我吃晚餐",
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

if __name__ == "__main__":
    app.run(debug=True)
