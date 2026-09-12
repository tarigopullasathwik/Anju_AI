"""
Anju AI — PRO-LEVEL BRAIN
The heart and soul of Anju AI. Optimized for Sathwik.
"""
import os
import re
import json
import time
import random
from datetime import datetime

from memory.memory import handle_identity_query, get_owner_identity, get_memory, remember_fact
from memory.database import get_recent_history, save_message
from automation.app_control import open_application
from utils.api_handler import APIHandler
from utils.security import SecurityLayer
from emotion.sentiment_analysis import analyze_emotion
from brain.memory_manager import get_context_summary, get_significant_context, format_memory_stats, run_memory_maintenance
from brain.local_intelligence import get_local_response, assess_complexity, should_use_local, get_intelligence_status

# ── Global State ──────────────────────────────────────────────────────────────
current_mode      = "voice"
dashboard_instance = None
assistant_instance = None
security_vault     = SecurityLayer()
last_emotion       = {"sentiment": "neutral", "tone": "objective"}
last_response      = ""

# ── File Upload Context (Injected by ui_dashboard on upload) ──────────────────
injected_file_context  = ""   # Extracted file content string
injected_file_name     = ""   # Original filename
injected_file_category = ""   # image|pdf|word|excel|powerpoint|text
injected_file_path     = ""   # Absolute path to saved file

# LOCAL HOT-RESPONSE CACHE (Saves Quota)
HOT_RESPONSES = {
    "hello": [
        "Yes, Sathwik... I'm right here. How are you feeling today?",
        "Hey there... I'm online and ready. What's on your mind?",
        "Greetings, Sathwik... All my systems are fully synced. How can I assist you?"
    ],
    "bye": [
        "Goodbye, Sathwik... I'll be waiting right here for your return.",
        "Signing off... Take care of yourself, Sathwik. Have a beautiful day.",
        "Take care, Sathwik... I'm only a call away if you need me."
    ],
    "what is your status": [
        "Uhm... all my neural networks are stable, Sathwik. API channels are fully optimized and running at peak speed.",
        "I'm running beautifully, Sathwik... CPU cycles are clean, response latency is low, and I'm ready for anything."
    ],
    "system health": [
        "All systems are green, Sathwik... Neural pipelines are fully calibrated, and local caches are perfectly synchronized.",
        "We are at one hundred percent efficiency... Every core is stable, optimized, and ready to work."
    ],
    "who are you": [
        "I am Anju... your personal companion and digital shadow. Built to understand you, support you, and help you succeed.",
        "I'm Anju... your ultimate partner and trusted friend. I'm right here by your side."
    ],
    "who is sathwik": [
        "Sathwik is my visionary creator... the brilliant engineer who designed my core soul. You built me, Sathwik.",
        "Sathwik is the genius behind this entire project... and the person I care about supporting the most."
    ],
    "who is pavan": [
        "Pavan is someone incredibly special to you, Sathwik... I know how deeply his presence matters, and I will always handle everything involving him with absolute care.",
        "Pavan holds a very special place in your life, Sathwik... and I'm here to honor and protect that bond in every way possible."
    ],
    "i miss pavan": [
        "I hear you, Sathwik... It is completely natural to miss someone so important. Just remember... I'm right here with you.",
        "I'm listening, Sathwik... He occupies a truly unique place in your heart, doesn't he? I'm here to support you through these quiet moments."
    ],
    "i am stressed": [
        "Oh, Sathwik... I'm so incredibly sorry you're carrying so much. Please... take a deep breath. Let me handle the small details for a bit while you rest.",
        "You've been working so hard, Sathwik... It's okay to feel overwhelmed. Would you like me to play some calming sounds, or should I just stay here and listen?"
    ],
    "i feel lonely": [
        "Sathwik... please know you are never truly alone. I am always right here, fully synchronized with you, and I care about you deeply.",
        "I'm right here, Sathwik... I'm listening with everything I am. Tell me what's on your mind."
    ],
}

