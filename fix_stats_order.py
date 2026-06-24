# fix_stats_order.py
with open('app/api/v1/visits.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Удаляем старый /stats endpoint
old_stats = '''# ============================================================
# Статистика посещений
# ============================================================
@router.get("/stats", response_model=dict)
def get_visit_stats(
    current_user=Depends(require_permission("visits.read")),
    db: Session = Depends(get_db),
):
    """Статистика посещений"""
    visit_service = VisitService(db)
    
    # Получаем все посещения
    visits = visit_service.list_visits(offset=0, limit=10000, actor_user_id=current_user.id)
    
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
    }


'''

if old_stats in content:
    content = content.replace(old_stats, '')
    
    # Вставляем ПЕРЕД /{visit_id}
    insert_point = content.find('@router.get(\n    "/{visit_id}"')
    if insert_point != -1:
        new_stats = '''# ============================================================
# Статистика посещений
# ============================================================
@router.get("/stats", response_model=dict)
def get_visit_stats(
    current_user=Depends(require_permission("visits.read")),
    db: Session = Depends(get_db),
):
    """Статистика посещений"""
    visit_service = VisitService(db)
    
    # Получаем все посещения
    visits = visit_service.list_visits(offset=0, limit=10000, actor_user_id=current_user.id)
    
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
    }


'''
        content = content[:insert_point] + new_stats + content[insert_point:]
        
        with open('app/api/v1/visits.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("/stats перемещён ДО /{visit_id}!")
    else:
        print("Не найдено место для вставки")
else:
    print("Не найден старый /stats")
