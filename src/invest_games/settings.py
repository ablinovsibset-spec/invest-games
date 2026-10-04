import os

from dotenv import load_dotenv


def require_routerai_key() -> str:
    load_dotenv()
    key = (os.environ.get("TYPESAFE_API_KEY") or "").strip()
    if not key:
        raise SystemExit("Нужен ключ RouterAI (TYPESAFE_API_KEY). Без него стол не стартует.")
    return key


def routerai_base_url() -> str:
    load_dotenv()
    return (os.environ.get("TYPESAFE_BASE_URL") or "https://routerai.ru/api").rstrip("/")
