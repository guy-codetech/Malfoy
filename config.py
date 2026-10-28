import os

from dotenv import load_dotenv

load_dotenv()


def _ids(raw):
    return {int(x) for x in raw.replace(" ", "").split(",") if x.isdigit()}


BOT_NAME = "Malfoy Bot"
TAGLINE = "A little world of coins & chaos"
VERSION = "1.0.0"

TOKEN = os.getenv("TOKEN", "")
OWNER_IDS = _ids(os.getenv("OWNER_IDS", ""))
DEFAULT_PREFIX = os.getenv("PREFIX", "m")
SUPPORT_URL = os.getenv("SUPPORT_URL", "")
WEBSITE_URL = os.getenv("WEBSITE_URL", "")
BANNER_URL = os.getenv("BANNER_URL", "")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0") or 0)

# Retain the original filename so existing installations keep their player data.
DATABASE_PATH = "data/lunii.db"
SYNC_SLASH_ON_START = True
PRESENCE_TEXT = "{prefix}help | Malfoy Bot"

ACCENT = 0xFFD9C9
ACCENT_OK = 0xA8E6C9
ACCENT_ERR = 0xFF8FA3
ACCENT_WARN = 0xFFD98A
ACCENT_INFO = 0xFFE3D6

EMOJI_PREFIX = "malfoy_"

CURRENCY = "coins"
START_CASH = 500
BANK_BASE_CAP = 5000
BANK_UPGRADE_COST_RATIO = 0.4
BANK_UPGRADE_GROWTH = 1.5
BANK_INTEREST_RATE = 0.01
BANK_INTEREST_MAX = 5000

DAILY_BASE = 250
DAILY_STREAK_BONUS = 25
DAILY_STREAK_MAX = 30
DAILY_WINDOW = 172800

WORK_RANGE = (80, 220)
BEG_RANGE = (10, 80)
BEG_CHANCE = 0.75
CRIME_WIN = (250, 700)
CRIME_LOSS = (150, 400)
CRIME_CHANCE = 0.55
ROB_CHANCE = 0.4
ROB_MIN_TARGET_CASH = 200
ROB_STEAL_RATIO = (0.10, 0.30)
ROB_FINE = (150, 400)

HUNT_COST = 10
FISH_COST = 10

COOLDOWNS = {
    "daily": 86400,
    "work": 1800,
    "beg": 60,
    "crime": 600,
    "rob": 900,
    "hunt": 25,
    "fish": 30,
}

DEFAULT_BET = 10
MAX_BET = 250000
SLOT_PAIR_MULTIPLIER = 1.5

LEVEL_UP_REWARD = 100
XP_RANGE = (4, 10)
XP_COOLDOWN = 12

HELP_CATEGORIES = ["Economy", "Bank", "Games", "Fun", "Info", "Settings"]
CATEGORY_ICONS = {
    "Economy": "COIN",
    "Bank": "BANK",
    "Games": "GAMES",
    "Fun": "HEART",
    "Info": "INFO",
    "Settings": "SETTINGS",
}
GATED_CATEGORIES = {"Economy", "Bank", "Games", "Fun"}

GIF_SOURCES = [
    {
        "name": "bre4d777",
        "base": "https://raw.githubusercontent.com/bre4d777/anime-gifs/master",
        "index": "https://raw.githubusercontent.com/bre4d777/anime-gifs/master/index.json",
    },
    {
        "name": "itsfizys",
        "base": "https://raw.githubusercontent.com/itsfizys/roleplay-gifs/main",
        "index": "https://raw.githubusercontent.com/itsfizys/roleplay-gifs/main/index.json",
    },
]

EXTENSIONS = [
    "cogs.events",
    "cogs.help",
    "cogs.economy",
    "cogs.bank",
    "cogs.games",
    "cogs.fun",
    "cogs.info",
    "cogs.settings",
    "cogs.owner",
]

FONT_DIR = "fonts"
CARDS_ENABLED = True
CARD_THEME = {
    "bg_top": (255, 240, 231),
    "bg_bottom": (255, 214, 203),
    "surface": (255, 255, 255),
    "ink": (122, 64, 66),
    "muted": (178, 128, 124),
    "accent": (255, 166, 150),
    "accent_soft": (255, 226, 216),
    "track": (248, 218, 209),
}
