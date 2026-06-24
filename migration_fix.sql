CREATE TABLE IF NOT EXISTS face_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
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
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    face_template_id UUID REFERENCES face_templates(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
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
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    shift_start TIMESTAMP WITH TIME ZONE NOT NULL,
    shift_end TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    actual_start TIMESTAMP WITH TIME ZONE,
    actual_end TIMESTAMP WITH TIME ZONE,
    location VARCHAR(255),
    notes TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS ix_employee_shifts_employee_id ON employee_shifts(employee_id);

ALTER TABLE users ADD COLUMN IF NOT EXISTS is_fired BOOLEAN DEFAULT FALSE;
UPDATE users SET is_fired = FALSE WHERE is_fired IS NULL;
