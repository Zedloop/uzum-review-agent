import re

import anthropic

from config import Config

_claude_client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)


def generate_text(prompt, system_instruction, model, json_mode=False):
    system = system_instruction
    if json_mode:
        system += "\n\nFaqat toza JSON qaytaring, kod bloklari (```) yoki boshqa matn qo'shmang."

    response = _claude_client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    text = next((b.text for b in response.content if b.type == "text"), "").strip()
    if json_mode:
        text = _extract_json(text)
    return text


def _extract_json(text):
    text = text.strip().strip("`")
    if text.lower().startswith("json"):
        text = text[4:].strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text
