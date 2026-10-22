import os, json, secrets, datetime as dt
from fastapi import FastAPI, Request, HTTPException, Header, Response
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
ALTER TABLE clubs ADD COLUMN IF NOT EXISTS license_paid_until TIMESTAMPTZ;
"""

@app.on_event("startup")
def _init():
    with pool.connection() as c:
        c.execute(BOOTSTRAP)
        c.commit()


def _apply_renewals(c):
    """Оплачено дальше, чем истекает -> продлеваем expires_at до paid_until."""
    rows = c.execute("""SELECT id, license_paid_until FROM clubs
        WHERE license_paid_until IS NOT NULL AND license_expires_at IS NOT NULL
          AND license_paid_until > license_expires_at""").fetchall()
    for r in rows:
        c.execute("""UPDATE clubs SET license_expires_at=%s, license_grace_until=NULL
                     WHERE id=%s""", (r[1], r[0]))
    return len(rows)


def _lic_status(exp, grace, now):
    if not exp:
        return "no_license", None
    if now < exp:
        return "active", (exp - now).days
    if grace and now < grace:
        return "grace", (grace - now).days
    return "blocked", None


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
    now = dt.datetime.now(dt.timezone.utc)
    with pool.connection() as c:
        _apply_renewals(c)
        rows = c.execute("""SELECT cl.slug, cl.name, cl.is_active, cl.wireguard_ip,
            cl.license_key, cl.license_expires_at, cl.license_grace_until,
            cl.license_paid_until, cl.last_seen_at, cl.created_at, h.payload
            FROM clubs cl
            LEFT JOIN LATERAL (SELECT payload FROM club_heartbeats
                WHERE club_id = cl.id ORDER BY received_at DESC LIMIT 1) h ON TRUE
            ORDER BY cl.created_at""").fetchall()
        c.commit()
    out = []
    for r in rows:
        st, days = _lic_status(r[5], r[6], now)
        online = bool(r[8] and (now - r[8]).total_seconds() < 180)
        payload = r[10] or {}
        out.append({"slug": r[0], "name": r[1], "active": r[2], "wireguard_ip": r[3],
            "license_key": (r[4][:12] + "...") if r[4] else None,
            "license_expires_at": r[5], "license_grace_until": r[6],
            "license_paid_until": r[7], "last_seen_at": r[8], "created_at": r[9],
            "online": online, "license_status": st, "license_days_left": days,
            "version": payload.get("version"), "clients": payload.get("clients")})
    return {"ok": True, "admin": admin, "clubs": out}


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
    now = dt.datetime.now(dt.timezone.utc)
    with pool.connection() as c:
        _apply_renewals(c)
        r = c.execute("""SELECT license_key, license_expires_at, license_grace_until,
            license_paid_until FROM clubs WHERE slug=%s""", (slug,)).fetchone()
        c.commit()
    if not r:
        raise HTTPException(404, "club not found")
    st, days = _lic_status(r[1], r[2], now)
    return {"ok": True, "slug": slug, "status": st, "days_left": days,
            "license_expires_at": r[1], "grace_until": r[2], "paid_until": r[3],
            "license_key": (r[0][:12] + "...") if r[0] else None}


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


@app.post("/platform/clubs/{slug}/license/renew")
def license_renew(request: Request, slug: str, body: dict):
    admin = _cn(request)
    note = str(body.get("note") or "manual")
    now = dt.datetime.now(dt.timezone.utc)
    if body.get("days"):
        exp = now + dt.timedelta(days=int(body["days"]))
    elif body.get("paid_until"):
        exp = dt.datetime.fromisoformat(str(body["paid_until"])).replace(tzinfo=dt.timezone.utc)
    else:
        raise HTTPException(400, "days или paid_until (YYYY-MM-DD) required")
    period = (exp - now).days
    grace_days = max(3, min(30, period // 10))
    grace = exp + dt.timedelta(days=grace_days)
    with pool.connection() as c:
        r = c.execute("""UPDATE clubs SET license_paid_until=%s, license_expires_at=%s,
                         license_grace_until=%s WHERE slug=%s RETURNING id""",
                      (exp, exp, grace, slug)).fetchone()
        if not r:
            raise HTTPException(404, "club not found")
        c.execute("""INSERT INTO license_history (club_id, license_key, days, grace_days, issued_by, note)
                     VALUES (%s,%s,%s,%s,%s,%s)""",
                  (r[0], "manual-renew", period, grace_days, admin, note))
        _audit(c, admin, "license.renew", slug,
               {"paid_until": exp.isoformat(), "grace_days": grace_days, "note": note},
               request.client.host)
        c.commit()
    return {"ok": True, "slug": slug, "license_paid_until": exp,
            "expires_at": exp, "grace_until": grace}


@app.post("/platform/clubs/{slug}/suspend")
def club_suspend(request: Request, slug: str, body: dict):
    admin = _cn(request)
    reason = str(body.get("reason") or "").strip()
    if not reason:
        raise HTTPException(400, "reason required")
    with pool.connection() as c:
        n = c.execute("UPDATE clubs SET is_active=FALSE WHERE slug=%s RETURNING id", (slug,)).fetchone()
        if not n:
            raise HTTPException(404, "club not found")
        _audit(c, admin, "club.suspend", slug, {"reason": reason}, request.client.host)
        c.commit()
    return {"ok": True, "slug": slug, "suspended": True}


@app.post("/platform/clubs/{slug}/resume")
def club_resume(request: Request, slug: str):
    admin = _cn(request)
    with pool.connection() as c:
        n = c.execute("UPDATE clubs SET is_active=TRUE WHERE slug=%s RETURNING id", (slug,)).fetchone()
        if not n:
            raise HTTPException(404, "club not found")
        _audit(c, admin, "club.resume", slug, None, request.client.host)
        c.commit()
    return {"ok": True, "slug": slug, "suspended": False}


@app.get("/platform/dashboard")
def dashboard(request: Request):
    _cn(request)
    now = dt.datetime.now(dt.timezone.utc)
    with pool.connection() as c:
        renewed = _apply_renewals(c)
        clubs = c.execute("""SELECT slug, name, is_active, license_expires_at,
            license_grace_until, license_paid_until, last_seen_at FROM clubs""").fetchall()
        clients = c.execute("""SELECT COALESCE(SUM((h.payload->>'clients')::int),0)
            FROM clubs cl LEFT JOIN LATERAL (SELECT payload FROM club_heartbeats
                WHERE club_id=cl.id ORDER BY received_at DESC LIMIT 1) h ON TRUE""").fetchone()[0]
        audit = c.execute("""SELECT actor, action, object, created_at FROM platform_audit
            ORDER BY created_at DESC LIMIT 20""").fetchall()
        c.commit()
    lic = {"active": 0, "grace": 0, "blocked": 0, "no_license": 0}
    expiring, online, suspended = [], 0, 0
    for r in clubs:
        st, _ = _lic_status(r[3], r[4], now)
        lic[st] = lic.get(st, 0) + 1
        if r[3] and r[3] > now and (r[3] - now).days <= 14:
            expiring.append({"slug": r[0], "name": r[1], "days": (r[3] - now).days})
        if not r[2]:
            suspended += 1
        elif r[6] and (now - r[6]).total_seconds() < 180:
            online += 1
    return {"ok": True, "kpis": {"clubs_total": len(clubs), "online": online,
            "suspended": suspended, "clients_total": clients, "licenses": lic,
            "expiring_14d": expiring, "renewals_applied": renewed},
            "events": [{"at": a[3], "actor": a[0], "action": a[1], "object": a[2]} for a in audit]}


@app.get("/platform/clubs/{slug}/detail")
def club_detail(request: Request, slug: str):
    _cn(request)
    now = dt.datetime.now(dt.timezone.utc)
    with pool.connection() as c:
        _apply_renewals(c)
        r = c.execute("""SELECT cl.id, cl.name, cl.slug, cl.is_active, cl.wireguard_ip,
            cl.license_key, cl.license_expires_at, cl.license_grace_until,
            cl.license_paid_until, cl.last_seen_at, cl.created_at
            FROM clubs cl WHERE cl.slug=%s""", (slug,)).fetchone()
        if not r:
            raise HTTPException(404, "club not found")
        hb = c.execute("""SELECT received_at, payload, ip FROM club_heartbeats
            WHERE club_id=%s ORDER BY received_at DESC LIMIT 1""", (r[0],)).fetchone()
        hist = c.execute("""SELECT days, grace_days, issued_by, issued_at, note
            FROM license_history WHERE club_id=%s ORDER BY issued_at DESC LIMIT 5""",
            (r[0],)).fetchall()
        aud = c.execute("""SELECT actor, action, created_at FROM platform_audit
            WHERE object=%s ORDER BY created_at DESC LIMIT 10""", (slug,)).fetchall()
        c.commit()
    st, days = _lic_status(r[6], r[7], now)
    online = bool(r[9] and (now - r[9]).total_seconds() < 180)
    return {"ok": True, "club": {
        "name": r[1], "slug": r[2], "active": r[3], "wireguard_ip": r[4],
        "license_key": (r[5][:12] + "...") if r[5] else None,
        "license_status": st, "license_days_left": days,
        "license_expires_at": r[6], "grace_until": r[7], "paid_until": r[8],
        "online": online, "last_seen_at": r[9], "created_at": r[10],
        "heartbeat": {"at": hb[0], "payload": hb[1], "ip": hb[2]} if hb else None,
        "license_history": [{"days": h[0], "grace": h[1], "by": h[2], "at": h[3], "note": h[4]} for h in hist],
        "recent_audit": [{"actor": a[0], "action": a[1], "at": a[2]} for a in aud]}}


@app.get("/platform/clubs/export.csv")
def clubs_csv(request: Request):
    admin = _cn(request)
    now = dt.datetime.now(dt.timezone.utc)
    import csv as _csv, io as _io
    with pool.connection() as c:
        _apply_renewals(c)
        rows = c.execute("""SELECT name, slug, is_active, license_expires_at,
            license_grace_until, license_paid_until, last_seen_at FROM clubs
            ORDER BY created_at""").fetchall()
        c.commit()
    buf = _io.StringIO()
    w = _csv.writer(buf, delimiter=";")
    w.writerow(["name", "slug", "active", "online", "license_status", "days_left",
                "expires_at", "paid_until", "last_seen"])
    for r in rows:
        st, days = _lic_status(r[3], r[4], now)
        online = bool(r[6] and (now - r[6]).total_seconds() < 180)
        w.writerow([r[0], r[1], "yes" if r[2] else "no", "yes" if online else "no",
                    st, days if days is not None else "",
                    r[3], r[5], r[6]])
    _audit_conn = None
    return Response(buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=clubs.csv"})


@app.post("/platform/clubs/{slug}/impersonate")
def impersonate(request: Request, slug: str, body: dict):
    admin = _cn(request)
    key = str(body.get("key") or "")
    if len(key) < 16:
        raise HTTPException(400, "key required (CLUB_ADMIN_KEY)")
    with pool.connection() as c:
        r = c.execute("SELECT wireguard_ip FROM clubs WHERE slug=%s", (slug,)).fetchone()
    if not r:
        raise HTTPException(404, "club not found")
    if not r[0]:
        raise HTTPException(409, "club has no wireguard_ip (connect club via WireGuard first)")
    import urllib.request, urllib.error
    req = urllib.request.Request(
        "http://%s:8001/admin/impersonate/start" % r[0],
        data=b"{}",
        headers={"Content-Type": "application/json", "X-Admin-Access-Key": key},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise HTTPException(502, "club refused: %s %s" % (e.code, e.read().decode()[:120]))
    except Exception as e:
        raise HTTPException(502, "club unreachable: %s" % str(e)[:120])
    with pool.connection() as c:
        _audit(c, admin, "impersonate.start", slug,
               {"session": data.get("session_id")}, request.client.host)
        c.commit()
    return {"ok": True, "slug": slug,
            "credentials": {"login": data["login"], "password": data["password"]},
            "expires_in_min": data.get("expires_in_min", 5),
            "note": "enter credentials in club desktop login; session audited"}


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
