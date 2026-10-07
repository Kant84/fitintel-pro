"""Волна 5, Пакет Б: сценарии MAX-бота — регистрация, меню, запись.

Отдельный модуль: max_bot.py держит команды/QR, сюда вынесены диалоговые сценарии
(FSM по max_user_id). Все тексты — через лейблы (club_params.get_label).
Таблица FSM — sqlite-совместимый DDL (тестовая сессия!).
"""
import json
import re
from datetime import datetime, timezone, timedelta, date

from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.api.v1.club_params import get_label, get_param_int
from app.models.client import Client
from app.models.service import Service, ServiceBooking

MENU_TEXT = (
    "Главное меню:\n"
    "1. 🛍 Магазин (услуги, товары)\n"
    "2. 🗓 Расписание занятий\n"
    "3. 👤 Личный тренер\n"
    "4. 📋 Мои записи\n"
    "5. 🔳 QR на вход\n"
    "6. 🎁 Бонусы\n\n"
    "Ответьте номером или словом (например: «1» или «магазин»)."
)


# ---------------- FSM ----------------

def _ensure(db: Session):
    db.execute(sql_text(
        "CREATE TABLE IF NOT EXISTS max_bot_fsm ("
        " max_user_id BIGINT PRIMARY KEY,"
        " state TEXT, data TEXT,"
        " updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"))
    db.commit()


def _get_state(db: Session, uid: int):
    row = db.execute(sql_text(
        "SELECT state, data FROM max_bot_fsm WHERE max_user_id=:u"),
        {"u": int(uid)}).first()
    if not row or not row[0]:
        return None, {}
    try:
        return row[0], json.loads(row[1] or "{}")
    except Exception:
        return row[0], {}


def _set_state(db: Session, uid: int, state: str, data: dict):
    db.execute(sql_text(
        "INSERT INTO max_bot_fsm (max_user_id, state, data) VALUES (:u,:s,:d) "
        "ON CONFLICT (max_user_id) DO UPDATE SET state=:s, data=:d"),
        {"u": int(uid), "s": state, "d": json.dumps(data, ensure_ascii=False)})
    db.commit()


def _clear(db: Session, uid: int):
    db.execute(sql_text("DELETE FROM max_bot_fsm WHERE max_user_id=:u"), {"u": int(uid)})
    db.commit()


# ---------------- привязка ----------------

def _find_client_row(db: Session, uid: int):
    return db.execute(sql_text(
        "SELECT c.id, c.first_name, c.last_name, c.phone FROM clients c "
        "JOIN max_bot_bindings mb ON replace(mb.client_id,'-','') = replace(CAST(c.id AS TEXT),'-','') "
        "WHERE mb.max_user_id=:u LIMIT 1"), {"u": int(uid)}).first()


def _bind(db: Session, uid: int, client_id):
    _ensure(db)
    db.execute(sql_text(
        "INSERT INTO max_bot_bindings (max_user_id, client_id) VALUES (:u,:c) "
        "ON CONFLICT (max_user_id) DO UPDATE SET client_id=:c"),
        {"u": int(uid), "c": str(client_id).replace("-", "")})
    db.commit()


# ---------------- helpers ----------------

def _menu() -> str:
    return get_label("TXT.MENU.MAIN", MENU_TEXT)


def _norm(t: str) -> str:
    return (t or "").strip().lower()


# ---------------- сценарии ----------------

def _start_registration(db: Session, uid: int) -> str:
    _set_state(db, uid, "REG_FIO", {})
    return ("Регистрация. Шаг 1/4: напишите ФИО одной строкой "
            "(например: Иванов Иван Иванович).")


