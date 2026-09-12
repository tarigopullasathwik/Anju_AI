import os
from dotenv import load_dotenv

# Load environment variables from .env file up one level
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path=env_path)

def get_api_key(key_name: str) -> str:
    """
    Retrieve an API key from environment variables.
    """
    val = os.getenv(key_name, "")
    if val:
        return val.strip().strip("'").strip('"')
    return ""
