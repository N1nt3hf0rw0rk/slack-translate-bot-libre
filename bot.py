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
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import requests

# Ініціалізація Slack App
app = App(token=os.environ["SLACK_BOT_TOKEN"])

# Мапа емодзі до мов (Slack передає емодзі як 'flag-ua' тощо)
LANGUAGE_EMOJIS = {
    "flag-gb": "en",
    "flag-ua": "uk",
    "flag-ru": "ru",
}

# Функція перекладу через LibreTranslate
def translate(text, target_lang):
    try:
        url = "https://libretranslate.com/translate"
        headers = {
            "Content-Type": "application/json",
        }
        payload = {
            "q": text,
            "source": "auto",
            "target": target_lang,
            "format": "text"
        }

        response = requests.post(url, headers=headers, json=payload, timeout=10)

        # Додай логування для діагностики
        if response.status_code != 200:
            return f"[Translation error: {response.status_code} - {response.text}]"

        return response.json().get("translatedText", "[Translation failed]")
    except Exception as e:
        return f"[Translation error: {e}]"

# Обробник події додавання емодзі
@app.event("reaction_added")
def handle_reaction_added(event, say, client, logger):
    emoji = event["reaction"]
    user_id = event["user"]
    channel = event["item"]["channel"]
    timestamp = event["item"]["ts"]

    logger.info(f"Reaction added: {emoji} by user {user_id} on message {timestamp}")

    if emoji not in LANGUAGE_EMOJIS:
        return

    try:
        # Отримання оригінального повідомлення
        response = client.conversations_history(
            channel=channel,
            latest=timestamp,
            limit=1,
            inclusive=True
        )
        original_msg = response["messages"][0]["text"]

        target_lang = LANGUAGE_EMOJIS[emoji]
        translated = translate(original_msg, target_lang)

        # Надсилання результату у DM користувачу
        client.chat_postMessage(
            channel=user_id,
            text=f"🔁 Переклад ({target_lang}):\n{translated}"
        )
    except Exception as e:
        logger.error(f"Error: {e}")

# Запуск бота через Socket Mode
if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    print("⚡️ Slack bot is running!")
    handler.start()
