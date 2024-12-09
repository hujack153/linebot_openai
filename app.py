from flask import Flask, session, request, abort
from flask_session import Session
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *

import os
import traceback
import openai

app = Flask(__name__)

# 確保 flask_session 資料夾存在
if not os.path.exists('./flask_session/'):
    os.makedirs('./flask_session/')

# 設定 Session 配置
app.config['SESSION_TYPE'] = 'filesystem'  # 使用檔案系統儲存 Session
app.config['SESSION_FILE_DIR'] = './flask_session/'  # 儲存 Session 的檔案目錄
app.config['SESSION_PERMANENT'] = False  # 設置 Session 為非永久性
app.config['SESSION_USE_SIGNER'] = True  # 增強 Session 的安全性
app.secret_key = 'f9b9f8f1d2e3a4c5b6c7d8e9f0a1b2c3'

# 啟用 Flask-Session
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
        max_tokens=200
    )
    print(response)
    answer = response['choices'][0]['text'].replace('。', '')
    return answer


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


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    msg = event.message.text

    if msg.lower() == "偏好":
        if user_id in session and session[user_id]:
            previous_choice = session[user_id]
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"你之前的偏好是：{previous_choice}")
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="你尚未設定任何偏好，請輸入「開始」來選擇你的偏好。")
            )
    elif msg.lower() == "開始" or msg.lower() == "重新選擇":
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
        session[user_id] = msg
        line_bot_api.reply_message(
            event.reply_token,
            [
                TextSendMessage(text=f"已儲存你的偏好：{msg}"),
                TextSendMessage(text=f"儲存偏好：{session.get(user_id)}")
            ]
        )
    else:
        try:
            GPT_answer = GPT_response(msg)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(GPT_answer))
        except Exception as e:
            print(traceback.format_exc())
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage('你所使用的 OPENAI API key 額度可能已經超過，請於後台 Log 內確認錯誤訊息')
            )


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
