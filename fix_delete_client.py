# fix_delete_client.py
with open('app/api/v1/clients.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'def delete_client' not in content:
    insert_point = content.find('# ============================================================')
    if insert_point == -1:
        insert_point = len(content)
    
    new_endpoint = '''

# ============================================================
# Удаление клиента
# ============================================================
@router.delete("/{client_id}")
def delete_client(
    client_id: UUID,
    current_user=Depends(require_permission("clients.delete")),
    db: Session = Depends(get_db),
):
    """Удаление клиента"""
    client_service = ClientService(db)
    client = client_service.get_client_by_id(str(client_id))
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    client_service.delete_client(client)
    return {"message": "Клиент удалён"}


'''
    content = content[:insert_point] + new_endpoint + content[insert_point:]
    
    with open('app/api/v1/clients.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("DELETE /clients/{id} добавлен!")
else:
    print("DELETE уже существует")
