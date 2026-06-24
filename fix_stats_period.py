# fix_stats_period.py
with open('app/api/v1/visits.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_stats = '''@router.get("/stats", response_model=dict)
def get_visit_stats(
    current_user=Depends(require_permission("visits.read")),
    db: Session = Depends(get_db),
):
    """Статистика посещений"""
    visit_service = VisitService(db)
    
    # Получаем все посещения
    visits = visit_service.list_all(limit=10000, offset=0)
    
    # Считаем статистику
    total = len(visits)
    active = sum(1 for v in visits if v.status == "ACTIVE")
    completed = sum(1 for v in visits if v.status == "COMPLETED")
    denied = sum(1 for v in visits if v.access_granted == False)
    
    return {
        "total_visits": total,
        "active_visits": active,
        "completed_visits": completed,
        "denied_visits": denied,
        "today_visits": sum(1 for v in visits if v.entry_time and v.entry_time.date() == datetime.now().date()),
    }'''

new_stats = '''@router.get("/stats", response_model=dict)
def get_visit_stats(
    date_from: str | None = Query(default=None, description="Дата начала периода (YYYY-MM-DD)"),
    date_to: str | None = Query(default=None, description="Дата конца периода (YYYY-MM-DD)"),
    current_user=Depends(require_permission("visits.read")),
    db: Session = Depends(get_db),
):
    """Статистика посещений с выбором периода"""
    from datetime import datetime, date
    visit_service = VisitService(db)
    
    # Получаем все посещения
    visits = visit_service.list_all(limit=10000, offset=0)
    
    # Фильтруем по периоду
    if date_from:
        from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
        visits = [v for v in visits if v.entry_time and v.entry_time.date() >= from_date]
    
    if date_to:
        to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
        visits = [v for v in visits if v.entry_time and v.entry_time.date() <= to_date]
    
    # Считаем статистику
    total = len(visits)
    active = sum(1 for v in visits if v.status == "ACTIVE")
    completed = sum(1 for v in visits if v.status == "COMPLETED")
    denied = sum(1 for v in visits if v.access_granted == False)
    
    return {
        "total_visits": total,
        "active_visits": active,
        "completed_visits": completed,
        "denied_visits": denied,
        "period": {
            "date_from": date_from,
            "date_to": date_to,
        },
    }'''

if old_stats in content:
    content = content.replace(old_stats, new_stats)
    with open('app/api/v1/visits.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Статистика с периодом добавлена!")
else:
    print("Не найден старый /stats")
