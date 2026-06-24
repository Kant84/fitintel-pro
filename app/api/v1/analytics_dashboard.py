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
