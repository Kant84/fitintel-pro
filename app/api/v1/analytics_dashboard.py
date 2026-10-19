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