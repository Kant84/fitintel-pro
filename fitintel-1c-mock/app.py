# -*- coding: utf-8 -*-
"""Mock HTTP API 1C:Fitness club (V3) + полная модель данных "Рыжий конь".
Схема по ER-диаграмме 1С:Фитнес клуб: Предприятие/Подразделения/Должности/
Сотрудники/Помещения/Виды занятий/Группы/Абонементы/Клиенты/Расписание.
Auth: Basic base64(UTF-8) + заголовок apikey.
"""
import base64, copy, os, uuid
from datetime import datetime, timedelta
from flask import Flask, jsonify, request

app = Flask(__name__)
app.url_map.strict_slashes = False

API_KEY   = os.environ.get("MOCK_API_KEY", "fitintel-mock-key-2026")
AUTH_USER = os.environ.get("MOCK_USER", "admin")
AUTH_PASS = os.environ.get("MOCK_PASSWORD", "demo123")
APP_VERSION = "2.0.0-full-schema"

CLUB_ID = "11111111-2222-3333-4444-555555555501"
CLUB = {"id": CLUB_ID, "name": 'Фитнес-клуб "Рыжий конь"',
        "address": "г. Москва, ул. Красногвардейская, д. 15",
        "phone": "+7 (495) 123-45-67", "email": "info@redhorse.fit",
        "timezone": "Europe/Moscow"}

def dt(days=0): return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

# =====================================================================
# 1. СПРАВОЧНИКИ (как в 1С) — русские ключи по ER-диаграмме
# =====================================================================

ENTERPRISES = [{
    "КодПредприятия": "ent-001",
    "Наименование": 'ООО "Рыжий конь"',
    "ЮридическийАдрес": "115035, г. Москва, ул. Бахрушина, д. 20, стр. 1",
    "КонтактныйТелефон": "+7 (495) 123-45-67",
    "ЭлектронныйАдрес": "info@redhorse.fit",
}]

DEPARTMENTS = [
    {"КодПодразделения": "dep-001", "НаименованиеПодразделения": "Администрация",
     "КодПредприятия": "ent-001", "Адрес": "г. Москва, ул. Красногвардейская, д. 15, оф. 2",
     "КонтактныйТелефон": "+7 (495) 123-45-67", "ЭлектронныйАдрес": "admin@redhorse.fit"},
    {"КодПодразделения": "dep-002", "НаименованиеПодразделения": "Тренерский состав",
     "КодПредприятия": "ent-001", "Адрес": "г. Москва, ул. Красногвардейская, д. 15, зал 1",
     "КонтактныйТелефон": "+7 (495) 123-45-68", "ЭлектронныйАдрес": "trainers@redhorse.fit"},
    {"КодПодразделения": "dep-003", "НаименованиеПодразделения": "Аква-зона",
     "КодПредприятия": "ent-001", "Адрес": "г. Москва, ул. Красногвардейская, д. 15, бассейн",
     "КонтактныйТелефон": "+7 (495) 123-45-69", "ЭлектронныйАдрес": "aqua@redhorse.fit"},
    {"КодПодразделения": "dep-004", "НаименованиеПодразделения": "Сервис (фитнес-бар)",
     "КодПредприятия": "ent-001", "Адрес": "г. Москва, ул. Красногвардейская, д. 15, бар",
     "КонтактныйТелефон": "+7 (495) 123-45-70", "ЭлектронныйАдрес": "bar@redhorse.fit"},
]

POSITIONS_RU = [
    {"КодДолжности": "pos-001", "НаименованиеДолжности": "Директор клуба"},
    {"КодДолжности": "pos-002", "НаименованиеДолжности": "Администратор"},
    {"КодДолжности": "pos-003", "НаименованиеДолжности": "Старший тренер"},
    {"КодДолжности": "pos-004", "НаименованиеДолжности": "Тренер тренажёрного зала"},
    {"КодДолжности": "pos-005", "НаименованиеДолжности": "Инструктор бассейна"},
    {"КодДолжности": "pos-006", "НаименованиеДолжности": "Бариста"},
]

def passport(series, number, issued, date):
    return f"{series} {number}, выдан {issued}, {date}"