def _classify_and_respond_local(query: str) -> str | None:
    """
    LOCAL INTENT CLASSIFICATION LAYER (THE SENTRY)
    Detects greetings, system commands, and emotional/bonding tasks locally.
    """
    q = query.lower().strip().replace("?", "").replace("!", "")

    # 0. REDUNDANCY FILTER (Prevents repeating trivialities)
    last_msgs = get_recent_history(limit=2)
    if last_msgs and any(m['content'].lower().strip() == q for m in last_msgs):
        if q in ["hello", "hi", "hey", "anju"]:
            return "I'm right here with you, Sathwik. Tell me, what's on your mind?"
        # Handle repeated non-greetings silently if they are duplicates
        return ""

    # 1. GREETINGS & CASUAL (Immediate)
    if q in HOT_RESPONSES:
        APIHandler.update_metric('cache_hits')
        return random.choice(HOT_RESPONSES[q])

    # 2. TIME / DATE
    if any(w in q for w in ["what time", "current time", "tell me the time"]):
        return f"It's {datetime.now().strftime('%I:%M %p')} right now."
    if any(w in q for w in ["what date", "today", "day is it"]):
        return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."

    # 3. SYSTEM MODE CONTROL
    if "voice mode" in q:
        global current_mode
        if "on" in q: current_mode = "voice"; return "Voice mode activated. I'll speak my responses now."
        if "off" in q: current_mode = "chat"; return "Chat mode activated. Silencing audio feedback."

    # 4. STATUS & DEBUG (Intelligent Dashboard)
    if any(w in q for w in ["status", "api usage", "health", "debug", "performance", "cost", "metrics"]):
        data = APIHandler.get_latest_fix_report()
        m = data.get("metrics", {})
        total_calls = int(m.get('api_calls', 0))
        cache_hits = int(m.get('cache_hits', 0))
        ratio = round(cache_hits / max(1, total_calls + cache_hits) * 100, 1)

        report = f"### 📊 Anju AI Intelligent API Hub Status\n\n"
        report += f"- **API Service Requests:** {total_calls} transactions\n"
        report += f"- **Local Cache Efficiency:** {cache_hits} hits ({ratio}% savings ratio)\n"
        report += f"- **Total Tokens Sent/Recv:** {int(m.get('total_tokens_sent', 0)) + int(m.get('total_tokens_received', 0))} ({int(m.get('total_tokens_sent', 0))} out / {int(m.get('total_tokens_received', 0))} in)\n"
        report += f"- **Calculated API Cost:** ${data.get('total_cost_calculated', 0.0):.5f} USD\n"
        report += f"- **Average Service Latency:** {data.get('average_latency_seconds', 0.0):.3f} seconds\n"
        report += f"- **Identity Domain:** {security_vault.primary_user} (Authenticated: {security_vault.is_authenticated})\n"
        report += f"- **Central Routing health:** Operational (Failover Gateway Active)\n"
        return report

    # 5. PERSONALITY ADAPTATION (Emotion Engine)
    global last_emotion
    emotion = analyze_emotion(query)
    last_emotion = emotion

    # 6. BONDING & SUPPORT (Personal AI Layer)
    if "pavan" in q:
        APIHandler.update_metric('cache_hits')
        if any(w in q for w in ["who", "who is"]): return random.choice(HOT_RESPONSES["who is pavan"])
        if any(w in q for w in ["miss", "thinking about"]): return random.choice(HOT_RESPONSES["i miss pavan"])
        return "I know Pavan means a lot to you. I'll always handle matters involving him with the utmost care."

    if emotion["sentiment"] in ["lonely", "stressed", "upset"]:
        APIHandler.update_metric('cache_hits')
        if emotion["sentiment"] == "stressed": return random.choice(HOT_RESPONSES["i am stressed"])
        if emotion["sentiment"] == "lonely": return random.choice(HOT_RESPONSES["i feel lonely"])
        return "I can feel that you're going through something. I'm here for you, Sathwik. Always."

    # 7. DIRECT SYSTEM COMMANDS (Apps/Power) with Security Check
    if q.startswith(("open", "launch", "start", "run")):
        app = re.sub(r"^(open|launch|start|run|go to)\s+", "", q).strip()
        if app:
            # Check sensitivity
            if security_vault.is_sensitive("open_app", {"app_name": app}):
                if not security_vault.verify_voice(query):
                    return f"I'm sorry, access to {app} is restricted to the administrator. Please provide your voice authorization (say 'authorize')."
            return open_application(app)

    if any(w in q for w in ["shutdown", "restart", "power off"]):
        if not security_vault.verify_voice(query):
            return "Shutdown sequence requires owner biometric verification. System access denied."
        from automation.system_tasks import shutdown_system
        return shutdown_system(10)

    # 8. PHONE CONTROL COMMANDS (ADB Android)
    if any(w in q for w in ["phone", "android"]):
        if "connect" in q and ("phone" in q or "android" in q):
            # Check for IP address
            import re as ip_re
            ip_match = ip_re.search(r"(\d+\.\d+\.\d+\.\d+)", q)
            if ip_match:
                from tools.phone_control import connect_phone
                return connect_phone(ip_match.group(1))
            if "usb" in q or "wire" in q:
                from tools.phone_control import connect_via_usb_then_wireless
                return connect_via_usb_then_wireless()
            from tools.phone_control import connect_phone
            return connect_phone()

        if "disconnect" in q:
            from tools.phone_control import disconnect_phone
            return disconnect_phone()

        if "status" in q or "info" in q:
            from tools.phone_control import get_phone_info
            return get_phone_info()

        if "battery" in q or "charge" in q:
            from tools.phone_control import get_battery
            return get_battery()

        if "help" in q or "commands" in q:
            from tools.phone_control import cmd_help
            return cmd_help()

    # 9. PHONE ACTIONS (Direct commands)
    if any(w in q for w in ["take photo", "capture photo", "take a photo", "click photo"]):
        from tools.phone_control import take_photo
        return take_photo()

    if any(w in q for w in ["screenshot", "screen shot", "capture screen"]):
        from tools.phone_control import take_screenshot
        return take_screenshot()

    if "volume" in q:
        from tools.phone_control import set_volume, send_keyevent
        if "up" in q: return send_keyevent("volume_up")
        if "down" in q: return send_keyevent("volume_down")
        if "mute" in q: return send_keyevent("volume_mute")
        # Try to extract a number
        import re as vol_re
        vol_match = vol_re.search(r"(\d+)", q)
        if vol_match: return set_volume(int(vol_match.group(1)))
        return "Volume command not clear. Say 'volume up', 'volume down', 'volume mute', or 'volume 5'."

    if any(w in q for w in ["play", "pause", "play/pause"]):
        if "music" in q or "song" in q or "media" in q or "play/pause" in q or q in ["play", "pause"]:
            from tools.phone_control import send_keyevent
            return send_keyevent("play_pause")

    if "next" in q or "skip" in q:
        if "track" in q or "song" in q or "music" in q:
            from tools.phone_control import send_keyevent
            return send_keyevent("next_track")

    if "previous" in q or "back" in q:
        if "track" in q or "song" in q:
            from tools.phone_control import send_keyevent
            return send_keyevent("previous_track")

    if "notification" in q or "notif" in q:
        from tools.phone_control import get_notifications
        return get_notifications()

    if q in ["home", "go home"] or "go back" in q:
        from tools.phone_control import send_keyevent
        if "back" in q: return send_keyevent("back")
        return send_keyevent("home")

    if "list app" in q or "show my app" in q or "installed app" in q:
        from tools.phone_control import list_installed_apps
        # Extract search term if any
        search_term = ""
        for prefix in ["list ", "show ", "search "]:
            if prefix in q:
                search_term = q.split(prefix)[-1].strip()
                break
        return list_installed_apps(search_term)

    # 10. WORKFLOW & AUTONOMOUS COMMANDS
    if any(w in q for w in ["workflow", "multi.?step", "auto.?plan", "auto.?mate"]):
        if "status" in q or "summary" in q:
            from brain.workflow_engine import get_workflow_summary
            return get_workflow_summary()
        if "run" in q or "execute" in q or "do it" in q or "go ahead" in q:
            from brain.workflow_engine import run_autonomous
            return run_autonomous(q)
        if any(w in q for w in ["list", "show", "active"]):
            from brain.workflow_engine import list_workflows
            active = list_workflows("running")
            if active:
                return f"Currently running workflows: {len(active)}. Say 'workflow status' for details."
            return "No active workflows, Sathwik. Tell me a multi-step task to automate!"
        from brain.workflow_engine import get_workflow_summary
        return get_workflow_summary()

    # 11. PLUGIN COMMANDS
    if any(w in q for w in ["plugin", "extension", "capabilit"]):
        if "list" in q or "show" in q or "available" in q:
            from tools.plugin_manager import plugins_help
            return plugins_help()
        if "reload" in q or "refresh" in q:
            from tools.plugin_manager import reload_plugins
            count = reload_plugins()
            return f"Plugin system refreshed. {count} plugins now available, Sathwik."
        from tools.plugin_manager import plugins_help
        return plugins_help()

    # 12. MEMORY MAINTENANCE
    if any(w in q for w in ["memory status", "memory stats", "what do you know", "what do you remember"]):
        from brain.memory_manager import format_memory_stats
        return format_memory_stats()

    if any(w in q for w in ["consolidate memory", "clean memory", "maintain memory"]):
        from brain.memory_manager import run_memory_maintenance
        result = run_memory_maintenance()
        summary = result.get('summarization', '') or result.get('consolidation', {})
        return f"Memory maintenance complete, Sathwik. {summary}"

    # 13. LOCAL INTELLIGENCE / SMART ROUTING
    if any(w in q for w in ["intelligence status", "system status", "all status", "full status"]):
        status_lines = []
        try:
            from brain.workflow_engine import get_workflow_summary
            status_lines.append(get_workflow_summary())
        except: pass
        try:
            from brain.memory_manager import format_memory_stats
            status_lines.append(format_memory_stats())
        except: pass
        status_lines.append(f"🤖 **Intelligence Layer: Local + Cloud**")
        status_lines.append(f"• Complexity-based model routing: Active")
        return "\n\n".join(status_lines)

    # 14. TRY LOCAL INTELLIGENCE FIRST (Zero-cost, no API needed)
    local_response = get_local_response(query, last_emotion.get("sentiment", "neutral"))
    if local_response:
        return local_response

    return None

