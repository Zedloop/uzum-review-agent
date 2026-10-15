import json
import os
import time

STATE_FILE = os.path.join(os.path.dirname(__file__), "data", "state.json")
LOCK_FILE = os.path.join(os.path.dirname(__file__), "data", "run.lock")
LOCK_STALE_SECONDS = 600


def _ensure_file():
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)


def load_state():
    _ensure_file()
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    _ensure_file()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def upsert_review(state, key, **fields):
    entry = state.get(key, {})
    entry.update(fields)
    state[key] = entry


def acquire_lock(timeout=30):
    """Ikki jarayon (masalan rejalashtirilgan tekshiruv va /restart) bir vaqtda
    ishlab, state.json'ni buzib qo'ymasligi uchun oddiy fayl-qulf."""
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    deadline = time.time() + timeout
    while True:
        try:
            fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        except FileExistsError:
            try:
                age = time.time() - os.path.getmtime(LOCK_FILE)
            except FileNotFoundError:
                continue
            if age > LOCK_STALE_SECONDS:
                try:
                    os.remove(LOCK_FILE)
                except FileNotFoundError:
                    pass
                continue
            if time.time() > deadline:
                return False
            time.sleep(1)


def release_lock():
    try:
        os.remove(LOCK_FILE)
    except FileNotFoundError:
        pass
