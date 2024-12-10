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

# 儲存使用者回答的資料
user_preferences = {}

# 固定的調酒選項
cocktails = [
    {
        "name": "莫吉托（Mojito）",
        "description": "清新的薄荷和青檸風味，帶有微甜，非常適合晴朗的天氣和愉快的心情。"
    },
    {
        "name": "琴費士（Gin Fizz）",
        "description": "琴酒、檸檬汁和蘇打水帶來微酸清爽的風味，適合陰天和平靜的心情。"
    },
    {
        "name": "白蘭地亞歷山大（Brandy Alexander）",
        "description": "柔和的白蘭地和奶香甜味，適合雨天或低落的心情，給人溫暖的感覺。"
    }
]

# ChatGPT Prompt
base_prompt = """
你是一位調酒專家，根據使用者的回答從以下三款調酒中推薦一款最適合的飲品，並解釋原因：
1. {cocktail1_name}: {cocktail1_desc}
2. {cocktail2_name}: {cocktail2_desc}
3. {cocktail3_name}: {cocktail3_desc}

使用者的回答：
- 心情：{mood}
- 天氣：{weather}
- 喜歡的巧克力：{chocolate}
- 喜歡的水果酸度：{fruit_acidity}

請選擇一款調酒，並以專業和親切的語氣給出推薦理由。
"""

def GPT_response(mood, weather, chocolate, fruit_acidity):
    try:
        # 構造 Prompt
        prompt = base_prompt.format(
            cocktail1_name=cocktails[0]["name"], cocktail1_desc=cocktails[0]["description"],
            cocktail2_name=cocktails[1]["name"], cocktail2_desc=cocktails[1]["description"],
            cocktail3_name=cocktails[2]["name"], cocktail3_desc=cocktails[2]["description"],
            mood=mood,
            weather=weather,
            chocolate=chocolate,
            fruit_acidity=fruit_acidity
        )

        # 使用 ChatCompletion，正確傳遞 messages
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一位調酒專家，會根據使用者的偏好推薦最適合的飲品。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        # 解析回應
        answer = response['choices'][0]['message']['content'].strip()
        return answer
    except openai.error.AuthenticationError:
        print("Authentication error: Check your API Key")
        return "無法驗證 API Key，請檢查設定。"
    except openai.error.RateLimitError:
        print("Rate limit exceeded: Too many requests")
        return "超出請求限制，請稍後再試。"
    except openai.error.OpenAIError as e:
        print(f"OpenAI API error: {e}")
        return "OpenAI API 無法處理請求，請稍後再試。"
    except Exception as e:
        print(f"其他錯誤：{e}")
        return "發生未知錯誤，請稍後再試。"



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

    # 問「今天的心情如何？」
    if msg.lower() == "開始" or msg.lower() == "重新選擇":
        buttons_template = TemplateSendMessage(
            alt_text='今天心情如何？',
            template=ButtonsTemplate(
                title='你好！今天的心情如何？',
                text='請選擇最貼近你現在心情的選項～',
                actions=[
                    MessageAction(label='開心', text='開心'),
                    MessageAction(label='平常心', text='平常心'),
                    MessageAction(label='難過', text='難過'),
                    MessageAction(label='生氣', text='生氣')
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)

    # 心情選擇
    elif msg in ["開心", "平常心", "難過", "生氣"]:
        user_preferences[user_id] = {"mood": msg}
        buttons_template = TemplateSendMessage(
            alt_text='天氣如何？',
            template=ButtonsTemplate(
                title='今天天氣如何呢？',
                text='告訴我今天的天氣吧～',
                actions=[
                    MessageAction(label='晴天', text='晴天'),
                    MessageAction(label='雨天', text='雨天'),
                    MessageAction(label='陰天', text='陰天')
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)

    # 天氣選擇
    elif msg in ["晴天", "雨天", "陰天"]:
        user_preferences[user_id]["weather"] = msg
        buttons_template = TemplateSendMessage(
            alt_text='你喜歡哪種巧克力？',
            template=ButtonsTemplate(
                title='你對巧克力的選擇是？',
                text='請選擇你最喜歡的巧克力～',
                actions=[
                    MessageAction(label='黑巧克力', text='黑巧克力'),
                    MessageAction(label='牛奶巧克力', text='牛奶巧克力'),
                    MessageAction(label='白巧克力(較甜)', text='白巧克力(較甜)')
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)

    # 巧克力選擇
    elif msg in ["黑巧克力", "牛奶巧克力", "白巧克力(較甜)"]:
        user_preferences[user_id]["chocolate"] = msg
        buttons_template = TemplateSendMessage(
            alt_text='你喜歡哪種水果的酸度？',
            template=ButtonsTemplate(
                title='你對水果酸度的偏好是？',
                text='選擇你最喜歡的水果酸度吧！',
                actions=[
                    MessageAction(label='檸檬', text='檸檬'),
                    MessageAction(label='橘子', text='橘子'),
                    MessageAction(label='草莓(微酸)', text='草莓(微酸)')
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)

    # 水果酸度選擇
    elif msg in ["檸檬", "橘子", "草莓(微酸)"]:
        user_preferences[user_id]["fruit_acidity"] = msg
        preferences = user_preferences[user_id]

        # 呼叫 GPT 生成推薦
        try:
            recommendation = GPT_response(
                mood=preferences["mood"],
                weather=preferences["weather"],
                chocolate=preferences["chocolate"],
                fruit_acidity=preferences["fruit_acidity"]
            )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(recommendation))
        except Exception as e:
            print(traceback.format_exc())
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage('生成推薦時發生錯誤，請稍後再試。')
            )
    
    # 如果訊息不符合邏輯，提示重新開始
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage('請輸入「開始」來選擇你的偏好。')
        )


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
