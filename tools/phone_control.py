"""
Anju AI — Phone Control Module
Connects to Android devices wirelessly via ADB (Android Debug Bridge).
Allows Anju to perform actions on Sathwik's phone through voice/text commands.
"""
import os
import re
import subprocess
import time
import threading
from datetime import datetime
from typing import Optional

# ── Constants ──────────────────────────────────────────────────────────────
# Auto-detect ADB: check local install first, then system PATH
_LOCAL_ADB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "adb_tools", "platform-tools", "adb.exe")
if os.path.exists(_LOCAL_ADB):
    ADB_PATH = _LOCAL_ADB
else:
    ADB_PATH = "adb"  # Fall back to system PATH
CONNECTION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "memory", "phone_config.json")

# ── Connection State ───────────────────────────────────────────────────────
_connected = False
_device_ip = None
_connection_lock = threading.Lock()
_last_connection_check = 0
_connection_check_interval = 30  # seconds

# ── Known App Package Names ───────────────────────────────────────────────
APP_PACKAGES = {
    "whatsapp": "com.whatsapp",
    "telegram": "org.telegram.messenger",
    "instagram": "com.instagram.android",
    "facebook": "com.facebook.katana",
    "facebook messenger": "com.facebook.orca",
    "twitter": "com.twitter.android",
    "x": "com.twitter.android",
    "snapchat": "com.snapchat.android",
    "youtube": "com.google.android.youtube",
    "spotify": "com.spotify.music",
    "netflix": "com.netflix.mediaclient",
    "chrome": "com.android.chrome",
    "gmail": "com.google.android.gm",
    "maps": "com.google.android.apps.maps",
    "photos": "com.google.android.apps.photos",
    "camera": "com.google.android.GoogleCamera",
    "clock": "com.google.android.deskclock",
    "calculator": "com.google.android.calculator",
    "settings": "com.android.settings",
    "play store": "com.android.vending",
    "dialer": "com.google.android.dialer",
    "contacts": "com.google.android.contacts",
    "messages": "com.google.android.apps.messaging",
    "files": "com.google.android.apps.nbu.files",
    "calendar": "com.google.android.calendar",
    "phone": "com.google.android.dialer",
    "discord": "com.discord",
    "reddit": "com.reddit.frontpage",
    "linkedin": "com.linkedin.android",
    "github": "com.github.android",
    "stack overflow": "com.stackexchange.stackoverflow",
}

# ── Key Event Codes ───────────────────────────────────────────────────────
KEYCODE = {
    "home": 3,
    "back": 4,
    "call": 5,
    "end_call": 6,
    "volume_up": 24,
    "volume_down": 25,
    "power": 26,
    "camera": 27,
    "clear": 28,
    "enter": 66,
    "menu": 82,
    "search": 84,
    "play_pause": 85,
    "stop": 86,
    "next_track": 87,
    "previous_track": 88,
    "volume_mute": 164,
    "notification": 83,
    "recent_apps": 187,
}

# ══════════════════════════════════════════════════════════════════════════
#  ADB EXECUTION HELPER
# ══════════════════════════════════════════════════════════════════════════

def _run_adb(args: list, timeout: int = 15) -> tuple:
    """
    Execute an ADB command and return (stdout, stderr, success).
    Automatically prepends 'adb' and optional device serial.
    """
    try:
        cmd = [ADB_PATH] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode == 0
    except FileNotFoundError:
        return "", "ADB not found. Install Android Platform Tools and add adb to PATH.", False
    except subprocess.TimeoutExpired:
        return "", "ADB command timed out.", False
    except Exception as e:
        return "", str(e), False


def _run_shell(command: str, timeout: int = 10) -> tuple:
    """Execute a shell command on the connected Android device."""
    return _run_adb(["shell", command], timeout=timeout)


# ══════════════════════════════════════════════════════════════════════════
#  CONNECTION MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════

def find_phone() -> Optional[str]:
    """
    Auto-discover phone on the network using ADB.
    Returns device IP if found, None otherwise.
    """
    # Start ADB server
    _run_adb(["start-server"])

    # List connected devices
    stdout, _, success = _run_adb(["devices"])
    if not success:
        return None

    # Check for already connected devices
    for line in stdout.split("\n"):
        line = line.strip()
        if line and "device" in line and "List" not in line:
            ip_part = line.split()[0]
            if ":" in ip_part:  # IP:port format
                return ip_part.split(":")[0]

    return None


