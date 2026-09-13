"""Small, resilient Flask deployment app for Anju AI."""
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
_clients: set[Any] = set()
_clients_lock = threading.Lock()
_state = {"status": "Standing By", "last_error": None}


def _broadcast(payload: dict[str, Any]) -> None:
    message = json.dumps(payload)
    dead: set[Any] = set()
    with _clients_lock:
        for client in tuple(_clients):
            try:
                client.send(message)
            except Exception:
                dead.add(client)
        _clients.difference_update(dead)


def _set_status(value: str) -> None:
    _state["status"] = value
    _broadcast({"type": "status", "value": value})


def _fallback_response(text: str) -> str:
    normalized = text.lower().strip()
    if normalized in {"hello", "hi", "hey", "anju"}:
        return "I'm here, Sathwik. Tell me what you need."
    if "who are you" in normalized:
        return "I'm Anju, your personal AI assistant."
    if "status" in normalized or "health" in normalized:
        return "Anju is online. The deployment API is responding, and I am ready."
    return "I received your message, but the AI provider is temporarily unavailable. Please try again in a moment."


def _save_message(role: str, content: str) -> None:
    try:
        from memory.database import save_message
        save_message(role, content)
    except Exception as exc:
        _state["last_error"] = f"memory unavailable: {exc}"


def _answer(text: str) -> str:
    """Use the full brain when available, without making the API depend on it."""
    try:
        import brain.brain as brain
        brain.dashboard_instance = _DashboardBridge()
        result = brain.process_query(text)
        if isinstance(result, str) and result.strip():
            return result.strip()
    except Exception as exc:
        _state["last_error"] = str(exc)
    return _fallback_response(text)


class _DashboardBridge:
    def update_status(self, value: str) -> None:
        _set_status(value)

    def add_message(self, sender: str, text: str, speak_flag: bool = False,
                    image: str | None = None, emotion: str | None = None) -> None:
        _broadcast({"type": "message", "sender": sender, "text": text,
                    "speak": speak_flag, "image": image, "emotion": emotion,
                    "audio": None})


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
    database_configured = bool(os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or
                                os.getenv("POSTGRES_PRISMA_URL") or os.getenv("POSTGRES_URL_NON_POOLING"))
    return jsonify({"status": "ok", "service": "anju-ai", "assistant": "ready",
                    "database": "configured" if database_configured else "local-fallback",
                    "last_error": _state["last_error"]})


@app.post("/api/chat")
def chat_api():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text", "")).strip()
    if not text:
        return jsonify({"ok": False, "error": "Message text is required"}), 400
    _save_message("user", text)
    _set_status("Processing")
    answer = _answer(text)
    _save_message("assistant", answer)
    _set_status("Standing By")
    return jsonify({"ok": True, "text": answer, "sender": "Anju"})


@app.get("/set_mode/<new_mode>")
def set_mode_route(new_mode: str):
    if new_mode not in {"voice", "chat"}:
        return jsonify({"status": "error", "message": "Unsupported mode"}), 400
    return jsonify({"status": "success", "message": f"{new_mode} mode activated"})


@app.post("/upload")
def upload_file():
    uploaded = request.files.get("file")
    filename = secure_filename(uploaded.filename or "") if uploaded else ""
    if not uploaded or not filename:
        return jsonify({"success": False, "error": "A file is required"}), 400
    UPLOAD_DIR.mkdir(exist_ok=True)
    uploaded.save(UPLOAD_DIR / filename)
    return jsonify({"success": True, "filename": filename,
                    "message": "File uploaded successfully."})


@sock.route("/ws")
def websocket(ws):
    with _clients_lock:
        _clients.add(ws)
    try:
        ws.send(json.dumps({"type": "status", "value": _state["status"]}))
        while True:
            raw = ws.receive()
            if raw is None:
                break
            try:
                payload = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                continue
            if payload.get("type") != "chat":
                continue
            text = str(payload.get("text", "")).strip()
            if not text:
                continue
            threading.Thread(target=_process_chat, args=(text,), daemon=True).start()
    finally:
        with _clients_lock:
            _clients.discard(ws)


def _process_chat(text: str) -> None:
    _set_status("Processing")
    _save_message("user", text)
    answer = _answer(text)
    _save_message("assistant", answer)
    _broadcast({"type": "message", "sender": "Anju", "text": answer,
                "speak": True, "image": None, "emotion": "neutral", "audio": None})
    _set_status("Standing By")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "3000")))
