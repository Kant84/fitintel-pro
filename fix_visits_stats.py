# fix_visits_stats.py
with open('app/api/v1/visits.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'def get_visit_stats' not in content:
    # Находим последний endpoint и добавляем после него
    insert_point = content.find('# ============================================================')
    if insert_point == -1:
        insert_point = len(content)
    
    new_endpoint = '''

# ============================================================
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
    content = content[:insert_point] + new_endpoint + content[insert_point:]
    
    # Добавляем импорт datetime
    if 'from datetime import datetime' not in content:
        content = content.replace(
            'from app.db.session import get_db',
            'from datetime import datetime\nfrom app.db.session import get_db'
        )
    
    with open('app/api/v1/visits.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("GET /visits/stats добавлен!")
else:
    print("GET /visits/stats уже существует")
