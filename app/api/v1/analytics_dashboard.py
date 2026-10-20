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
    """Сводка рисков оттока — SQL-правила, полный автоподбор схемы."""
    from sqlalchemy import text as _text

    def cols_of(tbl):
        try:
            return set(db.execute(_text(
                "SELECT column_name FROM information_schema.columns WHERE table_name=:t"),
                {"t": tbl}).scalars().all())
        except Exception:
            return set()

    c_cols = cols_of("clients")
    v_cols = cols_of("visits")
    p_cols = cols_of("payments")
    s_cols = cols_of("subscriptions")

    # имя клиента из доступных колонок
    if "full_name" in c_cols:
        name_expr = "NULLIF(c.full_name,'')"
    else:
        parts = [p for p in ("last_name", "first_name", "middle_name") if p in c_cols]
        if parts:
            name_expr = "NULLIF(TRIM(CONCAT_WS(' ', %s)), '')" % ", ".join("c." + p for p in parts)
        else:
            name_expr = "NULL"
    fb = ["NULLIF(c.%s,'')" % x for x in ("phone", "email") if x in c_cols]
    if fb:
        name_expr = "COALESCE(%s, %s)" % (name_expr, ", ".join(fb))
    name_expr = "COALESCE(%s, c.id::text)" % name_expr

    v_lat = "LEFT JOIN LATERAL (SELECT NULL::int AS last_visit_days, 0 AS visits_30d WHERE FALSE) v ON TRUE"
    if {"client_id", "entry_time"} <= v_cols:
        v_lat = ("LEFT JOIN LATERAL (SELECT EXTRACT(DAY FROM NOW() - MAX(entry_time))::int "
                 "AS last_visit_days, COUNT(*) FILTER (WHERE entry_time >= NOW() - "
                 "interval '30 days') AS visits_30d FROM visits v WHERE v.client_id = c.id) v ON TRUE")
    p_lat = "LEFT JOIN LATERAL (SELECT 0 AS payments_90d WHERE FALSE) p ON TRUE"
    if {"client_id", "created_at"} <= p_cols:
        st = " AND pay.status = 'COMPLETED'" if "status" in p_cols else ""
        p_lat = ("LEFT JOIN LATERAL (SELECT COUNT(*) AS payments_90d FROM payments pay "
                 "WHERE pay.client_id = c.id AND pay.created_at >= NOW() - interval '90 days'"
                 + st + ") p ON TRUE")
    s_lat = "LEFT JOIN LATERAL (SELECT NULL::int AS days_left WHERE FALSE) s ON TRUE"
    if {"client_id", "end_date"} <= s_cols and "status" in s_cols:
        s_lat = ("LEFT JOIN LATERAL (SELECT MIN(GREATEST(EXTRACT(DAY FROM (end_date - NOW()))"
                 "::int, 0)) AS days_left FROM subscriptions s WHERE s.client_id = c.id "
                 "AND s.status = 'ACTIVE') s ON TRUE")

    where = " WHERE c.status = 'ACTIVE'" if "status" in c_cols else ""
    sql = ("SELECT c.id, " + name_expr + " AS name, "
           "COALESCE(v.last_visit_days, 999) AS last_visit_days, "
           "COALESCE(v.visits_30d, 0) AS visits_30d, "
           "COALESCE(p.payments_90d, 0) AS payments_90d, "
           "COALESCE(s.days_left, 999) AS subscription_days_left "
           "FROM clients c " + v_lat + " " + p_lat + " " + s_lat + where)
    try:
        rows = db.execute(_text(sql)).all()
    except Exception as e:
        return {"error": str(e)[:250], "total_active": 0,
                "counts": {"low": 0, "medium": 0, "high": 0, "critical": 0},
                "top_risk": [], "model_type": "unavailable"}

    counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    top = []
    for r in rows:
        m = r._mapping
        last = m["last_visit_days"] or 999
        v30 = m["visits_30d"] or 0
        p90 = m["payments_90d"] or 0
        dl = m["subscription_days_left"]
        dl = 999 if dl is None else dl
        score = 0.0
        if last > 30: score += 0.3
        elif last > 14: score += 0.2
        if v30 == 0: score += 0.2
        if p90 == 0: score += 0.15
        if dl <= 7: score += 0.25
        elif dl <= 30: score += 0.15
        elif dl >= 999: score += 0.1
        score = min(round(score, 2), 1.0)
        lvl = ("critical" if score >= 0.8 else
               "high" if score >= 0.6 else
               "medium" if score >= 0.4 else "low")
        counts[lvl] += 1
        top.append({"client_id": str(m["id"]), "name": m["name"],
                    "probability": score, "risk_level": lvl})
    top.sort(key=lambda x: -x["probability"])
    return {"total_active": len(rows), "counts": counts,
            "top_risk": top[:10], "model_type": "sql_rules"}
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

