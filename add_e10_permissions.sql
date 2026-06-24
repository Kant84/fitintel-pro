INSERT INTO permissions (id, code, name, module, description, created_at, updated_at) VALUES
(gen_random_uuid(), 'credentials.reassign', 'Перепривязка credential', 'credentials', 'Перепривязка карты/браслета другому клиенту', NOW(), NOW()),
(gen_random_uuid(), 'credentials.manage', 'Управление credentials', 'credentials', 'Программирование MIFARE и управление', NOW(), NOW())
ON CONFLICT (code) DO NOTHING;

-- Добавляем права SUPER_ADMIN
INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
SELECT gen_random_uuid(), r.id, p.id, NOW(), NOW()
FROM roles r, permissions p
WHERE r.code = 'SUPER_ADMIN'
AND p.code IN ('credentials.reassign', 'credentials.manage')
ON CONFLICT DO NOTHING;
