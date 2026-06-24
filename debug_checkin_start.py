# debug_checkin_start.py
with open('app/api/v1/visits.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_start = '''def check_in(
    payload: VisitEntryRequest,
    current_user=Depends(require_permission("visits.create")),
    db: Session = Depends(get_db),
):
    """
    Алиас для /entry — регистрация входа клиента.
    """'''

new_start = '''def check_in(
    payload: VisitEntryRequest,
    current_user=Depends(require_permission("visits.create")),
    db: Session = Depends(get_db),
):
    """
    Алиас для /entry — регистрация входа клиента.
    """
    print(f"DEBUG check_in STARTED: {payload.model_dump()}")'''

if old_start in content:
    content = content.replace(old_start, new_start)
    with open('app/api/v1/visits.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("DEBUG добавлен в начало check_in!")
else:
    print("ERROR: Не найден check_in")
