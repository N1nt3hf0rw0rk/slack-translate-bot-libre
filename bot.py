import threading
import http.server
import socketserver

def run_fake_server():
    PORT = 8080
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving fake HTTP server on port {PORT}")
        httpd.serve_forever()

threading.Thread(target=run_fake_server, daemon=True).start()

import os
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError
from deep_translator import GoogleTranslator

# Логування
logging.basicConfig(level=logging.INFO)

# Ініціалізація додатку Slack
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Мапа емодзі до мов
EMOJI_TO_LANG = {
    "repeat": "uk",
    "gb": "en",
    "flag-gb": "en",
    "🇬🇧": "en",
    "ru": "ru",
    "flag-ru": "ru",
    "🇷🇺": "ru",
}

@app.event("reaction_added")
def handle_reaction_added(event, say, client, logger):
    reaction = event["reaction"]
    logger.info(f"Отримано реакцію: {reaction}")

    # Перевірка чи емодзі відповідає мові
    target_lang = EMOJI_TO_LANG.get(reaction)
    if not target_lang:
        logger.info(f"Емодзі '{reaction}' не підтримується.")
        return

    channel = event["item"]["channel"]
    timestamp = event["item"]["ts"]

    try:
        # Отримання повідомлення, на яке поставили реакцію
        result = client.conversations_history(channel=channel, latest=timestamp, inclusive=True, limit=1)
        original_message = result["messages"][0].get("text")

        if not original_message:
            logger.info("Не знайдено текст повідомлення.")
            return

        # Визначення мови оригіналу автоматично
        translated = GoogleTranslator(source="auto", target=target_lang).translate(original_message)

        # Надсилання перекладеного повідомлення
        say(
            text=f":{reaction}: Переклад ({target_lang}):\n{translated}",
            thread_ts=timestamp,
            reply_broadcast=False,
        )

    except SlackApiError as e:
        logger.error(f"Slack API помилка: {e.response['error']}")
    except Exception as e:
        logger.error(f"Інша помилка: {str(e)}")


if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
