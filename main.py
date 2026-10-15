import os
import sys
import time
from datetime import datetime

from agents.drafter import draft_reply
from agents.learner import record_rejection, update_lessons
from agents.reviewer import review_reply
from config import Config, validate
from state_store import acquire_lock, load_state, release_lock, save_state, upsert_review
from telegram_bot import fetch_decisions, mark_decision, send_conversation, send_text
from uzum_client import UzumClient


def build_review_text(review):
    parts = []
    if review.get("pros"):
        parts.append(f"Yoqqan narsa: {review['pros']}")
    if review.get("cons"):
        parts.append(f"Yoqmagan narsa: {review['cons']}")
    if review.get("content"):
        parts.append(review["content"])
    return "\n".join(parts) if parts else "(Mijoz matn qoldirmagan, faqat baho qo'ygan)"


PLACEHOLDER_NAMES = {"***", "Безымянный", "Anonim", "Anonymous", "Noma'lum"}


def extract_customer_name(review):
    if review.get("anonymous"):
        return None
    name = (review.get("customerName") or "").strip()
    if not name or name in PLACEHOLDER_NAMES:
        return None
    return name


def process_review(uzum, state, review, shop_id, raw_id, key):
    is_retry = key in state
    review_text = build_review_text(review)
    rating = review["rating"]
    customer_name = extract_customer_name(review)
    shop_name = review.get("shop", {}).get("title") or shop_id

    conversation = []
    reply = draft_reply(review_text, rating, customer_name=customer_name)
    conversation.append({"role": "Drafter", "text": reply})

    reviewer_approved = False
    for _ in range(Config.MAX_REVISIONS):
        try:
            verdict = review_reply(review_text, rating, reply)
        except Exception as e:
            conversation.append(
                {"role": "Reviewer", "text": f"⚠️ Reviewer javobini o'qib bo'lmadi ({e}), tekshiruv o'tkazib yuborildi"}
            )
            break
        if verdict["approved"]:
            conversation.append({"role": "Reviewer", "text": "✅ Tasdiqlandi"})
            reviewer_approved = True
            break
        conversation.append(
            {"role": "Reviewer", "text": f"🔁 Qayta yozish: {verdict['feedback']}"}
        )
        record_rejection(review_text, rating, reply, verdict["feedback"])
        reply = draft_reply(
            review_text, rating, customer_name=customer_name, feedback=verdict["feedback"]
        )
        conversation.append({"role": "Drafter", "text": reply})

    uzum.send_reply(raw_id, reply)
    status = "sent"
    if reviewer_approved:
        print(f"[{shop_name}] Sharh {raw_id}: Reviewer tasdiqladi, Uzum'ga avtomatik yuborildi.")
    else:
        print(f"[{shop_name}] Sharh {raw_id}: Reviewer {Config.MAX_REVISIONS} marta qayta yozdirgach ham "
              f"to'liq tasdiqlamadi, baribir eng so'nggi javob Uzum'ga yuborildi.")

    # Uzum'ga javob allaqachon yuborildi - holatni DARHOL saqlaymiz, shunda
    # pastdagi Telegram xabari muvaffaqiyatsiz bo'lsa ham, tashqi retry bu
    # sharhni qayta Uzum'ga yubormaydi (takroriy javob xavfining oldini olish).
    upsert_review(
        state,
        key,
        status=status,
        reply=reply,
        review_text=review_text,
        shop_id=shop_id,
        shop_name=shop_name,
        review_id=raw_id,
    )
    save_state(state)

    try:
        send_conversation(
            key,
            review_text,
            rating,
            conversation,
            reply,
            shop_id=shop_name,
            retry=is_retry,
            needs_approval=False,
            reviewer_approved=reviewer_approved,
        )
    except Exception as e:
        print(f"[{shop_name}] Sharh {raw_id}: Telegram'ga xabar yuborilmadi ({e}), lekin Uzum'ga javob yuborilgan edi.")


