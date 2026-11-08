# -*- coding: utf-8 -*-
"""Патч support_bot/app.py (v19) -> v20:
1) has_domain: вопрос без тематики ПО -> вежливый отказ (без мусорных статей KB).
2) Команда «месяц [N]» в ЛС: просмотр для админа, смена — только владельцу.
Запуск из корня репозитория:  python patch_bot_v20.py
Идемпотентен (маркеры есть -> skip).
"""
import py_compile

PATH = "support_bot/app.py"
src = open(PATH, encoding="utf-8").read()
changes = []

# 1) DOMAIN + has_domain
if "def has_domain(" in src:
    changes.append("has_domain: already present (skip)")
else:
    anchor = """    singles = sum(1 for w in OFFTOPIC_SINGLE if w in t)
    return singles >= 2"""
    assert src.count(anchor) == 1, "anchor offtopic_hit не найден"
    addition = anchor + """

DOMAIN = {"клиент","абонемент","платёж","платеж","оплат","касс","ккт","чек","турникет","браслет",
          "вход","визит","расписан","услуг","тренер","пользовател","роль","прав","лиценз","desktop",
          "программ","сервер","настройк","уведомлен","email","смс","max","вендинг","автомат","магазин",
          "склад","зарплат","отчёт","отчет","face","музык","шкафчик","rfid","скуд","ошибк","обновлен",
          "установк","qr","замер","фискальн","атол","эквайринг","банк","юкасса","скриншот","лог","доступ",
          "парол","сайт","баланс","кошелёк","бонус","скидк","замороз","списан","возврат","продл","тариф",
          "сообщен","чат","выйти","список","карточк","анкет","документ","фото","камер","датчик",
          "токен","api","синхрон","резервн","бэкап","оборудован","считыват","пропуск","онлайн","офлайн"}

def has_domain(text: str) -> bool:
    t = text.lower()
    return any(w in t for w in DOMAIN)"""
    src = src.replace(anchor, addition, 1)
    changes.append("has_domain: inserted")

# 2) guard в answer_or_forward
if "no-domain refused" in src:
    changes.append("guard: already present (skip)")
else:
    anchor = """    if offtopic_hit(text):
        log.info("offtopic refused: %.80s", text)
        await max_send(user_id, f"{greet(user_id)}{NL}{OFFTOPIC_REPLY}")
        return"""
    assert src.count(anchor) == 1, "anchor answer_or_forward не найден"
    addition = anchor + """
    if not has_domain(text):
        log.info("no-domain refused: %.80s", text)
        await max_send(user_id, f"{greet(user_id)}{NL}{OFFTOPIC_REPLY}")
        return"""
    src = src.replace(anchor, addition, 1)
    changes.append("guard: inserted")

# 3) «месяц [N]» в ЛС
if "Расчётный месяц начинается" in src:
    changes.append("месяц: already present (skip)")
else:
    anchor = """        if is_admin and text.strip().lower() in MODE_CMD:
            await max_send(user_id, mode_help(mode), attachments=mode_keyboard(mode))
            return {"ok": True}
        if is_admin and text and mode != "user":"""
    assert src.count(anchor) == 1, "anchor DM dispatch не найден"
    addition = """        if is_admin and text.strip().lower() in MODE_CMD:
            await max_send(user_id, mode_help(mode), attachments=mode_keyboard(mode))
            return {"ok": True}
        if is_admin and text.strip().lower().startswith("месяц"):
            parts = text.split()
            if len(parts) == 1:
                await max_send(user_id, f"Начало расчётного месяца: {get_setting('stats_month_start', '1')}-е число. "
                                        "Сменить (владелец): «месяц 5».")
                return {"ok": True}
            if get_role(user_id) == "superadmin" and parts[1].isdigit() and 1 <= int(parts[1]) <= 28:
                set_setting("stats_month_start", parts[1])
                await max_send(user_id, f"✅ Расчётный месяц начинается {parts[1]}-го числа.")
            else:
                await max_send(user_id, "Не изменено: нужна роль владельца и число 1–28.")
            return {"ok": True}
        if is_admin and text and mode != "user":"""
    src = src.replace(anchor, addition, 1)
    changes.append("месяц: inserted")

open(PATH, "w", encoding="utf-8", newline="\n").write(src)
py_compile.compile(PATH, doraise=True)
for c in changes:
    print(c)
print("PATCH_OK=1")