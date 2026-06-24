# fix_visit_access_check.py
with open('app/services/visit_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''        # Проверяем лимиты абонемента
        if subscription and not subscription.is_unlimited:
            if subscription.visits_used >= subscription.visit_limit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Лимит посещений абонемента исчерпан",
                )
        
        # Устанавливаем время входа с часовым поясом UTC'''

new_code = '''        # Проверяем наличие активного абонемента
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет активного абонемента",
            )
        
        # Проверяем лимиты абонемента
        if not subscription.is_unlimited:
            if subscription.visits_used >= subscription.visit_limit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Лимит посещений абонемента исчерпан",
                )
        
        # Устанавливаем время входа с часовым поясом UTC'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('app/services/visit_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Проверка активного абонемента добавлена!")
else:
    print("Не найден блок для замены")
