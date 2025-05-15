import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

def run_fake_server():
    PORT = 8080
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving fake HTTP server on port {PORT}")
        httpd.serve_forever()

threading.Thread(target=run_fake_server, daemon=True).start()

app = App(token=os.environ["SLACK_BOT_TOKEN"])

@app.event("reaction_added")
def handle_reaction(event, say):
    print("✅ REACTION ADDED EVENT RECEIVED:")
    print(event)
    say("Reaction received!")

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
