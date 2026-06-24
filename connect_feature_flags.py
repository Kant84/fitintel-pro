# connect_feature_flags.py
with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Находим импорт и добавляем подключение
old_import = 'from app.api.v1 import feature_flags  # E7a — Feature Flags'

new_import = 'from app.api.v1 import feature_flags  # E7a — Feature Flags\nfrom app.api.v1.feature_flags import router as feature_flags_router'

if old_import in content and 'feature_flags_router' not in content:
    content = content.replace(old_import, new_import)
    
    # Находим место для подключения (после других router'ов)
    old_router = 'app.include_router(video_alerts_router, prefix=settings.API_V1_PREFIX)'
    new_router = 'app.include_router(video_alerts_router, prefix=settings.API_V1_PREFIX)\napp.include_router(feature_flags_router, prefix=settings.API_V1_PREFIX + "/feature-flags")'
    
    if old_router in content:
        content = content.replace(old_router, new_router)
        with open('app/main.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Feature Flags router подключен!")
    else:
        print("ERROR: Не найден video_alerts_router")
else:
    print("ERROR: Не найден импорт или уже подключен")
