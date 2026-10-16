import requests
from flask import Flask, abort, request

from bot_listener import _run_cycle_for
from config import Config
from main import run_draft
from state_store import acquire_lock, release_lock
from telegram_bot import API_BASE

app = Flask(__name__)


def _notify(text):
    try:
        requests.post(
            f"{API_BASE}/sendMessage",
            json={"chat_id": Config.TELEGRAM_CHAT_ID, "text": text},
        )
    except Exception:
        pass


def _run_cycle():
    if not acquire_lock(timeout=10):
        return
    try:
        run_draft()
    except Exception as e:
        _notify(f"❌ Avtomatik tekshiruvda xato: {e}")
    finally:
        release_lock()


@app.route("/run-check")
def run_check_endpoint():
    token = request.args.get("token", "")
    if not Config.RUN_TOKEN or token != Config.RUN_TOKEN:
        abort(403)
    # Fon oqimida (thread) emas, shu so'rovning o'zida ishga tushiramiz -
    # ba'zi veb-hosting muhitlarida (masalan PythonAnywhere) so'rov tugagach
    # orqa fondagi thread to'xtatilib qo'yilishi mumkin, shuning uchun
    # ishonchliroq usul - natijani kutib, shu yerda bajarib tugatish.
    _run_cycle()
    return "OK", 200


@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    # Telegram'ning o'zidan kelayotganini tasdiqlash - setWebhook'da
    # ro'yxatdan o'tkazilgan maxfiy qiymat shu headerda qaytarilishi shart.
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not Config.TELEGRAM_WEBHOOK_SECRET or secret != Config.TELEGRAM_WEBHOOK_SECRET:
        abort(403)

    update = request.get_json(silent=True) or {}
    msg = update.get("message")
    if msg:
        text = (msg.get("text") or "").strip()
        chat_id = msg["chat"]["id"]
        if text == "/restart" and str(chat_id) == str(Config.TELEGRAM_CHAT_ID):
            _run_cycle_for(chat_id)
    return "OK", 200


if __name__ == "__main__":
    app.run()