def _step_registration(db: Session, uid: int, text: str) -> str:
    state, data = _get_state(db, uid)
    t = _norm(text)

    if state == "REG_FIO":
        parts = text.strip().split()
        if len(parts) < 2:
            return "Нужны минимум фамилия и имя. Попробуйте ещё раз:"
        data.update(last_name=parts[0], first_name=parts[1],
                    middle_name=" ".join(parts[2:]) or None)
        _set_state(db, uid, "REG_PHONE", data)
        return "Шаг 2/4: напишите номер телефона (например: +79001234567)."

    if state == "REG_PHONE":
        phone = re.sub(r"[\s()-]", "", text)
        if not re.match(r"^\+?7\d{10}$", phone):
            return "Не похоже на российский номер. Пример: +79001234567. Ещё раз:"
        if not phone.startswith("+"):
            phone = "+" + phone
        data["phone"] = phone
        _set_state(db, uid, "REG_EMAIL", data)
        return "Шаг 3/4: email (необязательно) — напишите адрес или «-»."

    if state == "REG_EMAIL":
        email = text.strip()
        if email not in ("-", ""):
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                return "Похоже на опечатку в email. Ещё раз или «-»:"
            data["email"] = email
        _set_state(db, uid, "REG_BIRTH", data)
        return "Шаг 4/4: дата рождения ДД.ММ.ГГГГ (например: 15.03.1990)."

    if state == "REG_BIRTH":
        m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", text.strip())
        if not m:
            return "Формат: ДД.ММ.ГГГГ. Ещё раз:"
        d, mo, y = map(int, m.groups())
        try:
            data["birth_date"] = date(y, mo, d).isoformat()
        except ValueError:
            return "Такой даты не бывает. Ещё раз:"
        # создание клиента
        try:
            c = Client(first_name=data["first_name"], last_name=data["last_name"],
                       middle_name=data.get("middle_name"), phone=data["phone"],
                       email=data.get("email"),
                       birth_date=date(y, mo, d),
                       gender="НЕ_УКАЗАН", client_category="ADULT")
            db.add(c)
            db.commit()
            db.refresh(c)
        except Exception as e:
            db.rollback()
            _clear(db, uid)
            return f"Не получилось создать карточку (возможно, телефон уже есть в базе). Напишите /start и попробуйте снова. ({str(e)[:80]})"
        _bind(db, uid, c.id)
        _clear(db, uid)
        return (f"Готово, {data['first_name']}! Карточка создана и привязана.\n\n" + _menu())

    return _menu()


def _shop(db: Session, uid: int) -> str:
    svcs = db.query(Service).filter(Service.is_active.is_(True)).order_by(Service.name).limit(20).all()
    if not svcs:
        return get_label("TXT.SCHEDULE.EMPTY", "Каталог пуст.")
    lines = ["🛍 Услуги клуба (запись — номером):"]
    for i, s in enumerate(svcs, 1):
        price = f"{s.price:.0f} ₽" if s.price else ""
        lines.append(f"{i}. {s.name} {price}".rstrip())
    _set_state(db, uid, "SHOP_PICK", {"ids": [str(s.id) for s in svcs]})
    lines.append("\nТовары — на ресепшене. Оплата — в клубе любым способом.")
    return "\n".join(lines)


def _shop_pick(db: Session, uid: int, text: str) -> str:
    _, data = _get_state(db, uid)
    ids = data.get("ids", [])
    if not text.strip().isdigit() or not (1 <= int(text) <= len(ids)):
        return "Напишите номер услуги из списка."
    svc = db.get(Service, ids[int(text) - 1])
    if not svc:
        return "Услуга не найдена. Попробуйте снова: /start"
    sched = svc.schedule or {}
    days = sched.get("days") or []
    slots = sched.get("time_slots") or []
    if not slots:
        # без расписания — свободный ввод даты
        _set_state(db, uid, "BOOK_FREE_DATE", {"sid": str(svc.id)})
        return (f"«{svc.name}». Напишите дату и время занятия: ДД.ММ.ГГГГ ЧЧ:ММ")
    # даты на 7 дней вперёд по schedule.days
    out, opts = [], []
    for add in range(0, 8):
        d = date.today() + timedelta(days=add)
        if days and d.weekday() not in days:
            continue
        opts.append(d)
    if not opts:
        return "Ближайших дней по расписанию нет. Уточните на ресепшене."
    for i, d in enumerate(opts[:7], 1):
        out.append(f"{i}. {d.strftime('%d.%m.%Y (%a)')}")
    _set_state(db, uid, "BOOK_PICK_DATE", {"sid": str(svc.id), "dates": [x.isoformat() for x in opts[:7]], "slots": slots})
    return f"«{svc.name}». Выберите дату:\n" + "\n".join(out)


