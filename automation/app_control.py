import os
import subprocess
import webbrowser
import winreg
import glob

def _try_launch(path: str, label: str) -> str | None:
    """Try to launch a path. Returns result string on success, None on failure."""
    try:
        os.startfile(path)
        return f"Opening {label}"
    except Exception:
        pass
    try:
        subprocess.Popen([path], shell=False)
        return f"Opening {label}"
    except Exception:
        pass
    return None

def _registry_search(app_key: str) -> str | None:
    """
    Search Windows Registry App Paths for installed applications.
    Covers Spotify, Discord, VLC, Steam, Chrome, etc.
    """
    reg_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths",
    ]
    hives = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]

    for hive in hives:
        for reg_path in reg_paths:
            try:
                with winreg.OpenKey(hive, reg_path) as root:
                    i = 0
                    while True:
                        try:
                            sub_name = winreg.EnumKey(root, i)
                            i += 1
                            # Match app name against registry key name
                            if app_key in sub_name.lower().replace(".exe", ""):
                                try:
                                    with winreg.OpenKey(root, sub_name) as sub:
                                        exe_path, _ = winreg.QueryValueEx(sub, "")
                                        if exe_path and os.path.exists(exe_path):
                                            result = _try_launch(exe_path, sub_name.replace(".exe", ""))
                                            if result:
                                                return result
                                except Exception:
                                    pass
                        except OSError:
                            break
            except Exception:
                continue
    return None

def _uninstall_registry_search(app_key: str) -> str | None:
    """
    Search Uninstall registry keys to find InstallLocation for broader app detection.
    Catches things like Telegram, WhatsApp, Notion, etc.
    """
    reg_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]
    hives = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]

    for hive in hives:
        for reg_path in reg_paths:
            try:
                with winreg.OpenKey(hive, reg_path) as root:
                    i = 0
                    while True:
                        try:
                            sub_name = winreg.EnumKey(root, i)
                            i += 1
                            try:
                                with winreg.OpenKey(root, sub_name) as sub:
                                    try:
                                        display_name, _ = winreg.QueryValueEx(sub, "DisplayName")
                                        if app_key in display_name.lower():
                                            # Try DisplayIcon first (usually the exe path)
                                            try:
                                                icon, _ = winreg.QueryValueEx(sub, "DisplayIcon")
                                                exe = icon.strip('"').split(",")[0].strip()
                                                if exe.endswith(".exe") and os.path.exists(exe):
                                                    result = _try_launch(exe, display_name)
                                                    if result:
                                                        return result
                                            except Exception:
                                                pass
                                            # Try InstallLocation + walk for exe
                                            try:
                                                install_loc, _ = winreg.QueryValueEx(sub, "InstallLocation")
                                                if install_loc and os.path.isdir(install_loc):
                                                    for f in os.listdir(install_loc):
                                                        if app_key in f.lower() and f.endswith(".exe"):
                                                            full = os.path.join(install_loc, f)
                                                            result = _try_launch(full, display_name)
                                                            if result:
                                                                return result
                                            except Exception:
                                                pass
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                        except OSError:
                            break
            except Exception:
                continue
    return None

def _startmenu_search(app_key: str) -> str | None:
    """Walk Start Menu for .lnk / .exe files matching the app name."""
    search_dirs = [
        os.path.join(os.environ.get("ProgramData", ""), r"Microsoft\Windows\Start Menu\Programs"),
        os.path.join(os.environ.get("APPDATA", ""),    r"Microsoft\Windows\Start Menu\Programs"),
    ]
    for s_dir in search_dirs:
        if not os.path.isdir(s_dir):
            continue
        for root, dirs, files in os.walk(s_dir):
            for file in files:
                fname = file.lower()
                if app_key in fname and fname.endswith((".lnk", ".exe")):
                    full_path = os.path.join(root, file)
                    result = _try_launch(full_path, file)
                    if result:
                        return result
    return None

def _common_dirs_search(app_key: str) -> str | None:
    """Search common installation directories for matching executables."""
    search_dirs = [
        os.environ.get("ProgramFiles", ""),
        os.environ.get("ProgramFiles(x86)", ""),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Apps"),
        os.environ.get("LOCALAPPDATA", ""),
        os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
    ]
    for s_dir in search_dirs:
        if not s_dir or not os.path.isdir(s_dir):
            continue
        for root, dirs, files in os.walk(s_dir):
            # Skip deep dives into irrelevant folders
            dirs[:] = [d for d in dirs if d.lower() not in ("windows", "system32", "syswow64", "drivers", "temp")]
            for file in files:
                fname = file.lower()
                if app_key in fname and fname.endswith(".exe"):
                    # Prefer exe whose name closely matches the query
                    full_path = os.path.join(root, file)
                    result = _try_launch(full_path, file)
                    if result:
                        return result
    return None

