import os

from dotenv import load_dotenv

load_dotenv()


def get_secret(name: str, default: str = "") -> str:
    value = os.getenv(name, "")
    if value:
        return value.strip()
    return default