# ═══════════════ W8: расширенная аналитика (когорты, LTV, загрузка, прогнозы, рекомендации) ═══════════════
@router.get("/extended")
def analytics_extended(db: Session = Depends(get_db)):
    from sqlalchemy import text as _text

    def cols_of(tbl):
        try:
            return set(db.execute(_text(
                "SELECT column_name FROM information_schema.columns WHERE table_name=:t"),
                {"t": tbl}).scalars().all())
        except Exception:
            return set()

    def q(sql, P=None):
        try:
            return [dict(r._mapping) for r in db.execute(_text(sql), P or {}).all()]
        except Exception:
            return []

    c_cols = cols_of("clients")
    v_cols = cols_of("visits")
    p_cols = cols_of("payments")
    s_cols = cols_of("subscriptions")
    has_visits = {"client_id", "entry_time"} <= v_cols
    has_payments = {"client_id", "created_at", "amount"} <= p_cols
    pay_st = " AND p.status='COMPLETED'" if "status" in p_cols else ""
    out = {}

    # 1. когортный retention
    if has_visits and "created_at" in c_cols:
        rows = q(
            "SELECT to_char(date_trunc('month', c.created_at),'YYYY-MM') AS cohort, "
            "COUNT(*) AS registered, "
            "COUNT(*) FILTER (WHERE NOW() - c.created_at >= interval '30 days') AS aged30, "
            "COUNT(*) FILTER (WHERE NOW() - c.created_at >= interval '30 days' "
            "AND v.last_visit >= NOW() - interval '30 days') AS retained30 "
            "FROM clients c LEFT JOIN LATERAL (SELECT MAX(v.entry_time) AS last_visit "
            "FROM visits v WHERE v.client_id = c.id) v ON TRUE "
            "GROUP BY 1 ORDER BY 1 DESC LIMIT 6")
        for r in rows:
            r["retention30_pct"] = (round(r["retained30"] / r["aged30"] * 100, 1)
                                    if r.get("aged30") else None)
        out["cohorts"] = rows
    else:
        out["cohorts"] = []

    # 2. LTV / ARPU (+ по сегменту)
    out["ltv"] = {}
    out["ltv_by_segment"] = []
    if has_payments:
        r = q("SELECT COALESCE(AVG(t.lifetime),0) AS ltv_avg, COALESCE(AVG(t.monthly),0) AS arpu_30d FROM ("
              "SELECT c.id, COALESCE((SELECT SUM(p.amount) FROM payments p "
              "WHERE p.client_id=c.id%s),0) AS lifetime, "
              "COALESCE((SELECT SUM(p.amount) FROM payments p WHERE p.client_id=c.id%s "
              "AND p.created_at >= NOW() - interval '30 days'),0) AS monthly FROM clients c) t" % (pay_st, pay_st))
        if r:
            out["ltv"] = r[0]
        seg_col = ("segment" if "segment" in c_cols else
                   ("client_tag" if "client_tag" in c_cols else None))
        if seg_col:
            out["ltv_by_segment"] = q(
                "SELECT COALESCE(NULLIF(c.%s,''),'(не задан)') AS segment, COUNT(*) AS clients, "
                "COALESCE(AVG(t.lifetime),0) AS ltv FROM clients c JOIN ("
                "SELECT c2.id, COALESCE((SELECT SUM(p.amount) FROM payments p "
                "WHERE p.client_id=c2.id%s),0) AS lifetime FROM clients c2) t ON t.id=c.id "
                "GROUP BY 1 ORDER BY 3 DESC LIMIT 10" % (seg_col, pay_st))

    # 3. месячный приток/отток + churn rate
    out["monthly_flow"] = []
    if "created_at" in c_cols:
        new_m = {r["m"]: r["cnt"] for r in q(
            "SELECT to_char(created_at,'YYYY-MM') AS m, COUNT(*) AS cnt FROM clients GROUP BY 1")}
        lost_m = {}
        if "status" in c_cols and "updated_at" in c_cols:
            lost_m = {r["m"]: r["cnt"] for r in q(
                "SELECT to_char(updated_at,'YYYY-MM') AS m, COUNT(*) AS cnt FROM clients "
                "WHERE status IN ('INACTIVE','ARCHIVED') GROUP BY 1")}
        total_r = q("SELECT COUNT(*) AS cnt FROM clients")
        total = total_r[0]["cnt"] if total_r else 0
        months = sorted(set(new_m) | set(lost_m))[-6:]
        out["monthly_flow"] = [
            {"month": m, "new": new_m.get(m, 0), "lost": lost_m.get(m, 0),
             "churn_rate_pct": round(lost_m.get(m, 0) / max(total, 1) * 100, 2)}
            for m in months]

    # 4. загрузка клуба
    occ = {}
    if has_visits:
        r = q("SELECT EXTRACT(HOUR FROM entry_time)::int AS hr, COUNT(*) AS cnt "
              "FROM visits GROUP BY 1 ORDER BY 1")
        occ["by_hour"] = r
        if r:
            mx = max(x["cnt"] for x in r)
            tot = sum(x["cnt"] for x in r) or 1
            occ["peak_hour"] = max(r, key=lambda x: x["cnt"])["hr"]
            occ["peak_share_pct"] = round(mx / tot * 100, 1)
        if "exit_time" in v_cols:
            d = q("SELECT AVG(EXTRACT(EPOCH FROM (exit_time - entry_time))/60) AS avg_min "
                  "FROM visits WHERE exit_time IS NOT NULL")
            if d and d[0]["avg_min"]:
                occ["avg_visit_min"] = round(d[0]["avg_min"], 1)
    out["occupancy"] = occ

    # 5. заморозки / должники
    st = {}
    if "status" in c_cols:
        st["clients_by_status"] = q(
            "SELECT status, COUNT(*) AS cnt FROM clients GROUP BY status ORDER BY 2 DESC")
    if s_cols and "status" in s_cols:
        st["subscriptions_by_status"] = q(
            "SELECT status, COUNT(*) AS cnt FROM subscriptions GROUP BY status ORDER BY 2 DESC")
    out["statuses"] = st

    # 6. воронка (если есть лиды/пробные)
    lt = q("SELECT table_name FROM information_schema.tables WHERE table_schema='public' "
           "AND (table_name ILIKE '%lead%' OR table_name ILIKE '%trial%' OR table_name ILIKE '%guest%')")
    out["funnel"] = {"available": bool(lt), "tables": [r["table_name"] for r in lt]}

    # 7. Holt (экспоненциальное сглаживание с трендом)
    def holt(vals, days, alpha=0.4, beta=0.1):
        if len(vals) < 3:
            return [float(vals[-1]) if vals else 0.0] * days
        level = vals[0]
        trend = vals[1] - vals[0]
        for v in vals[1:]:
            prev = level
            level = alpha * v + (1 - alpha) * (level + trend)
            trend = beta * (level - prev) + (1 - beta) * trend
        return [max(level + i * trend, 0.0) for i in range(1, days + 1)]

    ts = analytics_timeseries(None, None, db)["series"]
    out["holt_forecast_14d"] = {
        k: [round(x, 2) for x in holt(ts[k]["values"], 14)]
        for k in ("visits", "revenue", "new_clients")}

    # 8. отток в деньгах (рисковые клиенты × их средний платёж)
    out["churn_money_30d"] = {}
    if has_payments and has_visits and "status" in c_cols:
        rows = q(
            "SELECT COUNT(*) AS risky, COALESCE(SUM(avg_pay),0) AS expected_loss FROM ("
            "SELECT c.id, COALESCE((SELECT AVG(p.amount) FROM payments p "
            "WHERE p.client_id=c.id%s),0) AS avg_pay, "
            "(SELECT MAX(v.entry_time) FROM visits v WHERE v.client_id=c.id) AS last_v "
            "FROM clients c WHERE c.status='ACTIVE') t "
            "WHERE last_v IS NULL OR last_v < NOW() - interval '14 days'" % pay_st)
        if rows:
            out["churn_money_30d"] = rows[0]

    # 9. доверительный интервал прогноза выручки
    out["revenue_forecast_ci"] = {}
    vals = ts["revenue"]["values"]
    n = len(vals)
    if n >= 3:
        sx = sum(range(n))
        sy = sum(vals)
        den = n * sum(i * i for i in range(n)) - sx * sx
        if den:
            a = (n * sum(i * v for i, v in enumerate(vals)) - sx * sy) / den
            b = (sy - a * sx) / n
            resid = [v - (a * i + b) for i, v in enumerate(vals)]
            sd = (sum(r_ * r_ for r_ in resid) / (n - 2)) ** 0.5
            out["revenue_forecast_ci"] = {
                "sigma": round(sd, 2),
                "band_80": round(1.28 * sd, 2),
                "note": "±1.28σ ≈ 80%-ый интервал вокруг линии прогноза"}

    # 10. оплаты по типам
    pt = {}
    if has_payments:
        mcol = next((c for c in ("method", "payment_method", "type", "kind")
                     if c in p_cols), None)
        if mcol:
            pt["by_method_month"] = q(
                "SELECT to_char(created_at,'YYYY-MM') AS m, CAST(%s AS TEXT) AS method, "
                "COUNT(*) AS cnt, COALESCE(SUM(amount),0) AS total FROM payments "
                "GROUP BY 1,2 ORDER BY 1 DESC, 4 DESC LIMIT 24" % mcol)
    out["payment_types"] = pt

    # 11. рекомендации
    recs = []
    vwd = q("SELECT (EXTRACT(ISODOW FROM entry_time)::int-1) AS wd, "
            "EXTRACT(HOUR FROM entry_time)::int AS hr, COUNT(*) AS cnt FROM visits GROUP BY 1,2")
    if vwd:
        peak = max(vwd, key=lambda x: x["cnt"])
        recs.append("Пиковая загрузка: %s %d:00 (%d визитов) — усильте дежурство"
                    % (["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][peak["wd"]],
                       peak["hr"], peak["cnt"]))
    if "status" in c_cols and has_visits:
        nod = q("SELECT COUNT(*) AS cnt FROM clients c WHERE c.status='ACTIVE' "
                "AND NOT EXISTS (SELECT 1 FROM visits v WHERE v.client_id=c.id "
                "AND v.entry_time >= NOW() - interval '14 days')")
        if nod and nod[0]["cnt"]:
            recs.append("%d активных клиентов без визита >14 дней — запустите "
                        "возвратную кампанию" % nod[0]["cnt"])
    cm = out.get("churn_money_30d") or {}
    if cm.get("expected_loss"):
        recs.append("Ожидаемые потери оттока: ~%s ₽ — предложите продление группе риска"
                    % format(int(cm["expected_loss"]), ",").replace(",", " "))
    for c_ in (out.get("cohorts") or []):
        rp = c_.get("retention30_pct")
        if rp is not None and rp < 50:
            recs.append("Низкое удержание 30 дн. в когорте %s (%s%%) — проверьте онбординг"
                        % (c_["cohort"], rp))
            break
    out["recommendations"] = recs
    return out

# ═══════════════ W9: RFM, шкала посещений, отчёты по клиентам, CSAT ═══════════════
def _client_name_expr(c_cols):
    if "full_name" in c_cols:
        name_expr = "NULLIF(c.full_name,'')"
    else:
        parts = [p for p in ("last_name", "first_name", "middle_name") if p in c_cols]
        if parts:
            name_expr = "NULLIF(TRIM(CONCAT_WS(' ', %s)), '')" % ", ".join("c." + p for p in parts)
        else:
            name_expr = "NULL"
    fb = ["NULLIF(c.%s,'')" % x for x in ("phone", "email") if x in c_cols]
    if fb:
        name_expr = "COALESCE(%s, %s)" % (name_expr, ", ".join(fb))
    return "COALESCE(%s, c.id::text)" % name_expr


@router.get("/clients-rfm")
def analytics_clients_rfm(db: Session = Depends(get_db)):
    """RFM-анализ активных клиентов. Шкала 1-3: Recency 3=недавно,
    Frequency 3=часто, Monetary 1=большая сумма, 3=маленькая."""
    from sqlalchemy import text as _text

    def cols_of(tbl):
        try:
            return set(db.execute(_text(
                "SELECT column_name FROM information_schema.columns WHERE table_name=:t"),
                {"t": tbl}).scalars().all())
        except Exception:
            return set()

    def q(sql, P=None):
        try:
            return [dict(r._mapping) for r in db.execute(_text(sql), P or {}).all()]
        except Exception:
            return []

    c_cols = cols_of("clients")
    v_cols = cols_of("visits")
    p_cols = cols_of("payments")
    if not ({"client_id", "entry_time"} <= v_cols and {"client_id", "created_at", "amount"} <= p_cols):
        return {"available": False, "reason": "need visits(client_id,entry_time) and payments(client_id,created_at,amount)"}
    pay_st = " AND p.status='COMPLETED'" if "status" in p_cols else ""
    name_expr = _client_name_expr(c_cols)
    where = " WHERE c.status='ACTIVE'" if "status" in c_cols else ""
    rows = q(
        "SELECT c.id, %s AS name, "
        "(SELECT MAX(v.entry_time) FROM visits v WHERE v.client_id=c.id) AS last_v, "
        "(SELECT COUNT(*) FROM visits v WHERE v.client_id=c.id) AS freq, "
        "COALESCE((SELECT SUM(p.amount) FROM payments p WHERE p.client_id=c.id%s),0) AS mon "
        "FROM clients c%s" % (name_expr, pay_st, where))

    from datetime import datetime as _dt
    from datetime import timezone as _tz
    now = _dt.now(_tz.utc)
    for r in rows:
        r["recency_days"] = (now - r["last_v"]).days if r.get("last_v") else 9999
        r["frequency"] = int(r.get("freq") or 0)
        r["monetary"] = float(r.get("mon") or 0)

    def scores(values, hi_best=True):
        """Терцилы -> 1..3. hi_best: True => большие значения = 3."""
        n = len(values)
        if n == 0:
            return []
        order = sorted(range(n), key=lambda i: values[i], reverse=hi_best)
        out = [0] * n
        for rank, idx in enumerate(order):
            tier = 2 if rank < n / 3 else (1 if rank < 2 * n / 3 else 0)
            out[idx] = tier + 1
        return out

    n = len(rows)
    rec_s = scores([r["recency_days"] for r in rows], hi_best=False)
    fre_s = scores([r["frequency"] for r in rows], hi_best=True)
    mon_s = scores([r["monetary"] for r in rows], hi_best=True)
    mon_s = [4 - m for m in mon_s]

    dist = {"R": {1: 0, 2: 0, 3: 0}, "F": {1: 0, 2: 0, 3: 0}, "M": {1: 0, 2: 0, 3: 0}}
    cells = {}
    for i, r in enumerate(rows):
        R, F, M = rec_s[i], fre_s[i], mon_s[i]
        r["R"], r["F"], r["M"] = R, F, M
        dist["R"][R] += 1
        dist["F"][F] += 1
        dist["M"][M] += 1
        cells["%d%d%d" % (R, F, M)] = cells.get("%d%d%d" % (R, F, M), 0) + 1

    SEGMENTS = {
        "331": "Чемпионы (частые, недавние)", "332": "Чемпионы (частые, недавние)",
        "333": "Чемпионы+",
        "321": "Лояльные", "322": "Лояльные", "323": "Лояльные",
        "311": "Новички-спонсоры", "312": "Новички-спонсоры", "313": "Новички",
        "231": "В зоне риска (давно не были)", "232": "В зоне риска",
        "233": "В зоне риска", "221": "Спящие", "222": "Спящие", "223": "Спящие",
        "131": "Почти ушедшие (очень давно)", "132": "Почти ушедшие", "133": "Почти ушедшие",
        "211": "Разовые-спонсоры", "212": "Разовые", "213": "Разовые",
        "121": "Ушедшие спонсоры", "122": "Ушедшие", "123": "Ушедшие",
        "111": "Ушедшие (очень давно)", "112": "Ушедшие (очень давно)", "113": "Ушедшие (очень давно)",
    }
    segments = {}
    for i, r in enumerate(rows):
        key = "%d%d%d" % (r["R"], r["F"], r["M"])
        seg = SEGMENTS.get(key, "Прочие")
        segments.setdefault(seg, []).append(r)
    seg_summary = sorted(
        [{"segment": k, "count": len(v),
          "monetary_sum": round(sum(x["monetary"] for x in v), 2)}
         for k, v in segments.items()],
        key=lambda x: -x["count"])

    top = sorted(rows, key=lambda x: (x["R"], x["F"], x["M"]))[:10]
    return {"available": True, "total": n,
            "dist": dist, "cells27": cells,
            "segments": seg_summary,
            "top_champions": [
                {"client_id": str(r["id"]), "name": r["name"],
                 "R": r["R"], "F": r["F"], "M": r["M"],
                 "recency_days": r["recency_days"],
                 "frequency": r["frequency"], "monetary": r["monetary"]}
                for r in top]}


@router.get("/client-attendance")
def analytics_client_attendance(limit: int = 50, db: Session = Depends(get_db)):
    """Шкала посещений клиентов по ФИО: всего, за 30 дн, давность, в неделю."""
    from sqlalchemy import text as _text

    def cols_of(tbl):
        try:
            return set(db.execute(_text(
                "SELECT column_name FROM information_schema.columns WHERE table_name=:t"),
                {"t": tbl}).scalars().all())
        except Exception:
            return set()

    def q(sql, P=None):
        try:
            return [dict(r._mapping) for r in db.execute(_text(sql), P or {}).all()]
        except Exception as e:
            return [{"error": str(e)[:160]}]

    c_cols = cols_of("clients")
    v_cols = cols_of("visits")
    name_expr = _client_name_expr(c_cols)
    reg = "c.created_at" if "created_at" in c_cols else "NULL"
    if not {"client_id", "entry_time"} <= v_cols:
        return []
    rows = q(
        "SELECT c.id, %s AS name, COUNT(v.entry_time) AS visits_total, "
        "COUNT(v.entry_time) FILTER (WHERE v.entry_time >= NOW() - interval '30 days') AS visits_30d, "
        "MAX(v.entry_time) AS last_visit, %s AS registered "
        "FROM clients c LEFT JOIN visits v ON v.client_id = c.id "
        "GROUP BY c.id, %s ORDER BY visits_total DESC LIMIT :lim"
        % (name_expr, reg, name_expr),
        {"lim": min(max(int(limit or 50), 1), 500)})
    from datetime import datetime as _dt
    from datetime import timezone as _tz
    now = _dt.now(_tz.utc)
    out = []
    for r in rows:
        if "error" in r:
            return rows
        reg_d = r.get("registered")
        weeks = max(1.0, (now - reg_d).days / 7.0) if reg_d else None
        out.append({
            "client_id": str(r["id"]), "name": r["name"],
            "visits_total": int(r["visits_total"] or 0),
            "visits_30d": int(r["visits_30d"] or 0),
            "last_visit_days": (now - r["last_visit"]).days if r.get("last_visit") else None,
            "avg_per_week": round(int(r["visits_total"] or 0) / weeks, 2) if weeks else None,
        })
    return out


@router.get("/client-reports")
def analytics_client_reports(type: str = "new", date_from: str = None,
                             date_to: str = None, db: Session = Depends(get_db)):
    """Отчёты: new (новые клиенты), top (рейтинг по оплатам), lost (потерянные)."""
    from sqlalchemy import text as _text
    from datetime import date as _date, timedelta as _td

    def cols_of(tbl):
        try:
            return set(db.execute(_text(
                "SELECT column_name FROM information_schema.columns WHERE table_name=:t"),
                {"t": tbl}).scalars().all())
        except Exception:
            return set()

    def q(sql, P=None):
        try:
            return [dict(r._mapping) for r in db.execute(_text(sql), P or {}).all()]
        except Exception:
            return []

    c_cols = cols_of("clients")
    v_cols = cols_of("visits")
    p_cols = cols_of("payments")
    name_expr = _client_name_expr(c_cols)
    t = _date.today()
    d_to = date_to or t.isoformat()
    d_from = date_from or (t - _td(days=30)).isoformat()
    P = {"f": d_from, "t": d_to}

    if type == "new" and "created_at" in c_cols:
        extra = ""
        if {"client_id", "entry_time"} <= v_cols:
            extra = ", (SELECT COUNT(*) FROM visits v WHERE v.client_id=c.id) AS visits_cnt"
        mon = ""
        if {"client_id", "amount"} <= p_cols:
            st = " AND p.status='COMPLETED'" if "status" in p_cols else ""
            mon = ", COALESCE((SELECT SUM(p.amount) FROM payments p WHERE p.client_id=c.id%s),0) AS visits_sum" % st
        return q("SELECT c.id, %s AS name, c.phone, c.created_at::date AS created, "
                 "COALESCE(c.source,'') AS source%s%s FROM clients c "
                 "WHERE c.created_at::date BETWEEN :f AND :t ORDER BY c.created_at DESC"
                 % (name_expr, extra, mon), P)

    if type == "top":
        if not {"client_id", "created_at", "amount"} <= p_cols:
            return []
        st = " AND p.status='COMPLETED'" if "status" in p_cols else ""
        return q("SELECT c.id, %s AS name, c.phone, COUNT(p.id) AS payments_cnt, "
                 "COALESCE(SUM(p.amount),0) AS total, "
                 "COALESCE(AVG(p.amount),0) AS avg_check, "
                 "(SELECT MAX(v.entry_time) FROM visits v WHERE v.client_id=c.id) AS last_visit "
                 "FROM payments p JOIN clients c ON c.id = p.client_id "
                 "WHERE p.created_at::date BETWEEN :f AND :t%s "
                 "GROUP BY c.id, %s, c.phone ORDER BY total DESC LIMIT 100"
                 % (name_expr, st, name_expr), P)

    if type == "lost":
        if not {"client_id", "entry_time"} <= v_cols:
            return []
        last_expr = "(SELECT MAX(v.entry_time) FROM visits v WHERE v.client_id=c.id)"
        return q("SELECT c.id, %s AS name, c.phone, "
                 "(SELECT COUNT(*) FROM visits v WHERE v.client_id=c.id) AS visits_cnt, "
                 "%s AS last_visit FROM clients c "
                 "WHERE %s IS NOT NULL AND %s::date BETWEEN :f AND :t "
                 "ORDER BY last_visit" % (name_expr, last_expr, last_expr, last_expr), P)

    return []


@router.get("/csat/summary")
def analytics_csat_summary(db: Session = Depends(get_db)):
    from sqlalchemy import text as _text
    db.execute(_text(
        "CREATE TABLE IF NOT EXISTS csat_scores ("
        "id BIGSERIAL PRIMARY KEY, client_id TEXT, score INT NOT NULL, "
        "comment TEXT, source TEXT DEFAULT 'max', "
        "created_at TIMESTAMP DEFAULT NOW())"))
    db.commit()
    dist = {r["score"]: r["cnt"] for r in [
        dict(x._mapping) for x in db.execute(_text(
            "SELECT score, COUNT(*) AS cnt FROM csat_scores GROUP BY score")).all()]}
    avg = db.execute(_text(
        "SELECT AVG(score) AS a, COUNT(*) AS n FROM csat_scores")).first()
    monthly = [dict(r._mapping) for r in db.execute(_text(
        "SELECT to_char(created_at,'YYYY-MM') AS m, COUNT(*) AS cnt, "
        "ROUND(AVG(score),2) AS avg FROM csat_scores GROUP BY 1 ORDER BY 1 DESC LIMIT 12")).all()]
    total = (avg._mapping["n"] if avg else 0) or 0
    pos = sum(dist.get(s, 0) for s in (4, 5))
    return {"avg": round(float(avg._mapping["a"] or 0), 2) if avg else 0,
            "total": total, "csat_pct": round(pos / total * 100, 1) if total else None,
            "distribution": {str(k): dist.get(k, 0) for k in range(1, 6)},
            "monthly": monthly}


@router.post("/csat")
def analytics_csat_submit(payload: dict, db: Session = Depends(get_db)):
    from sqlalchemy import text as _text
    score = int(payload.get("score") or 0)
    if score < 1 or score > 5:
        return {"ok": False, "error": "score 1..5"}
    db.execute(_text(
        "CREATE TABLE IF NOT EXISTS csat_scores ("
        "id BIGSERIAL PRIMARY KEY, client_id TEXT, score INT NOT NULL, "
        "comment TEXT, source TEXT DEFAULT 'max', "
        "created_at TIMESTAMP DEFAULT NOW())"))
    db.execute(_text(
        "INSERT INTO csat_scores (client_id, score, comment, source) "
        "VALUES (:cid, :s, :cm, :src)"),
        {"cid": str(payload.get("client_id") or ""), "s": score,
         "cm": str(payload.get("comment") or "")[:500],
         "src": str(payload.get("source") or "max")[:30]})
    db.commit()
    return {"ok": True}


@router.get("/csat/pending")
def analytics_csat_pending(db: Session = Depends(get_db)):
    """Клиенты без оценки в текущем месяце — аудитория ежемесячного опроса."""
    from sqlalchemy import text as _text
    c_cols = set(db.execute(_text(
        "SELECT column_name FROM information_schema.columns WHERE table_name='clients'")
    ).scalars().all())
    name_expr = _client_name_expr(c_cols)
    try:
        rows = [dict(r._mapping) for r in db.execute(_text(
            "SELECT c.id, %s AS name, c.phone FROM clients c "
            "WHERE NOT EXISTS (SELECT 1 FROM csat_scores s WHERE s.client_id = c.id::text "
            "AND date_trunc('month', s.created_at) = date_trunc('month', NOW())) "
            "ORDER BY c.created_at DESC LIMIT 200" % name_expr)).all()]
        return {"pending": rows, "count": len(rows)}
    except Exception as e:
        return {"pending": [], "count": 0, "error": str(e)[:200]}

# ═══════════════ W10: ролевые блоки для дашборда (руководство/менеджеры/бухгалтерия) ═══════════════
@router.get("/roles")
def analytics_roles(db: Session = Depends(get_db)):
    """Данные для визуальных блоков: источники, оплаты, тарифы, статусы, будни, активные абонементы, тренеры."""
    from sqlalchemy import text as _text

    def cols_of(tbl):
        try:
            return set(db.execute(_text(
                "SELECT column_name FROM information_schema.columns WHERE table_name=:t"),
                {"t": tbl}).scalars().all())
        except Exception:
            return set()

    def q(sql, P=None):
        try:
            return [dict(r._mapping) for r in db.execute(_text(sql), P or {}).all()]
        except Exception:
            return []

    c_cols = cols_of("clients")
    p_cols = cols_of("payments")
    v_cols = cols_of("visits")
    s_cols = cols_of("subscriptions")
    out = {}

    if "created_at" in c_cols:
        src_col = "source" if "source" in c_cols else ("client_tag" if "client_tag" in c_cols else None)
        if src_col:
            out["new_by_source"] = q(
                "SELECT COALESCE(NULLIF(c.%s,''),'(не указан)') AS name, COUNT(*) AS cnt "
                "FROM clients c WHERE c.created_at >= NOW() - interval '30 days' "
                "GROUP BY 1 ORDER BY 2 DESC LIMIT 8" % src_col)

    if {"created_at", "amount"} <= p_cols:
        mcol = next((c for c in ("method", "payment_method", "type", "kind") if c in p_cols), None)
        if mcol:
            st = " AND status='COMPLETED'" if "status" in p_cols else ""
            out["revenue_by_method"] = q(
                "SELECT CAST(%s AS TEXT) AS name, COALESCE(SUM(amount),0) AS total, COUNT(*) AS cnt "
                "FROM payments WHERE created_at >= NOW() - interval '30 days'%s "
                "GROUP BY 1 ORDER BY 2 DESC LIMIT 8" % (mcol, st))

    t_cols = cols_of("tariffs")
    if {"tariff_id", "created_at"} <= s_cols and t_cols:
        tname = next((c for c in ("name", "title", "code") if c in t_cols), None)
        tprice = "price" if "price" in t_cols else None
        if tname:
            sel = "COALESCE(SUM(t.%s),0) AS total," % tprice if tprice else "0 AS total,"
            out["subs_by_tariff"] = q(
                "SELECT CAST(t.%s AS TEXT) AS name, COUNT(*) AS cnt, %s "
                "FROM subscriptions s JOIN tariffs t ON t.id = s.tariff_id "
                "WHERE s.created_at >= NOW() - interval '90 days' "
                "GROUP BY 1 ORDER BY 2 DESC LIMIT 10" % (tname, sel))

    if {"tariff_id", "status"} <= s_cols and "price" in t_cols:
        r = q("SELECT COALESCE(SUM(t.price),0) AS active_value, COUNT(*) AS active_cnt "
              "FROM subscriptions s JOIN tariffs t ON t.id = s.tariff_id WHERE s.status='ACTIVE'")
        out["active_subscriptions"] = r[0] if r else {}

    if "status" in c_cols:
        out["clients_by_status"] = q(
            "SELECT status AS name, COUNT(*) AS cnt FROM clients GROUP BY 1 ORDER BY 2 DESC")

    if "entry_time" in v_cols:
        out["visits_by_weekday"] = q(
            "SELECT (EXTRACT(ISODOW FROM entry_time)::int-1) AS wd, COUNT(*) AS cnt "
            "FROM visits GROUP BY 1 ORDER BY 1")

    if "status" in c_cols:
        r = q("SELECT COUNT(*) AS cnt FROM clients WHERE status IN ('DEBTOR','Должник')")
        out["debtors"] = r[0] if r else {}

    ts_cols = cols_of("trainer_sales")
    if ts_cols:
        amt = next((c for c in ("amount", "sum", "total", "value") if c in ts_cols), None)
        dcol = next((c for c in ("created_at", "date", "dt", "sale_date") if c in ts_cols), None)
        uname = next((c for c in ("trainer_name", "trainer", "user_name", "employee", "name") if c in ts_cols), None)
        if amt and dcol and uname:
            out["trainer_sales"] = q(
                "SELECT CAST(%s AS TEXT) AS name, COUNT(*) AS cnt, COALESCE(SUM(%s),0) AS total "
                "FROM trainer_sales WHERE %s >= NOW() - interval '30 days' "
                "GROUP BY 1 ORDER BY 3 DESC LIMIT 10" % (uname, amt, dcol))
    return out

@router.get("/inactive-clients")
def analytics_inactive_clients(days: int = 14, db: Session = Depends(get_db)):
    """Клиенты (ACTIVE), у которых последний визит >= days назад или визитов не было."""
    from sqlalchemy import text as _text
    c_cols = set(db.execute(_text(
        "SELECT column_name FROM information_schema.columns WHERE table_name='clients'")
    ).scalars().all())
    v_cols = set(db.execute(_text(
        "SELECT column_name FROM information_schema.columns WHERE table_name='visits'")
    ).scalars().all())
    if not {"client_id", "entry_time"} <= v_cols:
        return {"clients": []}
    name_expr = _client_name_expr(c_cols)
    where = " WHERE c.status='ACTIVE'" if "status" in c_cols else ""
    sql = (
        "SELECT c.id, %s AS name, "
        "COALESCE(EXTRACT(DAY FROM NOW() - MAX(v.entry_time))::int, 9999) AS days "
        "FROM clients c LEFT JOIN visits v ON v.client_id = c.id%s "
        "GROUP BY c.id, %s "
        "HAVING COALESCE(EXTRACT(DAY FROM NOW() - MAX(v.entry_time))::int, 9999) >= :d "
        "ORDER BY days DESC LIMIT 50" % (name_expr, where, name_expr))
    rows = db.execute(_text(sql), {"d": max(1, min(int(days or 14), 365))}).all()
    return {"clients": [{"client_id": str(r._mapping["id"]), "name": r._mapping["name"],
                         "days": r._mapping["days"]} for r in rows]}

# ═══════════════ W10: отделы сотрудников ═══════════════
@router.get("/departments")
def departments_list(db: Session = Depends(get_db)):
    from sqlalchemy import text as _text
    db.execute(_text("CREATE TABLE IF NOT EXISTS departments ("
                     "id SERIAL PRIMARY KEY, name VARCHAR(120) UNIQUE NOT NULL, "
                     "created_at TIMESTAMP DEFAULT NOW())"))
    db.commit()
    out = []
    try:
        out.extend(db.execute(_text("SELECT name FROM departments ORDER BY name")).scalars().all())
    except Exception:
        pass
    try:
        cols = set(db.execute(_text(
            "SELECT column_name FROM information_schema.columns WHERE table_name='users'")
        ).scalars().all())
        if "department" in cols:
            rows = db.execute(_text(
                "SELECT DISTINCT department FROM users "
                "WHERE department IS NOT NULL AND department <> '' ORDER BY 1")).scalars().all()
            for r in rows:
                if r not in out:
                    out.append(r)
    except Exception:
        pass
    return {"items": out}


@router.post("/departments")
def departments_add(payload: dict, db: Session = Depends(get_db)):
    from sqlalchemy import text as _text
    name = str(payload.get("name") or "").strip()
    if not name:
        return {"ok": False, "error": "name empty"}
    db.execute(_text("CREATE TABLE IF NOT EXISTS departments ("
                     "id SERIAL PRIMARY KEY, name VARCHAR(120) UNIQUE NOT NULL, "
                     "created_at TIMESTAMP DEFAULT NOW())"))
    try:
        db.execute(_text("INSERT INTO departments (name) VALUES (:n) "
                         "ON CONFLICT (name) DO NOTHING"), {"n": name[:120]})
        db.commit()
    except Exception:
        db.rollback()
    return {"ok": True}


@router.post("/users/{user_id}/department")
def user_set_department(user_id: str, payload: dict, db: Session = Depends(get_db)):
    from sqlalchemy import text as _text
    dep = str(payload.get("department") or "").strip()
    db.execute(_text("ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR(100)"))
    db.execute(_text("UPDATE users SET department = :d WHERE id::text = :i"),
               {"d": dep[:100] or None, "i": str(user_id)})
    db.commit()
    return {"ok": True}

# ═══════════════ W10: файлы клиентов (Clients/ID/Photos|Documents) ═══════════════
import os as _os
import re as _re
from fastapi import UploadFile, File, Form

CLIENTS_ROOT = "/app/static/clients"


@router.get("/clients/{cid}/files")
def client_files_list(cid: str):
    base = _os.path.join(CLIENTS_ROOT, str(cid))
    out = {"photos": [], "documents": []}
    for kind, key in (("Photos", "photos"), ("Documents", "documents")):
        d = _os.path.join(base, kind)
        if _os.path.isdir(d):
            for fn in sorted(_os.listdir(d))[:200]:
                out[key].append({"name": fn,
                                 "url": "/static/clients/%s/%s/%s" % (cid, kind, fn)})
    return out


@router.post("/clients/{cid}/files")
async def client_files_upload(cid: str, kind: str = Form("Photos"),
                              file: UploadFile = File(...)):
    safe = _re.sub(r'[^0-9A-Za-zА-Яа-яЁё_.\- ]', '_',
                   _os.path.basename(file.filename or "file"))
    kd = "Documents" if str(kind).lower().startswith("doc") else "Photos"
    d = _os.path.join(CLIENTS_ROOT, str(cid), kd)
    _os.makedirs(d, exist_ok=True)
    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        return {"ok": False, "error": "file > 20MB"}
    with open(_os.path.join(d, safe), "wb") as _f:
        _f.write(data)
    return {"ok": True, "name": safe,
            "url": "/static/clients/%s/%s/%s" % (cid, kd, safe)}


@router.delete("/clients/{cid}/files/{kind}/{name}")
def client_files_delete(cid: str, kind: str, name: str):
    safe = _re.sub(r'[^0-9A-Za-zА-Яа-яЁё_.\- ]', '_', _os.path.basename(name))
    kd = "Documents" if str(kind).lower().startswith("doc") else "Photos"
    p = _os.path.join(CLIENTS_ROOT, str(cid), kd, safe)
    try:
        if _os.path.isfile(p):
            _os.remove(p)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)[:150]}

