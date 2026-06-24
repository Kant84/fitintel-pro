# app/api/v1/sse.py
import asyncio
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/sse", tags=["SSE"])


async def event_generator(club_id: int):
    """Генератор SSE-событий для live dashboard (E17)"""
    from app.services.analytics_service import AnalyticsService
    from app.db.session import SessionLocal
    
    db = SessionLocal()
    try:
        while True:
            service = AnalyticsService(db)
            stats = service.dashboard(club_id)
            
            data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "club_id": club_id,
                "attendance_now": stats["attendance_today"],
                "revenue_today": stats["revenue_today"],
                "churn_alert": stats["churn_risk_count"] > 5,
            }
            
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            await asyncio.sleep(30)
    finally:
        db.close()


@router.get("/live/{club_id}")
async def sse_live(club_id: int, request: Request):
    """SSE поток real-time данных (E17)"""
    return StreamingResponse(
        event_generator(club_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
