"""Self-learning churn model — schema-autodetect."""
import json, math, logging
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Query
from sqlalchemy import text

logger = logging.getLogger(__name__)
router = APIRouter()

_engine = None
def _eng():
    global _engine
    if _engine is None:
        for mod in ("app.db.session", "app.core.database", "app.database"):
            try:
                m = __import__(mod, fromlist=["engine"])
                _engine = getattr(m, "engine")
                break
            except Exception:
                continue
    if _engine is None:
        raise RuntimeError("DB engine not found")
    return _engine

_COLS = {}
def _cols(table):
    if table not in _COLS:
        try:
            with _eng().connect() as c:
                rows = c.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name=:t"), {"t": table}).scalars().all()
            _COLS[table] = set(rows)
        except Exception:
            _COLS[table] = set()
    return _COLS[table]

def _table(*names):
    for n in names:
        if _cols(n):
            return n
    return None

def _pick(table, *cands):
    cs = _cols(table) if table else set()
    for c in cands:
        if c in cs:
            return c
    return None

def _mapping():
    vt = _table("visits", "access_logs", "checkins", "attendance")
    pt = _table("payments", "payment_transactions")
    st = _table("subscriptions", "abonements", "memberships")
    ct = _table("clients", "members") or "users"
    return {
        "visits_table": vt,
        "visits_owner": _pick(vt, "client_id", "user_id", "member_id"),
        "visits_time": _pick(vt, "check_in_at", "visited_at", "created_at", "ts", "timestamp", "date"),
        "payments_table": pt,
        "payments_amount": _pick(pt, "amount", "sum", "total", "value", "price"),
        "payments_time": _pick(pt, "created_at", "paid_at", "completed_at", "date"),
        "payments_status": _pick(pt, "status"),
        "subs_table": st,
        "subs_owner": _pick(st, "client_id", "user_id", "member_id"),
        "subs_end": _pick(st, "end_date", "expires_at", "valid_until", "until", "date_end"),
        "subs_status": _pick(st, "status"),
        "clients_table": ct,
        "clients_time": _pick(ct, "created_at", "registered_at"),
    }