EMPLOYEES_RU = [
    {"КодСотрудника": "e001", "ФИО": "Соколов Игорь Николаевич",
     "ПаспортныеДанные": passport("4510","123456","ТП №3 по г. Москве","15.03.2015"),
     "ДомашнийАдрес": "г. Москва, ул. Ленинская Слобода, д. 19, кв. 44",
     "КонтактныйТелефон": "79150001122", "ЭлектронныйАдрес": "trainer@sokolov.ru",
     "КодДолжности": "pos-003", "КодПодразделения": "dep-002"},
    {"КодСотрудника": "e002", "ФИО": "Орлова Наталья Сергеевна",
     "ПаспортныеДанные": passport("4509","654321","ОВД «Люблино» г. Москвы","22.07.2016"),
     "ДомашнийАдрес": "г. Москва, ул. Верхние Поля, д. 27, кв. 12",
     "КонтактныйТелефон": "79150003344", "ЭлектронныйАдрес": "natalya.orlova@mail.ru",
     "КодДолжности": "pos-004", "КодПодразделения": "dep-002"},
    {"КодСотрудника": "e003", "ФИО": "Волков Артём Дмитриевич",
     "ПаспортныеДанные": passport("4511","234567","ТП №78 по г. Москве","10.01.2014"),
     "ДомашнийАдрес": "г. Москва, пр-т Будённого, д. 51, кв. 208",
     "КонтактныйТелефон": "79150005566", "ЭлектронныйАдрес": "",
     "КодДолжности": "pos-004", "КодПодразделения": "dep-002"},
    {"КодСотрудника": "e004", "ФИО": "Медведева Юлия Андреевна",
     "ПаспортныеДанные": passport("4505","345678","ОВД «Текстильщики» г. Москвы","05.09.2018"),
     "ДомашнийАдрес": "г. Москва, ул. Саратовская, д. 8, кв. 65",
     "КонтактныйТелефон": "79150007788", "ЭлектронныйАдрес": "yulia.medvedeva@gmail.com",
     "КодДолжности": "pos-004", "КодПодразделения": "dep-002"},
    {"КодСотрудника": "e005", "ФИО": "Козлов Павел Сергеевич",
     "ПаспортныеДанные": passport("4513","456789","ТП №15 по г. Москве","18.11.2013"),
     "ДомашнийАдрес": "г. Москва, ул. Перерва, д. 39, кв. 101",
     "КонтактныйТелефон": "79150009900", "ЭлектронныйАдрес": "",
     "КодДолжности": "pos-004", "КодПодразделения": "dep-002"},
    {"КодСотрудника": "e006", "ФИО": "Тарасова Екатерина Игоревна",
     "ПаспортныеДанные": passport("4508","567890","ОВД «Кузьминки» г. Москвы","27.04.2017"),
     "ДомашнийАдрес": "г. Москва, ул. Юных Ленинцев, д. 61, кв. 9",
     "КонтактныйТелефон": "79150012233", "ЭлектронныйАдрес": "kate.tarasova@yandex.ru",
     "КодДолжности": "pos-005", "КодПодразделения": "dep-003"},
    {"КодСотрудника": "e007", "ФИО": "Жукова Ольга Петровна",
     "ПаспортныеДанные": passport("4502","678901","ТП №1 по г. Москве","03.02.2010"),
     "ДомашнийАдрес": "г. Москва, ул. Таганская, д. 44, кв. 3",
     "КонтактныйТелефон": "79150014455", "ЭлектронныйАдрес": "o.zhukova@redhorse.fit",
     "КодДолжности": "pos-001", "КодПодразделения": "dep-001"},
    {"КодСотрудника": "e008", "ФИО": "Смирнов Артём Викторович",
     "ПаспортныеДанные": passport("4512","789012","ТП №42 по г. Москве","14.06.2019"),
     "ДомашнийАдрес": "г. Москва, ул. Шарикоподшипниковская, д. 22, кв. 55",
     "КонтактныйТелефон": "79150016677", "ЭлектронныйАдрес": "",
     "КодДолжности": "pos-002", "КодПодразделения": "dep-001"},
    {"КодСотрудника": "e009", "ФИО": "Белов Дмитрий Станиславович",
     "ПаспортныеДанные": passport("4507","890123","ОВД «Печатники» г. Москвы","30.08.2020"),
     "ДомашнийАдрес": "г. Москва, ул. Гурьянова, д. 33, кв. 140",
     "КонтактныйТелефон": "79150018899", "ЭлектронныйАдрес": "d.belov@redhorse.fit",
     "КодДолжности": "pos-002", "КодПодразделения": "dep-001"},
    {"КодСотрудника": "e010", "ФИО": "Гусев Максим Олегович",
     "ПаспортныеДанные": passport("4514","901234","ТП №9 по г. Москве","11.12.2021"),
     "ДомашнийАдрес": "г. Москва, ул. 1-я Дубровская, д. 16, кв. 27",
     "КонтактныйТелефон": "79150020011", "ЭлектронныйАдрес": "",
     "КодДолжности": "pos-006", "КодПодразделения": "dep-004"},
]

