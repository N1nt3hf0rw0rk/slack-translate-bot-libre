import os
import openai
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.web import WebClient
from slack_sdk.errors import SlackApiError

# 🔑 OpenAI та Slack токени
openai.api_key = os.environ["OPENAI_API_KEY"]
app = App(token=os.environ["SLACK_BOT_TOKEN"])

# 🗺️ Відповідність емодзі → цільова мова
LANGUAGE_MAP = {
    "ua": "Ukrainian",
    "gb": "English",
    "ru": "Russian"
}

@app.event("reaction_added")
def handle_reaction(event, say, client: WebClient):
    try:
        emoji = event["reaction"]  # Наприклад: "gb", "ua", "ru"
        user_id = event["user"]
        item = event["item"]

        print(f"➡️ Reaction received: :{emoji}: from user {user_id}")

        if emoji not in LANGUAGE_MAP:
            print("❌ Unsupported emoji, skipping.")
            return

        # Отримуємо оригінальне повідомлення
        result = client.conversations_history(
            channel=item["channel"],
            latest=item["ts"],
            inclusive=True,
            limit=1
        )
        if not result["messages"]:
            print("❌ No message found.")
            return

        original_text = result["messages"][0]["text"]
        target_lang = LANGUAGE_MAP[emoji]

        print(f"🔤 Original: {original_text}")
        print(f"🌐 Translating to: {target_lang}")

        # GPT-переклад
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are a helpful assistant that translates any input to {target_lang}."},
                {"role": "user", "content": original_text}
            ],
            temperature=0.3,
        )
        translated_text = response["choices"][0]["message"]["content"].strip()

        print(f"✅ Translated: {translated_text}")

        # Надсилання в приват
        client.chat_postMessage(
            channel=user_id,
            text=f":repeat: Переклад ({target_lang}):\n{translated_text}"
        )

    except SlackApiError as e:
        print(f"Slack API error: {e.response['error']}")
    except Exception as e:
        print(f"Error during translation: {e}")

if __name__ == "__main__":
    print("🚀 Starting Slack translation bot...")
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
