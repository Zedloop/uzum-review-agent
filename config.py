import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    UZUM_API_BASE_URL = os.getenv(
        "UZUM_API_BASE_URL", "https://api-seller.uzum.uz/api/seller"
    )
    UZUM_API_KEY = os.getenv("UZUM_API_KEY")
    UZUM_SHOP_IDS = [
        shop_id.strip()
        for shop_id in os.getenv("UZUM_SHOP_IDS", "").split(",")
        if shop_id.strip()
    ]

    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    CLAUDE_MODEL_DRAFTER = os.getenv("CLAUDE_MODEL_DRAFTER", "claude-sonnet-5")
    CLAUDE_MODEL_REVIEWER = os.getenv("CLAUDE_MODEL_REVIEWER", "claude-sonnet-5")

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    MAX_REVISIONS = int(os.getenv("MAX_REVISIONS", "2"))
    MAX_REVIEWS_PER_RUN = int(os.getenv("MAX_REVIEWS_PER_RUN", "5"))

    RUN_TOKEN = os.getenv("RUN_TOKEN")


def validate():
    required = {
        "UZUM_API_KEY": Config.UZUM_API_KEY,
        "ANTHROPIC_API_KEY": Config.ANTHROPIC_API_KEY,
        "TELEGRAM_BOT_TOKEN": Config.TELEGRAM_BOT_TOKEN,
        "TELEGRAM_CHAT_ID": Config.TELEGRAM_CHAT_ID,
    }
    missing = [name for name, value in required.items() if not value]
    if not Config.UZUM_SHOP_IDS:
        missing.append("UZUM_SHOP_IDS")
    if missing:
        raise RuntimeError(
            f".env faylida quyidagilar to'ldirilmagan: {', '.join(missing)}"
        )
