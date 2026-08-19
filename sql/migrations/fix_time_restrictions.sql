ALTER TABLE tariffs 
ADD COLUMN IF NOT EXISTS time_restriction_type VARCHAR(50) DEFAULT 'FULLDAY',
ADD COLUMN IF NOT EXISTS allowed_start_time TIME,
ADD COLUMN IF NOT EXISTS allowed_end_time TIME;

ALTER TABLE subscriptions 
ADD COLUMN IF NOT EXISTS time_restriction_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS allowed_start_time TIME,
ADD COLUMN IF NOT EXISTS allowed_end_time TIME;

UPDATE tariffs SET time_restriction_type = 'FULLDAY' WHERE time_restriction_type IS NULL;
