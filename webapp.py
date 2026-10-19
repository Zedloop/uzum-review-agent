import requests
from flask import Flask, abort, request

from config import Config
from heartbeat import load_heartbeat, record_run
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
        record_run()
    except Exception as e:
        record_run(error=e)
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


@app.route("/health")
def health_endpoint():
    # Hetzner'dagi kuzatuvchi (watchdog) shu orqali agent oxirgi marta
    # qachon muvaffaqiyatli ishlaganini tekshiradi - faqat vaqtlar, maxfiy
    # ma'lumot yo'q.
    hb = load_heartbeat()
    return {"last_ok": hb.get("last_ok"), "last_error_at": hb.get("last_error_at")}


if __name__ == "__main__":
    app.run()
