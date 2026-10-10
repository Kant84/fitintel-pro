# W5: бот-лаунчер мини-приложения (интерфейс клуба — в приложении)
import re

# ВАЖНО: впишите URL мини-приложения из кабинета MAX (поле «Мини-приложение»)
APP_URL = "https://fixintel.ru/static/miniapp/index.html"

LAUNCHER_TEXT = "Приложение клуба:\n" + APP_URL

APP_KB = {"type": "inline_keyboard",
          "payload": {"buttons": [[{"type": "link",
                                    "text": "Открыть приложение",
                                    "url": APP_URL}]]}}

_NUM = re.compile(r"^n:(\d+)$")


def payload_to_text(payload: str) -> str:
    m = _NUM.match((payload or "").strip())
    if m:
        return m.group(1)
    return payload or ""


def keyboard_for(text: str):
    # лаунчер: всегда одна кнопка открытия приложения
    return APP_KB
