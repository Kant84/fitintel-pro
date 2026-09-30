# app/api/v1/reports_ops.py — операционные отчёты клуба (экран «Отчёты»)
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])


def _metric(db, queries, params):
    for sql in queries:
        try:
            return db.execute(text(sql), params).scalar()
        except Exception:
            db.rollback()
            continue
    return None


def _rows(db, queries, params):
    for sql in queries:
        try:
            return [dict(r) for r in db.execute(text(sql), params).mappings().all()]
        except Exception:
            db.rollback()
            continue
    return []


@router.get("/operational")
def operational_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    p = {"df": str(date_from), "dt": str(date_to)}
    return {
        "revenue": _metric(db, [
            "SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='COMPLETED' AND created_at::date BETWEEN :df AND :dt",
        ], p),
        "payments_count": _metric(db, [
            "SELECT COUNT(*) FROM payments WHERE created_at::date BETWEEN :df AND :dt",
        ], p),
        "refunds_sum": _metric(db, [
            "SELECT COALESCE(SUM(amount),0) FROM payments WHERE status IN ('REFUNDED','refunded') AND created_at::date BETWEEN :df AND :dt",
        ], p),
        "visits_count": _metric(db, [
            "SELECT COUNT(*) FROM visits WHERE entry_time::date BETWEEN :df AND :dt",
            "SELECT COUNT(*) FROM visits WHERE created_at::date BETWEEN :df AND :dt",
        ], p),
        "new_clients": _metric(db, [
            "SELECT COUNT(*) FROM clients WHERE created_at::date BETWEEN :df AND :dt",
        ], p),
        "new_subscriptions": _metric(db, [
            "SELECT COUNT(*) FROM subscriptions WHERE created_at::date BETWEEN :df AND :dt",
            "SELECT COUNT(*) FROM subscriptions WHERE start_date::date BETWEEN :df AND :dt",
        ], p),
        "sales_total": _metric(db, [
            "SELECT COALESCE(SUM(total_amount),0) FROM sales WHERE status='COMPLETED' AND created_at::date BETWEEN :df AND :dt",
        ], p),
    }


@router.get("/attendance")
def attendance_by_day(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    rows = _rows(db, [
        "SELECT entry_time::date::text AS day, COUNT(*) AS visits FROM visits "
        "WHERE entry_time::date BETWEEN :df AND :dt GROUP BY 1 ORDER BY 1",
        "SELECT created_at::date::text AS day, COUNT(*) AS visits FROM visits "
        "WHERE created_at::date BETWEEN :df AND :dt GROUP BY 1 ORDER BY 1",
    ], {"df": str(date_from), "dt": str(date_to)})
    return {"rows": rows}


@router.get("/inactive")
def inactive_clients(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    rows = _rows(db, [
        "SELECT (COALESCE(c.last_name,'')||' '||COALESCE(c.first_name,'')) AS client, "
        "c.phone, MAX(v.entry_time)::text AS last_visit "
        "FROM clients c LEFT JOIN visits v ON v.client_id = c.id "
        "WHERE COALESCE(c.is_active, TRUE) "
        "GROUP BY c.id, c.last_name, c.first_name, c.phone "
        "HAVING MAX(v.entry_time) IS NULL OR MAX(v.entry_time) < now() - make_interval(days => :days) "
        "ORDER BY last_visit NULLS FIRST LIMIT 500",
    ], {"days": days})
    return {"rows": rows}


@router.get("/expiring")
def expiring_subscriptions(
    days: int = Query(14, ge=1, le=90),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    rows = _rows(db, [
        "SELECT (COALESCE(c.last_name,'')||' '||COALESCE(c.first_name,'')) AS client, "
        "c.phone, s.end_date::text AS end_date, s.status "
        "FROM subscriptions s JOIN clients c ON c.id = s.client_id "
        "WHERE s.end_date BETWEEN CURRENT_DATE AND CURRENT_DATE + make_interval(days => :days) "
        "ORDER BY s.end_date LIMIT 500",
    ], {"days": days})
    return {"rows": rows}


@router.get("/payments-list")
def payments_list(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    base = ("SELECT {date}::text AS date, p.amount::text AS amount, p.payment_method, "
            "p.status, (COALESCE(c.last_name,'')||' '||COALESCE(c.first_name,'')) AS client "
            "FROM payments p LEFT JOIN clients c ON c.id = p.client_id "
            "WHERE {date} BETWEEN :df AND :dt ORDER BY 1 DESC LIMIT 500")
    rows = _rows(db, [
        base.format(date="p.created_at::date"),
        base.format(date="p.payment_date::date"),
        base.format(date="p.created_at"),
    ], {"df": str(date_from), "dt": str(date_to)})
    return {"rows": rows}


@router.get("/trainer-payroll")
def trainer_payroll(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # сессии тренеров: пробуем известные варианты таблиц расписания
    rows = _rows(db, [
        "SELECT (COALESCE(u.full_name, u.username)) AS trainer, COUNT(b.id) AS sessions, "
        "tp.rate_per_hour::text AS rate, (COUNT(b.id) * tp.rate_per_hour)::text AS total "
        "FROM trainer_profiles tp JOIN users u ON u.id = tp.user_id "
        "LEFT JOIN service_bookings b ON b.trainer_id = tp.user_id "
        "AND b.booking_date::date BETWEEN :df AND :dt "
        "GROUP BY u.full_name, u.username, tp.rate_per_hour ORDER BY total DESC",
        "SELECT (COALESCE(u.full_name, u.username)) AS trainer, COUNT(b.id) AS sessions, "
        "tp.rate_per_hour::text AS rate, (COUNT(b.id) * tp.rate_per_hour)::text AS total "
        "FROM trainer_profiles tp JOIN users u ON u.id = tp.user_id "
        "LEFT JOIN bookings b ON b.trainer_id = tp.user_id "
        "AND b.booking_date::date BETWEEN :df AND :dt "
        "GROUP BY u.full_name, u.username, tp.rate_per_hour ORDER BY total DESC",
    ], {"df": str(date_from), "dt": str(date_to)})
    return {"rows": rows}