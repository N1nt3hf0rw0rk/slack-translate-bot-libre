import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import requests

# Ініціалізація Slack App
app = App(token=os.environ["SLACK_BOT_TOKEN"])

# Мапа емодзі до мов
LANGUAGE_EMOJIS = {
    "🇬🇧": "en",
    "🇺🇦": "uk",
    "🇷🇺": "ru",
}

def translate(text, target_lang):
    resp = requests.post("https://libretranslate.de/translate", data={
        "q": text,
        "source": "auto",
        "target": target_lang,
        "format": "text"
    })
    return resp.json().get("translatedText", "[Translation failed]")

@app.event("reaction_added")
def handle_reaction_added(event, say, client, logger):
    emoji = event["reaction"]
    user_id = event["user"]
    channel = event["item"]["channel"]
    timestamp = event["item"]["ts"]

    if f":{emoji}:" not in LANGUAGE_EMOJIS and emoji not in LANGUAGE_EMOJIS:
        return

    try:
        response = client.conversations_history(channel=channel, latest=timestamp, limit=1, inclusive=True)
        original_msg = response["messages"][0]["text"]

        target_lang = LANGUAGE_EMOJIS.get(f":{emoji}:", LANGUAGE_EMOJIS.get(emoji))
        translated = translate(original_msg, target_lang)

        client.chat_postMessage(
            channel=user_id,
            text=f"🔁 Переклад ({target_lang}):\n{translated}"
        )
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    print("⚡️ Slack bot is running!")
    handler.start()