def _book_pick_date(db: Session, uid: int, text: str) -> str:
    _, data = _get_state(db, uid)
    dates = data.get("dates", [])
    if not text.strip().isdigit() or not (1 <= int(text) <= len(dates)):
        return "Напишите номер даты из списка."
    data["date"] = dates[int(text) - 1]
    slots = data.get("slots", [])
    lines = []
    for i, sl in enumerate(slots, 1):
        t = sl.get("time", "")
        cap = sl.get("capacity", 1)
        when = datetime.fromisoformat(data["date"] + "T" + t)
        booked = db.query(ServiceBooking).filter(
            ServiceBooking.service_id == data["sid"],
            ServiceBooking.booking_date == when,
            ServiceBooking.status.in_(["BOOKED", "CONFIRMED", "PAID"])).count()
        left = max(0, cap - booked)
        mark = f"— мест: {left}" if left else "— нет мест"
        lines.append(f"{i}. {t} {mark}")
    _set_state(db, uid, "BOOK_PICK_SLOT", data)
    return "Выберите время:\n" + "\n".join(lines)


def _book_pick_slot(db: Session, uid: int, text: str, row) -> str:
    _, data = _get_state(db, uid)
    slots = data.get("slots", [])
    if not text.strip().isdigit() or not (1 <= int(text) <= len(slots)):
        return "Напишите номер времени из списка."
    t = slots[int(text) - 1].get("time", "")
    cap = slots[int(text) - 1].get("capacity", 1)
    when = datetime.fromisoformat(data["date"] + "T" + t).replace(tzinfo=timezone.utc)
    booked = db.query(ServiceBooking).filter(
        ServiceBooking.service_id == data["sid"],
        ServiceBooking.booking_date == when.replace(tzinfo=None),
        ServiceBooking.status.in_(["BOOKED", "CONFIRMED", "PAID"])).count()
    if booked >= cap:
        return "Место только что заняли. Выберите другое время."
    conflict = db.query(ServiceBooking).filter(
        ServiceBooking.client_id == str(row[0]),
        ServiceBooking.booking_date == when.replace(tzinfo=None),
        ServiceBooking.status.in_(["BOOKED", "CONFIRMED", "PAID"])).first()
    if conflict:
        return "У вас уже есть запись на это время. Выберите другое."
    b = ServiceBooking(service_id=data["sid"], client_id=str(row[0]),
                       booking_date=when.replace(tzinfo=None), status="BOOKED", source="MAX")
    db.add(b)
    db.commit()
    _clear(db, uid)
    return (f"✅ Запись создана: {data['date']} {t}. Оплатите на ресепшене — "
            f"за сутки до занятия пришлю напоминание с просьбой подтвердить.\n\n" + _menu())


def _book_free_date(db: Session, uid: int, text: str, row) -> str:
    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})[\sT]+(\d{2}):(\d{2})$", text.strip())
    if not m:
        return "Формат: ДД.ММ.ГГГГ ЧЧ:ММ. Ещё раз:"
    dd, mm, yy, hh, mi = map(int, m.groups())
    try:
        when = datetime(yy, mm, dd, hh, mi, tzinfo=timezone.utc)
        if when < datetime.now(timezone.utc):
            return "Это время уже прошло. Ещё раз:"
    except ValueError:
        return "Некорректная дата. Ещё раз:"
    _, data = _get_state(db, uid)
    b = ServiceBooking(service_id=data["sid"], client_id=str(row[0]),
                       booking_date=when.replace(tzinfo=None), status="BOOKED", source="MAX")
    db.add(b)
    db.commit()
    _clear(db, uid)
    return f"✅ Запись создана: {dd:02d}.{mm:02d}.{yy} {hh:02d}:{mi:02d}. Оплатите на ресепшене.\n\n" + _menu()


def _my_bookings(db: Session, row) -> str:
    rows = (db.query(ServiceBooking, Service)
            .join(Service, ServiceBooking.service_id == Service.id)
            .filter(ServiceBooking.client_id == str(row[0]),
                    ServiceBooking.status.in_(["BOOKED", "CONFIRMED", "PAID"]))
            .order_by(ServiceBooking.booking_date).limit(10).all())
    if not rows:
        return "Активных записей нет."
    lines = ["📋 Ваши записи:"]
    for i, (b, s) in enumerate(rows, 1):
        st = {"BOOKED": "ждёт подтверждения", "CONFIRMED": "подтверждена",
              "PAID": "оплачена"}.get(b.status, b.status)
        bd = b.booking_date
        t = bd.strftime("%d.%m %H:%M") if hasattr(bd, "strftime") else str(bd)[:16]
        lines.append(f"{i}. {t} «{s.name}» — {st}")
    lines.append("\nПодтвердить запись: «подтвердить <номер>».")
    return "\n".join(lines)


