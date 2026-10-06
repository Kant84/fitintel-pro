# scripts/seed_demo.py
"""Сидер демо-данных: 50 взрослых клиентов + 10 детей + 18 сотрудников с ролями.

Запуск на сервере:
  docker cp scripts/seed_demo.py deploy-api-1:/app/scripts/seed_demo.py
  docker exec -w /app deploy-api-1 python scripts/seed_demo.py

Идемпотентен: пропускает дубли по email/телефону. Пароль всех: demo12345.
"""
import random
import uuid
from datetime import date, timedelta

from app.db.session import SessionLocal
from app.core.security import pwd_context
from sqlalchemy import text

SURNAMES = ["Иванов", "Петров", "Сидоров", "Смирнов", "Кузнецов", "Попов",
            "Васильев", "Соколов", "Михайлов", "Новиков", "Фёдоров",
            "Морозов", "Волков", "Алексеев", "Лебедев", "Семёнов",
            "Егоров", "Павлов", "Козлов", "Степанов", "Николаев", "Орлов"]
NAMES_M = ["Александр", "Дмитрий", "Максим", "Сергей", "Андрей", "Алексей",
           "Артём", "Илья", "Кирилл", "Михаил", "Никита", "Павел",
           "Роман", "Руслан", "Тимур", "Эдуард", "Юрий", "Ярослав"]
NAMES_F = ["Анна", "Мария", "Елена", "Ольга", "Наталья", "Ирина",
           "Екатерина", "Анастасия", "Татьяна", "Светлана", "Дарья",
           "Ксения", "Виктория", "Полина", "Марина", "Оксана", "Юлия", "Алина"]
PATR_M = ["Александрович", "Дмитриевич", "Сергеевич", "Андреевич",
          "Алексеевич", "Михайлович", "Николаевич", "Павлович", "Юрьевич"]
PATR_F = ["Александровна", "Дмитриевна", "Сергеевна", "Андреевна",
          "Алексеевна", "Михайловна", "Николаевна", "Павловна", "Юрьевна"]


def fio(gender):
    if gender == "m":
        return random.choice(NAMES_M), random.choice(SURNAMES), random.choice(PATR_M)
    return random.choice(NAMES_F), random.choice(SURNAMES), random.choice(PATR_F)


def phone():
    return "+7(999)%03d-%02d-%02d" % (random.randint(0, 999),
                                     random.randint(0, 99), random.randint(0, 99))


def email(local):
    return "%s%s@mail.ru" % (local, uuid.uuid4().hex[:8])


def main():
    db = SessionLocal()
    created_clients = created_staff = roles_assigned = skipped = 0
    try:
        # ---------- роли ----------
        roles = {r[0]: r[1] for r in
                 db.execute(text("SELECT code, id FROM roles")).fetchall()}
        if not roles:
            print("roles table is empty — seed roles first!")
            return

        def give_role(user_id, code):
            rid = roles.get(code)
            if not rid:
                return 0
            db.execute(text(
                "INSERT INTO user_roles (user_id, role_id) VALUES (:u, :r)"
                " ON CONFLICT DO NOTHING"), {"u": str(user_id), "r": str(rid)})
            return 1

        # ---------- клиенты (взрослые + дети) ----------
        adult_ids = []
        cols = {c[0] for c in db.execute(text(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_name='clients'")).fetchall()}
        for i in range(50):
            g = random.choice("mf")
            fn, ln, mn = fio(g)
            birth = date.today() - timedelta(days=random.randint(18 * 365, 60 * 365))
            data = {"first_name": fn, "last_name": ln, "phone": phone()}
            if "middle_name" in cols: data["middle_name"] = mn
            if "birth_date" in cols: data["birth_date"] = str(birth)
            if "gender" in cols: data["gender"] = "MALE" if g == "m" else "FEMALE"
            if "client_category" in cols: data["client_category"] = "STANDARD"
            if "email" in cols: data["email"] = email("client")
            if db.execute(text("SELECT 1 FROM clients WHERE phone=:p"),
                          {"p": data["phone"]}).first():
                skipped += 1
                continue
            keys, phs = ", ".join(data), ", ".join(":%s" % k for k in data)
            r = db.execute(text(
                "INSERT INTO clients (%s) VALUES (%s) RETURNING id" % (keys, phs)),
                {k: str(v) for k, v in data.items()})
            adult_ids.append(str(r.scalar()))
            created_clients += 1
        # дети до 16 (привязка к случайному взрослому, если есть parent_id)
        for i in range(10):
            g = random.choice("mf")
            fn, ln, mn = fio(g)
            birth = date.today() - timedelta(days=random.randint(6 * 365, 15 * 365))
            data = {"first_name": fn, "last_name": ln, "phone": phone()}
            if "middle_name" in cols: data["middle_name"] = mn
            if "birth_date" in cols: data["birth_date"] = str(birth)
            if "gender" in cols: data["gender"] = "MALE" if g == "m" else "FEMALE"
            if "client_category" in cols: data["client_category"] = "CHILD"
            if "parent_id" in cols and adult_ids:
                data["parent_id"] = random.choice(adult_ids)
            if "email" in cols: data["email"] = email("kid")
            if db.execute(text("SELECT 1 FROM clients WHERE phone=:p"),
                          {"p": data["phone"]}).first():
                skipped += 1
                continue
            keys, phs = ", ".join(data), ", ".join(":%s" % k for k in data)
            db.execute(text("INSERT INTO clients (%s) VALUES (%s)" % (keys, phs)),
                       {k: str(v) for k, v in data.items()})
            created_clients += 1

        # ---------- сотрудники ----------
        staff_plan = [("manager", 4), ("accountant", 1), ("trainer", 5),
                      ("cashier", 2), ("support", 2), ("admin", 3), ("owner", 1)]
        ucols = {c[0] for c in db.execute(text(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_name='users'")).fetchall()}
        for code, count in staff_plan:
            for _ in range(count):
                g = random.choice("mf")
                fn, ln, mn = fio(g)
                username = "%s_%s" % (code, uuid.uuid4().hex[:8])
                data = {"username": username,
                        "email": email(code),
                        "password_hash": pwd_context.hash("demo12345"),
                        "is_active": True, "is_superuser": False}
                if "phone" in ucols: data["phone"] = phone()
                if "first_name" in ucols: data["first_name"] = fn
                if "last_name" in ucols: data["last_name"] = ln
                if "is_verified" in ucols: data["is_verified"] = True
                keys, phs = ", ".join(data), ", ".join(":%s" % k for k in data)
                r = db.execute(text(
                    "INSERT INTO users (%s) VALUES (%s) RETURNING id" % (keys, phs)),
                    data)
                uid = r.scalar()
                roles_assigned += give_role(uid, code)
                created_staff += 1
        db.commit()
    except Exception as e:
        db.rollback()
        print("ERROR:", str(e)[:300])
        raise
    finally:
        db.close()
    print("clients: +%d (10 children), staff: +%d, roles assigned: %d, skipped: %d"
          % (created_clients, created_staff, roles_assigned, skipped))


if __name__ == "__main__":
    main()