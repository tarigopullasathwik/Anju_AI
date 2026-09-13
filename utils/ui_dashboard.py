import os
import threading
import webbrowser
import json
from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
from flask_sock import Sock

# Resolve the ui/ folder relative to this file
UI_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui")
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(ROOT_DIR, "uploads")

class AnjuDashboard:
    def __init__(self, host=None, port=None):
        # Bind to every interface so Vercel Sandbox can proxy the preview port.
        # Keep the local default port, while allowing the runner to provide PORT.
        self.host = host or os.getenv("HOST", "0.0.0.0")
        self.port = int(port or os.getenv("PORT", "3000"))
        self.clients = set()
        self.clients_lock = threading.Lock()

        # Persistence for new connections
        self.current_status = "Standing By"
        self.message_history = []
        self.history_lock = threading.Lock()
        self.on_message = None  # Callback for incoming messages
        self.on_file_upload = None  # Callback for file uploads

        self.app = Flask(__name__, static_folder=UI_DIR)
        CORS(self.app)  # Enable CORS for all routes
        self.sock = Sock(self.app)

        # Serve index.html at root
        @self.app.route("/")
        def index():
            return send_from_directory(UI_DIR, "index.html")

        # Serve any other static files (css, js, images in root)
        @self.app.route("/<path:filename>")
        def static_files(filename):
            # Check uploads directory first
            upload_path = os.path.join(UPLOAD_DIR, filename.replace("uploads/", "", 1))
            if os.path.exists(upload_path):
                return send_from_directory(os.path.dirname(upload_path), os.path.basename(upload_path))
            # Check output/ directory (for generated images)
            output_dir = os.path.join(ROOT_DIR, "output")
            output_path = os.path.join(ROOT_DIR, filename)
            if filename.startswith("output/") and os.path.exists(output_path):
                return send_from_directory(os.path.dirname(output_path), os.path.basename(output_path))
            # Check root directory as last resort
            if os.path.exists(output_path):
                return send_from_directory(os.path.dirname(output_path), os.path.basename(output_path))
            # Fallback to the UI directory
            return send_from_directory(UI_DIR, filename)

        @self.app.route("/set_mode/<new_mode>")
        def set_mode_route(new_mode):
            from brain.brain import set_mode
            result = set_mode(new_mode)
            return json.dumps({"status": "success", "message": result})

        # ── File Upload Endpoint ────────────────────────────────────────────────
        @self.app.route("/upload", methods=["POST"])
        def upload_file():
            """
            Accepts multipart/form-data file uploads.
            Saves to uploads/, scans with file_processor, injects context into brain.
            Returns JSON with scan result metadata.
            """
            if "file" not in request.files:
                return jsonify({"success": False, "error": "No file provided"}), 400

            file = request.files["file"]
            if file.filename == "":
                return jsonify({"success": False, "error": "Empty filename"}), 400

            # Ensure upload directory exists
            os.makedirs(UPLOAD_DIR, exist_ok=True)

            # Sanitize filename and save
            from werkzeug.utils import secure_filename
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_DIR, filename)

            # Handle duplicate names
            if os.path.exists(filepath):
                base, ext = os.path.splitext(filename)
                from datetime import datetime
                filename = f"{base}_{datetime.now().strftime('%H%M%S')}{ext}"
                filepath = os.path.join(UPLOAD_DIR, filename)

            file.save(filepath)
            print(f"[Upload] Saved file: {filepath}")

            # Run file scanner in background thread to not block response
            def scan_and_notify():
                try:
                    from tools.file_processor import scan_file, get_context_injection
                    scan_result = scan_file(filepath)

                    # Inject context into brain global state
                    try:
                        import brain.brain as brain
                        context_str = get_context_injection(scan_result)
                        brain.injected_file_context = context_str
                        brain.injected_file_name = scan_result.get("filename", filename)
                        brain.injected_file_category = scan_result.get("category", "unknown")
                        brain.injected_file_path = filepath
                    except Exception as e:
                        print(f"[Upload] Brain context injection error: {e}")

                    # Broadcast file scan result to all WebSocket clients
                    payload = {
                        "type": "file_scanned",
                        "filename": scan_result.get("filename"),
                        "category": scan_result.get("category"),
                        "icon": scan_result.get("icon"),
                        "preview": scan_result.get("preview", "")[:300],
                        "file_size": scan_result.get("file_size"),
                        "success": scan_result.get("success"),
                        "error": scan_result.get("error"),
                        "filepath_url": f"uploads/{filename}" if scan_result.get("category") == "image" else None,
                        "pages": scan_result.get("pages"),
                        "slides": scan_result.get("slides"),
                        "sheets": scan_result.get("sheets"),
                        "lines": scan_result.get("lines"),
                    }
                    self._broadcast(payload)

                    # Trigger Anju's automatic analysis response
                    if self.on_file_upload and scan_result.get("success"):
                        self.on_file_upload(scan_result)

                except Exception as e:
                    print(f"[Upload] Scan error: {e}")
                    self._broadcast({
                        "type": "file_scanned",
                        "success": False,
                        "error": str(e),
                        "filename": filename
                    })

            threading.Thread(target=scan_and_notify, daemon=True).start()

            return jsonify({
                "success": True,
                "filename": filename,
                "message": "File uploaded. Scanning in progress..."
            })

        # ── Download Modified File Endpoint ────────────────────────────────────
        @self.app.route("/download/<path:filename>")
        def download_file(filename):
            """Serves files from uploads/modified/ for download."""
            modified_dir = os.path.join(UPLOAD_DIR, "modified")
            return send_from_directory(modified_dir, filename, as_attachment=True)

        # WebSocket endpoint
        @self.sock.route("/ws")
        def ws_handler(ws):
            print(f"[WS] New client connected: {ws}")
            with self.clients_lock:
                self.clients.add(ws)

            # Send current state to newly connected client
            try:
                ws.send(json.dumps({"type": "status", "value": self.current_status}))
                with self.history_lock:
                    for msg in self.message_history:
                        # Append an 'is_history' flag so frontend doesn't re-speak them
                        history_msg = dict(msg)
                        history_msg["is_history"] = True
                        ws.send(json.dumps(history_msg))
            except Exception as e:
                print(f"[WS] Error sending initial state: {e}")

            try:
                while True:
                    # Keep connection alive (block until client disconnects)
                    msg = ws.receive()
                    if msg is None:  # Graceful disconnect
                        break

                    try:
                        data = json.loads(msg)
                        if data.get("type") == "chat" and self.on_message:
                            text = data.get("text")
                            source = data.get("source", "text")
                            # Run callback in a separate thread to avoid blocking the WS loop
                            threading.Thread(target=self.on_message, args=(text, source), daemon=True).start()
                    except json.JSONDecodeError:
                        pass  # Non-JSON message
            except Exception as e:
                print(f"[WS] Client error: {e}")
            finally:
                print(f"[WS] Client disconnected: {ws}")
                with self.clients_lock:
                    self.clients.discard(ws)

    def _broadcast(self, payload: dict):
        """Send a JSON payload to all connected WebSocket clients."""
        data = json.dumps(payload)
        dead = set()
        with self.clients_lock:
            for ws in self.clients:
                try:
                    ws.send(data)
                except Exception:
                    dead.add(ws)
            self.clients -= dead

    def update_status(self, status: str):
        """Called by the assistant to update status in the browser."""
        self.current_status = status
        self._broadcast({"type": "status", "value": status})

    def add_message(self, sender: str, text: str, speak_flag: bool = False, image: str = None, emotion: str = None):
        """Push a conversation message to the browser log.

        CLEAN VOICE PIPELINE:
        - Generates TTS SYNCHRONOUSLY before sending the message
        - Sends text AND audio together in one payload
        - No background thread, no async race conditions, no dual voice
        - Frontend simply plays the audio — one source, one voice
        """
        # 1. Generate TTS first (synchronous) — one clean pipeline
        audio_b64 = None
        if speak_flag and sender == "Anju":
            try:
                from voice.tts import generate_tts_base64
                audio_b64 = generate_tts_base64(text, emotion)
            except Exception as e:
                print(f"[Dashboard] TTS Error: {e}")

        # 2. Send message with audio (or without if TTS failed)
        payload = {
            "type": "message",
            "sender": sender,
            "text": text,
            "speak": speak_flag,
            "image": image,
            "emotion": emotion,
            "audio": audio_b64  # Audio included directly — no async race
        }
        with self.history_lock:
            # Strip audio from history to keep memory lean (50-200KB per audio msg)
            history_entry = dict(payload)
            history_entry["audio"] = None
            self.message_history.append(history_entry)
            if len(self.message_history) > 50:
                self.message_history.pop(0)
        self._broadcast(payload)

    def run(self):
        """Start Flask server and open the browser. Blocks forever."""
        def open_browser():
            import time
            time.sleep(1.2)  # Give Flask a moment to start
            webbrowser.open(f"http://{self.host}:{self.port}")

        threading.Thread(target=open_browser, daemon=True).start()

        # Run Flask (suppress reloader and noisy logs)
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        self.app.run(
            host=self.host,
            port=self.port,
            debug=False,
            use_reloader=False,
            threaded=True
        )


def start_dashboard():
    dashboard = AnjuDashboard()
    return dashboard


if __name__ == "__main__":
    db = start_dashboard()
    db.run()
