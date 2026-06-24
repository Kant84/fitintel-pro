<<<<<<< HEAD
-- ════════════════════════════════════════════════════════════
-- FitIntel Pro v1.3.1 — License Key
-- ════════════════════════════════════════════════════════════

INSERT INTO licenses (
    license_key, owner_name, owner_email, license_type,
    max_users, max_clients, max_terminals,
    issued_at, expires_at, is_active, is_revoked, signature
) VALUES (
    'FCD53A7672BEC8CA8CACBE23CA46F79C',
    'Kant84 Fitness Club',
    'admin@fitintel.pro',
    'professional',
    50,
    5000,
    10,
    '2026-06-14 10:05:11+0000',
    '2027-06-09 10:05:11+0000',
    TRUE,
    FALSE,
    'v1.3.1-auto-generated'
)
ON CONFLICT (license_key) DO NOTHING;
=======
INSERT INTO licenses (license_key, owner_name, owner_email, license_type, max_users, max_clients, max_terminals, issued_at, expires_at, is_active, is_revoked, signature) VALUES ('FCD53A7672BEC8CA8CACBE23CA46F79C', 'Kant84 Fitness Club', 'admin@fitintel.pro', 'professional', 50, 5000, 10, '2026-06-14 10:05:11+0000', '2027-06-09 10:05:11+0000', TRUE, FALSE, 'v1.3.1-auto-generated') ON CONFLICT (license_key) DO NOTHING;
>>>>>>> add08324efb53366e13ed9684e0652c6bdaa9143
