INSERT INTO permissions (id, code, name, module, description, created_at, updated_at) VALUES
(gen_random_uuid(), 'lockers.create', 'Создание шкафчика', 'lockers', 'Создание нового шкафчика', NOW(), NOW()),
(gen_random_uuid(), 'lockers.read', 'Чтение шкафчиков', 'lockers', 'Просмотр списка и статуса шкафчиков', NOW(), NOW()),
(gen_random_uuid(), 'lockers.update', 'Обновление шкафчика', 'lockers', 'Выдача/освобождение/блокировка шкафчика', NOW(), NOW()),
(gen_random_uuid(), 'lockers.delete', 'Удаление шкафчика', 'lockers', 'Удаление шкафчика', NOW(), NOW())
ON CONFLICT (code) DO NOTHING;

-- Добавляем SUPER_ADMIN
INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
SELECT gen_random_uuid(), r.id, p.id, NOW(), NOW()
FROM roles r, permissions p
WHERE r.code = 'SUPER_ADMIN'
AND p.code IN ('lockers.create', 'lockers.read', 'lockers.update', 'lockers.delete')
ON CONFLICT DO NOTHING;

-- Добавляем ADMIN
INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
SELECT gen_random_uuid(), r.id, p.id, NOW(), NOW()
FROM roles r, permissions p
WHERE r.code = 'ADMIN'
AND p.code IN ('lockers.create', 'lockers.read', 'lockers.update', 'lockers.delete')
ON CONFLICT DO NOTHING;

-- Добавляем RECEPTIONIST
INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
SELECT gen_random_uuid(), r.id, p.id, NOW(), NOW()
FROM roles r, permissions p
WHERE r.code = 'RECEPTIONIST'
AND p.code IN ('lockers.read', 'lockers.update')
ON CONFLICT DO NOTHING;
