# fix_env_redis.py
with open('.env', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('REDIS_PORT=6379', 'REDIS_PORT=6380')
content = content.replace('CELERY_BROKER_URL=redis://localhost:6379/0', 'CELERY_BROKER_URL=redis://localhost:6380/0')
content = content.replace('CELERY_RESULT_BACKEND=redis://localhost:6379/1', 'CELERY_RESULT_BACKEND=redis://localhost:6380/1')

with open('.env', 'w', encoding='utf-8') as f:
    f.write(content)

print(".env обновлён!")
