# fix_delete_user_endpoint.py
with open('app/api/v1/users.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'def delete_user' not in content:
    insert_point = content.find('@router.get("/{user_id}/roles"')
    new_endpoint = '''
# маршрут удаления пользователя
@router.delete("/{user_id}")
def delete_user(
    user_id: UUID,
    current_user=Depends(require_permission("users.delete")),
    db: Session = Depends(get_db),
):
    """Удаление пользователя"""
    user_service = UserService(db)
    user = user_service.get_user_by_id(str(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user_service.delete_user(user)
    return {"message": "Пользователь удалён"}


'''
    content = content[:insert_point] + new_endpoint + content[insert_point:]
    with open('app/api/v1/users.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("DELETE /users/{id} добавлен!")
else:
    print("DELETE уже существует")
