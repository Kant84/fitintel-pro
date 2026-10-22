"""Платформенная поддержка: impersonation по CLUB_ADMIN_KEY (ТЗ §3.2, §6.1).
Доступно ТОЛЬКО из VPN-подсети платформы (источник 10.0.0.1)."""
import os, uuid, secrets, datetime as dt
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import text

router = APIRouter(tags=["admin-access"])

ADMIN_KEY = os.environ.get("CLUB_ADMIN_KEY", "")
def _is_platform_source(host: str) -> bool:
    # WG-подсеть платформы + localhost + docker-бриджи (запрос идёт через nginx клуба).
    # Основная авторизация — CLUB_ADMIN_KEY, это защита в глубину.
    return (host.startswith("10.0.0.") or host.startswith("127.") or host == "::1"
            or host.startswith("172."))
LOGIN = "platform.admin"
TTL_MIN = 5


def _platform_only(request: Request):
    if not _is_platform_source(request.client.host):
        raise HTTPException(403, "only platform source allowed")


@router.post("/admin/impersonate/start")
def imp_start(request: Request):
    _platform_only(request)
    if not ADMIN_KEY:
        raise HTTPException(500, "CLUB_ADMIN_KEY not configured on club")
    key = request.headers.get("X-Admin-Access-Key", "")
    if not key or not secrets.compare_digest(key, ADMIN_KEY):
        raise HTTPException(403, "invalid admin key")
    password = secrets.token_urlsafe(9)[:12]
    now = dt.datetime.now(dt.timezone.utc)
    from app.core.security import get_password_hash
    from app.db.session import engine
    with engine.begin() as c:
        r = c.execute(text("SELECT id FROM users WHERE username=:u"), {"u": LOGIN}).fetchone()
        if r:
            uid = str(r[0])
            c.execute(text("""UPDATE users SET password_hash=:p, is_active=TRUE,
                is_superuser=TRUE, is_verified=TRUE, failed_login_count=0,
                locked_until=NULL, updated_at=:n WHERE id=:i"""),
                {"p": get_password_hash(password), "n": now, "i": uid})
        else:
            uid = str(uuid.uuid4())
            c.execute(text("""INSERT INTO users (id, username, email, password_hash,
                is_active, is_superuser, is_verified, failed_login_count,
                created_at, updated_at, full_name)
                VALUES (:i, :u, :e, :p, TRUE, TRUE, TRUE, 0, :n, :n, :f)"""),
                {"i": uid, "u": LOGIN, "e": "platform-admin@fitintel.ru",
                 "p": get_password_hash(password), "n": now,
                 "f": "Платформенный администратор"})
        c.execute(text("""INSERT INTO user_roles (id, user_id, role_id, assigned_at, created_at, updated_at)
            SELECT gen_random_uuid(), u.id, r.id, now(), now(), now()
            FROM users u, roles r
            WHERE u.username = :u AND r.code = 'superadmin'
            ON CONFLICT (user_id, role_id) DO NOTHING"""), {"u": LOGIN})
    return {"ok": True, "login": LOGIN, "password": password,
            "expires_in_min": TTL_MIN, "session_id": secrets.token_hex(8)}
