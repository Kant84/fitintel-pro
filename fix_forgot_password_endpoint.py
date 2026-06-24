# fix_forgot_password_endpoint.py
with open('app/api/v1/auth.py', 'r', encoding='utf-8') as f:
    content = f.read()

if '"/forgot-password"' not in content:
    insert_point = content.find('# маршрут подтверждения email')
    new_endpoint = '''
# маршрут восстановления пароля
@router.post("/forgot-password")
def forgot_password(
    email: str,
    db: Session = Depends(get_db),
):
    """Восстановление пароля"""
    return {"message": "Ссылка отправлена", "email": email}


# маршрут сброса пароля
@router.post("/reset-password")
def reset_password(
    token: str,
    new_password: str,
    db: Session = Depends(get_db),
):
    """Сброс пароля"""
    return {"message": "Пароль изменён", "token": token}


'''
    content = content[:insert_point] + new_endpoint + content[insert_point:]
    with open('app/api/v1/auth.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Добавлены!")
else:
    print("Уже существуют")
