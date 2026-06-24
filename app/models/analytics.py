# app/models/analytics.py
from datetime import datetime, timezone
from sqlalchemy import String, Numeric, Date, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AnalyticsDaily(Base):
    """Ежедневные агрегаты аналитики (E16)"""

    __tablename__ = "analytics_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    club_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    metric: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    forecast: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
