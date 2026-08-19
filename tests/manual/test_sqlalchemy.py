# tests/manual/test_sqlalchemy.py
import sys
sys.path.insert(0, r"C:\Users\PC\Desktop\2026\FitNexus AI\FitIntel AI")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.cash_desk_session import CashDeskSession

# Подключаемся к БД
engine = create_engine("postgresql+psycopg://postgres:FitNexus_Postgres_2026!@127.0.0.1:5432/fitnexus")
Session = sessionmaker(bind=engine)
db = Session()

# Проверяем get_current_session
cashier_user_id = "03c4751d-2483-49fa-a4ca-9e2d8c266748"
result = db.query(CashDeskSession).filter(
    CashDeskSession.cashier_user_id == cashier_user_id,
    CashDeskSession.status == "OPEN",
).first()

print(f"Query result: {result}")
if result:
    print(f"Session number: {result.session_number}")
    print(f"Cashier ID: {result.cashier_user_id}")
    print(f"Status: {result.status}")
else:
    print("No session found")

# Проверим все открытые смены
all_open = db.query(CashDeskSession).filter(CashDeskSession.status == "OPEN").all()
print(f"All open sessions: {len(all_open)}")
for s in all_open:
    print(f"  #{s.session_number}, cashier={s.cashier_user_id}, status={s.status}")
