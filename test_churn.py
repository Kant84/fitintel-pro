from app.db.session import SessionLocal
from app.ml import ChurnModel, EventLogger, FeatureStore

db = SessionLocal()

# 1. Реальный client_id из базы
from app.api.v1.license_api import _eng
from sqlalchemy import text
row = _eng().connect().execute(text("SELECT id FROM clients LIMIT 1")).first()
if not row:
    print("Нет клиентов в базе — создайте хотя бы одного через desktop")
    raise SystemExit

cid = str(row[0])
print("client_id:", cid)

# 2. Фичи
fs = FeatureStore(db)
feats = fs.get_client_features(cid)
print("features:", feats)

# 3. Предсказание
cm = ChurnModel(db)
print("prediction:", cm.predict(cid))