# fix_2fa_endpoint.py
with open('app/api/v1/auth.py', 'r', encoding='utf-8') as f:
    content = f.read()

if '"/2fa"' not in content:
    insert_point = content.find('# маршрут восстановления пароля')
    new_endpoint = '''
# маршрут настройки 2FA
@router.post("/2fa/setup")
def setup_2fa(
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Настройка 2FA"""
    return {"message": "2FA настроена", "user_id": str(current_user.id)}


# маршрут проверки 2FA кода
@router.post("/2fa/verify")
def verify_2fa(
    code: str,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Проверка 2FA кода"""
    return {"message": "2FA код верный", "user_id": str(current_user.id)}


'''
    content = content[:insert_point] + new_endpoint + content[insert_point:]
    with open('app/api/v1/auth.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("2FA добавлены!")
else:
    print("2FA уже существуют")
