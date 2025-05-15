import os
import threading
import http.server
import socketserver
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from googletrans import Translator
import logging

# 🔧 Fake HTTP server для Render
def run_fake_server():
    PORT = 8080
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving fake HTTP server on port {PORT}")
        httpd.serve_forever()

threading.Thread(target=run_fake_server, daemon=True).start()

# 🧠 Ініціалізація Slack та Google Translate
app = App(token=os.environ["SLACK_BOT_TOKEN"])
translator = Translator()
client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

# ✅ Мапа емодзі до ISO-кодів мов (а не назв)
emoji_to_lang = {
    "uk": "uk",  # українська
    "gb": "en",  # англійська
    "ru": "ru",  # російська
}

# 📝 Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.event("reaction_added")
def handle_reaction(event, say):
    reaction = event["reaction"].strip(":")
    item = event["item"]
    user_id = event["user"]

    logger.info(f"handle_reaction_added:Отримано реакцію: {reaction}")

    # 🎯 Визначаємо цільову мову
    target_lang_code = emoji_to_lang.get(reaction)
    if not target_lang_code:
        logger.info(f"Ігноровано реакцію: {reaction}")
        return

    try:
        channel_id = item["channel"]
        message_ts = item["ts"]

        # 📩 Отримуємо оригінальне повідомлення
        result = client.conversations_history(
            channel=channel_id, latest=message_ts, limit=1, inclusive=True
        )
        messages = result["messages"]
        if not messages:
            logger.error("Повідомлення не знайдено.")
            return

        original_text = messages[0].get("text", "")
        if not original_text:
            logger.info("Порожній текст.")
            return

        # 🌐 Переклад
        translated = translator.translate(original_text, dest=target_lang_code).text

        # 📨 Надсилання приватного повідомлення
        im = client.conversations_open(users=user_id)
        dm_channel = im["channel"]["id"]

        client.chat_postMessage(
            channel=dm_channel,
            text=f":repeat: Переклад ({target_lang_code}):\n{translated}"
        )

    except SlackApiError as e:
        logger.error(f"Slack API error: {e.response['error']}")
    except Exception as ex:
        logger.exception(f"Unexpected error: {ex}")

# ▶️ Запуск
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
