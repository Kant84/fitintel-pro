ALTER TABLE credentials 
ADD COLUMN IF NOT EXISTS face_confidence FLOAT,
ADD COLUMN IF NOT EXISTS face_template TEXT;
