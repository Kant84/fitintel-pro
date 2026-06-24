import json

# Переписываем chart endpoint полностью
chart_code = '''
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/chart", response_class=HTMLResponse)
def analytics_chart(
    club_id: int = 1,
    metric: str = "attendance",
    db: Session = Depends(get_db),
):
    """График аналитики с прогнозом (TS-010) — Chart.js"""
    
    service = AnalyticsService(db)
    result = service.forecast(club_id, metric, 7)
    
    # Формируем данные через json.dumps (None -> null)
    history_labels = [str(p["date"]) for p in result["history"]]
    history_values = [p["value"] for p in result["history"]]
    forecast_labels = [str(p["date"]) for p in result["forecast"]]
    forecast_values = [p["value"] for p in result["forecast"]]
    
    all_labels = history_labels + forecast_labels
    history_data = history_values + [None] * len(forecast_values)
    forecast_data = [None] * (len(history_values) - 1) + [history_values[-1] if history_values else 0] + forecast_values
    
    labels_json = json.dumps(all_labels, ensure_ascii=False)
    history_json = json.dumps(history_data, ensure_ascii=False)
    forecast_json = json.dumps(forecast_data, ensure_ascii=False)
    
    html = f\"\"\"<!DOCTYPE html>
<html>
<head>
    <title>FitIntel PRO — Аналитика</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }}
        h1 {{ color: #1F4E78; }}
        .stats {{ display: flex; gap: 20px; margin-bottom: 20px; }}
        .stat-box {{ background: #e8f4f8; padding: 15px; border-radius: 8px; flex: 1; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #1F4E78; }}
        .trend-up {{ color: green; }} .trend-down {{ color: red; }} .trend-stable {{ color: orange; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>FitIntel PRO — Аналитика: {metric}</h1>
        <div class="stats">
            <div class="stat-box">
                <div>Тренд</div>
                <div class="stat-value trend-{result["trend"].lower()}">{result["trend"]}</div>
            </div>
            <div class="stat-box">
                <div>Рекомендация</div>
                <div style="font-size: 14px;">{result["recommendation"]}</div>
            </div>
        </div>
        <canvas id="chart" width="800" height="400"></canvas>
    </div>
    <script>
        const ctx = document.getElementById('chart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {labels_json},
                datasets: [
                    {{
                        label: 'Факт',
                        data: {history_json},
                        borderColor: '#8884d8',
                        backgroundColor: '#8884d8',
                        fill: false,
                        tension: 0.1
                    }},
                    {{
                        label: 'Прогноз',
                        data: {forecast_json},
                        borderColor: '#82ca9d',
                        backgroundColor: '#82ca9d',
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.1
                    }}
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{ display: true, text: '{metric} — История и прогноз' }}
                }},
                scales: {{ y: {{ beginAtZero: true }} }}
            }}
        }});
    </script>
</body>
</html>\"\"\"
    
    return html
'''

with open('app/api/v1/analytics_chart.py', 'w', encoding='utf-8') as f:
    f.write(chart_code)

print("Chart fixed with json.dumps!")