ROOMS_RU = [
    {"КодПомещения": "room-001", "НаименованиеПомещения": "Тренажёрный зал"},
    {"КодПомещения": "room-002", "НаименованиеПомещения": "Зал групповых программ"},
    {"КодПомещения": "room-003", "НаименованиеПомещения": "Бассейн (25 м)"},
    {"КодПомещения": "room-004", "НаименованиеПомещения": "Сауна"},
    {"КодПомещения": "room-005", "НаименованиеПомещения": "Фитнес-бар"},
    {"КодПомещения": "room-006", "НаименованиеПомещения": "Раздевалка и душевые"},
]

WORKOUT_TYPES = [
    {"КодВидаЗанятий": "wt-001", "НаименованиеВидаЗанятий": "Силовая тренировка"},
    {"КодВидаЗанятий": "wt-002", "НаименованиеВидаЗанятий": "Йога"},
    {"КодВидаЗанятий": "wt-003", "НаименованиеВидаЗанятий": "Плавание"},
    {"КодВидаЗанятий": "wt-004", "НаименованиеВидаЗанятий": "Аква-аэробика"},
    {"КодВидаЗанятий": "wt-005", "НаименованиеВидаЗанятий": "Степ-аэробика"},
    {"КодВидаЗанятий": "wt-006", "НаименованиеВидаЗанятий": "Персональная тренировка"},
    {"КодВидаЗанятий": "wt-007", "НаименованиеВидаЗанятий": "Детская аква-гимнастика"},
]

GROUPS = [
    {"КодГруппы": "grp-001", "НаименованиеГруппы": "Утренняя группа"},
    {"КодГруппы": "grp-002", "НаименованиеГруппы": "Вечерняя группа"},
    {"КодГруппы": "grp-003", "НаименованиеГруппы": "Детская группа"},
    {"КодГруппы": "grp-004", "НаименованиеГруппы": "VIP-группа"},
]

MEMBERSHIP_TYPES = [
    {"КодАбонемента": "mt-001", "НаименованиеАбонемента": "Годовой безлимит", "Цена": 45000,
     "ДлительностьДней": 365, "КоличествоПосещений": 0},
    {"КодАбонемента": "mt-002", "НаименованиеАбонемента": "Полугодовой дневной", "Цена": 26000,
     "ДлительностьДней": 180, "КоличествоПосещений": 0},
    {"КодАбонемента": "mt-003", "НаименованиеАбонемента": "Квартальный", "Цена": 15000,
     "ДлительностьДней": 90, "КоличествоПосещений": 0},
    {"КодАбонемента": "mt-004", "НаименованиеАбонемента": "Месячный утренний", "Цена": 6000,
     "ДлительностьДней": 30, "КоличествоПосещений": 0},
    {"КодАбонемента": "mt-005", "НаименованиеАбонемента": "10 занятий (разовый пакет)", "Цена": 8000,
     "ДлительностьДней": 120, "КоличествоПосещений": 10},
    {"КодАбонемента": "mt-006", "НаименованиеАбонемента": "Детский (бассейн)", "Цена": 4000,
     "ДлительностьДней": 30, "КоличествоПосещений": 8},
]

