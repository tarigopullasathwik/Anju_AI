import os
import requests

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
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as http_err:
            # Return structured error information for caller to handle
            return {
                "error": str(http_err),
                "status_code": response.status_code if 'response' in locals() else None,
                "raw_response": response.text if 'response' in locals() else None,
            }
        except Exception as err:
            return {"error": str(err), "status_code": None}

    @staticmethod
    def count_tokens(text: str) -> int:
        """Estimate token count for a piece of text.

        TokenRouter does not expose a dedicated token‑count endpoint in the
        provided documentation, so we fall back to the common approximation of
        one token per four characters.
        """
        return len(text) // 4
