with open('app/api/v1/auth.py', 'r', encoding='utf-8') as f:
    content = f.read()

if '/register' not in content:
    # Add imports
    if 'from app.schemas.user import UserCreateRequest' not in content:
        content = content.replace(
            'from app.schemas.auth import CurrentUserResponse, LoginRequest, TokenResponse, TokenCheckResponse',
            'from app.schemas.auth import CurrentUserResponse, LoginRequest, TokenResponse, TokenCheckResponse' + chr(10) + 'from app.schemas.user import UserCreateRequest' + chr(10) + 'from app.repositories.user_repository import UserRepository' + chr(10) + 'from app.core.security import get_password_hash, decode_token'
        )
    
    # Add endpoints
    endpoints = chr(10) + '# === Added endpoints ===' + chr(10)
    endpoints += chr(10) + '@router.post("/register", response_model=TokenResponse)' + chr(10)
    endpoints += 'def register(payload: UserCreateRequest, db: Session = Depends(get_db)):' + chr(10)
    endpoints += '    auth_service = AuthService(db)' + chr(10)
    endpoints += '    existing = db.query(auth_service.user_repository.model).filter((auth_service.user_repository.model.email == payload.email) | (auth_service.user_repository.model.username == payload.username)).first()' + chr(10)
    endpoints += '    if existing:' + chr(10)
    endpoints += '        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")' + chr(10)
    endpoints += '    user = auth_service.user_repository.model(email=payload.email, username=payload.username, password_hash=get_password_hash(payload.password), is_active=payload.is_active)' + chr(10)
    endpoints += '    db.add(user)' + chr(10)
    endpoints += '    db.commit()' + chr(10)
    endpoints += '    db.refresh(user)' + chr(10)
    endpoints += '    access_token = auth_service.create_user_access_token(user)' + chr(10)
    endpoints += '    return TokenResponse(access_token=access_token, token_type="bearer", expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60)' + chr(10)
    
    endpoints += chr(10) + '@router.post("/refresh", response_model=TokenResponse)' + chr(10)
    endpoints += 'def refresh_token(payload: dict, db: Session = Depends(get_db)):' + chr(10)
    endpoints += '    token = payload.get("refresh_token") or payload.get("access_token")' + chr(10)
    endpoints += '    if not token:' + chr(10)
    endpoints += '        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token required")' + chr(10)
    endpoints += '    user_id = decode_token(token)' + chr(10)
    endpoints += '    if not user_id:' + chr(10)
    endpoints += '        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")' + chr(10)
    endpoints += '    auth_service = AuthService(db)' + chr(10)
    endpoints += '    user = db.query(auth_service.user_repository.model).filter(auth_service.user_repository.model.id == user_id).first()' + chr(10)
    endpoints += '    if not user or not user.is_active:' + chr(10)
    endpoints += '        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")' + chr(10)
    endpoints += '    access_token = auth_service.create_user_access_token(user)' + chr(10)
    endpoints += '    return TokenResponse(access_token=access_token, token_type="bearer", expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60)' + chr(10)
    
    endpoints += chr(10) + '@router.post("/logout", response_model=dict)' + chr(10)
    endpoints += 'def logout(current_user=Depends(get_current_active_user)):' + chr(10)
    endpoints += '    return {"status": "ok", "message": "Logout successful"}' + chr(10)
    
    content += endpoints
    
    with open('app/api/v1/auth.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK')
else:
    print('Already exists')