import os, json, secrets, datetime as dt
from fastapi import FastAPI, Request, HTTPException, Header
from psycopg_pool import ConnectionPool

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://platform_user:platform@platform_db:5432/platform")
ADMIN_CNS = {c.strip() for c in os.environ.get("ADMIN_CNS", "").split(",") if c.strip()}

app = FastAPI(title="FitIntel Platform API", docs_url=None, redoc_url=None)
pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=5)

BOOTSTRAP = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS clubs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  api_token TEXT UNIQUE NOT NULL,
  wireguard_ip TEXT,
  license_key TEXT,
  license_expires_at TIMESTAMPTZ,
  license_grace_until TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT TRUE,
  last_seen_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS club_heartbeats (
  id BIGSERIAL PRIMARY KEY,
  club_id UUID REFERENCES clubs(id),
  received_at TIMESTAMPTZ DEFAULT now(),
  payload JSONB,
  ip TEXT
);
CREATE TABLE IF NOT EXISTS platform_audit (
  id BIGSERIAL PRIMARY KEY,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  object TEXT,
  detail JSONB,
  ip TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS license_history (
  id BIGSERIAL PRIMARY KEY,
  club_id UUID REFERENCES clubs(id),
  license_key TEXT,
  days INTEGER,
  grace_days INTEGER,
  issued_by TEXT,
  issued_at TIMESTAMPTZ DEFAULT now(),
  note TEXT
);
CREATE INDEX IF NOT EXISTS idx_heartbeats_club ON club_heartbeats(club_id, received_at DESC);
"""

@app.on_event("startup")
def _init():
    with pool.connection() as c:
        c.execute(BOOTSTRAP)
        c.commit()

def _cn(request: Request) -> str:
    raw = request.headers.get("x-client-cn", "")
    cn = raw[3:].split(",")[0].strip() if raw.startswith("CN=") else raw.strip()
    if not cn or cn not in ADMIN_CNS:
        raise HTTPException(403, "admin client certificate required (CN not allowed)")
    return cn

def _audit(c, actor, action, obj=None, detail=None, ip=None):
    c.execute("INSERT INTO platform_audit (actor, action, object, detail, ip) VALUES (%s,%s,%s,%s,%s)",
              (actor, action, obj, json.dumps(detail, ensure_ascii=False) if detail else None, ip))

def _club_by_token(c, token: str):
    r = c.execute("SELECT id, slug, name, is_active FROM clubs WHERE api_token=%s", (token,)).fetchone()
    if not r:
        raise HTTPException(401, "unknown club token")
    if not r[3]:
        raise HTTPException(403, "club deactivated")
    return r

@app.get("/health")
def health():
    with pool.connection() as c:
        c.execute("SELECT 1")
    return {"ok": True, "service": "platform_api"}

@app.get("/platform/clubs")
def clubs_list(request: Request):
    admin = _cn(request)
    with pool.connection() as c:
        rows = c.execute("""SELECT slug, name, is_active, wireguard_ip, license_key,
            license_expires_at, license_grace_until, last_seen_at, created_at
            FROM clubs ORDER BY created_at""").fetchall()
    return {"ok": True, "admin": admin, "clubs": [
        {"slug": r[0], "name": r[1], "active": r[2], "wireguard_ip": r[3],
         "license_key": (r[4][:12] + "...") if r[4] else None,
         "license_expires_at": r[5], "license_grace_until": r[6],
         "last_seen_at": r[7], "created_at": r[8]} for r in rows]}

@app.post("/platform/clubs", status_code=201)
def club_create(request: Request, body: dict):
    admin = _cn(request)
    name, slug = str(body.get("name") or "").strip(), str(body.get("slug") or "").strip().lower()
    if not name or not slug:
        raise HTTPException(400, "name and slug required")
    token = "club_" + secrets.token_urlsafe(24)
    try:
        with pool.connection() as c:
            r = c.execute("INSERT INTO clubs (name, slug, api_token) VALUES (%s,%s,%s) RETURNING id",
                          (name, slug, token)).fetchone()
            _audit(c, admin, "club.create", slug, {"name": name}, request.client.host)
            c.commit()
    except Exception as e:
        raise HTTPException(409, "slug already exists: %s" % e)
    return {"ok": True, "slug": slug, "api_token": token,
            "note": "token shown once; store in club's ent_bridge env / agent config"}

@app.post("/platform/clubs/{slug}/token")
def club_rotate_token(request: Request, slug: str):
    admin = _cn(request)
    token = "club_" + secrets.token_urlsafe(24)
    with pool.connection() as c:
        n = c.execute("UPDATE clubs SET api_token=%s WHERE slug=%s RETURNING slug", (token, slug)).fetchone()
        if not n:
            raise HTTPException(404, "club not found")
        _audit(c, admin, "club.token_rotate", slug, None, request.client.host)
        c.commit()
    return {"ok": True, "api_token": token}

@app.get("/platform/clubs/{slug}/license")
def license_status(request: Request, slug: str):
    _cn(request)
    with pool.connection() as c:
        r = c.execute("""SELECT license_key, license_expires_at, license_grace_until
                         FROM clubs WHERE slug=%s""", (slug,)).fetchone()
    if not r:
        raise HTTPException(404, "club not found")
    key, exp, grace = r
    now = dt.datetime.now(dt.timezone.utc)
    if not key:
        status, days_left = "no_license", None
    elif exp and now < exp:
        status, days_left = "active", (exp - now).days
    elif grace and now < grace:
        status, days_left = "grace", (grace - now).days
    else:
        status, days_left = "expired", None
    return {"ok": True, "slug": slug, "status": status, "days_left": days_left,
            "license_expires_at": exp, "grace_until": grace,
            "license_key": (key[:12] + "...") if key else None}

@app.post("/platform/clubs/{slug}/license")
def license_attach(request: Request, slug: str, body: dict):
    admin = _cn(request)
    key = str(body.get("license_key") or "").strip()
    try:
        days = int(body.get("days"))
    except Exception:
        raise HTTPException(400, "days (int) required")
    if len(key) < 20:
        raise HTTPException(400, "license_key too short")
    grace_days = max(3, min(30, days // 10))
    now = dt.datetime.now(dt.timezone.utc)
    exp = now + dt.timedelta(days=days)
    grace = exp + dt.timedelta(days=grace_days)
    with pool.connection() as c:
        r = c.execute("""UPDATE clubs SET license_key=%s, license_expires_at=%s, license_grace_until=%s
                         WHERE slug=%s RETURNING id""", (key, exp, grace, slug)).fetchone()
        if not r:
            raise HTTPException(404, "club not found")
        c.execute("""INSERT INTO license_history (club_id, license_key, days, grace_days, issued_by, note)
                     VALUES (%s,%s,%s,%s,%s,%s)""",
                  (r[0], key, days, grace_days, admin, body.get("note")))
        _audit(c, admin, "license.attach", slug, {"days": days, "grace_days": grace_days}, request.client.host)
        c.commit()
    return {"ok": True, "slug": slug, "expires_at": exp, "grace_until": grace, "grace_days": grace_days}

@app.post("/platform/clubs/{slug}/license/issue")
def license_issue(request: Request, slug: str, body: dict):
    admin = _cn(request)
    plan = str(body.get("plan") or "Start")
    try:
        days = int(body.get("days"))
        maxc = int(body.get("max_clients", 50))
    except Exception:
        raise HTTPException(400, "days (int) required")
    import urllib.request
    req = urllib.request.Request(
        "http://license_studio_api:8003/issue",
        data=json.dumps({"plan": plan, "days": days, "max_clients": maxc,
                         "club": slug, "club_id": slug}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            issued = json.loads(r.read().decode())
    except Exception as e:
        raise HTTPException(502, "license studio unavailable: %s" % str(e)[:120])
    key, exp_s = issued["license_key"], issued["exp"]
    exp = dt.datetime.fromisoformat(exp_s).replace(tzinfo=dt.timezone.utc)
    grace_days = max(3, min(30, days // 10))
    grace = exp + dt.timedelta(days=grace_days)
    with pool.connection() as c:
        r = c.execute("""UPDATE clubs SET license_key=%s, license_expires_at=%s, license_grace_until=%s
                         WHERE slug=%s RETURNING id""", (key, exp, grace, slug)).fetchone()
        if not r:
            raise HTTPException(404, "club not found")
        c.execute("""INSERT INTO license_history (club_id, license_key, days, grace_days, issued_by, note)
                     VALUES (%s,%s,%s,%s,%s,%s)""",
                  (r[0], key, days, grace_days, admin, "via license-studio-api"))
        _audit(c, admin, "license.issue", slug, {"days": days, "plan": plan}, request.client.host)
        c.commit()
    return {"ok": True, "slug": slug, "license_key": key,
            "temp_password": issued["temp_password"],
            "exp": exp_s, "grace_until": grace.isoformat(),
            "note": "key+password shown once: hand to club out-of-band"}


@app.get("/platform/audit")
def audit_list(request: Request, actor: str = "", action: str = "", limit: int = 100):
    _cn(request)
    limit = max(1, min(limit, 500))
    q, args = "SELECT actor, action, object, detail, ip, created_at FROM platform_audit WHERE 1=1", []
    if actor:
        q += " AND actor=%s"; args.append(actor)
    if action:
        q += " AND action=%s"; args.append(action)
    q += " ORDER BY created_at DESC LIMIT %s"; args.append(limit)
    with pool.connection() as c:
        rows = c.execute(q, args).fetchall()
    return {"ok": True, "audit": [
        {"actor": r[0], "action": r[1], "object": r[2], "detail": r[3], "ip": r[4], "at": r[5]}
        for r in rows]}


@app.post("/platform/heartbeat")
def heartbeat(request: Request, body: dict,
              x_club_token: str = Header(default="", alias="X-Club-Token")):
    with pool.connection() as c:
        club = _club_by_token(c, x_club_token)
        c.execute("INSERT INTO club_heartbeats (club_id, payload, ip) VALUES (%s,%s,%s)",
                  (club[0], json.dumps(body, ensure_ascii=False)[:4000], request.client.host))
        c.execute("UPDATE clubs SET last_seen_at=now() WHERE id=%s", (club[0],))
        c.commit()
    return {"ok": True, "club": club[1], "server_time": dt.datetime.now(dt.timezone.utc).isoformat()}

@app.get("/platform/clubs/{slug}/heartbeat")
def heartbeat_last(request: Request, slug: str):
    _cn(request)
    with pool.connection() as c:
        r = c.execute("""SELECT h.received_at, h.payload, h.ip FROM club_heartbeats h
                         JOIN clubs cl ON cl.id=h.club_id
                         WHERE cl.slug=%s ORDER BY h.received_at DESC LIMIT 1""", (slug,)).fetchone()
    if not r:
        return {"ok": True, "slug": slug, "heartbeat": None}
    return {"ok": True, "slug": slug,
            "heartbeat": {"at": r[0], "payload": r[1], "ip": r[2]}}
