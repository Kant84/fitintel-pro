# W5: кнопочный интерфейс бота MAX (inline keyboard, без эмодзи)
import re


def build(rows):
    return {"type": "inline_keyboard",
            "payload": {"buttons": [[{"type": "callback", "text": t, "payload": p}
                                     for t, p in row] for row in rows]}}


MAIN = build([
    [("Магазин", "n:1"), ("Расписание занятий", "n:2")],
    [("Личный тренер", "n:3"), ("Мои записи", "n:4")],
    [("QR на вход", "n:5"), ("Бонусы", "n:6")],
    [("Мои дети", "n:7"), ("Пополнить баланс", "n:8")],
])
BACK_MAIN = build([[("Главное меню", "n:0")]])
SHOP_KIND = build([
    [("Занятия и услуги (запись)", "n:1"), ("Товары (оплата с баланса)", "n:2")],
    [("Главное меню", "n:0")],
])
REG = build([[("Зарегистрироваться", "n:1")]])

_NUM = re.compile(r"^n:(\d+)$")


def payload_to_text(payload: str) -> str:
    m = _NUM.match((payload or "").strip())
    if m:
        return m.group(1)
    if payload == "menu:main":
        return "0"
    return payload or ""


def _numbered(text):
    out = []
    for line in (text or "").splitlines():
        m = re.match(r"^\s*(\d+)\.\s+(.+)$", line)
        if m:
            name = m.group(2).split(" — ")[0].strip()[:40]
            out.append((name, "n:" + m.group(1)))
    return out


def keyboard_for(text: str):
    t = text or ""
    if t.startswith("Главное меню"):
        return MAIN
    if t.startswith("Магазин:"):
        return SHOP_KIND
    if t.startswith("Регистрация. Шаг 1/4"):
        return REG
    items = _numbered(t)
    if items and ("Услуги клуба" in t[:30] or "Товары (оплата" in t[:40]
                  or "Выберите время" in t[:60] or t.startswith("Мои записи")):
        rows = [items[i:i + 2] for i in range(0, len(items), 2)]
        rows.append([("Главное меню", "n:0")])
        return build(rows)
    return BACK_MAIN