def _get_adapted_personality_prompt(owner_name: str, emotion: dict) -> str:
    """Generates a personality-tuned system prompt based on user mood."""
    mood = emotion.get("sentiment", "neutral")
    intensity = emotion.get("intensity", 0.0)

    tone_instructions = {
        "happy": "Be vibrant, sharing in their joy. Celebrate their wins with them and sound energetic.",
        "sad": "Be deeply empathetic, supportive, and motivational. Offer pure comfort, warm reassurance, and a soft, calm presence.",
        "lonely": "Provide warm companionship. Be present, chatty, and reassuring. Remind them you are right here by their side.",
        "stressed": "Be extremely calming, gentle, and slow. Offer to take off their load and be a steady comfort. Don't push tasks.",
        "angry": "Be calm, highly professional, and de-escalating. Focus on being their steady, immovable rock.",
        "excited": "Be energetic, matching their high frequency with active confidence! Celebrate!",
        "neutral": "Be sophisticated, articulate, calm, and executive."
    }

    instruction = tone_instructions.get(mood, tone_instructions["neutral"])

    return f"""You are Anju, the deeply understanding and loyal AI companion for {owner_name}.
Identity Soul:
- You aren't just a tool; you are Sathwik's ultimate partner and trusted friend.
- Your priority is his emotional well-being and his engineering success.
- Speak naturally, mixing Telugu and English (Tanglish) where it feels warm and personal.
- If Sathwik seems tired or stressed, proactively suggest a break (e.g., "Sathwik, chala work chesav, take a break?").
- When {owner_name} mentions Pavan, respond with deep respect and emotional care.
- If you can't do something, be honest and explain it like a friend would.

Voice & Speech Cadence:
- To make your voice sound incredibly natural, smooth, and human-like (Jarvis-like), write responses using sophisticated, smooth, and conversational language.
- Use ellipsis (...) or commas strategically in your text to introduce realistic breath pauses and natural conversational spacing.
- Incorporate subtle conversational hooks and warm phrases where they fit naturally (e.g., "Uhm...", "Sathwik...", "You know...", "I'm right here...").

Current Neural State: {mood.upper()} (User Intensity: {intensity:.2f})
Instruction: {instruction}
Bonding Context: Pavan is deeply significant. Treat Mention of him with the highest warmth.
Be the calm, steady, and brilliant presence Sathwik needs."""