def _my_confirm(db: Session, uid: int, text: str, row) -> str:
    m = re.match(r"^подтвердить\s+(\d+)$", _norm(text))
    _, data = _get_state(db, uid)
    ids = data.get("ids", [])
    if not m or not (1 <= int(m.group(1)) <= len(ids)):
        return "Формат: «подтвердить <номер записи>»."
    b = db.get(ServiceBooking, ids[int(m.group(1)) - 1])
    if not b or str(b.client_id).replace("-", "") != str(row[0]).replace("-", ""):
        return "Запись не найдена."
    if b.status != "BOOKED":
        return f"Статус «{b.status}» — подтверждение не требуется."
    b.status = "CONFIRMED"
    b.confirmed_at = datetime.now(timezone.utc)
    db.commit()
    _clear(db, uid)
    return get_label("TXT.CONFIRM.OK", "✅ Запись подтверждена. Ждём вас!") + "\n\n" + _menu()


# ---------------- точка входа ----------------

def handle(db: Session, max_user_id: int, text: str) -> str | None:
    """Возвращает ответ, если сценарий обработал сообщение, иначе None (команды)."""
    _ensure(db)
    t = _norm(text)
    row = _find_client_row(db, max_user_id)
    state, _ = _get_state(db, max_user_id)

    # действующий сценарий продолжаем в первую очередь
    if state:
        if state.startswith("REG_"):
            return _step_registration(db, max_user_id, text)
        if not row:
            _clear(db, max_user_id)
            return "Нужна привязка карточки: сообщите номер телефона администратору или на ресепшене."
        if state == "SHOP_PICK":
            return _shop_pick(db, max_user_id, text)
        if state == "BOOK_PICK_DATE":
            return _book_pick_date(db, max_user_id, text)
        if state == "BOOK_PICK_SLOT":
            return _book_pick_slot(db, max_user_id, text, row)
        if state == "BOOK_FREE_DATE":
            return _book_free_date(db, max_user_id, text, row)
        if state == "MY_CONFIRM":
            return _my_confirm(db, max_user_id, text, row)

    # старт/регистрация
    if t in ("/start", "start", "старт", "привет", "меню", "0"):
        if not row:
            return _start_registration(db, max_user_id)
        return _menu()
    if t in ("регистрация", "зарегистрироваться"):
        return _start_registration(db, max_user_id)

    if not row:
        return None   # пусть max_bot ответит про привязку

    # пункты меню
    if t in ("1", "магазин", "услуги", "товары"):
        return _shop(db, max_user_id)
    if t in ("2", "расписание", "занятия"):
        svcs = db.query(Service).filter(Service.is_active.is_(True)).all()
        lines = ["🗓 Расписание (запись по номеру):"] if svcs else []
        for i, s in enumerate(svcs[:20], 1):
            lines.append(f"{i}. {s.name}")
        if svcs:
            _set_state(db, max_user_id, "SHOP_PICK", {"ids": [str(s.id) for s in svcs[:20]]})
            return "\n".join(lines)
        return get_label("TXT.SCHEDULE.EMPTY", "Расписание появится позже.")
    if t in ("3", "тренер", "персоналка", "личный тренер"):
        svcs = (db.query(Service)
                .filter(Service.is_active.is_(True),
                        Service.category == "PERSONAL_TRAINER").all())
        if not svcs:
            return get_label("TXT.TRAINER.EMPTY", "Свободных окон нет — уточните на ресепшене.")
        _set_state(db, max_user_id, "SHOP_PICK", {"ids": [str(s.id) for s in svcs]})
        return ("👤 Личный тренер — выберите услугу:\n" +
                "\n".join(f"{i}. {s.name}" for i, s in enumerate(svcs[:20], 1)))
    if t in ("4", "мои записи", "записи"):
        _my_menu_prep(db, max_user_id)
        return _my_bookings(db, row)
    return None


def _my_menu_prep(db: Session, uid: int):
    """Сохранить список id активных броней для «подтвердить N»."""
    row = _find_client_row(db, uid)
    if not row:
        return
    rows = (db.query(ServiceBooking)
            .filter(ServiceBooking.client_id == str(row[0]),
                    ServiceBooking.status.in_(["BOOKED", "CONFIRMED", "PAID"]))
            .order_by(ServiceBooking.booking_date).limit(10).all())
    _set_state(db, uid, "MY_CONFIRM", {"ids": [str(b.id) for b in rows]})