# =====================================================================
# 2. КЛИЕНТЫ (полные карточки, как в 1С) + членства
# =====================================================================
CUSTOMERS = [
 {"id":"c0000001-0000-4000-8000-000000000001","name":"Иванова Мария Сергеевна","phone":"79161234567","email":"maria.ivanova@mail.ru","birthday":"1990-04-12","sex":"female","note":"VIP-клиент, предпочитает утренние тренировки","updated_at":dt(-1),
  "group_id":"grp-004","membership_code":"mt-001","passport":passport("4515","111222","ТП №5 по г. Москве","20.05.2012"),"home_address":"г. Москва, ул. Мясницкая, д. 13, кв. 21"},
 {"id":"c0000001-0000-4000-8000-000000000002","name":"Петров Павел Андреевич","phone":"79269876543","email":"pavel.petrov@gmail.com","birthday":"1985-09-03","sex":"male","note":"","updated_at":dt(-3),
  "group_id":"grp-001","membership_code":"mt-002","passport":passport("4510","222333","ОВД «Басманный» г. Москвы","12.08.2014"),"home_address":"г. Москва, ул. Старая Басманная, д. 20, кв. 5"},
 {"id":"c0000001-0000-4000-8000-000000000003","name":"Сидорова Анна Викторовна","phone":"79031112233","email":"","birthday":"1998-01-27","sex":"female","note":"Заморозка по мед. показаниям","updated_at":dt(0),
  "group_id":"grp-001","membership_code":"mt-004","passport":passport("4504","333444","ТП №31 по г. Москве","25.02.2019"),"home_address":"г. Москва, ул. Бауманская, д. 5, кв. 77"},
 {"id":"c0000001-0000-4000-8000-000000000004","name":"Кузнецов Дмитрий Олегович","phone":"79165554433","email":"dkuznecov@yandex.ru","birthday":"1979-07-15","sex":"male","note":"","updated_at":dt(-10),
  "group_id":"grp-002","membership_code":"mt-003","passport":passport("4501","444555","ОВД «Таганский» г. Москвы","08.10.2005"),"home_address":"г. Москва, наб. Марка Шагала, д. 3, кв. 118"},
 {"id":"c0000001-0000-4000-8000-000000000005","name":"Смирнова Елена Павловна","phone":"79263332211","email":"elena.s@gmail.com","birthday":"1993-12-05","sex":"female","note":"","updated_at":dt(-2),
  "group_id":"grp-002","membership_code":"mt-005","passport":passport("4506","555666","ТП №12 по г. Москве","17.03.2017"),"home_address":"г. Москва, ул. Земляной Вал, д. 27, кв. 41"},
 {"id":"c0000001-0000-4000-8000-000000000006","name":"Морозова София Дмитриевна","phone":"79167778899","email":"","birthday":"2015-06-20","sex":"female","note":"Детская группа, сопровождение родителя","updated_at":dt(-1),
  "group_id":"grp-003","membership_code":"mt-006","passport":"Свидетельство о рождении IV-МЮ 456789, ЗАГС «Люблино», 10.07.2015","home_address":"г. Москва, ул. Летняя, д. 14, кв. 30"},
 {"id":"c0000001-0000-4000-8000-000000000007","name":"Новиков Андрей Сергеевич","phone":"79039998877","email":"a.novikov@outlook.com","birthday":"1975-11-11","sex":"male","note":"Корпоративный клиент (ООО «ТрансЛогистик»)","updated_at":dt(-4),
  "group_id":"grp-004","membership_code":"mt-001","passport":passport("4500","666777","ТП №2 по г. Москве","19.01.2000"),"home_address":"г. Москва, Кутузовский пр-т, д. 26, кв. 150"},
 {"id":"c0000001-0000-4000-8000-000000000008","name":"Фёдорова Дарья Константиновна","phone":"79160001122","email":"daria.fedorova@mail.ru","birthday":"2001-02-14","sex":"female","note":"","updated_at":dt(0),
  "group_id":"grp-002","membership_code":"mt-003","passport":passport("4520","777888","ТП №66 по г. Москве","23.06.2022"),"home_address":"г. Москва, ул. Авиамоторная, д. 50, кв. 66"},
]

def _m(mid, mtype, active, start, end, freezes=None, remaining=None, total=None):
    mt = next(x for x in MEMBERSHIP_TYPES if x["КодАбонемента"] == mtype)
    rec = {"id": mid, "membership_type": mtype, "name": mt["НаименованиеАбонемента"],
           "price": mt["Цена"], "is_active": active, "date_start": start, "date_end": end,
           "freezes": freezes or []}
    if remaining is not None:
        rec["remaining"] = remaining
        rec["total"] = total if total is not None else mt["КоличествоПосещений"]
    return rec

