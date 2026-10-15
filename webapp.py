import threading

import requests
from flask import Flask, abort, request

from config import Config
from main import run_draft
from state_store import acquire_lock, release_lock
from telegram_bot import API_BASE

app = Flask(__name__)


def _send(chat_id, text):
    try:
        requests.post(f"{API_BASE}/sendMessage", json={"chat_id": chat_id, "text": text})
    except Exception:
        pass


def _run_cycle(chat_id=None):
    if not acquire_lock(timeout=10):
        if chat_id:
            _send(chat_id, "⏳ Boshqa tekshiruv hozir ketyapti, biroz kutib qayta urinib ko'ring.")
        return
    try:
        # Eslatma: run_check() (Telegram getUpdates orqali Approve/Reject tugmasini
        # tekshirish) endi chaqirilmaydi - webhook rejimida getUpdates ishlamaydi
        # (409 Conflict) va bu funksiya baribir hech qachon ishlatilmaydi, chunki
        # javoblar har doim avtomatik yuboriladi, tugma orqali tasdiqlash shart emas.
        run_draft()
        if chat_id:
            _send(chat_id, "✅ Tekshiruv tugadi.")
    except Exception as e:
        if chat_id:
            _send(chat_id, f"❌ Xato yuz berdi: {e}")
    finally:
        release_lock()


@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    update = request.get_json(silent=True) or {}
    msg = update.get("message")
    if msg:
        text = (msg.get("text") or "").strip()
        chat_id = msg["chat"]["id"]
        if text == "/restart" and str(chat_id) == str(Config.TELEGRAM_CHAT_ID):
            _send(chat_id, "🔄 Tekshirilmoqda...")
            threading.Thread(target=_run_cycle, args=(chat_id,), daemon=True).start()
    return "", 200


@app.route("/run-check")
def run_check_endpoint():
    token = request.args.get("token", "")
    if not Config.RUN_TOKEN or token != Config.RUN_TOKEN:
        abort(403)
    threading.Thread(target=_run_cycle, daemon=True).start()
    return "OK", 200


if __name__ == "__main__":
    app.run()
