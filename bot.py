import os
import threading
import http.server
import socketserver
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.web import WebClient
import openai
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
openai.api_key = OPENAI_API_KEY

# 1. Start fake HTTP server for Render
def run_fake_server():
    PORT = 8080
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"✅ Fake HTTP server running on port {PORT}")
        httpd.serve_forever()

threading.Thread(target=run_fake_server, daemon=True).start()

# 2. Init Slack app
app = App(token=SLACK_BOT_TOKEN)

# 3. Define emoji-to-language mapping
emoji_lang_map = {
    "gb": "English",
    "us": "English",
    "uk": "Ukrainian",
    "ua": "Ukrainian",
    "ru": "Russian",
    "ru-flag": "Russian",
    "flag-ru": "Russian"
}

# 4. Translation function using ChatGPT
def translate_text(text, target_lang):
    prompt = f"Translate the following text into {target_lang}:\n\n{text}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        translated = response.choices[0].message["content"].strip()
        return translated
    except Exception as e:
        print(f"❌ Error during translation: {e}")
        return None

# 5. Listen to emoji reactions
@app.event("reaction_added")
def handle_reaction(event, say, client: WebClient):
    reaction = event["reaction"]
    item = event["item"]
    user = event["user"]

    target_lang = emoji_lang_map.get(reaction)
    if not target_lang:
        return  # Ignore unknown emoji

    # Get original message
    try:
        response = client.conversations_history(
            channel=item["channel"],
            latest=item["ts"],
            inclusive=True,
            limit=1
        )
        original_text = response["messages"][0]["text"]
    except Exception as e:
        print(f"❌ Failed to fetch original message: {e}")
        return

    # Translate message
    translated_text = translate_text(original_text, target_lang)
    if not translated_text:
        return

    # Post translation
    try:
        client.chat_postMessage(
            channel=item["channel"],
            thread_ts=item["ts"],
            text=f":{reaction}: ➤ *{target_lang} Translation:*\n{translated_text}"
        )
        print(f"✅ Translated to {target_lang}")
    except Exception as e:
        print(f"❌ Failed to send translated message: {e}")

# 6. Start bot
if __name__ == "__main__":
    print("🚀 Starting Slack translation bot...")
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
