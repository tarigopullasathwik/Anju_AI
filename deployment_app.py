"""Small Vercel runtime application.

This module intentionally avoids importing the desktop assistant, optional file
processors, camera tooling, or the local database during deployment startup.
Those features remain available through the local ``main.py`` launcher.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sock import Sock
from werkzeug.utils import secure_filename

ROOT_DIR = Path(__file__).resolve().parent
UI_DIR = ROOT_DIR / "ui"
UPLOAD_DIR = ROOT_DIR / "uploads"

app = Flask(__name__)
CORS(app)
sock = Sock(app)
clients: set[Any] = set()
clients_lock = threading.Lock()
status = "Standing By"


def broadcast(payload: dict[str, Any]) -> None:
    message = json.dumps(payload)
    dead: set[Any] = set()
    with clients_lock:
        for client in clients:
            try:
                client.send(message)
            except Exception:
                dead.add(client)
        clients.difference_update(dead)


def lazy_brain():
    """Load the assistant only when a user actually sends a chat message."""
    import brain.brain as brain
    brain.dashboard_instance = _DashboardBridge()
    return brain


class _DashboardBridge:
    def update_status(self, value: str) -> None:
        global status
        status = value
        broadcast({"type": "status", "value": value})

    def add_message(self, sender: str, text: str, speak_flag: bool = False,
                    image: str | None = None, emotion: str | None = None) -> None:
        broadcast({
            "type": "message", "sender": sender, "text": text,
            "speak": speak_flag, "image": image, "emotion": emotion,
            "audio": None,
        })


bridge = _DashboardBridge()


@app.get("/")
def index():
    return send_from_directory(str(UI_DIR), "index.html")


@app.get("/<path:filename>")
def static_files(filename: str):
    requested = (ROOT_DIR / filename).resolve()
    if requested.is_relative_to(ROOT_DIR) and requested.is_file():
        return send_from_directory(str(requested.parent), requested.name)
    return send_from_directory(str(UI_DIR), filename)


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "anju-ai"})


@app.get("/set_mode/<new_mode>")
def set_mode_route(new_mode: str):
    try:
        brain = lazy_brain()
        result = brain.set_mode(new_mode)
        return jsonify({"status": "success", "message": result})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.post("/upload")
def upload_file():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400
    uploaded = request.files["file"]
    filename = secure_filename(uploaded.filename or "")
    if not filename:
        return jsonify({"success": False, "error": "Empty filename"}), 400
    UPLOAD_DIR.mkdir(exist_ok=True)
    path = UPLOAD_DIR / filename
    uploaded.save(path)
    return jsonify({"success": True, "filename": filename,
                    "message": "File uploaded. Processing is available in local mode."})


@sock.route("/ws")
def websocket(ws):
    with clients_lock:
        clients.add(ws)
    try:
        ws.send(json.dumps({"type": "status", "value": status}))
        while True:
            raw = ws.receive()
            if raw is None:
                break
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if data.get("type") != "chat" or not data.get("text"):
                continue
            threading.Thread(target=_process_chat,
                             args=(str(data["text"]),), daemon=True).start()
    finally:
        with clients_lock:
            clients.discard(ws)


def _process_chat(text: str) -> None:
    try:
        bridge.update_status("Processing")
        brain = lazy_brain()
        brain.process_query(text.strip())
    except Exception as exc:
        bridge.add_message("Anju", f"I encountered an error: {exc}", speak_flag=False)
    finally:
        bridge.update_status("Standing By")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "3000")))
