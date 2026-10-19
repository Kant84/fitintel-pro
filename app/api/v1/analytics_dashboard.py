# app/api/v1/analytics_dashboard.py
import json
from datetime import date, timedelta
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.analytics import AnalyticsDaily
from app.models.payment import Payment
from app.models.visit import Visit

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard-chart", response_class=HTMLResponse)
def analytics_dashboard_chart(
    club_id: int = 1,
    db: Session = Depends(get_db),
):
    """Полный дашборд аналитики — 30 дней, графики, статистика"""
    
    # Получаем 30 дней данных
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    # Attendance
    attendance_data = db.query(AnalyticsDaily).filter(
        AnalyticsDaily.club_id == club_id,
        AnalyticsDaily.metric == 'attendance',
        AnalyticsDaily.date >= start_date
    ).order_by(AnalyticsDaily.date).all()
    
    # Revenue
    revenue_data = db.query(AnalyticsDaily).filter(
        AnalyticsDaily.club_id == club_id,
        AnalyticsDaily.metric == 'revenue',
        AnalyticsDaily.date >= start_date
    ).order_by(AnalyticsDaily.date).all()
    
    # Статистика
    total_visits = db.query(func.count(Visit.id)).scalar() or 0
    total_revenue = db.query(func.sum(Payment.amount)).filter(Payment.status == 'completed').scalar() or 0
    avg_check = total_revenue / total_visits if total_visits > 0 else 0
    avg_duration = db.query(func.avg(Visit.duration_minutes)).filter(Visit.status == 'COMPLETED').scalar() or 0
    
    # Top zones
    zones = db.query(Visit.zone, func.count(Visit.id)).group_by(Visit.zone).order_by(func.count(Visit.id).desc()).limit(5).all()
    
    # Формируем JSON
    att_labels = [str(d.date) for d in attendance_data]
    att_values = [float(d.value) for d in attendance_data]
    rev_labels = [str(d.date) for d in revenue_data]
    rev_values = [float(d.value) for d in revenue_data]
    
    # Прогноз attendance
    from app.services.analytics_service import AnalyticsService
    service = AnalyticsService(db)
    forecast = service.forecast(club_id, 'attendance', 7)
    forecast_labels = [str(p['date']) for p in forecast['forecast']]
    forecast_values = [p['value'] for p in forecast['forecast']]
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>FitIntel PRO — Дашборд</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; background: #f0f2f5; }}
        .header {{ background: #1F4E78; color: white; padding: 20px; text-align: center; }}
        .container {{ max-width: 1400px; margin: 20px auto; padding: 0 20px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .stat-label {{ color: #666; font-size: 14px; margin-bottom: 8px; }}
        .stat-value {{ font-size: 32px; font-weight: bold; color: #1F4E78; }}
        .stat-sub {{ color: #888; font-size: 12px; margin-top: 5px; }}
        .charts-grid {{ display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }}
        .chart-card {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .chart-title {{ font-size: 18px; font-weight: bold; color: #333; margin-bottom: 15px; }}
        .zones-list {{ list-style: none; padding: 0; }}
        .zones-list li {{ padding: 10px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; }}
        .zone-name {{ font-weight: 500; }}
        .zone-count {{ color: #1F4E78; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>FitIntel PRO — Аналитический дашборд</h1>
        <p>Период: {start_date} — {end_date} | Клуб #{club_id}</p>
    </div>
    
    <div class="container">
        <!-- Статистика -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Всего посещений</div>
                <div class="stat-value">{total_visits:,}</div>
                <div class="stat-sub">за всё время</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Выручка</div>
                <div class="stat-value">{total_revenue:,.0f} ₽</div>
                <div class="stat-sub">все платежи</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Средний чек</div>
                <div class="stat-value">{avg_check:,.0f} ₽</div>
                <div class="stat-sub">на посещение</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Среднее время</div>
                <div class="stat-value">{avg_duration:.0f} мин</div>
                <div class="stat-sub">в клубе</div>
            </div>
        </div>
        
        <!-- Графики -->
        <div class="charts-grid">
            <div class="chart-card">
                <div class="chart-title">Посещаемость — 30 дней + прогноз</div>
                <canvas id="attendanceChart" height="300"></canvas>
            </div>
            <div class="chart-card">
                <div class="chart-title">Топ зон</div>
                <ul class="zones-list">
                    {''.join([f'<li><span class="zone-name">{z[0]}</span><span class="zone-count">{z[1]}</span></li>' for z in zones])}
                </ul>
            </div>
            <div class="chart-card">
                <div class="chart-title">Выручка — 30 дней</div>
                <canvas id="revenueChart" height="300"></canvas>
            </div>
            <div class="chart-card">
                <div class="chart-title">Прогноз тренда</div>
                <div style="text-align: center; padding: 40px;">
                    <div style="font-size: 48px; color: {'green' if forecast['trend'] == 'UP' else 'red' if forecast['trend'] == 'DOWN' else 'orange'};">{forecast['trend']}</div>
                    <div style="margin-top: 20px; color: #666;">{forecast['recommendation']}</div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Attendance chart
        new Chart(document.getElementById('attendanceChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps(att_labels, ensure_ascii=False)},
                datasets: [
                    {{
                        label: 'Факт',
                        data: {json.dumps(att_values, ensure_ascii=False)},
                        borderColor: '#8884d8',
                        backgroundColor: 'rgba(136, 132, 216, 0.1)',
                        fill: true,
                        tension: 0.3
                    }},
                    {{
                        label: 'Прогноз',
                        data: {json.dumps([None]*(len(att_values)-1) + [att_values[-1] if att_values else 0] + forecast_values, ensure_ascii=False)},
                        borderColor: '#82ca9d',
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.3
                    }}
                ]
            }},
            options: {{
                responsive: true,
                interaction: {{ mode: 'index', intersect: false }},
                scales: {{ y: {{ beginAtZero: true }} }}
            }}
        }});
        
        // Revenue chart
        new Chart(document.getElementById('revenueChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(rev_labels, ensure_ascii=False)},
                datasets: [{{
                    label: 'Выручка (₽)',
                    data: {json.dumps(rev_values, ensure_ascii=False)},
                    backgroundColor: '#1F4E78',
                    borderRadius: 4
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{ y: {{ beginAtZero: true }} }}
            }}
        }});
    </script>
</body>
</html>'''
    
    return html

# ---------- Полная статистика клуба за период (dashboard W7) ----------
@router.get("/full-stats")
def analytics_full_stats(date_from: str = None, date_to: str = None,
                         db: Session = Depends(get_db)):
    """Все агрегаты для аналитического дашборда одним запросом."""
    from sqlalchemy import text as _text
    from datetime import date as _date, timedelta as _td

    t = _date.today()
    d_to = date_to or t.isoformat()
    d_from = date_from or (t - _td(days=30)).isoformat()
    P = {"f": d_from, "t": d_to}

    def q(sql):
        try:
            rows = db.execute(_text(sql), P).all()
            return [dict(r._mapping) for r in rows]
        except Exception as e:
            return [{"error": str(e)[:140]}]

    def probe(table_cands):
        for tbl in table_cands:
            cols = db.execute(_text(
                "SELECT column_name FROM information_schema.columns WHERE table_name=:t"),
                {"t": tbl}).scalars().all()
            if cols:
                return tbl, set(cols)
        return None, set()

    out = {"period": {"from": d_from, "to": d_to}}

    out["visits_by_day"] = q(
        "SELECT entry_time::date AS d, COUNT(*) AS cnt FROM visits "
        "WHERE entry_time::date BETWEEN :f AND :t GROUP BY 1 ORDER BY 1")
    out["revenue_by_day"] = q(
        "SELECT created_at::date AS d, COALESCE(SUM(amount),0) AS total, COUNT(*) AS cnt "
        "FROM payments WHERE created_at::date BETWEEN :f AND :t AND status='COMPLETED' "
        "GROUP BY 1 ORDER BY 1")
    out["new_clients_by_day"] = q(
        "SELECT created_at::date AS d, COUNT(*) AS cnt FROM clients "
        "WHERE created_at::date BETWEEN :f AND :t GROUP BY 1 ORDER BY 1")
    out["lost_clients_by_day"] = q(
        "SELECT updated_at::date AS d, COUNT(*) AS cnt FROM clients "
        "WHERE updated_at::date BETWEEN :f AND :t AND status IN ('INACTIVE','ARCHIVED') "
        "GROUP BY 1 ORDER BY 1")
    out["subs_by_day"] = q(
        "SELECT s.created_at::date AS d, COUNT(*) AS cnt, COALESCE(SUM(tar.price),0) AS total "
        "FROM subscriptions s LEFT JOIN tariffs tar ON tar.id = s.tariff_id "
        "WHERE s.created_at::date BETWEEN :f AND :t GROUP BY 1 ORDER BY 1")
    out["visits_wd_hour"] = q(
        "SELECT (EXTRACT(ISODOW FROM entry_time)::int - 1) AS wd, "
        "EXTRACT(HOUR FROM entry_time)::int AS hr, COUNT(*) AS cnt FROM visits "
        "WHERE entry_time::date BETWEEN :f AND :t GROUP BY 1,2 ORDER BY 1,2")

    # востребованность услуг (записи)
    tbl, cols = probe(["bookings", "service_bookings", "appointments", "schedules"])
    top_services = []
    if tbl and cols:
        name_col = next((c for c in ("service_name", "name", "title", "service") if c in cols), None)
        date_col = next((c for c in ("date", "created_at", "start_time", "scheduled_at") if c in cols), None)
        if name_col and date_col:
            top_services = q(
                f"SELECT {name_col} AS name, COUNT(*) AS cnt FROM {tbl} "
                f"WHERE {date_col}::date BETWEEN :f AND :t GROUP BY 1 ORDER BY 2 DESC LIMIT 10")
    out["top_services"] = top_services

    # тренеры (из тех же записей)
    top_trainers = []
    if tbl and cols:
        tr_col = next((c for c in ("trainer_name", "trainer", "trainer_id", "employee_name") if c in cols), None)
        date_col = next((c for c in ("date", "created_at", "start_time", "scheduled_at") if c in cols), None)
        if tr_col and date_col:
            top_trainers = q(
                f"SELECT CAST({tr_col} AS TEXT) AS name, COUNT(*) AS cnt FROM {tbl} "
                f"WHERE {date_col}::date BETWEEN :f AND :t GROUP BY 1 ORDER BY 2 DESC LIMIT 10")
    out["top_trainers"] = top_trainers

    # товары (продажи)
    tbl2, cols2 = probe(["sales", "warehouse_sales", "product_sales"])
    top_products = []
    if tbl2 and cols2:
        name_col = next((c for c in ("product_name", "name", "title", "item", "product") if c in cols2), None)
        date_col = next((c for c in ("created_at", "date", "sold_at") if c in cols2), None)
        amount_col = next((c for c in ("amount", "total", "price", "sum") if c in cols2), None)
        if name_col and date_col and amount_col:
            top_products = q(
                f"SELECT CAST({name_col} AS TEXT) AS name, COUNT(*) AS cnt, "
                f"COALESCE(SUM({amount_col}),0) AS total FROM {tbl2} "
                f"WHERE {date_col}::date BETWEEN :f AND :t GROUP BY 1 "
                f"ORDER BY 3 DESC LIMIT 10")
    out["top_products"] = top_products

    return out

# ═══════════════ W7-2: временные ряды, сезонный прогноз, отток, востребованность ═══════════════
@router.get("/timeseries")
def analytics_timeseries(date_from: str = None, date_to: str = None,
                         db: Session = Depends(get_db)):
    """Ежедневные ряды с нулями на пустых датах + MA7 + наклон + тренд %."""
    from sqlalchemy import text as _text
    from datetime import date as _date, timedelta as _td

    t = _date.today()
    d_to = date_to or t.isoformat()
    d_from = date_from or (t - _td(days=30)).isoformat()
    P = {"f": d_from, "t": d_to}

    def q(sql):
        try:
            rows = db.execute(_text(sql), P).all()
            return {str(r._mapping["d"]): float(r._mapping["v"]) for r in rows}
        except Exception:
            return {}

    visits = q("SELECT entry_time::date AS d, COUNT(*)::float AS v FROM visits "
               "WHERE entry_time::date BETWEEN :f AND :t GROUP BY 1")
    revenue = q("SELECT created_at::date AS d, COALESCE(SUM(amount),0)::float AS v "
                "FROM payments WHERE created_at::date BETWEEN :f AND :t "
                "AND status='COMPLETED' GROUP BY 1")
    newc = q("SELECT created_at::date AS d, COUNT(*)::float AS v FROM clients "
             "WHERE created_at::date BETWEEN :f AND :t GROUP BY 1")
    lost = q("SELECT updated_at::date AS d, COUNT(*)::float AS v FROM clients "
             "WHERE updated_at::date BETWEEN :f AND :t "
             "AND status IN ('INACTIVE','ARCHIVED') GROUP BY 1")
    subs = q("SELECT created_at::date AS d, COUNT(*)::float AS v FROM subscriptions "
             "WHERE created_at::date BETWEEN :f AND :t GROUP BY 1")

    f0 = _date.fromisoformat(d_from)
    t0 = _date.fromisoformat(d_to)
    days = []
    cur = f0
    while cur <= t0:
        days.append(cur.isoformat())
        cur += _td(days=1)

    def slope(vals):
        n = len(vals)
        if n < 2:
            return 0.0
        sx = sum(range(n))
        sy = sum(vals)
        den = n * sum(i * i for i in range(n)) - sx * sx
        return round((n * sum(i * v for i, v in enumerate(vals)) - sx * sy) / den, 4) if den else 0.0

    out = {}
    for key, m in (("visits", visits), ("revenue", revenue),
                   ("new_clients", newc), ("lost_clients", lost), ("subscriptions", subs)):
        vals = [m.get(d, 0.0) for d in days]
        ma7 = [round(sum(vals[max(0, i - 6):i + 1]) / len(vals[max(0, i - 6):i + 1]), 2)
               for i in range(len(vals))]
        half = max(1, len(vals) // 2)
        first, second = sum(vals[:half]), sum(vals[half:])
        out[key] = {
            "dates": days,
            "values": [round(v, 2) for v in vals],
            "ma7": ma7,
            "slope_per_day": slope(vals),
            "total": round(sum(vals), 2),
            "trend_pct": round((second - first) / first * 100, 1) if first else None,
        }
    return {"period": {"from": d_from, "to": d_to}, "series": out}


@router.get("/trend-forecast")
def analytics_trend_forecast(metric: str = "revenue", date_from: str = None,
                             date_to: str = None, days_ahead: int = 14,
                             db: Session = Depends(get_db)):
    """Сезонный прогноз: линейный тренд × сезонность дня недели × зарплатные дни."""
    from datetime import date as _date, timedelta as _td

    allowed = {"attendance": "visits", "revenue": "revenue", "new_clients": "new_clients"}
    skey = allowed.get(metric, "revenue")
    ts = analytics_timeseries(date_from, date_to, db)
    s = ts["series"][skey]
    vals, days = s["values"], s["dates"]
    n = len(vals)
    horizon = max(1, min(int(days_ahead or 14), 60))

    wd_mult = {k: 1.0 for k in range(7)}
    if n >= 8:
        from collections import defaultdict
        wd_vals = defaultdict(list)
        for d, v in zip(days, vals):
            wd_vals[_date.fromisoformat(d).weekday()].append(v)
        overall = sum(vals) / n
        if overall > 0:
            for k in range(7):
                if wd_vals.get(k):
                    wd_mult[k] = (sum(wd_vals[k]) / len(wd_vals[k])) / overall

    a = b = 0.0
    if n >= 2:
        sx = sum(range(n))
        sy = sum(vals)
        den = n * sum(i * i for i in range(n)) - sx * sx
        if den:
            a = (n * sum(i * v for i, v in enumerate(vals)) - sx * sy) / den
            b = (sy - a * sx) / n

    last_day = _date.fromisoformat(days[-1]) if days else _date.today()
    forecast = []
    for i in range(1, horizon + 1):
        d = last_day + _td(days=i)
        base = a * (n - 1 + i) + b
        if base < 0:
            base = 0.0
        val = base * wd_mult.get(d.weekday(), 1.0)
        if d.day in (5, 6, 7, 20, 21, 22):
            val *= 1.08
        forecast.append({"d": d.isoformat(), "value": round(val, 2)})

    trend = "UP" if a > 0.05 else ("DOWN" if a < -0.05 else "STABLE")
    return {
        "metric": skey,
        "history": [{"d": d, "value": v} for d, v in zip(days, vals)],
        "forecast": forecast,
        "trend": trend,
        "forecast_total": round(sum(p["value"] for p in forecast), 2),
        "seasonality": {str(k): round(v, 3) for k, v in wd_mult.items()},
    }


@router.get("/churn-summary")
def analytics_churn_summary(db: Session = Depends(get_db)):
    """Сводка рисков оттока по всем активным клиентам (ChurnModel)."""
    from sqlalchemy import text as _text
    from app.ml.churn_model import ChurnModel

    rows = db.execute(_text(
        "SELECT id, COALESCE(NULLIF(full_name,''), phone, email, id::text) AS name "
        "FROM clients WHERE status = 'ACTIVE'")).all()
    model = ChurnModel(db)
    counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    top = []
    total = 0
    for r in rows:
        cid = str(r._mapping["id"])
        try:
            res = model.predict(cid)
        except Exception:
            continue
        total += 1
        lvl = res.get("risk_level", "low")
        counts[lvl] = counts.get(lvl, 0) + 1
        top.append({"client_id": cid, "name": r._mapping["name"],
                    "probability": res.get("probability", 0),
                    "risk_level": lvl})
    top.sort(key=lambda x: -x["probability"])
    return {"total_active": total, "counts": counts, "top_risk": top[:10],
            "model_type": "xgboost" if getattr(model, "ml_model", None) else "rule_based"}


@router.get("/demand-tops")
def analytics_demand_tops(date_from: str = None, date_to: str = None,
                          db: Session = Depends(get_db)):
    """Востребованность услуг/тренеров/товаров — автопоиск таблиц по схеме БД."""
    from sqlalchemy import text as _text
    from datetime import date as _date, timedelta as _td

    t = _date.today()
    d_to = date_to or t.isoformat()
    d_from = date_from or (t - _td(days=30)).isoformat()
    P = {"f": d_from, "t": d_to}

    def find_tables(patterns):
        sql = ("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND ("
               + " OR ".join("table_name ILIKE '%s'" % p for p in patterns) + ") ORDER BY table_name")
        try:
            return [r[0] for r in db.execute(_text(sql)).all()]
        except Exception:
            return []

    def cols_of(tbl):
        try:
            return set(db.execute(_text(
                "SELECT column_name FROM information_schema.columns WHERE table_name=:t"),
                {"t": tbl}).scalars().all())
        except Exception:
            return set()

    def q(sql):
        try:
            return [dict(r._mapping) for r in db.execute(_text(sql), P).all()]
        except Exception:
            return []

    out = {"top_services": [], "top_trainers": [], "top_products": []}
    for tbl in find_tables(["book", "appoint", "schedul", "session", "class", "lesson", "train"]):
        cols = cols_of(tbl)
        if not cols:
            continue
        name_col = next((c for c in ("service_name", "service", "title", "name", "activity", "discipline") if c in cols), None)
        tr_col = next((c for c in ("trainer_name", "trainer", "trainer_id", "coach", "employee_name") if c in cols), None)
        date_col = next((c for c in ("date", "visit_date", "start_time", "scheduled_at", "starts_at", "created_at", "dt") if c in cols), None)
        if date_col and name_col and not out["top_services"]:
            out["top_services"] = q(
                "SELECT CAST(%s AS TEXT) AS name, COUNT(*) AS cnt FROM %s "
                "WHERE %s::date BETWEEN :f AND :t GROUP BY 1 ORDER BY 2 DESC LIMIT 10"
                % (name_col, tbl, date_col))
        if date_col and tr_col and not out["top_trainers"]:
            out["top_trainers"] = q(
                "SELECT CAST(%s AS TEXT) AS name, COUNT(*) AS cnt FROM %s "
                "WHERE %s::date BETWEEN :f AND :t GROUP BY 1 ORDER BY 2 DESC LIMIT 10"
                % (tr_col, tbl, date_col))
        if out["top_services"] and out["top_trainers"]:
            break
    for tbl in find_tables(["sale", "product", "warehouse", "store", "shop", "good"]):
        cols = cols_of(tbl)
        if not cols:
            continue
        name_col = next((c for c in ("product_name", "product", "item", "name", "title", "good") if c in cols), None)
        date_col = next((c for c in ("created_at", "sold_at", "date", "dt") if c in cols), None)
        amount_col = next((c for c in ("amount", "total", "price", "sum", "cost") if c in cols), None)
        if name_col and date_col and amount_col:
            out["top_products"] = q(
                "SELECT CAST(%s AS TEXT) AS name, COUNT(*) AS cnt, COALESCE(SUM(%s),0) AS total FROM %s "
                "WHERE %s::date BETWEEN :f AND :t GROUP BY 1 ORDER BY 3 DESC LIMIT 10"
                % (name_col, amount_col, tbl, date_col))
            break
    return out