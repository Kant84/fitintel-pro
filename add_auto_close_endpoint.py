# add_auto_close_endpoint.py
with open('app/api/v1/visits.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем в конец файла
auto_close_endpoint = '''


# ==========================================================
# АВТО-ЗАКРЫТИЕ ПОСЕЩЕНИЙ (E8.11)
# ==========================================================
@router.post(
    "/auto-close",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
def auto_close_visits(
    days_threshold: int = Query(default=1, ge=1, le=30, description="Закрыть посещения старше N дней"),
    current_user=Depends(require_permission("visits.update")),
    db: Session = Depends(get_db),
):
    """
    Авто-закрытие незавершённых посещений.
    
    Закрывает посещения, где клиент вошёл, но не вышел,
    и прошло более N дней.
    """
    service = VisitService(db)
    closed_count = service.close_incomplete_visits(days_threshold=days_threshold)
    return {
        "closed_count": closed_count,
        "message": f"Закрыто {closed_count} незавершённых посещений",
    }
'''

content = content + auto_close_endpoint

with open('app/api/v1/visits.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Endpoint /auto-close добавлен в конец файла!")