def connect_phone(ip: str = None, port: int = 5555) -> str:
    """
    Connect to Android phone wirelessly via ADB over TCP/IP.

    Args:
        ip: Phone IP address. If None, tries to auto-discover.
        port: ADB port (default 5555).

    Returns:
        Status message.
    """
    global _connected, _device_ip

    with _connection_lock:
        # Auto-discover if no IP given
        if not ip:
            found = find_phone()
            if found:
                ip = found
            else:
                return (
                    "I need your phone's IP address to connect wirelessly, Sathwik. "
                    "You can find it in your phone's Wi-Fi settings, or connect via USB first "
                    "and run: adb tcpip 5555"
                )

        # Connect to device
        stdout, stderr, success = _run_adb(["connect", f"{ip}:{port}"])

        if success or "connected" in stdout.lower():
            _connected = True
            _device_ip = ip
            _save_connection(ip, port)
            return f"Successfully connected to your phone at {ip}, Sathwik. I'm ready to help."
        else:
            return (
                f"I couldn't connect to {ip}:{port}. Make sure:\n"
                f"1. USB Debugging is enabled in Developer Options on your phone\n"
                f"2. Your phone is on the same Wi-Fi network\n"
                f"3. Wireless Debugging is enabled (Android 11+)\n"
                f"Error: {stderr or stdout}"
            )


def disconnect_phone() -> str:
    """Disconnect from the phone."""
    global _connected, _device_ip

    with _connection_lock:
        if _device_ip:
            _run_adb(["disconnect", _device_ip])

        _connected = False
        _device_ip = None
        _delete_connection()
        return "Phone disconnected, Sathwik. I'll be here when you need me to reconnect."


def is_connected() -> bool:
    """Check if phone is currently connected and responsive."""
    global _connected, _last_connection_check

    if not _connected:
        return False

    now = time.time()
    if now - _last_connection_check < _connection_check_interval:
        return _connected

    # Verify connection is still alive
    _last_connection_check = now
    stdout, _, success = _run_adb(["get-state"])
    if success and "device" in stdout:
        return True

    _connected = False
    return False


def _save_connection(ip: str, port: int):
    """Save connection details for auto-reconnect."""
    try:
        import json
        config_dir = os.path.dirname(CONNECTION_FILE)
        os.makedirs(config_dir, exist_ok=True)
        with open(CONNECTION_FILE, "w") as f:
            json.dump({"ip": ip, "port": port, "timestamp": datetime.now().isoformat()}, f)
    except Exception:
        pass


def _delete_connection():
    """Remove saved connection details."""
    try:
        if os.path.exists(CONNECTION_FILE):
            os.remove(CONNECTION_FILE)
    except Exception:
        pass


def auto_reconnect() -> str:
    """
    Attempt to restore last known ADB connection.
    Called automatically on system startup.
    """
    try:
        import json
        if os.path.exists(CONNECTION_FILE):
            with open(CONNECTION_FILE, "r") as f:
                config = json.load(f)
            if config.get("ip"):
                return connect_phone(config["ip"], config.get("port", 5555))
    except Exception:
        pass
    return "No saved phone connection found."


# ══════════════════════════════════════════════════════════════════════════
#  PHONE ACTIONS
# ══════════════════════════════════════════════════════════════════════════

def get_phone_status() -> dict:
    """Get comprehensive phone status information."""
    if not is_connected():
        return {"connected": False, "error": "Phone not connected"}

    info = {"connected": True}

    # Get battery level
    stdout, _, _ = _run_shell("dumpsys battery | grep level")
    if stdout:
        match = re.search(r"level:\s*(\d+)", stdout)
        if match:
            info["battery"] = int(match.group(1))

    # Get device name
    stdout, _, _ = _run_shell("getprop ro.product.model")
    if stdout:
        info["device_name"] = stdout.strip()

    # Get Android version
    stdout, _, _ = _run_shell("getprop ro.build.version.release")
    if stdout:
        info["android_version"] = stdout.strip()

    return info


