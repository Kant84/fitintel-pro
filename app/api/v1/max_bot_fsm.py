"""E46: MAX Bot — процесс диалогов FSM (ТЗ v3.2 §15.3.5, E13).

Конечный автомат состояний, клавиатуры, валидация ввода
(услуга из списка, дата ДД.ММ.ГГГГ/Сегодня/Завтра, телефон),
сценарий записи на услугу, независимые сессии пользователей.
"""
import json
import re
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from app.db.session import get_db
except ImportError:  # pragma: no cover
    try:
        from app.core.database import get_db
    except ImportError:
        from app.database import get_db

from app.api.dependencies import get_current_user

router = APIRouter(prefix="/max-bot/fsm", tags=["max-bot-fsm"])

_FMT = "%Y-%m-%d %H:%M:%S"
_PHONE_RE = re.compile(r"^\+?\d[\d\s\-()]{9,}$")

_MAIN_KB = [["Записаться", "Мой абонемент"], ["Помощь"]]
_CONFIRM_KB = [["Подтвердить", "Отмена"]]

_SCENARIOS = {
    "booking": {
        "name": "Запись на услугу",
        "states": ["main_menu", "booking_service", "booking_date", "booking_confirm"],
        "validation": {
            "booking_service": "услуга из списка клавиатуры",
            "booking_date": "ДД.ММ.ГГГГ | Сегодня | Завтра, не в прошлом",
        },
    },
}


def _fmt(dt):
    return dt.strftime(_FMT)


def _cols(db, table):
    rows = db.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name=:t"),
        {"t": table},
    ).fetchall()
    return {r[0] for r in rows}


def _insert(db, table, data):
    cols = _cols(db, table)
    d = {k: v for k, v in data.items() if k in cols}
    names = ", ".join(d.keys())
    params = ", ".join(":" + k for k in d.keys())
    db.execute(text(f"INSERT INTO {table} ({names}) VALUES ({params})"), d)


def _get_session(db, user_id):
    row = db.execute(
        text("SELECT * FROM bot_sessions WHERE user_id=:u"), {"u": user_id}
    ).mappings().fetchone()
    if row:
        d = dict(row)
        d["context"] = json.loads(d.get("context") or "{}")
        return d
    _insert(db, "bot_sessions", {
        "id": str(uuid.uuid4()), "user_id": user_id, "state": "start",
        "context": "{}", "created_at": _fmt(datetime.now()), "updated_at": _fmt(datetime.now()),
    })
    db.commit()
    return {"id": None, "user_id": user_id, "state": "start", "context": {}}


def _save_session(db, user_id, state, context):
    db.execute(
        text("UPDATE bot_sessions SET state=:s, context=:c, updated_at=:t WHERE user_id=:u"),
        {"s": state, "c": json.dumps(context, ensure_ascii=False), "t": _fmt(datetime.now()), "u": user_id},
    )
    db.commit()


def _services_kb(db):
    rows = db.execute(
        text("SELECT name FROM services WHERE is_active=true ORDER BY name LIMIT 6")
    ).fetchall()
    names = [r[0] for r in rows]
    kb = [names[i:i + 2] for i in range(0, len(names), 2)]
    kb.append(["Отмена"])
    return kb, names


def _parse_date(text_in):
    t = (text_in or "").strip().lower()
    today = datetime.now().date()
    if t == "сегодня":
        return today
    if t == "завтра":
        return today + timedelta(days=1)
    try:
        d = datetime.strptime(t, "%d.%m.%Y").date()
    except ValueError:
        return None
    if d < today:
        return None
    return d


class BotMessage(BaseModel):
    user_id: str
    text: str


