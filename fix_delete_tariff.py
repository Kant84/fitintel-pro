# fix_delete_tariff.py
with open('app/api/v1/tariffs.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'def delete_tariff' not in content:
    # Находим последний endpoint и добавляем после него
    insert_point = content.find('# ============================================================')
    if insert_point == -1:
        insert_point = len(content)
    
    new_endpoint = '''

# ============================================================
# Удаление тарифа
# ============================================================
@router.delete("/{tariff_id}")
def delete_tariff(
    tariff_id: UUID,
    current_user=Depends(require_permission("tariffs.delete")),
    db: Session = Depends(get_db),
):
    """Удаление тарифа"""
    tariff_service = TariffService(db)
    tariff = tariff_service.get_tariff_by_id(str(tariff_id))
    if not tariff:
        raise HTTPException(status_code=404, detail="Тариф не найден")
    tariff_service.delete_tariff(tariff)
    return {"message": "Тариф удалён"}


'''
    content = content[:insert_point] + new_endpoint + content[insert_point:]
    
    with open('app/api/v1/tariffs.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("DELETE /tariffs/{id} добавлен!")
else:
    print("DELETE уже существует")
