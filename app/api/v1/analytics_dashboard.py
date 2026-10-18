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