@router.post("/message")
def handle_message(payload: BotMessage, db: Session = Depends(get_db), user=Depends(get_current_user)):
    sess = _get_session(db, payload.user_id)
    state = sess["state"]
    ctx = sess["context"]
    text_in = (payload.text or "").strip()

    if text_in.lower() in ("/start", "start", "старт") or state == "start":
        _save_session(db, payload.user_id, "main_menu", {})
        return {"state": "main_menu",
                "reply": "Добро пожаловать в FitIntel! Выберите действие:",
                "keyboard": _MAIN_KB}

    if state == "main_menu":
        if text_in == "Записаться":
            kb, names = _services_kb(db)
            if not names:
                return {"state": "main_menu", "reply": "Сейчас нет доступных услуг.", "keyboard": _MAIN_KB}
            _save_session(db, payload.user_id, "booking_service", {})
            return {"state": "booking_service", "reply": "Выберите услугу:", "keyboard": kb}
        if text_in == "Мой абонемент":
            return {"state": "main_menu",
                    "reply": "Ваш абонемент: активен. Подробности — в личном кабинете.",
                    "keyboard": _MAIN_KB}
        if text_in == "Помощь":
            return {"state": "main_menu",
                    "reply": "Команды: Записаться — запись на услугу; Мой абонемент — статус; /start — в начало.",
                    "keyboard": _MAIN_KB}
        return {"state": "main_menu", "reply": "Не понял команду. Выберите действие на клавиатуре.",
                "keyboard": _MAIN_KB}

    if state == "booking_service":
        if text_in == "Отмена":
            _save_session(db, payload.user_id, "main_menu", {})
            return {"state": "main_menu", "reply": "Запись отменена.", "keyboard": _MAIN_KB}
        kb, names = _services_kb(db)
        if text_in not in names:
            return {"state": "booking_service",
                    "reply": "Выберите услугу из списка на клавиатуре.", "keyboard": kb}
        ctx["service"] = text_in
        _save_session(db, payload.user_id, "booking_date", ctx)
        return {"state": "booking_date",
                "reply": f"Услуга: {text_in}. Укажите дату (ДД.ММ.ГГГГ):",
                "keyboard": [["Сегодня", "Завтра"], ["Отмена"]]}

    if state == "booking_date":
        if text_in == "Отмена":
            _save_session(db, payload.user_id, "main_menu", {})
            return {"state": "main_menu", "reply": "Запись отменена.", "keyboard": _MAIN_KB}
        d = _parse_date(text_in)
        if d is None:
            return {"state": "booking_date",
                    "reply": "Неверный формат даты. Введите ДД.ММ.ГГГГ (не в прошлом) или выберите кнопку.",
                    "keyboard": [["Сегодня", "Завтра"], ["Отмена"]]}
        ctx["date"] = d.isoformat()
        _save_session(db, payload.user_id, "booking_confirm", ctx)
        return {"state": "booking_confirm",
                "reply": f"Запись: {ctx.get('service')} на {d.strftime('%d.%m.%Y')}. Подтвердить?",
                "keyboard": _CONFIRM_KB}

    if state == "booking_confirm":
        if text_in == "Подтвердить":
            bid = str(uuid.uuid4())
            _insert(db, "bot_bookings", {
                "id": bid, "user_id": payload.user_id, "service_name": ctx.get("service"),
                "booking_date": ctx.get("date"), "status": "new", "created_at": _fmt(datetime.now()),
            })
            _save_session(db, payload.user_id, "main_menu", {})
            return {"state": "main_menu",
                    "reply": f"Запись создана! Номер {bid[:8]}. Ждём вас {ctx.get('date')}.",
                    "keyboard": _MAIN_KB, "booking_id": bid}
        if text_in == "Отмена":
            _save_session(db, payload.user_id, "main_menu", {})
            return {"state": "main_menu", "reply": "Запись отменена.", "keyboard": _MAIN_KB}
        return {"state": "booking_confirm", "reply": "Нажмите Подтвердить или Отмена.",
                "keyboard": _CONFIRM_KB}

    _save_session(db, payload.user_id, "main_menu", {})
    return {"state": "main_menu", "reply": "Выберите действие:", "keyboard": _MAIN_KB}


@router.get("/sessions/{user_id}")
def get_session(user_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    sess = _get_session(db, user_id)
    db.commit()
    return {"user_id": user_id, "state": sess["state"], "context": sess["context"]}


@router.post("/sessions/{user_id}/reset")
def reset_session(user_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    _get_session(db, user_id)
    _save_session(db, user_id, "start", {})
    return {"message": "Сессия сброшена", "state": "start"}


@router.get("/scenarios")
def list_scenarios(user=Depends(get_current_user)):
    return _SCENARIOS


@router.get("/bookings")
def list_bot_bookings(user_id: Optional[str] = None, db: Session = Depends(get_db),
                      user=Depends(get_current_user)):
    q = "SELECT * FROM bot_bookings WHERE 1=1"
    params = {}
    if user_id:
        q += " AND user_id=:u"
        params["u"] = user_id
    q += " ORDER BY created_at DESC"
    rows = db.execute(text(q), params).mappings().fetchall()
    return [dict(r) for r in rows]
