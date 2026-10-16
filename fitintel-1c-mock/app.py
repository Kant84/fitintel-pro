# -*- coding: utf-8 -*-
"""Mock HTTP API 1C:Fitness club (V3) for FitIntel Pro dev/testing.
Auth: Basic (UTF-8) + 'apikey' header. Spec: Helix-QA/API api_fitness1cv3.yaml.
"""
import base64, copy, os, uuid
from datetime import datetime, timedelta
from flask import Flask, jsonify, request

app = Flask(__name__)
app.url_map.strict_slashes = False

API_KEY   = os.environ.get("MOCK_API_KEY", "fitintel-mock-key-2026")
AUTH_USER = os.environ.get("MOCK_USER", "СанакинАВ")
AUTH_PASS = os.environ.get("MOCK_PASSWORD", "demo123")

CLUB_ID = "11111111-2222-3333-4444-555555555501"
CLUB = {"id": CLUB_ID, "name": 'Фитнес-клуб "Рыжий конь"',
        "address": "г. Москва, ул. Красногвардейская, д. 15",
        "phone": "+7 (495) 123-45-67", "email": "info@redhorse.fit",
        "timezone": "Europe/Moscow"}

def dt(days=0): return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

CUSTOMERS = [
 {"id":"c0000001-0000-4000-8000-000000000001","name":"Иванова Мария Сергеевна","phone":"79161234567","email":"maria.ivanova@mail.ru","birthday":"1990-04-12","sex":"female","note":"VIP-клиент, предпочитает утренние тренировки","updated_at":dt(-1)},
 {"id":"c0000001-0000-4000-8000-000000000002","name":"Петров Павел Андреевич","phone":"79269876543","email":"pavel.petrov@gmail.com","birthday":"1985-09-03","sex":"male","note":"","updated_at":dt(-3)},
 {"id":"c0000001-0000-4000-8000-000000000003","name":"Сидорова Анна Викторовна","phone":"79031112233","email":"","birthday":"1998-01-27","sex":"female","note":"Заморозка по мед. показаниям","updated_at":dt(0)},
 {"id":"c0000001-0000-4000-8000-000000000004","name":"Кузнецов Дмитрий Олегович","phone":"79165554433","email":"dkuznecov@yandex.ru","birthday":"1979-07-15","sex":"male","note":"","updated_at":dt(-10)},
 {"id":"c0000001-0000-4000-8000-000000000005","name":"Смирнова Елена Павловна","phone":"79263332211","email":"elena.s@gmail.com","birthday":"1993-12-05","sex":"female","note":"","updated_at":dt(-2)},
]

MEMBERSHIPS = {
 "c0000001-0000-4000-8000-000000000001":[{"id":"m0000001-0000-4000-8000-000000000001","name":"Годовой безлимит","is_active":True,"date_start":dt(-300),"date_end":dt(65),"freezes":[]}],
 "c0000001-0000-4000-8000-000000000002":[{"id":"m0000001-0000-4000-8000-000000000002","name":"Утренний 12 мес.","is_active":True,"date_start":dt(-150),"date_end":dt(215),"freezes":[]}],
 "c0000001-0000-4000-8000-000000000003":[{"id":"m0000001-0000-4000-8000-000000000003","name":"Месячный разовый","is_active":True,"date_start":dt(-40),"date_end":dt(50),"freezes":[{"date_start":dt(0),"date_end":dt(16),"days":16}]}],
 "c0000001-0000-4000-8000-000000000004":[{"id":"m0000001-0000-4000-8000-000000000004","name":"Квартальный","is_active":False,"date_start":dt(-200),"date_end":dt(-110),"freezes":[]}],
 "c0000001-0000-4000-8000-000000000005":[{"id":"m0000001-0000-4000-8000-000000000005","name":"10 занятий (разовые)","is_active":True,"date_start":dt(-60),"date_end":dt(305),"freezes":[],"remaining":6,"total":10}],
}

