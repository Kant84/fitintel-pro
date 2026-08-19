# add_time_restrictions.sql
-- Добавляем поля для временных ограничений в tariffs
ALTER TABLE tariffs 
ADD COLUMN IF NOT EXISTS time_restriction_type VARCHAR(50) DEFAULT 'FULLDAY',
ADD COLUMN IF NOT EXISTS allowed_start_time TIME,
ADD COLUMN IF NOT EXISTS allowed_end_time TIME;

-- Добавляем поля для временных ограничений в subscriptions (наследуются от тарифа, но можно переопределить)
ALTER TABLE subscriptions 
ADD COLUMN IF NOT EXISTS time_restriction_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS allowed_start_time TIME,
ADD COLUMN IF NOT EXISTS allowed_end_time TIME;

-- Обновляем существующие тарифы
UPDATE tariffs SET time_restriction_type = 'FULLDAY' WHERE time_restriction_type IS NULL;
