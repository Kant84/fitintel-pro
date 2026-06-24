# fix_chart_no_auth.py
with open('app/api/v1/analytics_chart.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''@router.get("/chart", response_class=HTMLResponse)
def analytics_chart(
    club_id: int = 1,
    metric: str = "attendance",
    token: str = "",
    db: Session = Depends(get_db),
):
    # Проверяем токен из query-параметра
    from app.api.dependencies import get_current_user
    from fastapi import HTTPException, status
    try:
        current_user = get_current_user(token=token, db=db)
    except Exception:
        return "<h1>Ошибка авторизации</h1><p>Передайте ?token=ВАШ_JWT_ТОКЕН</p>"'''

new = '''@router.get("/chart", response_class=HTMLResponse)
def analytics_chart(
    club_id: int = 1,
    metric: str = "attendance",
    db: Session = Depends(get_db),
):'''

if old in content:
    content = content.replace(old, new)
    with open('app/api/v1/analytics_chart.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Chart auth removed!")
else:
    print("ERROR")
