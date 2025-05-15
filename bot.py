import os
import threading
import http.server
import socketserver
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError
import openai

def run_fake_server():
    PORT = 8080
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving fake HTTP server on port {PORT}")
        httpd.serve_forever()

threading.Thread(target=run_fake_server, daemon=True).start()

EMOJI_TO_LANG = {
    "gb": "en",
    "uk": "uk",
    "ru": "ru",
}

LANG_CODE_TO_NAME = {
    "en": "English",
    "uk": "Ukrainian",
    "ru": "Russian",
}

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
openai.api_key = os.environ.get("OPENAI_API_KEY")

def translate_text(text: str, target_lang_code: str) -> str:
    try:
        lang_name = LANG_CODE_TO_NAME.get(target_lang_code, target_lang_code)
        prompt = f"Please translate the following text into {lang_name} language:\n\n{text}"
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
def handle_reaction(event, client):
    print("Received reaction_added event:", event)
    emoji = event.get("reaction")
    print(f"Reaction emoji: {emoji}")
    user_who_reacted = event.get("user")
    item = event.get("item")
    channel_id = item.get("channel")
    message_ts = item.get("ts")

    if emoji not in EMOJI_TO_LANG:
        print("Emoji not in the translation list, skipping.")
        return

    target_lang_code = EMOJI_TO_LANG[emoji]

    try:
        result = client.conversations_history(channel=channel_id, latest=message_ts, inclusive=True, limit=1)
        messages = result.get("messages", [])
        if not messages:
            print("No message found for translation.")
            return
        original_text = messages[0].get("text", "")
        if not original_text:
            print("Original message has no text.")
            return

        translation = translate_text(original_text, target_lang_code)
        if translation is None:
            print("Translation failed.")
            return

        client.chat_postMessage(channel=user_who_reacted, text=f":repeat: Переклад ({target_lang_code}):\n{translation}")

    except SlackApiError as e:
        print(f"Slack API error: {e.response['error']}")

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()
