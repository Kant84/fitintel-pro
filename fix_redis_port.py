# fix_redis_port.py
import os

# Находим все файлы с redis
for root, dirs, files in os.walk('app'):
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            if 'redis' in content.lower() or '6379' in content:
                print(f"Found in: {path}")
                # Заменяем 6379 на 6380
                content = content.replace('port=6379', 'port=6380')
                content = content.replace(':6379', ':6380')
                content = content.replace('localhost:6379', 'localhost:6380')
                content = content.replace('127.0.0.1:6379', '127.0.0.1:6380')
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)

print("Redis port changed to 6380!")
