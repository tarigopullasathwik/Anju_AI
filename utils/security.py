import hashlib
import os
import json
import time

# Identity and Security Storage
SECURE_STORAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory", "security_profile.json")

class SecurityLayer:
    def __init__(self):
        self.primary_user = "Sathwik"
        self.is_authenticated = False
        self.auth_expiry = 0
        self._load_profile()

    def _load_profile(self):
        if os.path.exists(SECURE_STORAGE):
            with open(SECURE_STORAGE, 'r') as f:
                self.profile = json.load(f)
        else:
            self.profile = {"owner_voice_id": None, "trust_score": 0}

    def verify_voice(self, audio_text: str) -> bool:
        """
        Simulates voice biometric verification by checking speech patterns
        and identifying a 'Security Phrase' or signature within the input.
        In a real scenario, this would compare audio embeddings.
        """
        # Short-term authentication (lasts 10 minutes)
        if time.time() < self.auth_expiry:
            return True

        # Security phrase check (A 'Voice Key' used as a biometric proxy)
        voice_keys = ["authorize", "it is me", "identity confirmed", "access system"]
        if any(key in audio_text.lower() for key in voice_keys):
            print("[Security] Voice Biometric Pattern Matched: OWNER")
            self.auth_expiry = time.time() + 600 # 10 mins
            return True

        return False

    @staticmethod
    def is_sensitive(action: str, params: dict) -> bool:
        """Determines if an action requires elevated privileges."""
        sensitive_actions = ["shutdown", "delete", "format", "port_scan", "system_task"]
        if action in sensitive_actions:
            return True

        # Checking for app launch sensitivity
        if action == "open_app":
            sensitive_apps = ["terminal", "cmd", "powershell", "settings", "registry"]
            app_name = params.get("app_name", "").lower()
            if any(s in app_name for s in sensitive_apps):
                return True

        return False

    def get_access_level(self, user_input: str) -> str:
        """Returns 'owner' or 'guest' based on voice verification."""
        if self.verify_voice(user_input):
            return "owner"
        return "guest"
