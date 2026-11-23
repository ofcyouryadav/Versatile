from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
RUNTIME_CONFIG_PATH = BASE_DIR / "config.runtime.json"

# Load secrets from repo-root .env (or src/.env as fallback).
load_dotenv(ROOT_DIR / ".env")
load_dotenv(BASE_DIR / ".env", override=False)


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _env_int(name: str, default: int = 0) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def _env_int_list(name: str) -> list[int]:
    raw = _env(name)
    if not raw:
        return []
    return [int(item.strip()) for item in raw.split(",") if item.strip()]


POSTGRES_HOST = _env("POSTGRES_HOST", "localhost")
POSTGRES_PORT = _env_int("POSTGRES_PORT", 5432)
POSTGRES_USER = _env("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = _env("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = _env("POSTGRES_DB", "vxbot")

TORTOISE = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "host": POSTGRES_HOST,
                "port": POSTGRES_PORT,
                "user": POSTGRES_USER,
                "password": POSTGRES_PASSWORD,
                "database": POSTGRES_DB,
                "minsize": 1,
                "maxsize": 5,
                "max_queries": 50000,
                "max_inactive_connection_lifetime": 300,
                "timeout": 30,
                "command_timeout": 60,
                "server_settings": {
                    "application_name": "vxbot",
                },
            },
        }
    },
    "apps": {
        "models": {
            "models": ["models", "aerich.models"],
            "default_connection": "default",
        }
    },
}

POSTGRESQL = {
    "host": POSTGRES_HOST,
    "port": str(POSTGRES_PORT),
    "user": POSTGRES_USER,
    "password": POSTGRES_PASSWORD,
    "database": POSTGRES_DB,
}

DISCORD_TOKEN = _env("DISCORD_TOKEN", "")
GROQ_API_KEY = _env("GROQ_API_KEY", "")
GEMINI_API_KEY = _env("GEMINI_API_KEY", "")

SPOTIFY_CLIENT_ID = _env("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = _env("SPOTIFY_CLIENT_SECRET", "")

FASTAPI_URL = _env("FASTAPI_URL", "http://localhost:8080/")
FASTAPI_KEY = _env("FASTAPI_KEY", "")
PRIME_EMOJI = _env("PRIME_EMOJI", "")

EXTENSIONS = (
    "cogs.esports",
    "cogs.reminder",
    "cogs.mod",
    "cogs.events",
    "cogs.premium",
    "cogs.utility",
    "cogs.quomisc",
    "cogs.ai-chatbot",
)

OWN_name = _env("OWNER_NAME", "your_username")
OWN_AVATAR = _env("OWNER_AVATAR", "")
PRO_LINK = _env("BOT_INVITE", "")

COLOR = int(_env("BOT_COLOR", "0x0ACCF7"), 16)

PAYU_MERCHANT_KEY = _env("PAYU_MERCHANT_KEY", "your_merchant_key")
PAYU_MERCHANT_SALT = _env("PAYU_MERCHANT_SALT", "your_merchant_salt")
PAYU_BASE_URL = _env("PAYU_BASE_URL", "https://test.payu.in")
PAYU_SUCCESS_URL = _env("PAYU_SUCCESS_URL", "https://yourdomain.com/payusuccess")
PAYU_FAILURE_URL = _env("PAYU_FAILURE_URL", "https://yourdomain.com/payufailure")

PAYU_KEY = PAYU_MERCHANT_KEY
PAYU_SALT = PAYU_MERCHANT_SALT
PAYU_PAYMENT_LINK = PAYU_BASE_URL
SUCCESS_URL = PAYU_SUCCESS_URL
FAILED_URL = PAYU_FAILURE_URL
PAY_LINK = ""

FOOTER = _env("BOT_FOOTER", "Developed by Versatilex")
PREFIX = _env("BOT_PREFIX", "v")
SERVER_LINK = _env("SERVER_LINK", "")
BOT_INVITE = _env("BOT_INVITE", "")
WEBSITE = _env("WEBSITE", "")
REPOSITORY = _env("REPOSITORY", "https://github.com/ashish200729/vxbot")
SERVER_ID = _env_int("SERVER_ID", 0)

DEVS = _env_int_list("DEV_IDS")

SHARD_LOG = _env("SHARD_LOG", "")
ERROR_LOG = _env("ERROR_LOG", "")
PUBLIC_LOG = _env("PUBLIC_LOG", "")
GUILD_LOGS = _env("GUILD_LOGS", "")

PREMIUM_AVATAR = _env("PREMIUM_AVATAR", "")
PREMIUM_ROLE = _env_int("PREMIUM_ROLE", 0)
VOTER_ROLE = _env_int("VOTER_ROLE", 0)

SOCKET_URL = _env("SOCKET_URL", "")
SOCKET_AUTH = _env("SOCKET_AUTH", "")
SERVER_PORT = _env_int("SERVER_PORT", 8080)
RILP_PREMIUM = _env("RILP_PREMIUM", "")
RILP_HEADERS: dict = {}
PROXY_URI = _env("PROXY_URI") or None

LAVALINK_HOST = _env("LAVALINK_HOST", "lavalink.jirayu.net")
LAVALINK_PORT = _env_int("LAVALINK_PORT", 13592)
LAVALINK_PASSWORD = _env("LAVALINK_PASSWORD", "youshallnotpass")
LAVALINK_SECURE = _env("LAVALINK_SECURE", "false").lower() in {"1", "true", "yes"}

custom_avatar_url: str | None = None
custom_banner_url: str | None = None
custom_bio: str | None = None


def _load_runtime_config() -> None:
    global custom_avatar_url, custom_banner_url, custom_bio

    if not RUNTIME_CONFIG_PATH.exists():
        return

    try:
        data = json.loads(RUNTIME_CONFIG_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return

    custom_avatar_url = data.get("custom_avatar_url")
    custom_banner_url = data.get("custom_banner_url")
    custom_bio = data.get("custom_bio")


async def save() -> None:
    data = {
        "custom_avatar_url": custom_avatar_url,
        "custom_banner_url": custom_banner_url,
        "custom_bio": custom_bio,
    }
    RUNTIME_CONFIG_PATH.write_text(json.dumps(data, indent=2) + "\n")


_load_runtime_config()
