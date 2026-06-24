INSERT INTO permissions (id, code, name, description, created_at, updated_at) VALUES
(gen_random_uuid(), 'access.read', 'Чтение access control', 'Просмотр статуса устройств и логов', NOW(), NOW()),
(gen_random_uuid(), 'access.manage', 'Управление access control', 'Блокировка/разблокировка устройств', NOW(), NOW()),
(gen_random_uuid(), 'access.manual_open', 'Ручное открытие', 'Ручное открытие турникетов', NOW(), NOW()),
(gen_random_uuid(), 'access.emergency', 'Экстренное открытие', 'Экстренное открытие всех устройств', NOW(), NOW()),
(gen_random_uuid(), 'access.override', 'Принудительный доступ', 'Принудительное предоставление доступа', NOW(), NOW())
ON CONFLICT (code) DO NOTHING;

-- Добавляем права SUPER_ADMIN
INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
SELECT gen_random_uuid(), r.id, p.id, NOW(), NOW()
FROM roles r, permissions p
WHERE r.code = 'SUPER_ADMIN'
AND p.code IN ('access.read', 'access.manage', 'access.manual_open', 'access.emergency', 'access.override')
ON CONFLICT DO NOTHING;
