# app/schemas/analytics.py
from datetime import datetime, date
from typing import Literal
from pydantic import BaseModel, Field


class DashboardStats(BaseModel):
    attendance_today: int = Field(description="Посещений сегодня")
    revenue_today: float = Field(description="Выручка сегодня")
    forecast_week_revenue: float = Field(description="Прогноз выручки на неделю")
    churn_risk_count: int = Field(description="Клиентов с риском оттока")
    vs_last_week: float = Field(description="Изменение vs прошлая неделя %")


class ForecastRequest(BaseModel):
    metric: Literal["attendance", "revenue", "new_clients", "churn_risk"] = Field(description="Метрика")
    days_ahead: int = Field(default=7, ge=1, le=30, description="Дней вперед")


class ForecastPoint(BaseModel):
    date: date
    value: float
    is_forecast: bool = True


class MLFeatures(BaseModel):
    """ML-фичи для мультифакторного прогноза"""
    base: float = 0.0
    trend: float = 0.0
    season: str = "neutral"
    season_mult: float = 1.0
    payday_boost: float = 1.0
    weekend_boost: float = 1.0
    lag_7: int = 0
    rolling_7: float = 0.0


class ForecastResponse(BaseModel):
    metric: str
    history: list[ForecastPoint]
    forecast: list[ForecastPoint]
    trend: Literal["UP", "DOWN", "STABLE", "UNKNOWN"]
    recommendation: str
    ml_features: MLFeatures | None = None


class RecalcResponse(BaseModel):
    success: bool
    message: str
    date: date
    metrics_updated: list[str]


class AnalyticsDailyResponse(BaseModel):
    id: int
    club_id: int
    metric: str
    date: date
    value: float
    forecast: float | None
    created_at: datetime

    class Config:
        from_attributes = True
