# W5: бот-лаунчер мини-приложения
# ПУТЬ: app/services/bot_keyboards.py
import re

LAUNCHER_TEXT = "Откройте приложение клуба кнопкой ниже."

_NUM = re.compile(r"^n:(\d+)$")


def payload_to_text(payload: str) -> str:
    m = _NUM.match((payload or "").strip())
    if m:
        return m.group(1)
    return payload or ""


def keyboard_for(text: str, link: str | None = None):
    url = link or "https://fixintel.ru/static/miniapp/index.html"
    return {"type": "inline_keyboard",
            "payload": {"buttons": [[{"type": "link",
                                      "text": "Открыть приложение",
                                      "url": url}]]}}