def open_app(app_name: str) -> str:
    """
    Open an app on the phone by name.
    Uses a curated package name dictionary with fallback to package search.
    """
    if not is_connected():
        return "Phone is not connected, Sathwik. Say 'connect my phone' first."

    name = app_name.lower().strip()

    # Direct lookup
    package = APP_PACKAGES.get(name)

    if not package:
        # Try to find the package by searching installed packages
        stdout, _, success = _run_shell(f"pm list packages | grep -i {name.replace(' ', '')}")
        if success and stdout:
            lines = stdout.strip().split("\n")
            if lines and "package:" in lines[0]:
                package = lines[0].replace("package:", "").strip()

    if not package:
        # Try launching app by name via monkey
        stdout, _, success = _run_shell(f"monkey -p {name} -c android.intent.category.LAUNCHER 1 2>/dev/null")
        if success:
            return f"Attempting to open {app_name} on your phone, Sathwik..."
        return (
            f"I couldn't find the app '{app_name}' on your phone, Sathwik. "
            f"Try saying 'list apps' to see available apps."
        )

    # Launch the app
    stdout, _, success = _run_shell(
        f"monkey -p {package} -c android.intent.category.LAUNCHER 1 2>/dev/null"
    )

    if success or "events" in stdout:
        return f"Opening {app_name.capitalize()} on your phone now, Sathwik."
    else:
        return f"I tried to open {app_name} but encountered an issue. The app may not be installed."


def send_sms(phone_number: str, message: str) -> str:
    """
    Send an SMS message from the phone via ADB intent.

    Note: On Android 14+, this requires specific permissions via adb shell appops.
    """
    if not is_connected():
        return "Phone is not connected, Sathwik."

    # Clean the phone number
    number = re.sub(r"[^\d+]", "", phone_number)
    if not number:
        return "I need a valid phone number, Sathwik."

    # Use Android intent to open SMS with pre-filled content
    encoded_msg = message.replace(" ", "%20").replace("\n", "%0A")
    cmd = (
        f'am start -a android.intent.action.SENDTO '
        f'-d "sms:{number}" '
        f'--es "sms_body" "{message}" '
        f'--ez "exit_on_sent" true '
        f'2>/dev/null'
    )

    stdout, _, success = _run_shell(cmd)

    if success:
        # Try to auto-send by simulating Enter key
        _run_shell("input keyevent 66", timeout=3)
        return f"SMS sent to {number}, Sathwik. Message content is private, as it should be."
    else:
        return (
            f"I've opened the SMS composer for {number}. The message is ready - "
            f"you may need to tap send on your phone due to Android security."
        )


def take_photo() -> str:
    """
    Take a photo using the phone camera and save it to the uploads directory.
    """
    if not is_connected():
        return "Phone is not connected, Sathwik."

    # Open camera
    _run_shell("am start -a android.media.action.STILL_IMAGE_CAMERA 2>/dev/null")
    time.sleep(1.5)  # Wait for camera to load

    # Tap shutter button (center of screen - approximate)
    _run_shell("input tap 540 960 2>/dev/null")
    time.sleep(1)  # Wait for photo to be taken

    # Go back to home
    _run_shell("input keyevent 3 2>/dev/null")

    # Try to pull the latest photo from DCIM
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    local_path = os.path.join(uploads_dir, f"phone_photo_{timestamp}.jpg")

    # Pull latest photo
    stdout, _, pull_success = _run_adb([
        "shell", "ls", "-t", "/sdcard/DCIM/Camera/", "2>/dev/null", "|", "head", "-1"
    ], timeout=10)

    if pull_success and stdout.strip():
        latest_photo = stdout.strip()
        _run_adb(["pull", f"/sdcard/DCIM/Camera/{latest_photo}", local_path], timeout=15)

        if os.path.exists(local_path):
            return f"Photo captured and saved to uploads, Sathwik! 📸"

    return "Camera opened on your phone, Sathwik. The photo should be in your gallery."


