# fix_redis_config.py
with open('app/core/config.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_port = '''    REDIS_PORT: int = Field(
        default=6379,
        description="Порт Redis.",
    )'''

new_port = '''    REDIS_PORT: int = Field(
        default=6380,
        description="Порт Redis.",
    )'''

if old_port in content:
    content = content.replace(old_port, new_port)
    with open('app/core/config.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("REDIS_PORT изменён на 6380!")
else:
    print("ERROR: Не найден REDIS_PORT")
