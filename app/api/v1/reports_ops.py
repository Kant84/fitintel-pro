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


def _rows(db, queries, params):
    """Возвращает строки первого успешного запроса."""
    for sql in queries:
        try:
            rows = db.execute(text(sql), params).mappings().all()
            return [dict(row) for row in rows]
        except Exception:
            db.rollback()
    return []


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
    
@router.get("/attendance")
def attendance_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Посещаемость по дням за выбранный период."""
    rows = _rows(db, [
        "SELECT entry_time::date::text AS date, COUNT(*) AS visits "
        "FROM visits WHERE entry_time::date BETWEEN :df AND :dt "
        "GROUP BY entry_time::date ORDER BY entry_time::date",
    ], {"df": str(date_from), "dt": str(date_to)})
    return {"rows": rows}


@router.get("/inactive")
def inactive_clients_report(
    days: int = Query(30, ge=1, le=3650),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Активные клиенты без посещений дольше указанного числа дней."""
    rows = _rows(db, [
        "SELECT c.id::text AS client_id, "
        "TRIM(CONCAT(c.first_name, ' ', c.last_name)) AS client, c.phone, "
        "MAX(v.entry_time)::text AS last_visit "
        "FROM clients c LEFT JOIN visits v ON v.client_id = c.id "
        "WHERE c.is_active IS TRUE "
        "GROUP BY c.id, c.first_name, c.last_name, c.phone "
        "HAVING MAX(v.entry_time) IS NULL OR "
        "MAX(v.entry_time) < NOW() - (:days || ' days')::interval "
        "ORDER BY MAX(v.entry_time) NULLS FIRST LIMIT 500",
    ], {"days": days})
    return {"rows": rows}


@router.get("/expiring")
def expiring_subscriptions_report(
    days: int = Query(14, ge=0, le=3650),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Действующие абонементы, срок которых скоро заканчивается."""
    rows = _rows(db, [
        "SELECT s.id::text AS subscription_id, "
        "TRIM(CONCAT(c.first_name, ' ', c.last_name)) AS client, c.phone, "
        "t.name AS tariff, s.end_date::text AS end_date, "
        "(s.end_date - CURRENT_DATE) AS days_left "
        "FROM subscriptions s "
        "JOIN clients c ON c.id = s.client_id "
        "JOIN tariffs t ON t.id = s.tariff_id "
        "WHERE s.is_active IS TRUE AND s.status = 'ACTIVE' "
        "AND s.end_date BETWEEN CURRENT_DATE AND "
        "CURRENT_DATE + (:days || ' days')::interval "
        "ORDER BY s.end_date LIMIT 500",
    ], {"days": days})
    return {"rows": rows}


@router.get("/payments-list")
def payments_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Платёжные документы за период, без изменения их состояния."""
    rows = _rows(db, [
        "SELECT p.id::text AS payment_id, p.created_at::text AS created_at, "
        "TRIM(CONCAT(c.first_name, ' ', c.last_name)) AS client, "
        "p.amount, p.currency, p.payment_method, p.payment_direction, "
        "p.payment_category, p.status "
        "FROM payments p LEFT JOIN clients c ON c.id = p.client_id "
        "WHERE p.created_at::date BETWEEN :df AND :dt "
        "ORDER BY p.created_at DESC LIMIT 500",
    ], {"df": str(date_from), "dt": str(date_to)})
    return {"rows": rows}


@router.get("/trainer-payroll")
def trainer_payroll_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Зарплатный отчёт за месяц, содержащий конечную дату периода."""
    from app.api.v1.payroll import calc
    result = calc(period=date_to.strftime("%Y-%m"), current_user=user, db=db)
    return {"rows": result["items"], "period": result["period"]}


@router.get("/hourly")
def attendance_by_hour(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Загруженность по часам (0–23) за период — для оптимизации расписания."""
    rows = _rows(db, [
        "SELECT EXTRACT(HOUR FROM entry_time)::int AS hour, COUNT(*) AS visits "
        "FROM visits WHERE entry_time::date BETWEEN :df AND :dt "
        "GROUP BY 1 ORDER BY 1",
    ], {"df": str(date_from), "dt": str(date_to)})
    return {"rows": rows}


@router.get("/shifts")
def staff_shifts(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """График работы персонала (смены) за период."""
    rows = _rows(db, [
        "SELECT (COALESCE(u.full_name, u.username)) AS employee, "
        "s.shift_date::text AS date, s.start_time::text AS start, "
        "s.end_time::text AS \"end\", s.status "
        "FROM employee_shifts s JOIN users u ON u.id = s.user_id "
        "WHERE s.shift_date::date BETWEEN :df AND :dt ORDER BY s.shift_date, s.start_time LIMIT 500",
        "SELECT (COALESCE(u.full_name, u.username)) AS employee, "
        "s.start_time::date::text AS date, s.start_time::text AS start, "
        "s.end_time::text AS \"end\", s.status "
        "FROM employee_shifts s JOIN users u ON u.id = s.user_id "
        "WHERE s.start_time::date BETWEEN :df AND :dt ORDER BY 2, 3 LIMIT 500",
    ], {"df": str(date_from), "dt": str(date_to)})
    return {"rows": rows}    