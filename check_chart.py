import requests

headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3ZGIwN2E0Yy0wYmY5LTRhNTctYmQ5Zi05ZjA4OGJhMTU3ODMiLCJleHAiOjE3ODIzMzk3NTcsInRva2VuX3R5cGUiOiJhY2Nlc3MifQ.OGXglTspyz1E4drT2Zd6ogMAfqR73ay6CuJ9TVlquU8"}
r = requests.get("http://localhost:8001/api/v1/analytics/dashboard-chart?club_id=1", headers=headers)

# Ищем данные в HTML
html = r.text
import re

# Находим labels
labels_match = re.search(r'labels: (\[.*?\])', html, re.DOTALL)
if labels_match:
    print("Labels found:", labels_match.group(1)[:100])

# Находим данные
data_match = re.search(r'data: (\[.*?\])', html, re.DOTALL)
if data_match:
    print("Data found:", data_match.group(1)[:100])

# Находим прогноз
forecast_match = re.search(r'Прогноз тренда', html)
if forecast_match:
    print("Forecast section found!")

print("HTML length:", len(html))
print("Chart.js found:", "chart.js" in html.lower())