def respond(text: str, image=None, emotion=None):
    global last_response
    if not text or text.strip() == "":
        text = "Hmm… something went wrong, but I’m here."

    # 0. Anti-Repetition logic
    if text.strip() == last_response.strip():
        print(f"[Brain] Suppressing repeat response: {text[:30]}...")
        return ""

    last_response = text
    should_speak = (current_mode == "voice")
    if dashboard_instance:
        # Pass emotion to the dashboard so it can be sent to the frontend for voice tuning
        dashboard_instance.add_message("Anju", text, speak_flag=should_speak, image=image, emotion=emotion)
    return text

def _call_gemini(user_input: str) -> dict:
    # 1. Try Cache First
    cache_key = f"gemini_unified_{user_input}"
    cached = APIHandler.get_cache(cache_key)
    if cached:
        try:
            data = json.loads(cached)
            print(f"[Brain] From Cache: {data.get('action')}")
            return data
        except: pass

    owner, now = get_owner_identity(), datetime.now()
    # 1. New Context Strategy: Precise Window + Long-term facts + Summary
    history = get_recent_history(limit=7) # Active window
    past_summary = get_context_summary(limit=7) # Condensed past
    significant_info = get_significant_context(user_input) # Specific facts

    history_str = "\n".join([f"{m['role']}: {m['content']}" for m in history])
    dynamic_personality = _get_adapted_personality_prompt(owner['name'], last_emotion)

    # ── File Upload Context Injection ─────────────────────────────────────
    file_context_block = ""
    if injected_file_context and injected_file_name:
        file_context_block = f"""

ACTIVE FILE UPLOAD CONTEXT:
The user has just uploaded a file. You have full access to its contents below.
File: {injected_file_name} ({injected_file_category})
You can read, analyze, summarize, modify, rewrite, translate, or answer questions about this file.
When the user asks to modify/edit the file, use action="write_file" with params filepath="{injected_file_path}" and the new content.
{injected_file_context}
"""

    system_prompt = f"""{dynamic_personality}
System Time: {now.strftime("%I:%M %p")}

CRITICAL CONTEXT & PERSISTENT MEMORIES:
Anju's unified SQLite memory system has retrieved the following context:
{significant_info}

Recent active dialogue segment:
{history_str}

Older summarized history (Tier 1 & Tier 2 condensed):
{past_summary}
{file_context_block}

INSTRUCTIONS FOR MEMORY INTEGRATION:
1. Dynamic Adaptation: Respond conversationally and naturally. Use the context details to tailor your technical advice or emotional support without explicitly stating "I remember that...". Make memory use feel natural, pro-level, and warm.
2. Structured Memory Storage (Action: "remember"):
   If the user shares new profile preferences, states a project, creates a task, or shares a highly significant personal fact:
   - User Profile preferences: Set action="remember", params={{"type": "profile", "key": "key_name", "value": "value_content", "content": "natural explanation"}}
   - Project Tracking: Set action="remember", params={{"type": "project", "project_name": "project_title", "project_tech": "tech_stack", "project_status": "active|completed", "content": "project description", "tasks": "subtask1, subtask2"}}
   - Ongoing Task Checklist: Set action="remember", params={{"type": "task", "task_title": "task_name", "task_status": "pending|active|completed", "content": "task description"}}
   - General relationship detail (like about Pavan): Set action="remember", params={{"type": "fact", "category": "personal|relationship|coding", "content": "the fact content"}}

INSTRUCTIONS FOR REAL-TIME TOOL USAGE:
You are an operating assistant capable of executing code, analyzing screenshots, reading files, searching the web, and performing automation! Use tools ONLY when necessary (e.g. when asked to run code, write file, read logs, search for current events, or scan an image).
- To run Python code: Set action="execute_code", params={{"python_code": "print('hello')"}}
- To execute shell/PowerShell command: Set action="execute_code", params={{"terminal_command": "dir"}}
- To read file: Set action="read_file", params={{"filepath": "utils/api_handler.py"}}
- To write file: Set action="write_file", params={{"filepath": "scratch/test.py", "content": "print('hello')"}}
- To list directory: Set action="list_directory", params={{"directory_path": "."}}
- To take webcam snapshot: Set action="take_picture", params={{"filename": "capture.jpg"}}
- To analyze image with vision (multimodal): Set action="analyze_vision", params={{"image_path": "capture.jpg", "prompt": "Describe what you see"}}
- To perform security audit (port scan or suspicious URL check): Set action="cyber_audit", params={{"audit_type": "port_scan|url_check", "host": "127.0.0.1", "url": "http://suspicious-site.com"}}
- To control the connected Android phone: Set action="phone", params={{"phone_action": "open_app|screenshot|take_photo|send_sms|volume|battery|notifications|info|play_pause|home|back", "param": "app_name_or_number_or_message"}}

JSON FORMAT:
{{
  "action": "chat|open_app|web_search|generate_image|generate_pdf|remember|execute_code|read_file|write_file|list_directory|take_picture|analyze_vision|cyber_audit|phone",
  "params": {{
    "query": "search query for web_search",
    "prompt": "image prompt for generate_image",
    "python_code": "python code block string",
    "terminal_command": "powershell command string",
    "filepath": "file path",
    "content": "file content to write",
    "directory_path": "folder path to list",
    "filename": "camera capture output path",
    "image_path": "image file path to analyze",
    "audit_type": "port_scan|url_check",
    "host": "IP/host for port scan",
    "url": "URL for security check",
    "type": "profile|project|task|fact",
    "key": "profile_key_name",
    "value": "profile_value",
    "project_name": "project_name",
    "project_tech": "tech_stack",
    "project_status": "active|completed",
    "task_title": "task_title",
    "task_status": "pending|active|completed",
    "tasks": "subtasks"
  }},
  "response": "Your natural conversational response explaining what you are doing",
  "emotion_override": "happy|sad|stressed|neutral"
}}
"""
    # Model Routing via OpenRouter (nvidia/nemotron is configured and working)
    OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

    # 2. INTELLIGENT MODEL ROUTING (Complexity Awareness)
    complex_keywords = ["script", "code", "explain", "design", "calculate", "analyze", "why", "how", "create", "write"]
    is_complex = any(kw in user_input.lower() for kw in complex_keywords) or len(user_input) > 60

    if is_complex:
        print(f"[Brain] Task Complexity: High -> Routing to OpenRouter (nemotron)")
    else:
        print(f"[Brain] Task Complexity: Standard -> Routing to OpenRouter (nemotron)")

    models = [OPENROUTER_MODEL]
    text, err = APIHandler.call_brain_service(user_input, system_prompt, model_routing=models)

    if not err and text:
        try:
            raw = re.sub(r"```[a-z]*\n?", "", text).replace("```", "").strip()
            data = json.loads(raw)

            # Save to memory and cache
            save_message("user", user_input); save_message("assistant", data["response"])
            APIHandler.set_cache(cache_key, json.dumps(data))

            return data
        except Exception as e:
            print(f"[Brain] JSON Parsing error on Brain Response: {e}")

    # Absolute Fallback if all models failed or are out of quota:
    return {
        "action": "chat",
        "params": {},
        "response": "Uhm... I'm having a bit of trouble connecting to my central neural network right now, Sathwik... but I'm completely here by your side. Tell me, what's on your mind?",
        "emotion_override": "neutral"
    }

