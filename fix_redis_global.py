# fix_redis_global.py
with open('app/api/v1/feature_flags.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем сброс redis_client при изменении настроек
old_get_redis = '''def get_redis() -> Redis:
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client'''

new_get_redis = '''def get_redis() -> Redis:
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    else:
        # Проверяем, живо ли соединение
        try:
            redis_client.ping()
        except:
            redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client'''

if old_get_redis in content:
    content = content.replace(old_get_redis, new_get_redis)
    with open('app/api/v1/feature_flags.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Redis get_redis исправлен!")
else:
    print("ERROR: Не найден get_redis")