def _ensure():
    with _eng().begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS ai_models (
            id SERIAL PRIMARY KEY, name VARCHAR(64) UNIQUE,
            weights TEXT, trained_at TIMESTAMP, samples INT DEFAULT 0, accuracy NUMERIC(6,3))"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS ai_predictions (
            id SERIAL PRIMARY KEY, client_id INT, prob NUMERIC(5,4),
            created_at TIMESTAMP DEFAULT NOW(), outcome INT, resolved_at TIMESTAMP)"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS ai_accuracy_log (
            id SERIAL PRIMARY KEY, model VARCHAR(64), accuracy NUMERIC(6,3),
            samples INT, created_at TIMESTAMP DEFAULT NOW())"""))

def _features(cid, mp):
    vt, vo, vtm = mp["visits_table"], mp["visits_owner"], mp["visits_time"]
    if not vt or not vo or not vtm:
        return None
    try:
        with _eng().connect() as c:
            last = c.execute(text(f"SELECT MAX({vtm}) FROM {vt} WHERE {vo}=:i"), {"i": cid}).scalar()
            v30 = c.execute(text(f"SELECT COUNT(*) FROM {vt} WHERE {vo}=:i AND {vtm} > NOW() - INTERVAL '30 days'"), {"i": cid}).scalar() or 0
            sdl = 0
            if mp["subs_table"] and mp["subs_owner"] and mp["subs_end"]:
                sub = c.execute(text(f"SELECT MAX({mp['subs_end']}) FROM {mp['subs_table']} WHERE {mp['subs_owner']}=:i"), {"i": cid}).scalar()
                if sub:
                    sdl = (sub.date() if hasattr(sub, "date") else sub) - date.today()
                    sdl = sdl.days if hasattr(sdl, "days") else 0
    except Exception as e:
        logger.warning("features fail %s: %s", cid, e)
        return None
    if last is not None and getattr(last, "tzinfo", None) is not None:
        last = last.replace(tzinfo=None)
    dslv = (datetime.now() - last).days if last else 60
    return [min(dslv, 60) / 60.0, min(v30, 30) / 30.0, max(min(sdl, 90), -30) / 90.0, 1.0 if sdl > 0 else 0.0]

def _ids(mp):
    try:
        with _eng().connect() as c:
            return c.execute(text(f"SELECT id FROM {mp['clients_table']} LIMIT 2000")).scalars().all()
    except Exception:
        return []

def _train(samples):
    w = [0.0] * 5
    lr, iters = 0.3, 600
    for _ in range(iters):
        grad = [0.0] * 5
        for x, y in samples:
            z = w[4] + sum(w[i] * x[i] for i in range(4))
            p = 1 / (1 + math.exp(-max(-30, min(30, z))))
            err = p - y
            for i in range(4):
                grad[i] += err * x[i]
            grad[4] += err
        n = max(len(samples), 1)
        for i in range(5):
            w[i] -= lr * grad[i] / n
    return w

def _prob(w, x):
    z = w[4] + sum(w[i] * x[i] for i in range(4))
    return 1 / (1 + math.exp(-max(-30, min(30, z))))

@router.post("/ai/churn/train")
def train():
    import traceback
    try:
        return _train_inner()
    except Exception:
        return {"ok": False, "error": traceback.format_exc()}

def _train_inner():
    _ensure()
    mp = _mapping()
    samples = []
    for cid in _ids(mp):
        x = _features(cid, mp)
        if x is None:
            continue
        samples.append((x, 1 if x[0] * 60 > 30 else 0))
    if len(samples) < 5:
        return {"ok": False, "note": "Мало данных для обучения", "samples": len(samples), "mapping": mp}
    w = _train(samples)
    acc = round(sum(1 for x, y in samples if (_prob(w, x) > 0.5) == bool(y)) / len(samples), 3)
    with _eng().begin() as c:
        c.execute(text("""INSERT INTO ai_models (name, weights, trained_at, samples, accuracy)
            VALUES ('churn', :w, NOW(), :s, :a)
            ON CONFLICT (name) DO UPDATE SET weights=EXCLUDED.weights,
            trained_at=EXCLUDED.trained_at, samples=EXCLUDED.samples, accuracy=EXCLUDED.accuracy"""),
            {"w": json.dumps(w), "s": len(samples), "a": acc})
        c.execute(text("INSERT INTO ai_accuracy_log (model, accuracy, samples) VALUES ('churn', :a, :s)"),
                  {"a": acc, "s": len(samples)})
    return {"ok": True, "samples": len(samples), "accuracy": acc, "weights": [round(v, 3) for v in w]}

@router.get("/ai/churn/predict")
def predict(limit: int = Query(50)):
    _ensure()
    with _eng().connect() as c:
        row = c.execute(text("SELECT weights FROM ai_models WHERE name='churn'")).scalar()
    if not row:
        return {"ok": False, "note": "Модель не обучена — нажми «Обучить»"}
    w = json.loads(row)
    mp = _mapping()
    out = []
    for cid in _ids(mp):
        x = _features(cid, mp)
        if x is None:
            continue
        out.append({"client_id": cid, "churn_prob": round(_prob(w, x), 3),
                    "days_since_visit": round(x[0] * 60), "visits_30d": round(x[1] * 30)})
    out.sort(key=lambda r: -r["churn_prob"])
    out = out[:limit]
    with _eng().begin() as c:
        for r in out:
            c.execute(text("INSERT INTO ai_predictions (client_id, prob) VALUES (:i,:p)"),
                      {"i": r["client_id"], "p": r["churn_prob"]})
    return {"ok": True, "at_risk": out}

@router.post("/ai/churn/resolve")
def resolve():
    _ensure()
    mp = _mapping()
    vt, vo, vtm = mp["visits_table"], mp["visits_owner"], mp["visits_time"]
    done, agg = 0, None
    with _eng().begin() as c:
        rows = c.execute(text("""SELECT id, client_id FROM ai_predictions
            WHERE outcome IS NULL AND created_at < NOW() - INTERVAL '14 days'""")).all()
        for pid, cid in rows:
            last = None
            if vt and vo and vtm:
                last = c.execute(text(f"SELECT MAX({vtm}) FROM {vt} WHERE {vo}=:i"), {"i": cid}).scalar()
            if last is not None and getattr(last, "tzinfo", None) is not None:
                last = last.replace(tzinfo=None)
            actual = 1 if (not last or (datetime.now() - last).days > 30) else 0
            c.execute(text("UPDATE ai_predictions SET outcome=:o, resolved_at=NOW() WHERE id=:p"),
                      {"o": actual, "p": pid})
            done += 1
        agg = c.execute(text("""SELECT COUNT(*), AVG(CASE WHEN (prob>0.5)::int = outcome THEN 1.0 ELSE 0.0 END)
            FROM ai_predictions WHERE outcome IS NOT NULL""")).first()
        if agg and agg[0]:
            c.execute(text("UPDATE ai_models SET accuracy=:a WHERE name='churn'"), {"a": round(float(agg[1]), 3)})
    return {"ok": True, "resolved": done,
            "validated_accuracy": round(float(agg[1]), 3) if agg and agg[0] else None}

@router.get("/ai/status")
def status():
    _ensure()
    with _eng().connect() as c:
        m = c.execute(text("SELECT weights, trained_at, samples, accuracy FROM ai_models WHERE name='churn'")).first()
        hist = c.execute(text("SELECT accuracy, samples, created_at FROM ai_accuracy_log ORDER BY id")).all()
    return {"trained": bool(m),
            "weights": json.loads(m[0]) if m else None,
            "trained_at": str(m[1]) if m else None,
            "samples": m[2] if m else 0,
            "accuracy": float(m[3]) if m and m[3] is not None else None,
            "accuracy_history": [{"accuracy": float(h[0]), "samples": h[1], "at": str(h[2])} for h in hist]}
