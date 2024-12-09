from flask import Flask, session, request, abort
from flask_session import Session
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *

import os
import traceback
import openai

app = Flask(__name__)
app.secret_key = 'f9b9f8f1d2e3a4c5b6c7d8e9f0a1b2c3'

# 使用 Flask-Session
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
Session(app)

# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# OpenAI API Key 初始化設定
openai.api_key = os.getenv('OPENAI_API_KEY')


def GPT_response(text):
    # 使用 OpenAI API 生成回應
    response = openai.Completion.create(
        model="gpt-3.5-turbo-instruct",
        prompt=text,
        temperature=0.5,
        max_tokens=500
    )
    print(response)
    answer = response['choices'][0]['text'].replace('。', '')
    return answer


# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    # 取得 X-Line-Signature header 值
    signature = request.headers['X-Line-Signature']
    # 取得請求的 body 作為文字
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # 處理 webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    msg = event.message.text

    if msg.lower() == "偏好" and user_id in session:
        # 回覆儲存的偏好
        previous_choice = session[user_id]
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"你之前的偏好是：{previous_choice}")
        )
    elif msg.lower() == "開始" or msg.lower() == "重新選擇":
        # 顯示選擇偏好的按鈕
        buttons_template = TemplateSendMessage(
            alt_text='選擇偏好',
            template=ButtonsTemplate(
                title='你的調酒偏好',
                text='請選擇你喜歡的口感：',
                actions=[
                    MessageAction(label='酒感', text='我喜歡酒感'),
                    MessageAction(label='酸甜', text='我喜歡酸甜')
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)
    elif msg in ["我喜歡酒感", "我喜歡酸甜"]:
        # 儲存偏好到 Session
        session[user_id] = msg
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"已儲存你的偏好：{msg}")
        )
    else:
        # 使用 OpenAI API 回覆
        try:
            GPT_answer = GPT_response(msg)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(GPT_answer))
        except:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage('你所使用的 OPENAI API key 額度可能已經超過，請於後台 Log 內確認錯誤訊息')
            )



@handler.add(PostbackEvent)
def handle_postback(event):
    print(event.postback.data)


@handler.add(MemberJoinedEvent)
def welcome(event):
    uid = event.joined.members[0].user_id
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, uid)
    name = profile.display_name
    message = TextSendMessage(text=f'{name} 歡迎加入！請輸入「開始」來選擇你的調酒偏好！')
    line_bot_api.reply_message(event.reply_token, message)


# 保留 Flask 主程式
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
