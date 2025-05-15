import os
import threading
import http.server
import socketserver
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError
import openai

# Запуск фейкового HTTP сервера для Render
def run_fake_server():
    PORT = 8080
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving fake HTTP server on port {PORT}")
        httpd.serve_forever()

threading.Thread(target=run_fake_server, daemon=True).start()

# Ініціалізація бота Slack
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN or not OPENAI_API_KEY:
    print("Error: One or more environment variables are missing: SLACK_BOT_TOKEN, SLACK_APP_TOKEN, OPENAI_API_KEY")
    exit(1)

openai.api_key = OPENAI_API_KEY

app = App(token=SLACK_BOT_TOKEN)

# Словник мови відповідно до емодзі реакцій
EMOJI_TO_LANG = {
    "gb": "English",
    "uk": "Ukrainian",
    "ru": "Russian"
}

def translate_text(text: str, target_lang: str) -> str:
    try:
        prompt = f"Translate this text into {target_lang}:\n\n{text}"
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful translator."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500,
        )
        translation = response.choices[0].message['content'].strip()
        return translation
    except Exception as e:
        print(f"Error during translation: {e}")
        return None

@app.event("reaction_added")
def handle_reaction_added(event, client):
    reaction = event.get("reaction")
    user_id = event.get("user")
    item = event.get("item", {})
    channel = item.get("channel")
    ts = item.get("ts")

    if reaction not in EMOJI_TO_LANG:
        return  # Ігноруємо нецільові реакції

    target_lang = EMOJI_TO_LANG[reaction]

    try:
        # Отримуємо оригінальне повідомлення
        result = client.conversations_history(channel=channel, latest=ts, limit=1, inclusive=True)
        messages = result.get("messages", [])
        if not messages:
            return

        original_text = messages[0].get("text")
        if not original_text:
            return

        # Переклад
        translated_text = translate_text(original_text, target_lang)
        if not translated_text:
            return

        # Відправляємо переклад користувачу у приват
        client.chat_postMessage(channel=user_id, text=f":repeat: Переклад ({target_lang}):\n{translated_text}")

    except SlackApiError as e:
        print(f"Slack API Error: {e.response['error']}")

if __name__ == "__main__":
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
