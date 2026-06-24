# fix_sse_real_data.py
with open('app/api/v1/sse.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''async def event_generator(club_id: int):
    """Генератор SSE-событий для live dashboard (E17)"""
    while True:
        # Собираем данные
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "club_id": club_id,
            "attendance_now": 0,  # Будет из БД
            "revenue_today": 0,
            "churn_alert": False,
        }
        
        yield f"data: {json.dumps(data, ensure_ascii=False)}\\n\\n"
        await asyncio.sleep(30)  # 30 сек интервал'''

new = '''async def event_generator(club_id: int, db):
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
            
            yield f"data: {json.dumps(data, ensure_ascii=False)}\\n\\n"
            await asyncio.sleep(30)
    finally:
        db.close()'''

if old in content:
    content = content.replace(old, new)
    
    # Исправляем вызов
    content = content.replace(
        '''return StreamingResponse(
        event_generator(club_id),''',
        '''return StreamingResponse(
        event_generator(club_id, db),'''
    )
    
    with open('app/api/v1/sse.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SSE с реальными данными!")
else:
    print("ERROR")
