"""E60: Self-Learning API — настоящее самообучение."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.ml.pricing_engine import PricingEngine
from app.ml.self_heal import SelfHeal
from app.ml.churn_model import ChurnModel

router = APIRouter(prefix="/self-learn", tags=["Self-Learning / AI"])

@router.get("/pricing/analyze")
def analyze_pricing(db: Session = Depends(get_db)):
    """Анализ всех тарифов с рекомендациями цен."""
    engine = PricingEngine(db)
    return {"tariffs": engine.analyze_tariffs()}

@router.post("/pricing/apply")
def apply_pricing(tariff_id: str, new_price: float, db: Session = Depends(get_db)):
    """Применить рекомендованную цену."""
    engine = PricingEngine(db)
    success = engine.apply_price(tariff_id, new_price)
    return {"applied": success, "tariff_id": tariff_id, "new_price": new_price}

@router.post("/self-heal")
def run_self_heal(db: Session = Depends(get_db)):
    """Запустить самоисцеление БД."""
    healer = SelfHeal(db)
    results = healer.run_all()
    return {"healed": True, "fixes": results}

@router.get("/churn/analyze")
def analyze_churn(client_id: str, db: Session = Depends(get_db)):
    """Предсказать отток клиента."""
    model = ChurnModel(db)
    return model.predict(client_id)

@router.get("/churn/batch")
def batch_churn_analysis(db: Session = Depends(get_db)):
    """Анализ оттока для всех активных клиентов."""
    model = ChurnModel(db)
    sql = text("SELECT id FROM clients WHERE status = 'active' LIMIT 100")
    rows = db.execute(sql).fetchall()
    results = []
    for row in rows:
        pred = model.predict(str(row[0]))
        if pred["risk_level"] in ("high", "critical"):
            results.append(pred)
    return {"at_risk_clients": len(results), "predictions": results}
