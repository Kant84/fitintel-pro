# fix_logout_endpoint.py
with open('app/api/v1/auth.py', 'r', encoding='utf-8') as f:
    content = f.read()

if '"/logout"' not in content:
    insert_point = content.find('# маршрут обновления токена')
    new_endpoint = '''
# маршрут выхода
@router.post("/logout")
def logout(
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Выход пользователя"""
    return {"message": "Выход выполнен", "user_id": str(current_user.id)}


'''
    content = content[:insert_point] + new_endpoint + content[insert_point:]
    with open('app/api/v1/auth.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("/logout добавлен!")
else:
    print("/logout уже существует")
