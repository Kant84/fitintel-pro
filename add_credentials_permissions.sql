INSERT INTO permissions (id, code, name, module, description, created_at, updated_at) VALUES
(gen_random_uuid(), 'credentials.create', 'Создание credential', 'credentials', 'Создание карт, браслетов, ключей', NOW(), NOW()),
(gen_random_uuid(), 'credentials.read', 'Чтение credential', 'credentials', 'Просмотр credentials клиента', NOW(), NOW()),
(gen_random_uuid(), 'credentials.update', 'Обновление credential', 'credentials', 'Блокировка/разблокировка', NOW(), NOW()),
(gen_random_uuid(), 'credentials.delete', 'Удаление credential', 'credentials', 'Удаление карт и браслетов', NOW(), NOW())
ON CONFLICT (code) DO NOTHING;

-- Добавляем всем ролям SUPER_ADMIN
INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
SELECT gen_random_uuid(), r.id, p.id, NOW(), NOW()
FROM roles r, permissions p
WHERE r.code = 'SUPER_ADMIN'
AND p.code IN ('credentials.create', 'credentials.read', 'credentials.update', 'credentials.delete', 'credentials.reassign', 'credentials.manage')
ON CONFLICT DO NOTHING;
