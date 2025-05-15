import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

app = App(token=os.environ["SLACK_BOT_TOKEN"])

@app.event("reaction_added")
def handle_reaction(event, say):
    print("✅ REACTION ADDED EVENT RECEIVED:")
    print(event)
    say("Reaction received!")

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
