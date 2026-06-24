# fix_chart_js.py
with open('app/api/v1/analytics_chart.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем None на null в JS
content = content.replace('[None] * len(forecast_values)', '[null] * len(forecast_values)')
content = content.replace('[None] * (todayIndex - 1)', '[null] * (todayIndex - 1)')

with open('app/api/v1/analytics_chart.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Chart.js fixed: None -> null")
