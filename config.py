import os
from pathlib import Path

from dotenv import load_dotenv

# Aniq shu loyihaning o'z .env fayli, override=True bilan - aks holda bir
# nechta loyiha bitta jarayonda birlashtirilganda (masalan PythonAnywhere'da),
# avval yuklangan boshqa loyihaning o'zgaruvchilari ustidan yozilmay qolib,
# noto'g'ri qiymatlar (masalan boshqa loyihaning Telegram tokeni) ishlatilib
# ketishi mumkin edi.
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)


class Config:
    UZUM_API_BASE_URL = os.getenv(
        "UZUM_API_BASE_URL", "https://api-seller.uzum.uz/api/seller"
    )
    UZUM_API_KEY = os.getenv("UZUM_API_KEY")
    UZUM_OAUTH_URL = os.getenv("UZUM_OAUTH_URL", "https://api-seller.uzum.uz/api/oauth/token")
    UZUM_USERNAME = os.getenv("UZUM_USERNAME")
    UZUM_PASSWORD = os.getenv("UZUM_PASSWORD")
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

    # Telegram webhook'ning haqiqatan Telegram'dan kelganini tekshirish uchun
    # maxfiy qiymat (setWebhook'da secret_token sifatida ro'yxatdan o'tkaziladi)
    TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")


def validate():
    required = {
        "ANTHROPIC_API_KEY": Config.ANTHROPIC_API_KEY,
        "TELEGRAM_BOT_TOKEN": Config.TELEGRAM_BOT_TOKEN,
        "TELEGRAM_CHAT_ID": Config.TELEGRAM_CHAT_ID,
    }
    missing = [name for name, value in required.items() if not value]
    if not Config.UZUM_SHOP_IDS:
        missing.append("UZUM_SHOP_IDS")
    # Uzum token kerak: yo UZUM_USERNAME+UZUM_PASSWORD (avtomatik yangilanadi),
    # yo'q bo'lsa hech bo'lmasa qo'lda kiritilgan UZUM_API_KEY bo'lishi shart.
    has_login = Config.UZUM_USERNAME and Config.UZUM_PASSWORD
    if not has_login and not Config.UZUM_API_KEY:
        missing.append("UZUM_USERNAME+UZUM_PASSWORD (yoki UZUM_API_KEY)")
    if missing:
        raise RuntimeError(
            f".env faylida quyidagilar to'ldirilmagan: {', '.join(missing)}"
        )
