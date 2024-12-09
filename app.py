from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *

import os
import traceback
import openai

app = Flask(__name__)

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
    msg = event.message.text

    # 問使用者「酒感」或「酸甜」
    if msg.lower() == "開始" or msg.lower() == "重新選擇":
        buttons_template = TemplateSendMessage(
            alt_text='選擇偏好',
            template=ButtonsTemplate(
                title='你的調酒偏好',
                text='請選擇你喜歡的口感：',
                actions=[
                    MessageAction(label='酒感', text='酒感'),
                    MessageAction(label='酸甜', text='酸甜')
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)

    # 如果使用者選擇「酒感」，則詢問下一個問題
    elif msg == "酒感":
        buttons_template = TemplateSendMessage(
            alt_text='選擇酒感偏好',
            template=ButtonsTemplate(
                title='你的酒感偏好',
                text='請選擇你喜歡的口感：',
                actions=[
                    MessageAction(label='苦甜', text='苦甜'),
                    MessageAction(label='不甜', text='不甜')
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)

    # 如果使用者選擇「酸甜」，則詢問下一個問題
    elif msg == "酸甜":
        buttons_template = TemplateSendMessage(
            alt_text='選擇酸甜偏好',
            template=ButtonsTemplate(
                title='你的酸甜偏好',
                text='請選擇你喜歡的口感：',
                actions=[
                    MessageAction(label='清爽草本', text='清爽草本'),
                    MessageAction(label='溫潤木質', text='溫潤木質')
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)

    # 如果使用者回答其他問題，呼叫 OpenAI API 回應
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
