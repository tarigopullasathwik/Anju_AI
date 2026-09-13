"""
Anju AI — Entry Point
Wires the brain, dashboard, memory, and file-upload handler together,
then starts the Flask web server.
"""
import os
import sys
import time
import random
import threading

# Ensure the project root is on sys.path so all package imports resolve
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from memory.database import init_db
from utils.ui_dashboard import AnjuDashboard
from utils.api_handler import APIHandler
import brain.brain as brain


class AnjuAssistant:

    def __init__(self):
        # Dashboard (Flask + WebSocket server)
        self.dashboard = AnjuDashboard()
        self.dashboard.on_message = self.process_command
        self.dashboard.on_file_upload = brain.handle_file_upload

        # Runtime state
        self.is_running = True
        self.is_processing = False
        self.last_interaction_time = time.time()
        self.lock = threading.Lock()

        # Link brain globals so it can push messages and reference the assistant
        brain.dashboard_instance = self.dashboard
        brain.assistant_instance = self

        # Initialise API metrics DB tables
        APIHandler._init_metrics()

    def process_command(self, user_input: str, source: str = "text"):
        """Receive a message from the WebSocket and route it through the brain."""
        if not user_input or not user_input.strip():
            return

        user_input = user_input.strip()
        print(f"\n[{source.upper()}] User: {user_input}")

        self.dashboard.update_status("Processing")

        # Graceful exit commands
        if user_input.lower() in ("exit", "quit", "stop", "goodbye"):
            brain.respond("Goodbye Sathwik! Powering down.")
            self.is_running = False
            return

        try:
            self.is_processing = True
            brain.process_query(user_input)
        except Exception as e:
            print(f"[ERROR] {e}")
            brain.respond(random.choice([
                "Hmm... something went slightly off. Let me fix that.",
                "Give me a second Sathwik. I'm handling it.",
                "I had a brief interruption. Could you repeat that?",
            ]))
        finally:
            self.is_processing = False

        self.dashboard.update_status("Standing By")
        self.last_interaction_time = time.time()

    def start(self):
        """Initialise the database, print the banner, and start the server."""
        init_db()
        print("=" * 42)
        print("  Anju AI — PRO Edition  |  Starting...")
        print("=" * 42)
        self.dashboard.run()  # blocks until server exits


# WSGI entrypoint used by Vercel and other deployment platforms.
# The instance is created at import time so `main:app` is discoverable.
assistant = AnjuAssistant()
app = assistant.dashboard.app


if __name__ == "__main__":
    assistant.start()
