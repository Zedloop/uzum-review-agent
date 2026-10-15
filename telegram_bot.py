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
):
    header_lines = [f"🏪 Do'kon: {shop_id}"] if shop_id else []
    if retry:
        header_lines.append("🔁 Qayta yozilgan javob (avvalgisi rad etilgan edi)")
    header_lines += [
        f"🆕 Yangi sharh (baho: {rating}/5)",
        f'"{review_text}"',
        "",
        "💬 Drafter va Reviewer suhbati:",
    ]
    header = "\n".join(header_lines)

    footer_lines = [f'\n✅ Yakuniy javob:\n"{final_reply}"']
    if not needs_approval:
        if reviewer_approved:
            footer_lines.append("\n🤖 Reviewer tasdiqladi — Uzum'ga avtomatik yuborildi.")
        else:
            footer_lines.append(
                "\n🤖 Reviewer to'liq tasdiqlamadi, lekin eng so'nggi javob baribir "
                "Uzum'ga avtomatik yuborildi."
            )
    footer = "\n".join(footer_lines)

    conversation_text = "".join(
        f"\n▫️ {turn['role']}: {turn['text']}" for turn in conversation
    )

    budget = TELEGRAM_MAX_LEN - len(header) - len(footer) - 40
    if budget > 0 and len(conversation_text) > budget:
        conversation_text = conversation_text[:budget] + "\n... (qisqartirildi)"
    elif budget <= 0:
        conversation_text = "\n(suhbat juda uzun, ko'rsatilmadi)"

    text = f"{header}{conversation_text}{footer}"
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
