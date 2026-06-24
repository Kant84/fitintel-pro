# fix_schema_ml.py
with open('app/schemas/analytics.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''class ForecastResponse(BaseModel):
    """Ответ прогноза (E16)"""
    metric: str
    history: list[ForecastPoint]
    forecast: list[ForecastPoint]
    trend: Literal["UP", "DOWN", "STABLE", "UNKNOWN"]
    recommendation: str'''

new = '''class MLFeatures(BaseModel):
    """ML-фичи для прогноза"""
    base: float
    trend: float
    season: str
    season_mult: float
    payday_boost: float
    weekend_boost: float
    lag_7: int
    rolling_7: float

class ForecastResponse(BaseModel):
    """Ответ прогноза (E16)"""
    metric: str
    history: list[ForecastPoint]
    forecast: list[ForecastPoint]
    trend: Literal["UP", "DOWN", "STABLE", "UNKNOWN"]
    recommendation: str
    ml_features: MLFeatures | None = None'''

if old in content:
    content = content.replace(old, new)
    with open('app/schemas/analytics.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Schema updated with ml_features!")
else:
    print("ERROR")