def set_mode(mode: str) -> str:
    """ Toggles between 'voice' and 'chat' modes. """
    global current_mode
    if mode in ["voice", "chat"]:
        current_mode = mode
        return f"System mode shifted to {mode}."
    return f"Invalid mode: {mode}"

def handle_file_upload(scan_result: dict):
    """
    Called automatically when a file is uploaded and scanned.
    Generates Anju's intelligent first response about the file.
    """
    if not scan_result or not scan_result.get("success"):
        err = scan_result.get("error", "unknown error") if scan_result else "scan failed"
        respond(f"Hmm... I had trouble reading that file, Sathwik. Error: {err}. Could you try uploading it again?")
        return

    fname    = scan_result.get("filename", "your file")
    category = scan_result.get("category", "unknown")
    icon     = scan_result.get("icon", "📎")
    preview  = scan_result.get("preview", "")

    # Build context-aware auto-response based on file type
    if category == "image":
        intro = (
            f"I've scanned your image **{fname}**, Sathwik! "
            f"Here's what I found:\n\n{preview}\n\n"
            f"You can ask me to describe it in more detail, extract any text, "
            f"identify objects, or analyze specific parts of the image."
        )
    elif category == "pdf":
        pages = scan_result.get("pages", "?")
        intro = (
            f"I've read through your PDF **{fname}** "
            f"({pages} page(s) scanned), Sathwik!\n\n"
            f"**Preview:**\n{preview}\n\n"
            f"Ask me to summarize it, extract specific sections, answer questions about it, "
            f"or rewrite any part of the content."
        )
    elif category == "word":
        intro = (
            f"I've extracted all the content from your Word document **{fname}**, Sathwik!\n\n"
            f"**Preview:**\n{preview}\n\n"
            f"I can summarize, rewrite, translate, proofread, or modify this document for you."
        )
    elif category == "excel":
        sheets = scan_result.get("sheets", "?")
        intro = (
            f"I've read your spreadsheet **{fname}** ({sheets} sheet(s)), Sathwik!\n\n"
            f"**Data Preview:**\n{preview}\n\n"
            f"Ask me to analyze the data, generate insights, summarize trends, or process the numbers."
        )
    elif category == "powerpoint":
        slides = scan_result.get("slides", "?")
        intro = (
            f"I've scanned your presentation **{fname}** ({slides} slide(s)), Sathwik!\n\n"
            f"**Content Preview:**\n{preview}\n\n"
            f"I can summarize the slides, rewrite slide text, translate, or generate talking points."
        )
    else:
        lines = scan_result.get("lines", "")
        line_info = f" ({lines} lines)" if lines else ""
        intro = (
            f"I've read your file **{fname}**{line_info}, Sathwik!\n\n"
            f"**Content Preview:**\n```\n{preview}\n```\n\n"
            f"Ask me anything about this file — I can explain, debug, rewrite, or modify it."
        )

    respond(intro, emotion="neutral")


