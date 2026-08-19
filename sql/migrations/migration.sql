CREATE TABLE IF NOT EXISTS face_templates (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_type VARCHAR(20) NOT NULL DEFAULT 'client',
    face_encoding JSONB NOT NULL,
    photo_path VARCHAR(255),
    quality_score FLOAT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS ix_face_templates_user_id ON face_templates(user_id);

CREATE TABLE IF NOT EXISTS face_recognition_logs (
    id SERIAL PRIMARY KEY,
    face_template_id INTEGER REFERENCES face_templates(id) ON DELETE SET NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    user_type VARCHAR(20),
    terminal_id VARCHAR(100) NOT NULL,
    terminal_location VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    reason VARCHAR(255),
    confidence_score FLOAT,
    match_score FLOAT,
    processing_time_ms INTEGER,
    has_valid_subscription BOOLEAN,
    has_valid_shift BOOLEAN,
    is_employee_active BOOLEAN,
    is_fired BOOLEAN,
    captured_photo_path VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_face_recognition_logs_terminal_id ON face_recognition_logs(terminal_id);

CREATE TABLE IF NOT EXISTS employee_shifts (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    shift_start TIMESTAMP WITH TIME ZONE NOT NULL,
    shift_end TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    actual_start TIMESTAMP WITH TIME ZONE,
    actual_end TIMESTAMP WITH TIME ZONE,
    location VARCHAR(255),
    notes TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS ix_employee_shifts_employee_id ON employee_shifts(employee_id);

CREATE TABLE IF NOT EXISTS licenses (
    id SERIAL PRIMARY KEY,
    license_key VARCHAR(255) UNIQUE NOT NULL,
    owner_name VARCHAR(255) NOT NULL,
    owner_email VARCHAR(255) NOT NULL,
    license_type VARCHAR(50) NOT NULL DEFAULT 'standard',
    max_users INTEGER NOT NULL DEFAULT 100,
    max_terminals INTEGER NOT NULL DEFAULT 5,
    max_clients INTEGER NOT NULL DEFAULT 1000,
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    signature TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS ix_licenses_license_key ON licenses(license_key);

CREATE TABLE IF NOT EXISTS license_activations (
    id SERIAL PRIMARY KEY,
    license_id INTEGER NOT NULL REFERENCES licenses(id) ON DELETE CASCADE,
    device_id VARCHAR(255) NOT NULL,
    device_name VARCHAR(255),
    ip_address VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    activated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deactivated_at TIMESTAMP WITH TIME ZONE
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS is_fired BOOLEAN DEFAULT FALSE;
UPDATE users SET is_fired = FALSE WHERE is_fired IS NULL;
