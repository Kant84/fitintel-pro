# Подключаем reports router
with open('app/api/v1/__init__.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'from app.api.v1 import reports' not in content:
    # Находим последний импорт и добавляем после него
    old_import = 'from app.api.v1 import payments'
    new_import = 'from app.api.v1 import payments\\nfrom app.api.v1 import reports'
    content = content.replace(old_import, new_import)
    
    # Находим подключение payments и добавляем reports
    old_router = 'api_router.include_router(payments.router, prefix="/payments", tags=["payments"])'
    new_router = 'api_router.include_router(payments.router, prefix="/payments", tags=["payments"])\\napi_router.include_router(reports.router, prefix="/reports", tags=["reports"])'
    content = content.replace(old_router, new_router)
    
    with open('app/api/v1/__init__.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Router подключен!")
else:
    print("Router уже подключен")

# Добавляем право reports.export
import subprocess
subprocess.run([
    'psql', '-h', '127.0.0.1', '-U', 'postgres', '-d', 'fitnexus',
    '-c', "INSERT INTO permissions (id, code, name, module, description, created_at, updated_at) VALUES (gen_random_uuid(), 'reports.export', 'Export reports', 'reports', 'Экспорт отчётов', NOW(), NOW()) ON CONFLICT DO NOTHING;"
], check=False)

subprocess.run([
    'psql', '-h', '127.0.0.1', '-U', 'postgres', '-d', 'fitnexus',
    '-c', "INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at) SELECT gen_random_uuid(), r.id, p.id, NOW(), NOW() FROM roles r, permissions p WHERE r.code = 'admin' AND p.code = 'reports.export' ON CONFLICT DO NOTHING;"
], check=False)

print("Права добавлены!")