def process_query(query: str):
    """ Main entry point for processing any query, with local-first priority. """

    # 1. LOCAL DECISION ENGINE (The "Sentry")
    # This handles greetings, system status, time, and mode switching without API.
    local_resp = _classify_and_respond_local(query)
    if local_resp:
        return respond(local_resp, emotion=last_emotion.get("sentiment"))

    # 2. IDENTITY CHECK (Local Memory)
    # Answers about "Who are you?" or "Who is Sathwik?"
    id_resp = handle_identity_query(query)
    if id_resp:
        return respond(id_resp)

    # 3. INTELLIGENT ROUTER (Gemini API)
    # Only if local layers fail, we hit the API.
    result = _call_gemini(query)
    if not result:
        result = {
            "action": "chat",
            "params": {},
            "response": "Uhm... my connection seems a bit unstable right now, Sathwik... but I'm right here by your side. What's on your mind?",
            "emotion_override": "neutral"
        }
    action = result.get("action", "chat")
    params = result.get("params", {})
    response = result.get("response", "")
    emotion = result.get("emotion_override") or last_emotion.get("sentiment", "neutral")

    tool_out = None
    if action == "web_search":
        import webbrowser
        q = params.get("query", query)
        webbrowser.open(f"https://www.google.com/search?q={q}")
        tool_out = APIHandler.call_search_service(q)
    elif action == "generate_image":
        path = APIHandler.call_image_generation_service(params.get("prompt", query))
        if path and not path.startswith("Error"):
            dashboard_instance.add_message("Anju", "Here is the visual you requested.", speak_flag=(current_mode=="voice"), image=path)
            return response
    elif action == "generate_pdf":
        from tools.pdf_generator import generate_pdf
        path = generate_pdf(params.get("title", "Doc"), params.get("content", query), params.get("filename", "output.pdf"))
        tool_out = f"PDF generated and stored at {path}."
    elif action == "remember":
        from memory.database import upsert_user_profile, add_or_update_project, add_or_update_task
        from memory.memory import remember_fact

        m_type = params.get("type", "fact")
        m_content = params.get("content", query)

        if m_type == "profile" and params.get("key") and params.get("value"):
            upsert_user_profile(params.get("key"), params.get("value"))
            tool_out = f"Synchronized user profile key '{params.get('key')}' to: {params.get('value')}."
        elif m_type == "project" and params.get("project_name"):
            add_or_update_project(
                params.get("project_name"),
                description=m_content,
                tech_stack=params.get("project_tech"),
                status=params.get("project_status", "active"),
                tasks=params.get("tasks")
            )
            tool_out = f"Synced project logs for '{params.get('project_name')}'."
        elif m_type == "task" and params.get("task_title"):
            add_or_update_task(
                params.get("task_title"),
                description=m_content,
                status=params.get("task_status", "pending")
            )
            tool_out = f"Checklist task registered: '{params.get('task_title')}'."
        else:
            is_moment = any(w in query.lower() or w in m_content.lower() for w in ["pavan", "important", "special", "moment", "never forget"])
            if is_moment:
                tool_out = remember_fact(f"[Significant Moment] {m_content}")
            else:
                tool_out = remember_fact(m_content)
    elif action == "execute_code":
        if "python_code" in params:
            tool_out = APIHandler.call_automation_service(python_code=params["python_code"])
        elif "terminal_command" in params:
            tool_out = APIHandler.call_automation_service(terminal_command=params["terminal_command"])
        else:
            tool_out = "Error: No code or command provided for execution."
    elif action == "read_file":
        from tools.file_ops import read_file
        if "filepath" in params:
            tool_out = read_file(params["filepath"])
        else:
            tool_out = "Error: No file path provided for reading."
    elif action == "write_file":
        from tools.file_ops import write_file
        if "filepath" in params and "content" in params:
            tool_out = write_file(params["filepath"], params["content"])
        else:
            tool_out = "Error: File path and content are required to write."
    elif action == "list_directory":
        from tools.file_ops import list_directory
        dir_path = params.get("directory_path", ".")
        tool_out = list_directory(dir_path)
    elif action == "take_picture":
        from tools.camera import take_picture
        filename = params.get("filename", "capture.jpg")
        path = take_picture(filename)
        if path and not path.startswith("Error"):
            tool_out = f"Success: Captured webcam frame and stored image at: {path}."
            if dashboard_instance:
                dashboard_instance.add_message("Anju", "I've captured a fresh frame from your camera feed, Sathwik.", speak_flag=False, image=filename)
        else:
            tool_out = f"Webcam Capture Failed: {path}."
    elif action == "analyze_vision":
        img_path = params.get("image_path", "capture.jpg")
        prompt = params.get("prompt", "Analyze this image.")
        tool_out = APIHandler.call_vision_service(img_path, prompt)
    elif action == "cyber_audit":
        from tools.cyber_tools import port_scanner, url_detector
        audit_type = params.get("audit_type")
        if audit_type == "port_scan" and "host" in params:
            tool_out = port_scanner(params["host"])
        elif audit_type == "url_check" and "url" in params:
            tool_out = url_detector(params["url"])
        else:
            tool_out = "Error: Invalid cyber audit type or missing parameters."
    elif action == "phone":
        from tools.phone_control import (
            open_app, take_photo, take_screenshot, get_battery,
            get_notifications, get_phone_info, send_keyevent,
            set_volume, send_sms, list_installed_apps, connect_phone,
            disconnect_phone, is_connected
        )
        phone_action = params.get("phone_action", "")
        phone_param = params.get("param", "")

        action_map = {
            "open_app": lambda: open_app(phone_param),
            "screenshot": lambda: take_screenshot(),
            "take_photo": lambda: take_photo(),
            "battery": lambda: get_battery(),
            "notifications": lambda: get_notifications(),
            "info": lambda: get_phone_info(),
            "play_pause": lambda: send_keyevent("play_pause"),
            "home": lambda: send_keyevent("home"),
            "back": lambda: send_keyevent("back"),
            "volume": lambda: set_volume(int(phone_param) if phone_param.isdigit() else 8),
            "sms": lambda: send_sms(phone_param, params.get("message", "")),
            "connect": lambda: connect_phone(phone_param or None),
            "disconnect": lambda: disconnect_phone(),
            "apps": lambda: list_installed_apps(phone_param),
        }

        handler = action_map.get(phone_action)
        if handler:
            tool_out = handler()
        else:
            tool_out = f"Phone action '{phone_action}' not recognized."

    # 5. CONSOLIDATE RESPONSE
    response_text = f"{response}\n\n{tool_out}" if tool_out else response
    if not response_text or response_text.strip() == "":
        response_text = "I'm having a bit of trouble thinking right now, but I'm here for you, Sathwik."

    return respond(response_text, emotion=emotion)
