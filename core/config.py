import os
import random
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

BASE_URL = os.getenv("BASE_URL", "https://www.noor-book.com")

PROJECT_DIR = Path(__file__).parent.parent
DOWNLOAD_DIR = PROJECT_DIR / "downloads"
COVERS_DIR = PROJECT_DIR / "covers"
DB_PATH = PROJECT_DIR / os.getenv("DB_PATH", "noor_book.db")

MIN_DELAY = float(os.getenv("MIN_DELAY", "2.0"))
MAX_DELAY = float(os.getenv("MAX_DELAY", "5.0"))

MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
TIMEOUT = int(os.getenv("TIMEOUT", "30"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1048576"))

MAX_PAGES_PER_TAG = int(os.getenv("MAX_PAGES_PER_TAG", "0"))
DRIVE_ROOT_FOLDER_ID = os.getenv("DRIVE_ROOT_FOLDER_ID", "11jYzFDYYDH_-JciVyn-GUydVejEVdXn2")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def get_random_delay() -> float:
    return random.uniform(MIN_DELAY, MAX_DELAY)

def get_random_user_agent() -> str:
    return random.choice(USER_AGENTS)
