"""Tuzatishlar xotirasi: Reviewer Drafter javobini rad etib, keyin to'g'ri
javob tasdiqlangan har bir holat ("xato -> to'g'ri" juftligi) doimiy
saqlanadi. Yangi sharhga javob yozishda shu xotiradan eng o'xshash holatlar
Drafter'ga namuna sifatida ko'rsatiladi - shunda bir marta tuzatilgan xato
keyingi o'xshash sharhda takrorlanmaydi.

Saboqlar (learner.py) - umumiy qoidalar; bu yerda - aniq misollar.
"""
import json
import os
import re
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CORRECTIONS_FILE = os.path.join(DATA_DIR, "corrections.json")
MAX_CORRECTIONS = 300   # eng eskilari o'chiriladi (fayl cheksiz o'smasin)
EXAMPLES_PER_DRAFT = 3

_WORD = re.compile(r"[\w'ʻʼ‘’]{3,}", re.UNICODE)
_CYRILLIC = re.compile(r"[а-яёўқғҳА-ЯЁЎҚҒҲ]")


def _load():
    if not os.path.exists(CORRECTIONS_FILE):
        return []
    with open(CORRECTIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(items):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = CORRECTIONS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items[-MAX_CORRECTIONS:], f, ensure_ascii=False, indent=1)
    os.replace(tmp, CORRECTIONS_FILE)


def _words(text):
    return {w.lower() for w in _WORD.findall(text or "")}


def _script(text):
    return "cyrillic" if len(_CYRILLIC.findall(text or "")) > 3 else "latin"


def _rating_bucket(rating):
    return "neg" if rating <= 2 else ("mid" if rating == 3 else "pos")


def record_correction(review_text, rating, attempts, final_reply, approved):
    """attempts: [(rad etilgan javob, Reviewer sababi), ...]. approved -
    oxirgi javob Reviewer tomonidan tasdiqlanganmi (aks holda u "to'g'ri
    namuna" sifatida ko'rsatilmaydi, faqat xato va sabab ko'rsatiladi)."""
    if not attempts:
        return
    items = _load()
    items.append({
        "ts": datetime.now().isoformat(timespec="seconds"),
        "review_text": review_text[:600],
        "rating": rating,
        "attempts": [{"draft": d[:1000], "feedback": fb[:600]} for d, fb in attempts],
        "fixed_reply": final_reply[:1000] if approved else None,
    })
    _save(items)


def relevant_corrections(review_text, rating, k=EXAMPLES_PER_DRAFT):
    """Yangi sharhga eng o'xshash oldingi tuzatishlar. O'xshashlik: umumiy
    so'zlar + bir xil alifbo (javob shu alifboda yoziladi) + bir xil baho
    guruhi. To'g'ri javobi bor (tasdiqlangan) holatlar ustun."""
    items = _load()
    if not items:
        return []
    words, script, bucket = _words(review_text), _script(review_text), _rating_bucket(rating)
    scored = []
    for i, it in enumerate(items):
        other = _words(it["review_text"])
        overlap = len(words & other) / (len(words | other) or 1)
        score = overlap * 3
        score += 1.0 if _script(it["review_text"]) == script else 0
        score += 0.5 if _rating_bucket(it["rating"]) == bucket else 0
        score += 0.5 if it.get("fixed_reply") else 0
        score += i / len(items) * 0.3  # yangilari biroz ustun
        scored.append((score, i, it))
    scored.sort(key=lambda x: x[:2], reverse=True)
    return [it for _, _, it in scored[:k]]


def format_examples(examples):
    if not examples:
        return ""
    parts = ["Oldin shunga o'xshash sharhlarda qilingan XATOLAR va ularning tuzatilgan varianti "
             "(bu xatolarni takrorlamang, lekin javobni so'zma-so'z ko'chirmang - shu sharhga mos yozing):"]
    for n, ex in enumerate(examples, 1):
        parts.append(f"\n--- Misol {n} (baho {ex['rating']}/5) ---\nSharh: \"{ex['review_text']}\"")
        for a in ex["attempts"]:
            parts.append(f"❌ Rad etilgan javob: \"{a['draft']}\"\n   Sabab: {a['feedback']}")
        if ex.get("fixed_reply"):
            parts.append(f"✅ Tasdiqlangan javob: \"{ex['fixed_reply']}\"")
    return "\n".join(parts)


def count_corrections():
    return len(_load())


def first_try_stats(state, since_ts, until_ts=None):
    """state.json'dagi javoblar bo'yicha: nechtasi birinchi urinishda
    tasdiqlangan (Drafter o'sishini o'lchash uchun)."""
    total = first = 0
    for key, entry in state.items():
        if key.startswith("_") or not isinstance(entry, dict) or "rewrites" not in entry:
            continue
        ts = entry.get("answered_at", 0)
        if ts < since_ts or (until_ts and ts >= until_ts):
            continue
        total += 1
        first += 1 if entry["rewrites"] == 0 and entry.get("reviewer_approved") else 0
    return first, total
