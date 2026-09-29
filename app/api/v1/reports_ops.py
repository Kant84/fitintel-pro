# app/api/v1/reports_ops.py — операционные отчёты клуба (экран «Отчёты»)
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])


def _metric(db, queries, params):
    """Пробуем запросы по очереди; первая успешная scalar-выдача — результат."""
    for sql in queries:
        try:
            return db.execute(text(sql), params).scalar()
        except Exception:
            db.rollback()
            continue
    return None


@router.get("/operational")
def operational_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    p = {"df": str(date_from), "dt": str(date_to)}
    r = {}
    r["revenue"] = _metric(db, [
        "SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='COMPLETED' AND created_at::date BETWEEN :df AND :dt",
        "SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='completed' AND created_at::date BETWEEN :df AND :dt",
    ], p)
    r["payments_count"] = _metric(db, [
        "SELECT COUNT(*) FROM payments WHERE created_at::date BETWEEN :df AND :dt",
    ], p)
    r["refunds_sum"] = _metric(db, [
        "SELECT COALESCE(SUM(amount),0) FROM payments WHERE status IN ('REFUNDED','refunded') AND created_at::date BETWEEN :df AND :dt",
    ], p)
    r["visits_count"] = _metric(db, [
        "SELECT COUNT(*) FROM visits WHERE entry_time::date BETWEEN :df AND :dt",
        "SELECT COUNT(*) FROM visits WHERE created_at::date BETWEEN :df AND :dt",
    ], p)
    r["new_clients"] = _metric(db, [
        "SELECT COUNT(*) FROM clients WHERE created_at::date BETWEEN :df AND :dt",
    ], p)
    r["new_subscriptions"] = _metric(db, [
        "SELECT COUNT(*) FROM subscriptions WHERE created_at::date BETWEEN :df AND :dt",
        "SELECT COUNT(*) FROM subscriptions WHERE start_date::date BETWEEN :df AND :dt",
    ], p)
    r["sales_total"] = _metric(db, [
        "SELECT COALESCE(SUM(total_amount),0) FROM sales WHERE status='COMPLETED' AND created_at::date BETWEEN :df AND :dt",
    ], p)
    return r