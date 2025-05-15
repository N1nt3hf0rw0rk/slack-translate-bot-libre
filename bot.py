import os
import threading
import http.server
import socketserver
import requests
import deepl
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# --- Fake HTTP server for Render ---
def run_fake_server():
    PORT = 8080
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving fake HTTP server on port {PORT}")
        httpd.serve_forever()

threading.Thread(target=run_fake_server, daemon=True).start()

# --- DeepL Translator ---
DEEPL_API_KEY = os.environ.get("DEEPL_API_KEY")
translator = deepl.Translator(auth_key=DEEPL_API_KEY)

# --- Slack App ---
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

# --- Emoji to language code mapping ---
EMOJI_LANGUAGE_MAP = {
    "ua": "UA",  # Ukrainian
    "flag-gb": "EN-GB",  # English (British flag)
    "us": "EN-US",     # ✅ Альтернатива
    "ru": "RU",  # Russian
}

@app.event("reaction_added")
def handle_reaction_added(event, say, logger):
    reaction = event.get("reaction")
    item = event.get("item")
    user = event.get("user")

    if reaction not in EMOJI_LANGUAGE_MAP:
        return  # Ignore unrelated reactions

    try:
        # Get original message
        response = client.conversations_history(
            channel=item["channel"],
            inclusive=True,
            latest=item["ts"],
            limit=1
        )

        if not response["messages"]:
            return

        original_text = response["messages"][0].get("text", "")
        if not original_text:
            return

        target_lang = EMOJI_LANGUAGE_MAP[reaction]

        # Translate
        result = translator.translate_text(original_text, target_lang=target_lang)

        # Send as private message
        client.chat_postMessage(
            channel=user,
            text=f":repeat: Переклад ({target_lang.lower()}):\n{result.text}"
        )

    except SlackApiError as e:
        logger.error(f"Slack API error: {e.response['error']}")
    except Exception as e:
        logger.error(f"Error during translation: {str(e)}")

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