MEMBERSHIPS = {
 "c0000001-0000-4000-8000-000000000001": [_m("m0000001-0000-4000-8000-000000000001","mt-001",True,dt(-300),dt(65))],
 "c0000001-0000-4000-8000-000000000002": [_m("m0000001-0000-4000-8000-000000000002","mt-002",True,dt(-150),dt(215))],
 "c0000001-0000-4000-8000-000000000003": [_m("m0000001-0000-4000-8000-000000000003","mt-004",True,dt(-40),dt(50),freezes=[{"date_start":dt(0),"date_end":dt(16),"days":16}])],
 "c0000001-0000-4000-8000-000000000004": [_m("m0000001-0000-4000-8000-000000000004","mt-003",False,dt(-200),dt(-110))],
 "c0000001-0000-4000-8000-000000000005": [_m("m0000001-0000-4000-8000-000000000005","mt-005",True,dt(-60),dt(305),remaining=6,total=10)],
 "c0000001-0000-4000-8000-000000000006": [_m("m0000001-0000-4000-8000-000000000006","mt-006",True,dt(-10),dt(80),remaining=6,total=8)],
 "c0000001-0000-4000-8000-000000000007": [_m("m0000001-0000-4000-8000-000000000007","mt-001",True,dt(-30),dt(335))],
 "c0000001-0000-4000-8000-000000000008": [_m("m0000001-0000-4000-8000-000000000008","mt-003",True,dt(-20),dt(160))],
}

# =====================================================================
# 3. РАСПИСАНИЕ ЗАНЯТИЙ (2 недели, групповые + персональные)
# =====================================================================
_WEEKDAY = [
    ("07:00","08:00","wt-002","e002","room-002"),
    ("08:00","09:30","wt-006","e001","room-001"),
    ("10:00","11:00","wt-003","e006","room-003"),
    ("12:00","13:00","wt-004","e006","room-003"),
    ("17:00","18:00","wt-001","e001","room-001"),
    ("18:00","19:00","wt-005","e003","room-002"),
    ("19:00","20:00","wt-002","e003","room-002"),
    ("20:00","21:00","wt-001","e004","room-001"),
]
_WEEKEND = [
    ("10:00","11:00","wt-003","e006","room-003"),
    ("11:00","12:00","wt-004","e006","room-003"),
    ("12:00","13:00","wt-001","e004","room-001"),
    ("13:00","14:00","wt-002","e005","room-002"),
    ("15:00","16:00","wt-007","e006","room-003"),
]
_PERSONAL = [(1,"09:00","10:30","e001","c0000001-0000-4000-8000-000000000001"),
             (3,"14:00","15:30","e001","c0000001-0000-4000-8000-000000000007"),
             (6,"11:00","12:30","e004","c0000001-0000-4000-8000-000000000008")]

SCHEDULE = []
_sid = 1
for _day in range(14):
    _d = dt(_day)
    _wd = (datetime.now() + timedelta(days=_day)).weekday()
    for _t1, _t2, _wt, _emp, _room in (_WEEKDAY if _wd < 5 else _WEEKEND):
        SCHEDULE.append({"id": f"sch-{_sid:04d}", "date": _d, "time_start": _t1, "time_end": _t2,
                         "workout_type_id": _wt, "employee_id": _emp, "room_id": _room,
                         "client_id": None, "club_id": CLUB_ID,
                         "capacity": 12, "occupied": 3 + (_sid % 10)})
        _sid += 1
for _day, _t1, _t2, _emp, _cid in _PERSONAL:
    SCHEDULE.append({"id": f"sch-{_sid:04d}", "date": dt(_day), "time_start": _t1, "time_end": _t2,
                     "workout_type_id": "wt-006", "employee_id": _emp, "room_id": "room-001",
                     "client_id": _cid, "club_id": CLUB_ID,
                     "capacity": 1, "occupied": 1})
    _sid += 1