def take_screenshot() -> str:
    """
    Take a screenshot of the phone screen and save it locally.
    """
    if not is_connected():
        return "Phone is not connected, Sathwik."

    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    local_path = os.path.join(uploads_dir, f"phone_screen_{timestamp}.png")

    # Take screenshot on device
    _run_shell("screencap -p /sdcard/screen_temp.png", timeout=10)

    # Pull to computer
    _, _, pull_success = _run_adb(["pull", "/sdcard/screen_temp.png", local_path], timeout=15)

    # Clean up
    _run_shell("rm /sdcard/screen_temp.png")

    if pull_success and os.path.exists(local_path):
        size_kb = os.path.getsize(local_path) / 1024
        return f"Screenshot captured! ({size_kb:.0f} KB) — It's saved in uploads."
    else:
        return "I tried to capture your phone screen but ran into an issue."


def get_notifications() -> str:
    """Retrieve recent notifications from the phone."""
    if not is_connected():
        return "Phone is not connected, Sathwik."

    stdout, _, success = _run_shell("dumpsys notification --noredact 2>/dev/null | grep -A 2 'tickerText=' | head -30", timeout=10)

    if success and stdout:
        notifications = [line.strip() for line in stdout.split("\n") if line.strip()]
        if notifications:
            # Group and deduplicate
            seen = set()
            unique = []
            for n in notifications:
                if n not in seen:
                    seen.add(n)
                    unique.append(n.replace("tickerText=", "").strip())

            result = "Recent notifications on your phone:\n" + "\n".join(unique[:8])
            return result

    return "No recent notifications found, or notification access is restricted."


def send_keyevent(key_name: str) -> str:
    """
    Send a key event to the phone (home, back, volume, play/pause, etc.)
    """
    if not is_connected():
        return "Phone is not connected, Sathwik."

    key = key_name.lower().replace(" ", "_")
    key_code = KEYCODE.get(key)

    if key_code is None:
        available = ", ".join(KEYCODE.keys())
        return f"Key '{key_name}' not recognized. Available keys: {available}"

    stdout, _, success = _run_shell(f"input keyevent {key_code}")

    key_labels = {
        "home": "Going home", "back": "Going back", "play_pause": "Toggling play/pause",
        "volume_up": "Turning volume up", "volume_down": "Turning volume down",
        "volume_mute": "Muting volume", "next_track": "Skipping to next track",
        "previous_track": "Going to previous track", "notification": "Opening notifications",
        "recent_apps": "Opening recent apps", "camera": "Opening camera",
    }

    label = key_labels.get(key, f"Sending {key_name}")
    return f"{label} on your phone, Sathwik."


def set_volume(level: int) -> str:
    """
    Set media volume (0-15 on most Android devices).
    """
    if not is_connected():
        return "Phone is not connected, Sathwik."

    level = max(0, min(15, level))
    _run_shell(f"media volume --show --stream 3 --set {level}", timeout=5)

    if level == 0:
        return "Phone volume muted, Sathwik."
    elif level <= 5:
        return f"Phone volume set to low ({level}/15)."
    elif level <= 10:
        return f"Phone volume set to medium ({level}/15)."
    else:
        return f"Phone volume set to high ({level}/15)."


def list_installed_apps(search: str = "") -> str:
    """
    List installed apps on the phone, optionally filtered by search term.
    """
    if not is_connected():
        return "Phone is not connected, Sathwik."

    cmd = "pm list packages -3 2>/dev/null"  # Only user-installed apps
    if search:
        cmd = f"pm list packages 2>/dev/null | grep -i {search}"

    stdout, _, success = _run_shell(cmd, timeout=10)

    if success and stdout:
        packages = []
        for line in stdout.split("\n"):
            pkg = line.replace("package:", "").strip()
            if pkg:
                # Extract app name from package
                name = pkg.split(".")[-1] if "." in pkg else pkg
                packages.append(name)

        if packages:
            result = f"Found {len(packages)} app(s):\n" + ", ".join(sorted(packages)[:30])
            if len(packages) > 30:
                result += f"\n... and {len(packages) - 30} more"
            return result

    return "No apps found or unable to access app list."


