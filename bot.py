import os
import logging
import threading
import http.server
import socketserver
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = App(token=SLACK_BOT_TOKEN)
openai = OpenAI(api_key=OPENAI_API_KEY)

# Emoji to language mapping
EMOJI_LANG_MAP = {
    ":repeat:": "UK",      # Ukrainian
    ":gb:": "EN-GB",       # English (British)
    ":ru:": "RU"            # Russian
}

# Start fake HTTP server (for Render port binding workaround)
def run_fake_server():
    PORT = 8080
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving fake HTTP server on port {PORT}")
        httpd.serve_forever()

threading.Thread(target=run_fake_server, daemon=True).start()

# Translation via ChatGPT API
def translate_with_chatgpt(text, target_lang):
    prompt = f"Translate this into {target_lang}:
" + text
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful translator."},
                {"role": "user", "content": prompt}
            ]
        )
        translation = response.choices[0].message.content.strip()
        return translation
    except Exception as e:
        logging.error(f"Translation error: {e}")
        return "⚠️ Error during translation."

# Reaction handler
@app.event("reaction_added")
def handle_reaction_added(body, say, client: WebClient):
    event = body.get("event", {})
    reaction = f":{event.get('reaction')}:"

    if reaction not in EMOJI_LANG_MAP:
        return

    target_lang = EMOJI_LANG_MAP[reaction]
    item = event.get("item", {})

    if item.get("type") != "message":
        return

    try:
        channel = item.get("channel")
        message_ts = item.get("ts")
        user = event.get("user")

        result = client.conversations_history(channel=channel, latest=message_ts, inclusive=True, limit=1)
        messages = result.get("messages", [])
        if not messages:
            return

        original_text = messages[0].get("text", "")
        if not original_text:
            return

        translated_text = translate_with_chatgpt(original_text, target_lang)

        client.chat_postMessage(channel=user, text=f"*Переклад ({target_lang}):*\n{translated_text}")
    except Exception as e:
        logging.error(f"Error handling reaction: {e}")

if __name__ == "__main__":
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
