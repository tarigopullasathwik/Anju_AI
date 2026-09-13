import os
import time
import requests


class TokenRouterError(RuntimeError):
    """Actionable error returned when the provider cannot produce a reply."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _safe_provider_error(response: requests.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                return str(error.get("message") or error.get("type") or "provider error")
            if error:
                return str(error)
    except ValueError:
        pass
    return response.text[:500].strip() or response.reason or "provider error"


def _validate_completion(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise TokenRouterError("TokenRouter returned a non-JSON response")
    if payload.get("error"):
        error = payload["error"]
        message = error.get("message") if isinstance(error, dict) else str(error)
        raise TokenRouterError(message or "TokenRouter returned an error")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise TokenRouterError("TokenRouter response contained no choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise TokenRouterError("TokenRouter response contained no assistant content")
    return payload


class TokenRouterClient:
    """Simple client for TokenRouter API used for chat completions and token counting.

    The client reads the API key from the environment variable ``TOKENROUTER_API_KEY``.
    An optional ``TOKENROUTER_BASE_URL`` can be set; otherwise it defaults to
    ``https://api.tokenrouter.com/v1`` as specified by the user.
    ``TOKENROUTER_DEFAULT_MODEL`` can be set to specify the default model to use.
    """

    @staticmethod
    def _get_api_key() -> str:
        api_key = os.getenv("TOKENROUTER_API_KEY")
        if not api_key:
            raise ValueError("TOKENROUTER_API_KEY missing from environment variables")
        return api_key

    @staticmethod
    def _get_base_url() -> str:
        return os.getenv("TOKENROUTER_BASE_URL", "https://api.tokenrouter.com/v1")

    @staticmethod
    def _get_default_model() -> str:
        # Default to a widely‑available model if not set
        return os.getenv("TOKENROUTER_DEFAULT_MODEL", "gpt-3.5-turbo")

    @staticmethod
    def chat_completion(messages: list, model: str = None, temperature: float = 0.7) -> dict:
        """Call the TokenRouter ``/chat/completions`` endpoint.

        Parameters
        ----------
        messages: list
            List of message dictionaries conforming to the OpenAI chat format.
        model: str, optional
            Model identifier understood by TokenRouter. If ``None`` the default
            model from ``TOKENROUTER_DEFAULT_MODEL`` is used.
        temperature: float
            Sampling temperature; forwarded to the API unchanged.
        """
        if model is None:
            model = TokenRouterClient._get_default_model()
        url = f"{TokenRouterClient._get_base_url().rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {TokenRouterClient._get_api_key()}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        last_error = None
        for attempt in range(3):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                if response.status_code == 429 or response.status_code >= 500:
                    raise TokenRouterError(_safe_provider_error(response), response.status_code)
                if not response.ok:
                    raise TokenRouterError(_safe_provider_error(response), response.status_code)
                return _validate_completion(response.json())
            except (requests.RequestException, TokenRouterError, ValueError) as exc:
                last_error = exc
                status = getattr(exc, "status_code", None)
                if attempt < 2 and (status is None or status == 429 or status >= 500):
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                break
        message = str(last_error) if last_error else "TokenRouter request failed"
        return {"error": message, "status_code": getattr(last_error, "status_code", None)}

    @staticmethod
    def count_tokens(text: str) -> int:
        """Estimate token count for a piece of text.

        TokenRouter does not expose a dedicated token‑count endpoint in the
        provided documentation, so we fall back to the common approximation of
        one token per four characters.
        """
        return len(text) // 4