CABINETS = [{"id":f"cab-{i:03d}","number":str(i),"state":"free","club_id":CLUB_ID} for i in range(1,61)]
CLUB_CABINETS = []
EMPLOYEES = [
 {"id":"e0000001-0000-4000-8000-000000000001","name":"Соколов Игорь Николаевич","phone":"79150001122","email":"trainer@sokolov.ru","position_id":"pos-001","is_active":True},
 {"id":"e0000001-0000-4000-8000-000000000002","name":"Орлова Наталья Сергеевна","phone":"79150003344","email":"","position_id":"pos-002","is_active":True},
 {"id":"e0000001-0000-4000-8000-000000000003","name":"Волков Артём Дмитриевич","phone":"79150005566","email":"","position_id":"pos-001","is_active":True},
]
POSITIONS = [{"id":"pos-001","name":"Тренер тренажёрного зала"},{"id":"pos-002","name":"Инструктор групповых программ"}]
ROOMS = [{"id":"room-001","name":"Тренажёрный зал"},{"id":"room-002","name":"Зал групповых программ"},{"id":"room-003","name":"Бассейн"}]
DIRECTIONS = [{"id":"dir-001","name":"Силовая тренировка"},{"id":"dir-002","name":"Йога"},{"id":"dir-003","name":"Плавание"}]
SECTIONS = [{"id":"sec-001","name":"Силовой тренинг","direction_id":"dir-001","room_id":"room-001","employee_id":"e0000001-0000-4000-8000-000000000001"},
            {"id":"sec-002","name":"Йога утренняя","direction_id":"dir-002","room_id":"room-002","employee_id":"e0000001-0000-4000-8000-000000000002"},
            {"id":"sec-003","name":"Аква-аэробика","direction_id":"dir-003","room_id":"room-003","employee_id":"e0000001-0000-4000-8000-000000000003"}]
SCHEDULES = [{"id":f"sch-{i:03d}","section_id":f"sec-00{(i%3)+1}","date":dt(i),"time_start":f"{8+(i%10):02d}:00","time_end":f"{9+(i%10):02d}:00","capacity":12,"occupied":5+(i%6)} for i in range(1,15)]
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
    if request.path in ("/health",):
        return None
    if request.path.startswith("/hs/api/v3"):
        return check_auth()

@app.get("/health")
def health(): return {"status": "ok", "service": "fitintel-1c-mock"}

@app.get("/hs/api/v3/auth_types")
def auth_types(): return ok({"auth_types":[{"id":1,"name":"1С:Предприятие"}]})

@app.get("/hs/api/v3/clubs/")
def clubs(): return ok([CLUB])

@app.get("/hs/api/v3/states/")
def states(): return ok(STATES)

@app.get("/hs/api/v3/visit_types/")
def visit_types(): return ok(VISIT_TYPES)

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
    new = {"id": str(uuid.uuid4()), "name": d["name"], "phone": d["phone"],
           "email": d.get("email",""), "birthday": d.get("birthday",""),
           "sex": d.get("sex",""), "note": d.get("note",""), "updated_at": dt(0)}
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
    for f in ("name","phone","email","birthday","sex","note"):
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

@app.get("/hs/api/v3/customers/<cid>/club_cabinets/")
def customer_cabinets(cid):
    return ok([x for x in CLUB_CABINETS if x["customer_id"] == cid])

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

@app.get("/hs/api/v3/employees/")
def employees(): return ok(copy.deepcopy(EMPLOYEES))

@app.get("/hs/api/v3/employee_positions/")
def positions(): return ok(POSITIONS)

@app.get("/hs/api/v3/rooms/")
def rooms(): return ok(ROOMS)

@app.get("/hs/api/v3/training_directions/")
def directions(): return ok(DIRECTIONS)

@app.get("/hs/api/v3/sections/")
def sections(): return ok(copy.deepcopy(SECTIONS))

@app.get("/hs/api/v3/schedules/")
def schedules():
    d = request.args.get("date")
    items = SCHEDULES if not d else [s for s in SCHEDULES if s["date"] == d]
    return ok(copy.deepcopy(items))

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
    sid = d.get("state_id")
    st = next((s for s in STATES if s["id"] == sid), None)
    if not st: return fail(422, "Неизвестное состояние")
    PERSON_STATE[pid] = {"state_id": sid, "state_name": st["name"], "changed_at": datetime.now().isoformat()}
    VISITS.append({"id": str(uuid.uuid4()), "person_id": pid, "state_id": sid, "state_name": st["name"],
                   "date": dt(0), "time": datetime.now().strftime("%H:%M"), "club_id": CLUB_ID})
    return ok(PERSON_STATE[pid])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)