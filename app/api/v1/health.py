# app/api/v1/health.py

# импорт text для простого SQL-запроса
from sqlalchemy import text

# импорт APIRouter и Depends
from fastapi import APIRouter, Depends

# импорт Session
from sqlalchemy.orm import Session

# импорт подключения к БД
from app.db.session import get_db


# создаём роутер health
router = APIRouter(prefix="/health", tags=["Health"])


# health endpoint
@router.get("/")
def health_check(db: Session = Depends(get_db)):
    # проверяем, что база отвечает
    db.execute(text("SELECT 1"))

    # возвращаем технический ответ
    return {
        "status": "ok",
        "app": "FitIntel Pro",
        "module": "crm",
        "database": "ok",
    }