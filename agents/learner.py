import json
import os
from datetime import datetime

from agents._llm import generate_text
from config import Config

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
FEEDBACK_LOG_FILE = os.path.join(DATA_DIR, "feedback_log.json")
LESSONS_FILE = os.path.join(DATA_DIR, "lessons.json")
MAX_LESSONS = 25
RECENT_FEEDBACK_LIMIT = 30
# Har siklda emas - shuncha yangi rad etish to'plangach saboqlar yangilanadi
# (har safar qayta yozilaverib, eski saboqlar yo'qolib ketmasligi uchun)
DISTILL_EVERY = 5
# Yangi ro'yxat eskisidan shuncha qoidadan ko'proq qisqa bo'lsa - AI saboqlarni
# "unutgan" deb hisoblab, yangilanish qabul qilinmaydi
MAX_LESSONS_DROP = 2

DISTILL_SYSTEM_PROMPT = f"""Siz Uzum Market mijozlar sharhlariga javob yozuvchi "Drafter" AI
agentini yaxshilash uchun undagi xatolar tarixini tahlil qiluvchi yordamchisiz.
Sizga ikkita narsa beriladi: (1) hozirgi saboqlar ro'yxati (bo'sh bo'lishi ham mumkin),
(2) Muharrir (Reviewer) tomonidan yaqinda rad etilgan javoblar va ularning sabablari.
Vazifangiz: hozirgi ro'yxatni YANGILASH, uni noldan qayta yozish EMAS:
- mavjud saboqlarni saqlang - ular avvalgi xatolardan olingan, o'chirmang;
- yangi rad etishlarda mavjud saboqlarda yo'q xato naqshi bo'lsa - yangi saboq qo'shing;
- yangi misollar mavjud saboqni aniqlashtirsa - o'sha saboqni aniqroq qilib qayta yozing;
- bir xil ma'nodagi saboqlarni bittaga birlashtirish mumkin, lekin ma'no yo'qolmasin;
- "diqqat bilan tekshiring" kabi umumiy gaplar emas - aniq, amaliy qoida yozing
  (qaysi so'z/qurilma noto'g'ri va o'rniga qaysi biri to'g'ri);
- saboq ichida taqiqlangan iborani "to'g'ri namuna" sifatida keltirmang.
Ro'yxat ko'pi bilan {MAX_LESSONS} ta qoidadan iborat bo'lsin, har biri bitta qisqa jumla.
Faqat quyidagi JSON formatida javob bering, boshqa hech narsa yozmang:
{{"lessons": ["qoida 1", "qoida 2", ...]}}"""


def _load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def record_rejection(review_text, rating, draft, feedback):
    """Reviewer rad etgan javobni keyinchalik tahlil qilish uchun saqlaydi."""
    log = _load_json(FEEDBACK_LOG_FILE, [])
    log.append(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "review_text": review_text[:500],
            "rating": rating,
            "draft": draft[:1000],
            "feedback": feedback,
        }
    )
    _save_json(FEEDBACK_LOG_FILE, log)


def get_lessons():
    data = _load_json(LESSONS_FILE, {"lessons": []})
    return data.get("lessons", [])


def update_lessons():
    """To'plangan rad etishlar asosida saboqlar ro'yxatini AI yordamida yangilaydi."""
    log = _load_json(FEEDBACK_LOG_FILE, [])
    if len(log) < DISTILL_EVERY:
        return

    current_lessons = get_lessons()
    recent = log[-RECENT_FEEDBACK_LIMIT:]
    feedback_text = "\n".join(
        f'- Sharh: "{item["review_text"]}" (baho {item["rating"]}) | '
        f'Javob: "{item["draft"]}" | Sabab: {item["feedback"]}'
        for item in recent
    )
    current_text = "\n".join(f"- {lesson}" for lesson in current_lessons) or "(hozircha yo'q)"

    prompt = (
        f"Hozirgi saboqlar ro'yxati:\n{current_text}\n\n"
        f"Yaqinda rad etilgan javoblar:\n{feedback_text}\n\n"
        "Yangilangan saboqlar ro'yxatini tuzing."
    )

    try:
        text = generate_text(
            prompt, DISTILL_SYSTEM_PROMPT, Config.CLAUDE_MODEL_REVIEWER, json_mode=True
        )
        result = json.loads(text)
        lessons = result.get("lessons", [])[:MAX_LESSONS]
    except Exception as e:
        print(f"Saboqlarni yangilashda xato: {e}")
        return

    if lessons and len(lessons) < len(current_lessons) - MAX_LESSONS_DROP:
        print(f"Saboqlar yangilanmadi: yangi ro'yxat {len(lessons)} ta, eskisi {len(current_lessons)} ta - "
              "eski saboqlar yo'qolib ketmasligi uchun rad etildi.")
        # Har siklda qayta urinib API'ga pul sarflamaslik uchun jurnalni
        # tozalaymiz - bu holatlar memory.py'da aniq misol sifatida saqlangan
        _save_json(FEEDBACK_LOG_FILE, [])
        return

    if lessons:
        _save_json(
            LESSONS_FILE,
            {"lessons": lessons, "updated_at": datetime.now().isoformat(timespec="seconds")},
        )
        _save_json(FEEDBACK_LOG_FILE, [])
        print(f"Saboqlar ro'yxati yangilandi ({len(lessons)} ta qoida).")