def _ru_name(code):
    for coll, key in ((EMPLOYEES_RU,"КодСотрудника"), (WORKOUT_TYPES,"КодВидаЗанятий"),
                      (ROOMS_RU,"КодПомещения"), (CUSTOMERS,"id")):
        for r in coll:
            if r.get(key) == code:
                return r.get("ФИО") or r.get("НаименованиеВидаЗанятий") or r.get("НаименованиеПомещения") or r.get("name")
    return None

SCHEDULE_RU = [{
    "КодРасписания": s["id"],
    "КодВидаЗанятия": s["workout_type_id"],
    "НаименованиеВидаЗанятий": _ru_name(s["workout_type_id"]),
    "КодСотрудника": s["employee_id"],
    "ФИОСотрудника": _ru_name(s["employee_id"]),
    "КодПомещения": s["room_id"],
    "НаименованиеПомещения": _ru_name(s["room_id"]),
    "ДатаПроведенияЗанятия": s["date"],
    "ВремяНачала": s["time_start"],
    "ВремяОкончания": s["time_end"],
    "КодКлиента": s["client_id"],
    "ФИОКлиента": _ru_name(s["client_id"]) if s["client_id"] else None,
    "ЗанятоМест": s["occupied"], "ВсегоМест": s["capacity"],
} for s in SCHEDULE]

CUSTOMERS_RU = [{
    "КодКлиента": c["id"], "ФИО": c["name"],
    "КодАбонемента": c.get("membership_code"),
    "НаименованиеАбонемента": next((x["НаименованиеАбонемента"] for x in MEMBERSHIP_TYPES if x["КодАбонемента"]==c.get("membership_code")), None),
    "КодГруппы": c.get("group_id"),
    "НаименованиеГруппы": next((g["НаименованиеГруппы"] for g in GROUPS if g["КодГруппы"]==c.get("group_id")), None),
    "ПаспортныеДанные": c.get("passport"), "ДомашнийАдрес": c.get("home_address"),
    "КонтактныйТелефон": c.get("phone"), "ЭлектронныйАдрес": c.get("email"),
    "ДатаРождения": c.get("birthday"), "Пол": c.get("sex"), "Примечание": c.get("note"),
} for c in CUSTOMERS]

# ---------- прочее (СКУД/шкафчики/визиты) ----------
CABINETS = [{"id":f"cab-{i:03d}","number":str(i),"state":"free","club_id":CLUB_ID} for i in range(1,61)]
CLUB_CABINETS = []
STATES = [{"id":1,"name":"В клубе"},{"id":2,"name":"Не в клубе"},{"id":3,"name":"Заморожено"},{"id":4,"name":"Членство истекло"}]
VISIT_TYPES = [{"id":1,"name":"Тренировка"},{"id":2,"name":"Гостевой визит"},{"id":3,"name":"Заморозка"}]
VISITS = []
PERSON_STATE = {}

def ok(data): return jsonify({"result": True, "data": data})
def fail(code, msg): return jsonify({"result": False, "error": code, "error_message": msg})

def check_auth():
    key = request.headers.get("apikey", "")
    if not key:
        return fail(1062, "Не указан ключ авторизации внешнего приложения")
    if key != API_KEY:
        return fail(1063, "Неверный ключ авторизации внешнего приложения")
    auth = request.headers.get("Authorization", "")
    expected = "Basic " + base64.b64encode(f"{AUTH_USER}:{AUTH_PASS}".encode("utf-8")).decode()
    if auth != expected:
        return fail(401, "Ошибка аутентификации пользователя 1С")
    return None

@app.before_request
def gate():
    if request.path in ("/health",) or request.path.startswith("/static"):
        return None
    if request.path.startswith("/hs/api/v3"):
        return check_auth()

# ---------- сервис ----------
@app.get("/health")
def health(): return {"status":"ok","service":"fitintel-1c-mock","version":APP_VERSION,
                      "schema":{"clients":len(CUSTOMERS),"employees":len(EMPLOYEES_RU),
                                "schedule":len(SCHEDULE_RU),"membership_types":len(MEMBERSHIP_TYPES)}}

@app.get("/hs/api/v3/auth_types")
def auth_types(): return ok({"auth_types":[{"id":1,"name":"1С:Предприятие"}]})

@app.get("/hs/api/v3/clubs/")
def clubs(): return ok([CLUB])

@app.get("/hs/api/v3/states/")
def states(): return ok(STATES)

