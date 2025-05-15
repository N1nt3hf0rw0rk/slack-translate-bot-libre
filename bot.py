import os
import logging
import threading
import http.server
import socketserver

from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_sdk.errors import SlackApiError
from deep_translator import GoogleTranslator

# Логування
logging.basicConfig(level=logging.INFO)

# Slack App
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
handler = SlackRequestHandler(app)

# Flask
flask_app = Flask(__name__)

# Емодзі → мова
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

    target_lang = EMOJI_TO_LANG.get(reaction)
    if not target_lang:
        logger.info(f"Емодзі '{reaction}' не підтримується.")
        return

    channel = event["item"]["channel"]
    timestamp = event["item"]["ts"]

    try:
        result = client.conversations_history(channel=channel, latest=timestamp, inclusive=True, limit=1)
        original_message = result["messages"][0].get("text")

        if not original_message:
            logger.info("Не знайдено текст повідомлення.")
            return

        translated = GoogleTranslator(source="auto", target=target_lang).translate(original_message)

        say(
            text=f":{reaction}: Переклад ({target_lang}):\n{translated}",
            thread_ts=timestamp,
            reply_broadcast=False,
        )

    except SlackApiError as e:
        logger.error(f"Slack API помилка: {e.response['error']}")
    except Exception as e:
        logger.error(f"Інша помилка: {str(e)}")

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

# --- Псевдо-сервер на 8080 для Render ---
def run_fake_server():
    PORT = 8080
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving fake HTTP server on port {PORT}")
        httpd.serve_forever()

# --- Запуск ---
if __name__ == "__main__":
    threading.Thread(target=run_fake_server, daemon=True).start()

    mode = os.environ.get("APP_ENV", "socket")

    if mode == "web":
        port = int(os.environ.get("PORT", 3000))
        flask_app.run(host="0.0.0.0", port=port)
    else:
        SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