# ═══════════════ W11: расширенная анкета клиента, контакты, автомобили ═══════════════
CLIENT_EXTRA_COLS = [
    ("passport", "VARCHAR(64)"), ("citizenship", "VARCHAR(64)"),
    ("marital_status", "VARCHAR(32)"), ("children", "VARCHAR(128)"),
    ("home_address", "VARCHAR(255)"), ("postal_address", "VARCHAR(255)"),
    ("work_company", "VARCHAR(128)"), ("work_position", "VARCHAR(128)"),
    ("contract_kind", "VARCHAR(128)"), ("discount_percent", "NUMERIC(5,2) DEFAULT 0"),
    ("blocked", "BOOLEAN DEFAULT FALSE"), ("blocked_reason", "VARCHAR(255)"),
    ("confidential", "BOOLEAN DEFAULT FALSE"), ("guest_note", "VARCHAR(255)"),
]


def _ensure_client_cols(db):
    from sqlalchemy import text as _text
    for name, typ in CLIENT_EXTRA_COLS:
        try:
            db.execute(_text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS %s %s" % (name, typ)))
        except Exception:
            pass
    db.commit()


@router.get("/clients/{cid}/profile")
def client_profile_get(cid: str, db: Session = Depends(get_db)):
    from sqlalchemy import text as _text
    _ensure_client_cols(db)
    cols = ", ".join(c for c, _ in CLIENT_EXTRA_COLS)
    row = db.execute(_text("SELECT %s FROM clients WHERE id::text = :i" % cols),
                     {"i": str(cid)}).mappings().first()
    return dict(row) if row else {}


@router.post("/clients/{cid}/profile")
def client_profile_set(cid: str, payload: dict, db: Session = Depends(get_db)):
    from sqlalchemy import text as _text
    _ensure_client_cols(db)
    allowed = {c for c, _ in CLIENT_EXTRA_COLS}
    sets, params = [], {"i": str(cid)}
    for k, v in (payload or {}).items():
        if k in allowed:
            sets.append("%s = :%s" % (k, k))
            params[k] = v
    if sets:
        db.execute(_text("UPDATE clients SET %s WHERE id::text = :i" % ", ".join(sets)), params)
        db.commit()
    return {"ok": True, "updated": len(sets)}


def _ensure_table(db, ddl):
    from sqlalchemy import text as _text
    db.execute(_text(ddl))
    db.commit()


@router.get("/clients/{cid}/contacts")
def client_contacts_get(cid: str, db: Session = Depends(get_db)):
    from sqlalchemy import text as _text
    _ensure_table(db, "CREATE TABLE IF NOT EXISTS client_contacts ("
                      "id BIGSERIAL PRIMARY KEY, client_id TEXT, kind VARCHAR(16), "
                      "type_label VARCHAR(32), value VARCHAR(160), "
                      "is_primary BOOLEAN DEFAULT FALSE, "
                      "created_at TIMESTAMP DEFAULT NOW())")
    rows = db.execute(_text(
        "SELECT id, kind, type_label, value, is_primary FROM client_contacts "
        "WHERE client_id = :i ORDER BY id"), {"i": str(cid)}).mappings().all()
    return {"items": [dict(r) for r in rows]}


@router.post("/clients/{cid}/contacts")
def client_contacts_add(cid: str, payload: dict, db: Session = Depends(get_db)):
    from sqlalchemy import text as _text
    _ensure_table(db, "CREATE TABLE IF NOT EXISTS client_contacts ("
                      "id BIGSERIAL PRIMARY KEY, client_id TEXT, kind VARCHAR(16), "
                      "type_label VARCHAR(32), value VARCHAR(160), "
                      "is_primary BOOLEAN DEFAULT FALSE, "
                      "created_at TIMESTAMP DEFAULT NOW())")
    kind = str(payload.get("kind") or "phone")[:16]
    db.execute(_text(
        "INSERT INTO client_contacts (client_id, kind, type_label, value, is_primary) "
        "VALUES (:i, :k, :t, :v, :p)"),
        {"i": str(cid), "k": kind, "t": str(payload.get("type_label") or "")[:32],
         "v": str(payload.get("value") or "")[:160],
         "p": bool(payload.get("is_primary"))})
    db.commit()
    return {"ok": True}


@router.delete("/clients/{cid}/contacts/{cid2}")
def client_contacts_del(cid: str, cid2: int, db: Session = Depends(get_db)):
    from sqlalchemy import text as _text
    db.execute(_text("DELETE FROM client_contacts WHERE id = :n AND client_id = :i"),
               {"n": int(cid2), "i": str(cid)})
    db.commit()
    return {"ok": True}


@router.get("/clients/{cid}/cars")
def client_cars_get(cid: str, db: Session = Depends(get_db)):
    from sqlalchemy import text as _text
    _ensure_table(db, "CREATE TABLE IF NOT EXISTS client_cars ("
                      "id BIGSERIAL PRIMARY KEY, client_id TEXT, mark VARCHAR(64), "
                      "number VARCHAR(32), note VARCHAR(160), "
                      "created_at TIMESTAMP DEFAULT NOW())")
    rows = db.execute(_text(
        "SELECT id, mark, number, note FROM client_cars WHERE client_id = :i ORDER BY id"),
        {"i": str(cid)}).mappings().all()
    return {"items": [dict(r) for r in rows]}


@router.post("/clients/{cid}/cars")
def client_cars_add(cid: str, payload: dict, db: Session = Depends(get_db)):
    from sqlalchemy import text as _text
    _ensure_table(db, "CREATE TABLE IF NOT EXISTS client_cars ("
                      "id BIGSERIAL PRIMARY KEY, client_id TEXT, mark VARCHAR(64), "
                      "number VARCHAR(32), note VARCHAR(160), "
                      "created_at TIMESTAMP DEFAULT NOW())")
    db.execute(_text(
        "INSERT INTO client_cars (client_id, mark, number, note) VALUES (:i, :m, :n, :t)"),
        {"i": str(cid), "m": str(payload.get("mark") or "")[:64],
         "n": str(payload.get("number") or "")[:32],
         "t": str(payload.get("note") or "")[:160]})
    db.commit()
    return {"ok": True}


@router.delete("/clients/{cid}/cars/{cid2}")
def client_cars_del(cid: str, cid2: int, db: Session = Depends(get_db)):
    from sqlalchemy import text as _text
    db.execute(_text("DELETE FROM client_cars WHERE id = :n AND client_id = :i"),
               {"n": int(cid2), "i": str(cid)})
    db.commit()
    return {"ok": True}

# ═══════════════ W11: лицевой счёт (пополнение/списание/история) ═══════════════
import uuid as _uuid


def _ensure_wallet(db):
    from sqlalchemy import text as _text
    try:
        db.execute(_text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS wallet_balance NUMERIC(12,2) DEFAULT 0"))
    except Exception:
        pass
    db.execute(_text("CREATE TABLE IF NOT EXISTS wallet_ops ("
                     "id TEXT PRIMARY KEY, client_id TEXT, delta NUMERIC(12,2), "
                     "balance_after NUMERIC(12,2), comment TEXT, created_by TEXT, "
                     "created_at TIMESTAMP DEFAULT NOW())"))
    db.commit()


@router.get("/clients/{cid}/wallet")
def wallet_get(cid: str, db: Session = Depends(get_db)):
    from sqlalchemy import text as _text
    _ensure_wallet(db)
    bal = db.execute(_text(
        "SELECT wallet_balance FROM clients WHERE id::text = :i"), {"i": str(cid)}).scalar()
    ops = db.execute(_text(
        "SELECT id, delta, balance_after, comment, created_by, created_at "
        "FROM wallet_ops WHERE client_id = :i ORDER BY created_at DESC LIMIT 100"),
        {"i": str(cid)}).mappings().all()
    return {"balance": float(bal or 0),
            "operations": [dict(r) for r in ops]}


@router.post("/clients/{cid}/wallet")
def wallet_op(cid: str, payload: dict, db: Session = Depends(get_db)):
    from sqlalchemy import text as _text
    _ensure_wallet(db)
    try:
        delta = abs(float(payload.get("amount") or 0))
    except Exception:
        return {"ok": False, "error": "amount"}
    if not delta:
        return {"ok": False, "error": "amount"}
    if str(payload.get("direction") or "in") == "out":
        delta = -delta
    row = db.execute(_text(
        "SELECT wallet_balance FROM clients WHERE id::text = :i"), {"i": str(cid)}).first()
    if not row:
        return {"ok": False, "error": "client not found"}
    new_bal = float(row[0] or 0) + delta
    if new_bal < 0:
        return {"ok": False, "error": "Недостаточно средств (баланс %.2f)" % float(row[0] or 0)}
    db.execute(_text("UPDATE clients SET wallet_balance = :b WHERE id::text = :i"),
               {"b": new_bal, "i": str(cid)})
    db.execute(_text(
        "INSERT INTO wallet_ops (id, client_id, delta, balance_after, comment, created_by) "
        "VALUES (:id, :i, :d, :b, :c, :u)"),
        {"id": str(_uuid.uuid4()), "i": str(cid), "d": delta, "b": new_bal,
         "c": str(payload.get("comment") or "")[:200],
         "u": str(payload.get("created_by") or "admin")[:64]})
    db.commit()
    return {"ok": True, "balance": new_bal}
    

# ═══════════════ W12: безопасное медиа-хранилище (envelope encryption, tenant-aware) ═══════════════
import base64 as _b64
import hashlib as _hl
import hmac as _hm
import io as _io
import os as _os
import uuid as _uuid
from fastapi import UploadFile, File, Form, Request, Header, Depends as _Depends
from fastapi.responses import JSONResponse as _JSON

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _AESGCM
except Exception:
    _AESGCM = None

MEDIA_ROOT = "/srv/media"
DEFAULT_TENANT = "t-1"


def _load_kek() -> bytes:
    path = _os.environ.get("MEDIA_MASTER_KEY_FILE", "/run/secrets/media_master_key")
    try:
        raw = open(path, "rb").read().strip()
        key = _b64.b64decode(raw)
        if len(key) == 32:
            return key
    except Exception:
        pass
    return _hl.sha256(b"fitintel-dev-media-key-change-me").digest()


_KEK = _load_kek()
_SIG_KEY = _hl.sha256(_KEK + b":urlsig").digest()


def _tenant() -> str:
    return DEFAULT_TENANT


def _sign(file_id: str, exp: int) -> str:
    return _hm.new(_SIG_KEY, ("%s:%d" % (file_id, exp)).encode(), _hl.sha256).hexdigest()


def _check_sig(file_id: str, sig: str, exp: int) -> bool:
    try:
        if int(exp) < int(__import__("time").time()):
            return False
        return _hm.compare_digest(_sign(file_id, int(exp)), str(sig or ""))
    except Exception:
        return False


def _encrypt(data: bytes, aad: bytes):
    dek = _AESGCM.generate_key(bit_length=256)
    fn = _os.urandom(12)
    ct = _AESGCM(dek).encrypt(fn, data, aad)
    kn = _os.urandom(12)
    edek = _AESGCM(_KEK).encrypt(kn, dek, None)
    return (ct, _b64.b64encode(edek).decode(), _b64.b64encode(kn).decode(),
            _b64.b64encode(fn).decode())


def _decrypt(ct: bytes, edek: str, kn: str, fn: str, aad: bytes) -> bytes:
    dek = _AESGCM(_KEK).decrypt(_b64.b64decode(kn), _b64.b64decode(edek), None)
    return _AESGCM(dek).decrypt(_b64.b64decode(fn), ct, aad)


def _strip_image(data: bytes, mime: str) -> tuple:
    if not mime.startswith("image/"):
        return data, mime
    try:
        from PIL import Image as _Img
        im = _Img.open(_io.BytesIO(data))
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        buf = _io.BytesIO()
        im.save(buf, format="JPEG", quality=88)
        return buf.getvalue(), "image/jpeg"
    except Exception:
        return data, mime


def _ensure_media(db):
    from sqlalchemy import text as _text
    db.execute(_text("""CREATE TABLE IF NOT EXISTS media_files (
        id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL DEFAULT 't-1',
        owner_type TEXT NOT NULL, owner_id TEXT NOT NULL,
        photo_type TEXT NOT NULL DEFAULT 'document',
        orig_name TEXT, mime TEXT, size BIGINT, sha256 TEXT,
        dek_enc TEXT, dek_nonce TEXT, file_nonce TEXT,
        key_version INT DEFAULT 1, path TEXT, legacy_path TEXT,
        created_by TEXT, created_at TIMESTAMP DEFAULT NOW(),
        archived_at TIMESTAMP)"""))
    db.execute(_text("CREATE INDEX IF NOT EXISTS idx_media_owner ON media_files (tenant_id, owner_type, owner_id)"))
    db.execute(_text("""CREATE TABLE IF NOT EXISTS media_access_log (
        id BIGSERIAL PRIMARY KEY, file_id TEXT, user_id TEXT, user_role TEXT,
        session_id TEXT, owner_id TEXT, action TEXT, result TEXT,
        ip TEXT, user_agent TEXT, reason TEXT,
        created_at TIMESTAMP DEFAULT NOW())"""))
    db.execute(_text("""CREATE OR REPLACE FUNCTION media_log_immutable() RETURNS TRIGGER AS $$
        BEGIN RAISE EXCEPTION 'media_access_log is append-only: % not allowed', TG_OP; RETURN NULL; END;
        $$ LANGUAGE plpgsql"""))
    db.execute(_text("""DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'media_log_no_update') THEN
                CREATE TRIGGER media_log_no_update BEFORE UPDATE OR DELETE ON media_access_log
                FOR EACH ROW EXECUTE FUNCTION media_log_immutable();
            END IF;
        END $$"""))
    db.commit()


def _audit(db, file_id, action, result, request, user=None, owner_id="", reason=None):
    try:
        from sqlalchemy import text as _text
        uid, role = "", ""
        if user is not None:
            uid = str(user.get("sub", "")) if isinstance(user, dict) else str(getattr(user, "id", ""))
        db.execute(_text(
            "INSERT INTO media_access_log (file_id, user_id, user_role, session_id, owner_id, "
            "action, result, ip, user_agent, reason) VALUES (:f, :u, :r, :s, :o, :a, :res, :ip, :ua, :rs)"),
            {"f": str(file_id or ""), "u": uid, "r": role, "s": "", "o": str(owner_id or ""),
             "a": action, "res": result,
             "ip": (request.client.host if request and request.client else ""),
             "ua": (request.headers.get("user-agent", "")[:200] if request else ""),
             "rs": (str(reason)[:255] if reason else None)})
        db.commit()
    except Exception:
        pass


def _bearer_user(authorization: str):
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        import jwt as _jwt
        from app.core.config import settings
        return _jwt.decode(authorization.split(None, 1)[1], settings.SECRET_KEY, algorithms=["HS256"])
    except Exception:
        return None


@router.get("/media")
def media_list(owner_type: str = "client", owner_id: str = "", request: Request = None,
               db: Session = _Depends(get_db), authorization: str = Header(None)):
    _ensure_media(db)
    user = _bearer_user(authorization)
    if user is None:
        return {"items": [], "error": "auth required"}
    from sqlalchemy import text as _text
    rows = db.execute(_text(
        "SELECT id, orig_name, mime, size, photo_type, created_at FROM media_files "
        "WHERE tenant_id = :t AND owner_type = :ot AND owner_id = :oi AND archived_at IS NULL "
        "ORDER BY created_at DESC LIMIT 300"),
        {"t": _tenant(), "ot": owner_type, "oi": str(owner_id)}).mappings().all()
    import time as _time
    items = []
    for r in rows:
        exp = int(_time.time()) + 300
        items.append({"id": r["id"], "orig_name": r["orig_name"], "mime": r["mime"],
                      "size": r["size"], "photo_type": r["photo_type"],
                      "created_at": str(r["created_at"]),
                      "url": "/api/v1/analytics/media/%s/content?sig=%s&exp=%d" % (r["id"], _sign(r["id"], exp), exp)})
    _audit(db, "", "list", "ok", request, user, owner_id)
    return {"items": items}


@router.post("/media/upload")
async def media_upload(request: Request, file: UploadFile = File(...),
                       owner_type: str = Form("client"), owner_id: str = Form(""),
                       photo_type: str = Form("document"),
                       db: Session = _Depends(get_db), authorization: str = Header(None)):
    _ensure_media(db)
    user = _bearer_user(authorization)
    if user is None:
        return {"ok": False, "error": "auth required"}
    if _AESGCM is None:
        return {"ok": False, "error": "cryptography not installed"}
    raw = await file.read()
    if len(raw) > 20 * 1024 * 1024:
        return {"ok": False, "error": "file > 20MB"}
    mime = str(file.content_type or "application/octet-stream")
    ext = _os.path.splitext(file.filename or "")[1].lower()
    if mime.startswith("image/") and ext not in (".jpg", ".jpeg", ".png", ".webp"):
        return {"ok": False, "error": "bad image ext"}
    data, mime = _strip_image(raw, mime)
    fid = _uuid.uuid4().hex
    aad = ("tenant:%s:%s:%s:%s" % (_tenant(), owner_type, owner_id, fid)).encode()
    ct, edek, kn, fn = _encrypt(data, aad)
    sha = _hl.sha256(data).hexdigest()
    rel = "%s/%s/%s/%s.enc" % (_tenant(), owner_type, str(owner_id), fid)
    dest = _os.path.join(MEDIA_ROOT, rel)
    _os.makedirs(_os.path.dirname(dest), exist_ok=True)
    with open(dest + ".tmp", "wb") as f:
        f.write(ct)
    _os.replace(dest + ".tmp", dest)
    from sqlalchemy import text as _text
    db.execute(_text(
        "INSERT INTO media_files (id, tenant_id, owner_type, owner_id, photo_type, orig_name, "
        "mime, size, sha256, dek_enc, dek_nonce, file_nonce, key_version, path, created_by) "
        "VALUES (:id, :t, :ot, :oi, :pt, :on, :m, :s, :sh, :de, :kn, :fn, 1, :p, :cb)"),
        {"id": fid, "t": _tenant(), "ot": owner_type, "oi": str(owner_id),
         "pt": str(photo_type)[:32], "on": _os.path.basename(file.filename or "")[:200],
         "m": mime, "s": len(data), "sh": sha, "de": edek, "kn": kn, "fn": fn,
         "p": rel, "cb": str(user.get("sub", ""))[:64]})
    db.commit()
    _audit(db, fid, "upload", "ok", request, user, owner_id)
    import time as _time
    exp = int(_time.time()) + 300
    return {"ok": True, "id": fid,
            "url": "/api/v1/analytics/media/%s/content?sig=%s&exp=%d" % (fid, _sign(fid, exp), exp)}


@router.get("/media/{file_id}/content")
def media_content(file_id: str, request: Request, sig: str = None, exp: int = None,
                  reason: str = None, db: Session = _Depends(get_db),
                  authorization: str = Header(None)):
    _ensure_media(db)
    user = _bearer_user(authorization)
    if user is None and not (sig and _check_sig(file_id, sig, exp)):
        _audit(db, file_id, "view", "denied_401", request, user)
        return _JSON({"error": "auth_required"}, status_code=401)
    from sqlalchemy import text as _text
    r = db.execute(_text(
        "SELECT * FROM media_files WHERE id = :i AND tenant_id = :t AND archived_at IS NULL"),
        {"i": file_id, "t": _tenant()}).mappings().first()
    if not r:
        _audit(db, file_id, "view", "not_found_404", request, user)
        return _JSON({"error": "not_found"}, status_code=404)
    try:
        with open(_os.path.join(MEDIA_ROOT, r["path"]), "rb") as f:
            ct = f.read()
        aad = ("tenant:%s:%s:%s:%s" % (_tenant(), r["owner_type"], r["owner_id"], file_id)).encode()
        data = _decrypt(ct, r["dek_enc"], r["dek_nonce"], r["file_nonce"], aad)
    except Exception:
        _audit(db, file_id, "view", "error_500", request, user, r.get("owner_id"))
        return _JSON({"error": "decrypt_failed"}, status_code=500)
    _audit(db, file_id, "view", "ok", request, user, r.get("owner_id"), reason)
    from fastapi.responses import Response as _Resp
    return _Resp(content=data, media_type=r["mime"] or "application/octet-stream")


@router.delete("/media/{file_id}")
def media_delete(file_id: str, request: Request, db: Session = _Depends(get_db),
                 authorization: str = Header(None)):
    _ensure_media(db)
    user = _bearer_user(authorization)
    if user is None:
        return {"ok": False, "error": "auth required"}
    from sqlalchemy import text as _text
    db.execute(_text("UPDATE media_files SET archived_at = NOW() WHERE id = :i AND tenant_id = :t"),
               {"i": file_id, "t": _tenant()})
    db.commit()
    _audit(db, file_id, "delete", "ok", request, user)
    return {"ok": True}    