@app.get("/hs/api/v3/visit_types/")
def visit_types(): return ok(VISIT_TYPES)

# ---------- V3: клиенты (обратная совместимость с десктопом) ----------
@app.get("/hs/api/v3/customers/")
def customers_list():
    items = copy.deepcopy(CUSTOMERS)
    changed_after = request.args.get("changed_after")
    if changed_after:
        items = [c for c in items if c["updated_at"] >= changed_after[:10]]
    return ok(items)

@app.post("/hs/api/v3/customers/")
def customers_create():
    d = request.get_json(silent=True) or {}
    if not d.get("name") or not d.get("phone"):
        return fail(422, "Обязательные поля: name, phone")
    phone = str(d.get("phone", "")).strip()
    existing = next((x for x in CUSTOMERS if str(x.get("phone", "")).strip() == phone), None)
    if existing:
        for f in ("name", "email", "birthday", "sex", "note",
                  "group_id", "membership_code", "passport", "home_address"):
            if d.get(f):
                existing[f] = d[f]
        existing["updated_at"] = dt(0)
        return ok(existing)
    new = dict(d)
    new.setdefault("id", str(uuid.uuid4()))
    new.setdefault("email",""); new.setdefault("birthday",""); new.setdefault("sex","")
    new.setdefault("note",""); new.setdefault("updated_at", dt(0))
    new.setdefault("group_id","grp-002"); new.setdefault("membership_code","mt-005")
    new.setdefault("passport",""); new.setdefault("home_address","")
    CUSTOMERS.append(new)
    return ok(new)

@app.get("/hs/api/v3/customers/<cid>/")
def customer_get(cid):
    c = next((x for x in CUSTOMERS if x["id"] == cid), None)
    return ok(c) if c else fail(404, "Клиент не найден")

@app.patch("/hs/api/v3/customers/<cid>/")
def customer_patch(cid):
    c = next((x for x in CUSTOMERS if x["id"] == cid), None)
    if not c: return fail(404, "Клиент не найден")
    d = request.get_json(silent=True) or {}
    for f in ("name","phone","email","birthday","sex","note","group_id","membership_code","passport","home_address"):
        if f in d: c[f] = d[f]
    c["updated_at"] = dt(0)
    return ok(c)

@app.get("/hs/api/v3/customers/<cid>/photo/")
def customer_photo(cid):
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
    return app.response_class(png, mimetype="image/png")

@app.get("/hs/api/v3/customers/<cid>/memberships/")
def customer_memberships(cid):
    return ok(copy.deepcopy(MEMBERSHIPS.get(cid, [])))

# ---------- V3: сотрудники/расписание (латинские ключи, как раньше) ----------
@app.get("/hs/api/v3/employees/")
def employees():
    return ok([{
        "id": e["КодСотрудника"], "name": e["ФИО"], "phone": e["КонтактныйТелефон"],
        "email": e["ЭлектронныйАдрес"], "position_id": e["КодДолжности"],
        "department_id": e["КодПодразделения"], "passport": e["ПаспортныеДанные"],
        "home_address": e["ДомашнийАдрес"], "is_active": True,
    } for e in EMPLOYEES_RU])

@app.get("/hs/api/v3/employee_positions/")
def employee_positions():
    return ok([{"id": p["КодДолжности"], "name": p["НаименованиеДолжности"]} for p in POSITIONS_RU])

@app.get("/hs/api/v3/departments/")
def departments():
    return ok([{"id": d["КодПодразделения"], "name": d["НаименованиеПодразделения"],
                "enterprise_id": d["КодПредприятия"], "phone": d["КонтактныйТелефон"],
                "email": d["ЭлектронныйАдрес"]} for d in DEPARTMENTS])

@app.get("/hs/api/v3/rooms/")
def rooms():
    return ok([{"id": r["КодПомещения"], "name": r["НаименованиеПомещения"]} for r in ROOMS_RU])

@app.get("/hs/api/v3/training_directions/")
def directions():
    return ok([{"id": w["КодВидаЗанятий"], "name": w["НаименованиеВидаЗанятий"]} for w in WORKOUT_TYPES])

@app.get("/hs/api/v3/schedules/")
def schedules():
    d = request.args.get("date")
    items = SCHEDULE if not d else [s for s in SCHEDULE if s["date"] == d]
    return ok(copy.deepcopy(items))