def open_application(app_name: str) -> str:
    """
    Universal application launcher for Windows.
    Uses a layered approach:
    1. Quick launch dict (instant for known apps)
    2. Windows Registry App Paths (covers all properly installed apps)
    3. Windows Uninstall registry (broader coverage)
    4. Start Menu link search
    5. Common installation directories
    6. 'where.exe' PATH lookup
    7. Final fallback: os.startfile / subprocess
    """
    app_key = app_name.strip().lower()

    # ─── 1. QUICK LAUNCH DICT ───────────────────────────────────────────────
    quick_launch = {
        "notepad":          ["notepad.exe"],
        "calculator":       ["calc.exe"],
        "paint":            ["mspaint.exe"],
        "cmd":              ["cmd.exe"],
        "command prompt":   ["cmd.exe"],
        "terminal":         ["wt.exe"],
        "powershell":       ["powershell.exe"],
        "task manager":     ["taskmgr.exe"],
        "file explorer":    ["explorer.exe"],
        "explorer":         ["explorer.exe"],
        "control panel":    ["control.exe"],
        "snipping tool":    ["SnippingTool.exe"],
        "word":             ["winword.exe"],
        "excel":            ["excel.exe"],
        "powerpoint":       ["powerpnt.exe"],
        "outlook":          ["outlook.exe"],
        "teams":            ["msteams.exe"],
        "edge":             ["msedge.exe"],
        "microsoft edge":   ["msedge.exe"],
        "chrome": [
            os.path.join(os.environ.get("ProgramFiles", ""),       r"Google\Chrome\Application\chrome.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", ""),  r"Google\Chrome\Application\chrome.exe"),
        ],
        "google chrome": [
            os.path.join(os.environ.get("ProgramFiles", ""),       r"Google\Chrome\Application\chrome.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", ""),  r"Google\Chrome\Application\chrome.exe"),
        ],
        "firefox": [
            os.path.join(os.environ.get("ProgramFiles", ""),       r"Mozilla Firefox\firefox.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", ""),  r"Mozilla Firefox\firefox.exe"),
        ],
        "vs code": [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Programs\Microsoft VS Code\Code.exe"),
        ],
        "visual studio code": [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Programs\Microsoft VS Code\Code.exe"),
        ],
        "spotify": [
            os.path.join(os.environ.get("APPDATA", ""), r"Spotify\Spotify.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\WindowsApps\Spotify.exe"),
        ],
        "vlc": [
            os.path.join(os.environ.get("ProgramFiles", ""),       r"VideoLAN\VLC\vlc.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", ""),  r"VideoLAN\VLC\vlc.exe"),
        ],
        "discord": [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Discord\Update.exe"),
            os.path.join(os.environ.get("APPDATA", ""), r"discord\Discord.exe"),
        ],
        "steam": [
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), r"Steam\steam.exe"),
            os.path.join(os.environ.get("ProgramFiles", ""),       r"Steam\steam.exe"),
        ],
        "whatsapp": [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), r"WhatsApp\WhatsApp.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Packages\5319275A.WhatsAppDesktop_cv1g1gvanyjgm\LocalState\WhatsApp.exe"),
            r"whatsapp://", # URI scheme fallback
        ],
        "telegram": [
            os.path.join(os.environ.get("APPDATA", ""), r"Telegram Desktop\Telegram.exe"),
        ],
        "zoom": [
            os.path.join(os.environ.get("APPDATA", ""), r"Zoom\bin\Zoom.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Zoom\bin\Zoom.exe"),
        ],
        "obs": [
            os.path.join(os.environ.get("ProgramFiles", ""),      r"obs-studio\bin\64bit\obs64.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), r"obs-studio\bin\32bit\obs32.exe"),
        ],
        "settings": ["ms-settings:"],
        "youtube": ["https://www.youtube.com"],
        "netflix": ["https://www.netflix.com"],
        "facebook": ["https://www.facebook.com"],
        "instagram": ["https://www.instagram.com"],
        "twitter": ["https://twitter.com"],
        "x": ["https://x.com"],
        "reddit": ["https://www.reddit.com"],
        "github": ["https://github.com"],
        "chatgpt": ["https://chat.openai.com"],
        "gmail": ["https://mail.google.com"],
    }

    matched_key = None
    for key in quick_launch:
        if key in app_key or app_key in key:
            matched_key = key
            break

    if matched_key:
        for path in quick_launch[matched_key]:
            if path.startswith("http") or path.startswith("ms-") or path.count("://") > 0:
                webbrowser.open(path)
                return f"Opening {matched_key}"
            elif os.path.isabs(path):
                if os.path.exists(path):
                    result = _try_launch(path, matched_key)
                    if result:
                        return result
            else:
                result = _try_launch(path, matched_key)
                if result:
                    return result

    # ─── 2. REGISTRY – App Paths ────────────────────────────────────────────
    result = _registry_search(app_key)
    if result:
        return result

    # ─── 3. REGISTRY – Uninstall entries ────────────────────────────────────
    result = _uninstall_registry_search(app_key)
    if result:
        return result

    # ─── 4. START MENU SEARCH ───────────────────────────────────────────────
    result = _startmenu_search(app_key)
    if result:
        return result

    # ─── 5. BROWSER FALLBACK for browser-related queries ────────────────────
    if any(kw in app_key for kw in ("chrome", "browser", "google", "firefox", "edge")):
        webbrowser.open("https://www.google.com")
        return "Opening browser"

    # ─── 6. 'where.exe' PATH LOOKUP ─────────────────────────────────────────
    try:
        result_bytes = subprocess.check_output(
            ["where", f"*{app_key}*"], stderr=subprocess.DEVNULL, timeout=3
        )
        paths = result_bytes.decode().strip().splitlines()
        for p in paths:
            p = p.strip()
            if p.endswith(".exe") and os.path.exists(p):
                result = _try_launch(p, app_name)
                if result:
                    return result
    except Exception:
        pass

    # ─── 7. COMMON DIRS SEARCH ──────────────────────────────────────────────
    result = _common_dirs_search(app_key)
    if result:
        return result

    # ─── 8. FINAL FALLBACK ──────────────────────────────────────────────────
    try:
        os.startfile(app_name)
        return f"Trying to open {app_name}"
    except Exception:
        pass

    # If it fails completely, maybe they just wanted a website or google search for the app
    try:
        import urllib.parse
        safe_app = urllib.parse.quote(app_name)
        webbrowser.open(f"https://www.google.com/search?q={safe_app}")
        return f"I couldn't find an installed app named '{app_name}'. I have opened a Google search for it instead."
    except Exception:
        return f"Sorry, I couldn't find '{app_name}' on your system."
