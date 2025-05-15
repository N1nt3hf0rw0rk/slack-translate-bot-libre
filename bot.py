import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.web import WebClient
from flask import Flask, request
from threading import Thread
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
PORT = int(os.environ.get("PORT", 8080))

# Slack + OpenAI setup
app = App(token=SLACK_BOT_TOKEN)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Flask web app for Render port binding
flask_app = Flask(__name__)

@flask_app.route("/", methods=["GET"])
def health_check():
    return "Slack translation bot is running!", 200

# Emoji-to-language map
EMOJI_TO_LANG = {
    "gb": "English",
    "flag-ua": "Ukrainian language",
    "ru": "Russian"
}

@app.event("reaction_added")
def handle_reaction_added(body, say, client: WebClient, logger):
    event = body.get("event", {})
    reaction = event.get("reaction")
    item = event.get("item", {})
    user = event.get("user")

    logger.info(f"Reaction received: {reaction} from user {user}")

    if reaction not in EMOJI_TO_LANG:
        logger.info(f"Unsupported reaction: {reaction}")
        return

    target_lang = EMOJI_TO_LANG[reaction]
    channel_id = item.get("channel")
    message_ts = item.get("ts")

    try:
        result = client.conversations_history(channel=channel_id, latest=message_ts, limit=1, inclusive=True)
        original_message = result["messages"][0].get("text", "")
        logger.info(f"Original message: {original_message}")
    except Exception as e:
        logger.error(f"Error fetching original message: {e}")
        return

    prompt = f"Translate this message to {target_lang}: \"{original_message}\""

    try:
        chat_response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that translates messages."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        translated_text = chat_response.choices[0].message.content.strip()

        client.chat_postMessage(
            channel=user,
            text=f"Translated to {target_lang}:\n{translated_text}"
        )

    except Exception as e:
        logger.error(f"Translation failed: {e}")

# Run Flask + Slack bot in parallel
def start_socket_mode():
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()

if __name__ == "__main__":
    thread = Thread(target=start_socket_mode)
    thread.start()
    flask_app.run(host="0.0.0.0", port=PORT)
