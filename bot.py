import os
import logging
import threading
import http.server
import socketserver
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Запускаємо фейковий HTTP-сервер для Render (порт 8080)
def run_fake_server():
    PORT = 8080
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving fake HTTP server on port {PORT}")
        httpd.serve_forever()

threading.Thread(target=run_fake_server, daemon=True).start()

# Slack App
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Emoji -> target language mapping
EMOJI_LANG_MAP = {
    ":gb:": "English",
    ":ukraine:": "Ukrainian",
    ":ru:": "Russian"
}

# Обробка emoji-реакцій
@app.event("reaction_added")
def handle_reaction_added(event, client, say, logger):
    try:
        emoji = f":{event['reaction']}:">
        logger.info(f"Reaction received: {emoji}")

        if emoji not in EMOJI_LANG_MAP:
            return

        # Отримуємо оригінальне повідомлення
        channel = event["item"]["channel"]
        timestamp = event["item"]["ts"]

        original_message_response = client.conversations_history(channel=channel, latest=timestamp, inclusive=True, limit=1)
        original_text = original_message_response["messages"][0]["text"]

        target_lang = EMOJI_LANG_MAP[emoji]

        logger.info(f"Translating to: {target_lang}")

        prompt = f"Translate this message to {target_lang}:
\n" + original_text

        completion = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a translation assistant."},
                {"role": "user", "content": prompt}
            ]
        )

        translated_text = completion.choices[0].message.content.strip()

        # Надсилаємо переклад в приват користувачу
        user = event["user"]
        client.chat_postMessage(channel=user, text=f"Переклад на {target_lang}:\n{translated_text}")

    except Exception as e:
        logger.error(f"Error during translation: {e}")

# Запуск Socket Mode
if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()
