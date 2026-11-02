import requests

from config import Config

API_BASE = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}"
TELEGRAM_MAX_LEN = 4096


def send_text(text):
    response = requests.post(
        f"{API_BASE}/sendMessage", json={"chat_id": Config.TELEGRAM_CHAT_ID, "text": text}
    )
    response.raise_for_status()


def send_conversation(
    review_id,
    review_text,
    rating,
    conversation,
    final_reply,
    shop_id=None,
    retry=False,
    needs_approval=True,
    reviewer_approved=True,
    product=None,
    customer=None,
):
    """Bir qarashda tushunarli xabar: baho, mahsulot, mijoz nima dedi, biz
    nima javob berdik. Drafter/Reviewer ichki suhbati ko'rsatilmaydi - faqat
    necha marta qayta yozilgani."""
    rating = int(rating or 0)
    belgi = "🔴" if rating <= 2 else "🟡" if rating == 3 else "🟢"
    sarlavha = f"{belgi} {'⭐' * rating}{'☆' * (5 - rating)} {rating}/5"
    if shop_id:
        sarlavha += f" · {shop_id}"
    lines = [sarlavha]
    if product:
        lines.append(f"📦 {product}")
    if customer:
        lines.append(f"👤 {customer}")
    if retry:
        lines.append("🔁 Qayta yozilgan javob (avvalgisi rad etilgan edi)")

    if review_text.startswith("(Mijoz matn qoldirmagan"):
        lines += ["", "💬 Mijoz: faqat baho qo'ygan, matn yozmagan"]
    else:
        lines += ["", "💬 Mijoz yozdi:", review_text]
    lines += ["", "✍️ Javobimiz:", final_reply, ""]

    qayta = sum(1 for turn in conversation if turn.get("role") == "Reviewer" and "Qayta" in turn.get("text", ""))
    if needs_approval:
        lines.append("⏳ Tasdiqlashingizni kutmoqda")
    elif reviewer_approved:
        lines.append("✅ Uzum'ga yuborildi" + (f" · AI {qayta} marta qayta yozdi" if qayta else ""))
    else:
        lines.append(f"⚠️ Uzum'ga yuborildi, lekin AI {qayta} marta qayta yozib ham to'liq tasdiqlamadi — tekshirib qo'ying")

    text = "\n".join(lines)
    if len(text) > TELEGRAM_MAX_LEN:
        text = text[: TELEGRAM_MAX_LEN - 20] + "\n... (qisqartirildi)"

    payload = {"chat_id": Config.TELEGRAM_CHAT_ID, "text": text}
    if needs_approval:
        payload["reply_markup"] = {
            "inline_keyboard": [
                [
                    {"text": "✅ Approve", "callback_data": f"approve:{review_id}"},
                    {"text": "❌ Reject", "callback_data": f"reject:{review_id}"},
                ]
            ]
        }

    response = requests.post(f"{API_BASE}/sendMessage", json=payload)
    response.raise_for_status()
    return response.json()["result"]["message_id"]


def fetch_decisions(offset=0):
    response = requests.get(
        f"{API_BASE}/getUpdates", params={"offset": offset, "timeout": 0}
    )
    response.raise_for_status()
    updates = response.json()["result"]

    decisions = []
    next_offset = offset
    for update in updates:
        next_offset = update["update_id"] + 1
        callback = update.get("callback_query")
        if not callback:
            continue

        action, review_id = callback["data"].split(":", 1)
        decisions.append(
            {
                "review_id": review_id,
                "approved": action == "approve",
                "chat_id": callback["message"]["chat"]["id"],
                "message_id": callback["message"]["message_id"],
                "text": callback["message"]["text"],
            }
        )

        requests.post(
            f"{API_BASE}/answerCallbackQuery",
            json={
                "callback_query_id": callback["id"],
                "text": "Qabul qilindi ✅" if action == "approve" else "Bekor qilindi ❌",
            },
        )

    return decisions, next_offset


def mark_decision(chat_id, message_id, original_text, status_line):
    requests.post(
        f"{API_BASE}/editMessageText",
        json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": f"{original_text}\n\n{status_line}",
            "reply_markup": {"inline_keyboard": []},
        },
    )