# ---------- REFERENCE: полная модель 1С (русские ключи) ----------
REFERENCE = {
    "enterprises": ENTERPRISES, "departments": DEPARTMENTS, "positions": POSITIONS_RU,
    "employees": EMPLOYEES_RU, "rooms": ROOMS_RU, "workout_types": WORKOUT_TYPES,
    "groups": GROUPS, "membership_types": MEMBERSHIP_TYPES,
    "clients": CUSTOMERS_RU, "schedule": SCHEDULE_RU,
}

@app.get("/hs/api/v3/reference/<name>")
def reference(name):
    if name not in REFERENCE:
        return fail(404, f"Справочник '{name}' не найден. Доступны: {', '.join(REFERENCE)}")
    return ok(copy.deepcopy(REFERENCE[name]))

@app.get("/hs/api/v3/stats/summary")
def stats_summary():
    return ok({
        "version": APP_VERSION,
        "clients": len(CUSTOMERS_RU), "employees": len(EMPLOYEES_RU),
        "departments": len(DEPARTMENTS), "positions": len(POSITIONS_RU),
        "rooms": len(ROOMS_RU), "workout_types": len(WORKOUT_TYPES),
        "groups": len(GROUPS), "membership_types": len(MEMBERSHIP_TYPES),
        "schedule_rows": len(SCHEDULE_RU),
        "cabinets": len(CABINETS), "assignments": len(CLUB_CABINETS),
        "visits": len(VISITS),
    })

# ---------- шкафчики ----------
@app.get("/hs/api/v3/cabinets/")
def cabinets(): return ok(copy.deepcopy(CABINETS))

@app.get("/hs/api/v3/club_cabinets/")
def club_cabinets_list(): return ok(copy.deepcopy(CLUB_CABINETS))

@app.post("/hs/api/v3/customers/<cid>/club_cabinets/")
def club_cabinets_assign(cid):
    d = request.get_json(silent=True) or {}
    cab = next((x for x in CABINETS if x["id"] == d.get("cabinet_id")), None)
    if not cab: return fail(404, "Шкафчик не найден")
    if cab["state"] != "free": return fail(409, "Шкафчик занят")
    if any(x["customer_id"] == cid for x in CLUB_CABINETS): return fail(409, "У клиента уже есть шкафчик")
    rec = {"id": str(uuid.uuid4()), "customer_id": cid, "cabinet_id": cab["id"], "date": dt(0), "club_id": CLUB_ID}
    CLUB_CABINETS.append(rec); cab["state"] = "occupied"
    return ok(rec)

@app.delete("/hs/api/v3/club_cabinets/<rid>/")
def club_cabinets_release(rid):
    rec = next((x for x in CLUB_CABINETS if x["id"] == rid), None)
    if not rec: return fail(404, "Назначение не найдено")
    cab = next((x for x in CABINETS if x["id"] == rec["cabinet_id"]), None)
    if cab: cab["state"] = "free"
    CLUB_CABINETS.remove(rec)
    return ok({"released": rid})

# ---------- визиты (turnstile) ----------
@app.get("/hs/api/v3/visits/")
def visits_list():
    d = request.args.get("date")
    items = VISITS if not d else [v for v in VISITS if v["date"] == d]
    return ok(copy.deepcopy(items))

@app.get("/hs/api/v3/persons/<pid>/state/")
def person_state_get(pid):
    st = PERSON_STATE.get(pid)
    return ok(st) if st else ok(None)

@app.post("/hs/api/v3/persons/<pid>/state/")
def person_state_set(pid):
    d = request.get_json(silent=True) or {}
    sid_ = d.get("state_id")
    st = next((s for s in STATES if s["id"] == sid_), None)
    if not st: return fail(422, "Неизвестное состояние")
    PERSON_STATE[pid] = {"state_id": sid_, "state_name": st["name"], "changed_at": datetime.now().isoformat()}
    VISITS.append({"id": str(uuid.uuid4()), "person_id": pid, "state_id": sid_, "state_name": st["name"],
                   "date": dt(0), "time": datetime.now().strftime("%H:%M"), "club_id": CLUB_ID})
    return ok(PERSON_STATE[pid])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)