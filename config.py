import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

# Tashkent / Uzbekistan timezone (UTC+5)
UZB_TZ = timezone(timedelta(hours=5))

def get_tashkent_str(fmt="%d.%m.%Y %H:%M"):
    return datetime.now(UZB_TZ).strftime(fmt)

def get_tashkent_db_str():
    return datetime.now(UZB_TZ).strftime("%Y-%m-%d %H:%M:%S")

# Paths to check for environment configuration
desktop_txt_path = Path("C:/Users/iMaster/Desktop/TAMINOT_BOT_SOZLAMALARI.txt")
desktop_env_path = Path("C:/Users/iMaster/Desktop/.env")
local_env_path = Path(__file__).resolve().parent / ".env"

# Load local .env first
if local_env_path.exists():
    load_dotenv(dotenv_path=local_env_path)

# If BOT_TOKEN is still empty, load from Desktop file
if not os.getenv("BOT_TOKEN") and desktop_txt_path.exists():
    load_dotenv(dotenv_path=desktop_txt_path, override=True)

if not os.getenv("BOT_TOKEN") and desktop_env_path.exists():
    load_dotenv(dotenv_path=desktop_env_path, override=True)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Admin IDs can be comma-separated: e.g. 12345678,87654321
raw_admins = os.getenv("ADMIN_IDS", "").strip()
ADMIN_IDS = set()
if raw_admins:
    for item in raw_admins.split(","):
        item = item.strip()
        if item.isdigit():
            ADMIN_IDS.add(int(item))

# Default Group ID (can also be saved dynamically in DB via /set_group)
DEFAULT_GROUP_ID = os.getenv("GROUP_ID", "").strip()
DEFAULT_GROUP_ID = int(DEFAULT_GROUP_ID) if DEFAULT_GROUP_ID and (DEFAULT_GROUP_ID.startswith("-") or DEFAULT_GROUP_ID.isdigit()) else None

DB_PATH = Path(__file__).resolve().parent / "taminot_bot.db"