def get_battery() -> str:
    """Get battery status from the phone."""
    if not is_connected():
        return "Phone is not connected, Sathwik."

    stdout, _, success = _run_shell("dumpsys battery", timeout=5)

    if success and stdout:
        level = "?"
        status = "?"
        for line in stdout.split("\n"):
            line = line.strip()
            if "level:" in line:
                level = line.split(":")[1].strip()
            if "status:" in line and "AC" not in line and "USB" not in line:
                raw = line.split(":")[1].strip()
                status_map = {"1": "unknown", "2": "charging", "3": "discharging", "4": "not charging", "5": "full"}
                status = status_map.get(raw, raw)

        return f"Your phone battery is at **{level}%** and is currently **{status}**, Sathwik."

    return "Could not read battery information."


def get_phone_info() -> str:
    """
    Get detailed information about the connected phone.
    """
    if not is_connected():
        return "Phone is not connected, Sathwik."

    info = []

    # Model
    stdout, _, _ = _run_shell("getprop ro.product.model")
    if stdout: info.append(f"📱 Model: {stdout.strip()}")

    # Manufacturer
    stdout, _, _ = _run_shell("getprop ro.product.manufacturer")
    if stdout: info.append(f"🏭 Manufacturer: {stdout.strip()}")

    # Android version
    stdout, _, _ = _run_shell("getprop ro.build.version.release")
    if stdout: info.append(f"🤖 Android: {stdout.strip()}")

    # Battery
    stdout, _, _ = _run_shell("dumpsys battery | grep -E 'level|status'")
    if stdout:
        for line in stdout.split("\n"):
            info.append(f"🔋 {line.strip()}")

    # IP address
    stdout, _, _ = _run_shell("ip addr show wlan0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d/ -f1")
    if stdout:
        info.append(f"🌐 IP: {stdout.strip()}")

    return "\n".join(info) if info else "Phone status available but details couldn't be read."


def connect_via_usb_then_wireless(port: int = 5555) -> str:
    """
    Two-step connection: Restart ADB in TCPIP mode via USB, then connect wirelessly.
    Useful for initial setup when the phone is connected via USB.
    """
    # Ensure ADB server is running
    _run_adb(["start-server"])

    # Check USB device
    stdout, _, _ = _run_adb(["devices"])
    has_usb = False
    for line in stdout.split("\n"):
        if line.strip() and "device" in line and "List" not in line and ":" not in line:
            has_usb = True
            break

    if not has_usb:
        return (
            "No USB device detected. Please connect your phone via USB cable first, "
            "or provide your phone's IP address directly.\n\n"
            "Commands to run on phone:\n"
            "1. Enable Developer Options (Settings > About Phone > Build Number tap 7x)\n"
            "2. Enable USB Debugging in Developer Options\n"
            "3. Connect via USB cable"
        )

    # Restart ADB in TCPIP mode on the phone
    stdout, stderr, success = _run_adb(["tcpip", str(port)])

    if success:
        # Get phone IP
        ip_stdout, _, _ = _run_shell("ip addr show wlan0 2>/dev/null | grep 'inet ' | awk '{print $2}'")
        if ip_stdout:
            ip = ip_stdout.strip().split("/")[0]
            return connect_phone(ip, port)
        else:
            return (
                "ADB is now in TCPIP mode. Please provide your phone's IP address "
                "so I can connect wirelessly. Say: 'connect phone at <IP>'"
            )
    else:
        return f"Failed to switch ADB to TCPIP mode: {stderr or stdout}"


def cmd_help() -> str:
    """Return available phone control commands for the help system."""
    return """**📱 Phone Control Commands:**
• "Connect my phone" — Connect wirelessly via ADB
• "Connect phone via USB" — Set up wireless via USB tethering
• "Open WhatsApp" — Open any app on your phone
• "Take a photo" — Use your phone's camera
• "Screenshot my phone" — Capture phone screen
• "Send SMS to <number>" — Send a text message
• "Call <contact>" — Make a call
• "What's my battery?" — Check battery level
• "Volume up/down" — Control phone volume
• "Play/Pause" — Control media playback
• "List my apps" — See installed apps
• "Phone notifications" — Read recent notifications
• "Disconnect phone" — Disconnect Anju from your phone
• "Phone status" — Show detailed phone info"""
