import os
import time
import random
import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
import dotenv
from utils.tokenrouter_client import TokenRouterClient
# Load environment variables from .env
dotenv.load_dotenv()
import requests
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory")
DB_PATH = os.path.join(DB_DIR, "anju_memory.db")

class APIHandler:
    @staticmethod
    def _init_metrics():
        """Initializes the metric tables for cost, token, and performance tracking."""
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR, exist_ok=True)

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # System stats metrics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_metrics (
                    key TEXT PRIMARY KEY,
                    value REAL
                )
            ''')

            # Centralized API Transaction Logs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    service_name TEXT,
                    latency_seconds REAL,
                    tokens_used INTEGER,
                    cost_usd REAL,
                    status TEXT,
                    error_message TEXT
                )
            ''')

            # API Performance Failures Log
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    issue_type TEXT,
                    raw_error TEXT,
                    fix_applied TEXT
                )
            ''')

            # Initialize default metrics if not present
            metrics = [
                ('api_calls', 0.0),
                ('cache_hits', 0.0),
                ('errors_prevented', 0.0),
                ('total_tokens_sent', 0.0),
                ('total_tokens_received', 0.0),
                ('total_cost_usd', 0.0)
            ]
            for m_key, m_val in metrics:
                cursor.execute("INSERT OR IGNORE INTO system_metrics (key, value) VALUES (?, ?)", (m_key, m_val))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[APIHandler] Init metrics error: {e}")

    @staticmethod
    def update_metric(key: str, increment: float = 1.0):
        """Increments a system metric securely."""
        try:
            APIHandler._init_metrics()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE system_metrics SET value = value + ? WHERE key = ?", (increment, key))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[APIHandler] Update metric error: {e}")

    @staticmethod
    def get_metrics() -> dict:
        """Retrieves all system metrics as a structured dictionary."""
        APIHandler._init_metrics()
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM system_metrics")
            rows = cursor.fetchall()
            conn.close()
            return {row[0]: row[1] for row in rows}
        except Exception:
            return {
                "api_calls": 0, "cache_hits": 0, "errors_prevented": 0,
                "total_tokens_sent": 0, "total_tokens_received": 0, "total_cost_usd": 0
            }

    @staticmethod
    def log_api_call(service_name: str, latency: float, tokens_used: int = 0, cost_usd: float = 0.0, status: str = "success", error_message: str = ""):
        """Logs a single API transaction, calculating costs and updating global aggregators."""
        try:
            APIHandler._init_metrics()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO api_logs (timestamp, service_name, latency_seconds, tokens_used, cost_usd, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (datetime.now().isoformat(), service_name, latency, tokens_used, cost_usd, status, error_message))
            conn.commit()
            conn.close()

            # Increment global aggregators
            APIHandler.update_metric('api_calls', 1.0)
            if tokens_used > 0:
                APIHandler.update_metric('total_tokens_received', tokens_used)
            if cost_usd > 0.0:
                APIHandler.update_metric('total_cost_usd', cost_usd)
        except Exception as e:
            print(f"[APIHandler] Trans Log Error: {e}")

    # ── Intelligent Caching System ──────────────────────────────────────────────
    @staticmethod
    def get_cache(prompt: str, ttl_hours: int = 24) -> str:
        """Retrieves a cached response if it has not expired."""
        try:
            prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_cache (
                    hash TEXT PRIMARY KEY,
                    prompt TEXT,
                    response TEXT,
                    timestamp TEXT
                )
            ''')

            cursor.execute("SELECT response, timestamp FROM api_cache WHERE hash = ?", (prompt_hash,))
            row = cursor.fetchone()
            conn.close()

            if row:
                cached_res, timestamp = row
                cached_time = datetime.fromisoformat(timestamp)
                if datetime.now() - cached_time < timedelta(hours=ttl_hours):
                    APIHandler.update_metric('cache_hits')
                    print(f"[APIHandler] Cache Hit for hash: {prompt_hash[:8]}")
                    return cached_res
            return None
        except Exception as e:
            print(f"[APIHandler] Cache Read Error: {e}")
            return None

    @staticmethod
    def set_cache(prompt: str, response: str):
        """Stores a prompt-response translation in local cache."""
        try:
            prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO api_cache (hash, prompt, response, timestamp) VALUES (?, ?, ?, ?)",
                (prompt_hash, prompt, response, datetime.now().isoformat())
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[APIHandler] Cache Write Error: {e}")

    # ── Multi-Model Registry ────────────────────────────────────────────────────
    MODEL_REGISTRY = {
        # Format: "name": {"provider": "google", "capabilities": ["chat", "code", "vision"], "cost_per_mtok": 0.075}
        "gemini-flash-latest": {
            "provider": "google",
            "capabilities": ["chat", "code", "vision", "fast"],
            "cost_per_mtok_input": 0.075,
            "cost_per_mtok_output": 0.30,
            "speed": "fast",
            "quality": "high",
        },
        "gemini-2.0-flash": {
            "provider": "google",
            "capabilities": ["chat", "code", "vision", "reasoning"],
            "cost_per_mtok_input": 0.10,
            "cost_per_mtok_output": 0.40,
            "speed": "fast",
            "quality": "very_high",
        },
        "local_fallback": {
            "provider": "local",
            "capabilities": ["chat", "simple"],
            "cost_per_mtok_input": 0.0,
            "cost_per_mtok_output": 0.0,
            "speed": "instant",
            "quality": "basic",
        },
    }

    @staticmethod
    def get_model_info(model_name: str) -> dict:
        """Get information about a registered model."""
        return APIHandler.MODEL_REGISTRY.get(model_name, {
            "provider": "unknown",
            "capabilities": ["chat"],
            "cost_per_mtok_input": 0,
            "cost_per_mtok_output": 0,
            "speed": "unknown",
            "quality": "unknown",
        })

    @staticmethod
    def list_available_models() -> list[str]:
        """List all registered model names."""
        return list(APIHandler.MODEL_REGISTRY.keys())

    @staticmethod
    def select_best_model(required_capabilities: list[str] = None,
                          prefer_speed: bool = False,
                          prefer_quality: bool = False) -> str:
        """
        Select the best model based on requirements.

        Args:
            required_capabilities: e.g. ["chat"], ["code", "vision"]
            prefer_speed: If True, prefers faster models
            prefer_quality: If True, prefers higher quality models

        Returns:
            Model name string
        """
        candidates = []

        for name, info in APIHandler.MODEL_REGISTRY.items():
            if info["provider"] == "local":
                continue  # Skip local fallback for selection

            if required_capabilities:
                if not all(cap in info["capabilities"] for cap in required_capabilities):
                    continue

            candidates.append((name, info))

        if not candidates:
            return "gemini-flash-latest"  # Default fallback

        # Sort by speed or quality preference
        if prefer_speed:
            candidates.sort(key=lambda x: {"fast": 0, "medium": 1, "slow": 2}.get(x[1]["speed"], 1))
        elif prefer_quality:
            candidates.sort(key=lambda x: {"basic": 3, "high": 1, "very_high": 0}.get(x[1]["quality"], 2))

        return candidates[0][0]

    @staticmethod
    def estimate_cost(model_name: str, input_chars: int, output_chars: int) -> float:
        """Estimate the cost of an API call in USD."""
        info = APIHandler.get_model_info(model_name)
        input_tokens = input_chars // 4
        output_tokens = output_chars // 4
        cost = (input_tokens * info["cost_per_mtok_input"] / 1_000_000) + \
               (output_tokens * info["cost_per_mtok_output"] / 1_000_000)
        return cost

    # ── Modular Independent Dispatchers ─────────────────────────────────────────
    @staticmethod
    def call_brain_service(user_input: str, system_prompt: str, model_routing: list = None) -> tuple:
        """
        Dispatches the main Gemini brain routing.
        Features dynamic cost estimation, cost trackers, and automatic model failover.
        """
        # Use TokenRouter for brain conversation (free model)
        if not model_routing:
            model_routing = ["default"]
        start_time = time.time()
        # Compute input tokens estimate (1 token ~ 4 chars)
        input_tokens = len(system_prompt + user_input) // 4

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
            # If model_routing specifies "default", let the client choose its default model
            model_param = None if model_routing[0] == "default" else model_routing[0]
            resp = TokenRouterClient.chat_completion(messages, model=model_param)
            # If the response contains an error field, treat as failure
            if isinstance(resp, dict) and resp.get("error"):
                raise Exception(resp.get("error"))
            text_response = resp.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            latency = time.time() - start_time
            output_tokens = len(text_response) // 4
            total_tokens = input_tokens + output_tokens
            cost = resp.get("usage", {}).get("total_cost", 0.0) if isinstance(resp, dict) else 0.0
            APIHandler.log_api_call("brain", latency, tokens_used=total_tokens, cost_usd=cost, status="success")
            APIHandler.update_metric('total_tokens_sent', input_tokens)
            return text_response, None
        except Exception as e:
            err_str = str(e)
            print(f"[APIHandler] TokenRouter brain error: {err_str}")
            # Attempt OpenAI fallback if configured
            try:
                # OpenRouter integration for specific model
                if model_routing[0] == "nvidia/nemotron-3-ultra-550b-a55b:free":
                    # Use OpenRouter API
                    openrouter_key = os.getenv("OPENROUTER_API_KEY")
                    if not openrouter_key:
                        raise ValueError("OPENROUTER_API_KEY missing for OpenRouter usage")
                    openrouter_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
                    temperature = 0.7  # Default temperature
                    # Build request payload
                    openrouter_payload = {
                        "model": model_routing[0],
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": 1024,
                    }
                    headers = {
                        "Authorization": f"Bearer {openrouter_key}",
                        "Content-Type": "application/json",
                    }
                    try:
                        resp = requests.post(f"{openrouter_url.rstrip('/')}/chat/completions", json=openrouter_payload, headers=headers, timeout=30)
                        resp.raise_for_status()
                        openrouter_resp = resp.json()
                    except requests.HTTPError as http_err:
                        raise Exception(str(http_err))
                    text_response = openrouter_resp.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    latency = time.time() - start_time
                    output_tokens = len(text_response) // 4
                    total_tokens = input_tokens + output_tokens
                    cost = 0.0  # Cost tracking not implemented for OpenRouter
                    APIHandler.log_api_call("brain_openrouter", latency, tokens_used=total_tokens, cost_usd=cost, status="success")
                    APIHandler.update_metric('total_tokens_sent', input_tokens)
                    return text_response, None
                # OpenAI fallback (legacy)
                import openai
                openai_api_key = os.getenv("OPENAI_API_KEY")
                if not openai_api_key:
                    raise ValueError("OPENAI_API_KEY missing for fallback")
                openai.api_key = openai_api_key
                model = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-3.5-turbo")
                openai_resp = openai.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                )
                text_response = openai_resp.choices[0].message.content.strip()
                latency = time.time() - start_time
                output_tokens = len(text_response) // 4
                total_tokens = input_tokens + output_tokens
                cost = 0.0
                APIHandler.log_api_call("brain_fallback", latency, tokens_used=total_tokens, cost_usd=cost, status="success")
                APIHandler.update_metric('total_tokens_sent', input_tokens)
                return text_response, None
            except Exception as fallback_err:
                fallback_str = str(fallback_err)
                APIHandler.log_issue("Brain Fallback Error", fallback_str, "OpenAI fallback failed")
                APIHandler.update_metric('errors_prevented')
                latency = time.time() - start_time
                APIHandler.log_api_call("brain", latency, status="failed", error_message=err_str + " | fallback: " + fallback_str)
                return None, f"Brain request failed: {err_str} (fallback error: {fallback_str})"

    @staticmethod
    def call_voice_service(text: str) -> tuple:
        """
        Tracks voice syntheses metrics.
        TTS triggers dynamically in separate threads inside ui_dashboard.
        """
        start_time = time.time()
        try:
            # We approximate token cost if we hit external OpenAI TTS
            # Let's count characters. OpenAI TTS standard costs $15 per million characters ($0.000015 per char)
            char_count = len(text)
            cost = char_count * 0.000015
            latency = 0.5 # Handled asynchronously

            APIHandler.log_api_call("voice", latency, tokens_used=char_count // 4, cost_usd=cost, status="success")
            return True, None
        except Exception as e:
            APIHandler.log_api_call("voice", 0.1, status="failed", error_message=str(e))
            return False, str(e)

    @staticmethod
    def call_search_service(query: str) -> str:
        """Dispatches dynamic search with metrics log."""
        start_time = time.time()
        try:
            from tools.web_search import search_web
            res = search_web(query)
            latency = time.time() - start_time
            APIHandler.log_api_call("search", latency, status="success")
            return res
        except Exception as e:
            APIHandler.log_api_call("search", 0.1, status="failed", error_message=str(e))
            return f"Error executing web search: {e}"

    @staticmethod
    def call_image_generation_service(prompt: str) -> str:
        """Dispatches Flux Image Generation with cost (Free Flux Pollinations)."""
        start_time = time.time()
        try:
            from tools.image_generator import generate_image
            res = generate_image(prompt)
            latency = time.time() - start_time
            # Cost is 0 since we bypass DALL-E keys by routing to free Flux.ai!
            APIHandler.log_api_call("image_generation", latency, cost_usd=0.0, status="success")
            return res
        except Exception as e:
            APIHandler.log_api_call("image_generation", 0.1, status="failed", error_message=str(e))
            return f"Error executing image generation: {e}"

    @staticmethod
    def call_memory_service(query: str) -> str:
        """Searches local SQLite semantic facts registry."""
        start_time = time.time()
        try:
            from memory.memory import get_memory
            res = get_memory(query)
            latency = time.time() - start_time
            # Local SQLite search is completely offline
            APIHandler.log_api_call("memory", latency, cost_usd=0.0, status="success")
            return res
        except Exception as e:
            APIHandler.log_api_call("memory", 0.01, status="failed", error_message=str(e))
            return f"Error searching memory: {e}"

    @staticmethod
    def call_vision_service(image_path: str, prompt: str) -> str:
        """Dispatches multimodal base64 vision parsing."""
        start_time = time.time()
        try:
            from tools.vision_analyzer import analyze_image_with_vision
            res = analyze_image_with_vision(image_path, prompt)
            latency = time.time() - start_time

            # Input tokens estimate (Image is represented as roughly 258 tokens in Gemini flash)
            input_tokens = (len(prompt) // 4) + 258
            output_tokens = len(res) // 4
            cost = (input_tokens * 0.000000075) + (output_tokens * 0.0000003)

            APIHandler.log_api_call("vision", latency, tokens_used=input_tokens+output_tokens, cost_usd=cost, status="success")
            return res
        except Exception as e:
            APIHandler.log_api_call("vision", 0.1, status="failed", error_message=str(e))
            return f"Error executing vision analysis: {e}"

    @staticmethod
    def call_automation_service(python_code: str = None, terminal_command: str = None) -> str:
        """Executes terminal/automation scripts locally."""
        start_time = time.time()
        try:
            from tools.code_execution import execute_python_code, execute_terminal_command
            if python_code:
                res = execute_python_code(python_code)
            elif terminal_command:
                res = execute_terminal_command(terminal_command)
            else:
                res = "Error: No script block passed."

            latency = time.time() - start_time
            APIHandler.log_api_call("automation", latency, cost_usd=0.0, status="success")
            return res
        except Exception as e:
            APIHandler.log_api_call("automation", 0.1, status="failed", error_message=str(e))
            return f"Error running automation: {e}"

    # ── Performance and Reporting ───────────────────────────────────────────────
    @staticmethod
    def call_gemini_with_backoff(client, model, contents, config=None, max_retries=3):
        """Standard compatibility interface supporting exponential backoff."""
        delay = 2
        APIHandler.update_metric('api_calls')

        for attempt in range(max_retries):
            try:
                time.sleep(0.3) # Spacing
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config
                )
                return response.text.strip(), None
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "QuotaExceeded" in error_msg:
                    print(f"[APIHandler] Rate limit backoff (Attempt {attempt+1}/{max_retries}). Sleep: {delay}s")
                    APIHandler.log_issue("Rate Limit", error_msg, f"Backoff: {delay}s")
                    time.sleep(delay + random.uniform(0, 1))
                    delay *= 2
                    continue
                APIHandler.update_metric('errors_prevented')
                return None, error_msg

        return None, "Max retries exceeded."

    @staticmethod
    def log_issue(issue_type, raw_error, fix_applied):
        """Persists performance issues into the database."""
        try:
            APIHandler._init_metrics()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO performance_logs (timestamp, issue_type, raw_error, fix_applied) VALUES (?, ?, ?, ?)",
                (datetime.now().isoformat(), issue_type, raw_error, fix_applied)
            )
            conn.commit()
            conn.close()
        except:
            pass

    @staticmethod
    def get_latest_fix_report() -> dict:
        """Generates a detailed summary of API metrics and logs for diagnostics."""
        metrics = APIHandler.get_metrics()
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT issue_type, raw_error, fix_applied, timestamp FROM performance_logs ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()

            # Fetch total API Cost
            cursor.execute("SELECT SUM(cost_usd) FROM api_logs")
            cost_sum = cursor.fetchone()[0] or 0.0

            # Fetch average latency
            cursor.execute("SELECT AVG(latency_seconds) FROM api_logs")
            avg_latency = cursor.fetchone()[0] or 0.0

            conn.close()

            report = {
                "metrics": metrics,
                "total_cost_calculated": round(cost_sum, 5),
                "average_latency_seconds": round(avg_latency, 3),
                "last_fix": {
                    "issue": row[0],
                    "fix": row[2],
                    "time": row[3]
                } if row else None
            }
            return report
        except Exception:
            return {"metrics": metrics, "total_cost_calculated": 0.0, "average_latency_seconds": 0.0, "last_fix": None}