def run_draft():
    """Yangi javobsiz sharhlarni topib, Drafter/Reviewer orqali javob tayyorlaydi
    va tasdiqlash uchun Telegram'ga yuboradi. Bir ishga tushirishda ko'pi bilan
    Config.MAX_REVIEWS_PER_RUN ta (eng eskisidan boshlab) sharh qayta ishlanadi."""
    validate()
    uzum = UzumClient()
    state = load_state()

    reviews = uzum.fetch_unanswered_reviews()
    pending_reviews = [
        review
        for review in reviews
        if state.get(f"{review['shop']['id']}:{review['reviewId']}", {}).get("status")
        in (None, "rejected")
    ]
    batch = pending_reviews[: Config.MAX_REVIEWS_PER_RUN]
    failures = []

    for review in batch:
        shop_id = str(review["shop"]["id"])
        raw_id = str(review["reviewId"])
        key = f"{shop_id}:{raw_id}"

        shop_name = review.get("shop", {}).get("title") or shop_id
        try:
            try:
                process_review(uzum, state, review, shop_id, raw_id, key)
            except Exception as first_error:
                print(f"[{shop_name}] Sharh {raw_id}: xato ({first_error}), 5 soniyadan keyin qayta urinib ko'riladi")
                time.sleep(5)
                process_review(uzum, state, review, shop_id, raw_id, key)
        except Exception as e:
            print(f"[{shop_name}] Sharh {raw_id}: XATO, o'tkazib yuborildi - {e}")
            failures.append(f"[{shop_name}] Sharh {raw_id}: {e}")

        time.sleep(1.5)

    if not batch:
        print("Javobsiz (hali qayta ishlanmagan) sharh topilmadi.")
    else:
        qolgan = len(pending_reviews) - len(batch)
        if qolgan > 0:
            print(f"Yana {qolgan} ta javobsiz sharh navbatda (keyingi 'draft' ishga tushirishda).")

    if failures:
        summary = "\n".join(failures[:10])
        more = f"\n... va yana {len(failures) - 10} ta" if len(failures) > 10 else ""
        try:
            send_text(
                f"⚠️ {len(failures)} ta sharhni qayta ishlashda xato yuz berdi:\n{summary}{more}\n\n"
                "Sabab ko'pincha Claude (Anthropic) balansi tugagani yoki API kaliti muddati "
                "o'tgani bo'lishi mumkin - tekshirib ko'ring."
            )
        except Exception:
            pass

    update_lessons()


def run_check():
    """Telegram'da bosilgan Approve/Reject tugmalarini tekshiradi va
    tasdiqlangan javoblarni Uzum'ga yuboradi."""
    validate()
    uzum = UzumClient()
    state = load_state()
    offset = state.get("_telegram_offset", 0)

    decisions, next_offset = fetch_decisions(offset)
    state["_telegram_offset"] = next_offset

    if not decisions:
        print("Yangi qaror (Approve/Reject) topilmadi.")

    for decision in decisions:
        key = decision["review_id"]
        entry = state.get(key)
        if not entry or entry.get("status") != "pending":
            continue

        shop_label = entry.get("shop_name") or entry["shop_id"]
        if decision["approved"]:
            uzum.send_reply(entry["review_id"], entry["reply"])
            entry["status"] = "sent"
            status_line = "✅ TASDIQLANDI — javob Uzum'ga yuborildi"
            print(f"[{shop_label}] Sharh {entry['review_id']}: javob Uzum'ga yuborildi.")
        else:
            entry["status"] = "rejected"
            status_line = "❌ RAD ETILDI — Uzum'ga yuborilmadi"
            print(f"[{shop_label}] Sharh {entry['review_id']}: rad etildi.")

        mark_decision(decision["chat_id"], decision["message_id"], decision["text"], status_line)

    save_state(state)


if __name__ == "__main__":
    _log_path = os.environ.get("UZUM_AGENT_LOG")
    if _log_path:
        sys.stdout = open(_log_path, "a", encoding="utf-8", buffering=1)
        sys.stderr = sys.stdout

    command = sys.argv[1] if len(sys.argv) > 1 else "draft"
    print(f"--- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {command} ---")
    if command not in ("draft", "check"):
        print("Foydalanish: python main.py [draft|check]")
    elif not acquire_lock():
        print("Boshqa jarayon hozir ishlamoqda, o'tkazib yuborildi.")
    else:
        try:
            if command == "draft":
                run_draft()
            elif command == "check":
                run_check()
        finally:
            release_lock()
