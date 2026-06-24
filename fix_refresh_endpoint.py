# fix_refresh_endpoint.py
with open('app/api/v1/auth.py', 'r', encoding='utf-8') as f:
    content = f.read()

if '"/refresh"' not in content:
    insert_point = content.find('@router.post("/token"')
    new_endpoint = '''
# маршрут обновления токена
@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    """Обновление access token"""
    auth_service = AuthService(db)
    user = auth_service.authenticate_user(payload.login, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    access_token = auth_service.create_user_access_token(user)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


'''
    content = content[:insert_point] + new_endpoint + content[insert_point:]
    with open('app/api/v1/auth.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("/refresh добавлен!")
else:
    print("/refresh уже существует")
