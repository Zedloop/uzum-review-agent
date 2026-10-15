import json
import os
import time
import traceback

import requests

from config import Config, validate
from main import run_check, run_draft
from state_store import acquire_lock, release_lock
from telegram_bot import API_BASE

OFFSET_FILE = os.path.join(os.path.dirname(__file__), "data", "listener_offset.json")


def _load_offset():
    if not os.path.exists(OFFSET_FILE):
        return 0
    try:
        with open(OFFSET_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("offset", 0)
    except Exception:
        return 0


def _save_offset(offset):
    os.makedirs(os.path.dirname(OFFSET_FILE), exist_ok=True)
    with open(OFFSET_FILE, "w", encoding="utf-8") as f:
        json.dump({"offset": offset}, f)


def _send(chat_id, text):
    try:
        requests.post(f"{API_BASE}/sendMessage", json={"chat_id": chat_id, "text": text})
    except Exception:
        pass


def _run_cycle_for(chat_id):
    if not acquire_lock(timeout=10):
        _send(chat_id, "⏳ Boshqa tekshiruv hozir ketyapti, biroz kutib qayta urinib ko'ring.")
        return
    try:
        _send(chat_id, "🔄 Tekshirilmoqda...")
        run_check()
        run_draft()
        _send(chat_id, "✅ Tekshiruv tugadi.")
    except Exception as e:
        _send(chat_id, f"❌ Xato yuz berdi: {e}")
    finally:
        release_lock()


def _poll_once(offset):
    resp = requests.get(f"{API_BASE}/getUpdates", params={"offset": offset, "timeout": 30})
    resp.raise_for_status()
    updates = resp.json()["result"]

    for update in updates:
        offset = update["update_id"] + 1
        msg = update.get("message")
        if not msg:
            continue
        text = (msg.get("text") or "").strip()
        chat_id = msg["chat"]["id"]
        if text == "/restart" and str(chat_id) == str(Config.TELEGRAM_CHAT_ID):
            print(f"/restart buyrug'i olindi (chat_id={chat_id})")
            _run_cycle_for(chat_id)

    return offset


def listen():
    validate()
    print("Bot tinglovchisi ishga tushdi, /restart buyrug'ini kutmoqda...")

    offset = _load_offset()

    while True:
        try:
            new_offset = _poll_once(offset)
            if new_offset != offset:
                offset = new_offset
                _save_offset(offset)
        except Exception as e:
            print(f"Tinglovchi xatosi (davom etmoqda): {e}")
            traceback.print_exc()
            time.sleep(5)


if __name__ == "__main__":
    while True:
        try:
            listen()
        except Exception as e:
            print(f"Tinglovchi butunlay yiqildi, 10 soniyadan keyin qayta boshlanadi: {e}")
            traceback.print_exc()
            time.sleep(10)
