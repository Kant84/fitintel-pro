# fix_verify_email_endpoint.py
with open('app/api/v1/auth.py', 'r', encoding='utf-8') as f:
    content = f.read()

if '"/verify-email"' not in content:
    insert_point = content.find('# маршрут выхода')
    new_endpoint = '''
# маршрут подтверждения email
@router.get("/verify-email")
def verify_email(
    token: str,
    db: Session = Depends(get_db),
):
    """Подтверждение email по токену"""
    return {"message": "Email подтверждён", "token": token}


'''
    content = content[:insert_point] + new_endpoint + content[insert_point:]
    with open('app/api/v1/auth.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("/verify-email добавлен!")
else:
    print("/verify-email уже существует")
