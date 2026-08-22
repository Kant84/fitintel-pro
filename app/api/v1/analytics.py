"""E16: Time Series Analytics & Forecasting (TZ v3.4 §4.28) — schema-autodetect."""
import json, asyncio, logging
from datetime import date, timedelta
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
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
        c.execute(text("""CREATE TABLE IF NOT EXISTS analytics_daily (
            id SERIAL PRIMARY KEY, club_id INT DEFAULT 1, metric VARCHAR(20) NOT NULL,
            date DATE NOT NULL, value NUMERIC(14,2) DEFAULT 0, forecast NUMERIC(14,2),
            created_at TIMESTAMP DEFAULT NOW(),
            CONSTRAINT uix_daily_metric UNIQUE (club_id, metric, date))"""))
        c.execute(text("CREATE INDEX IF NOT EXISTS ix_analytics_date ON analytics_daily(date, metric)"))

def _q1(sql, params):
    try:
        with _eng().connect() as c:
            return float(c.execute(text(sql), params).scalar() or 0)
    except Exception as e:
        logger.warning("metric fail: %s", e)
        return 0.0

def _metric(metric, d, mp):
    if metric == "attendance" and mp["visits_table"] and mp["visits_time"]:
        return _q1(f"SELECT COUNT(*) FROM {mp['visits_table']} WHERE DATE({mp['visits_time']})=:d", {"d": d})
    if metric == "revenue" and mp["payments_table"] and mp["payments_amount"] and mp["payments_time"]:
        st = ""
        if mp["payments_status"]:
            st = "AND (status IN ('completed','paid','success','done','завершен') OR status IS NULL)"
        return _q1(f"SELECT COALESCE(SUM({mp['payments_amount']}),0) FROM {mp['payments_table']} WHERE DATE({mp['payments_time']})=:d {st}", {"d": d})
    if metric == "new_clients" and mp["clients_time"]:
        return _q1(f"SELECT COUNT(*) FROM {mp['clients_table']} WHERE DATE({mp['clients_time']})=:d", {"d": d})
    if metric == "churn_risk" and mp["visits_table"] and mp["visits_owner"] and mp["visits_time"]:
        if mp["subs_table"] and mp["subs_owner"]:
            st = ""
            if mp["subs_status"]:
                st = "AND (s.%s='active' OR s.%s='активен')" % (mp["subs_status"], mp["subs_status"])
            exp = ""
            if mp["subs_end"]:
                exp = "AND (s.%s IS NULL OR s.%s >= CURRENT_DATE)" % (mp["subs_end"], mp["subs_end"])
            return _q1(f"""SELECT COUNT(DISTINCT s.{mp['subs_owner']}) FROM {mp['subs_table']} s
                WHERE 1=1 {st} {exp}
                AND NOT EXISTS (SELECT 1 FROM {mp['visits_table']} v
                    WHERE v.{mp['visits_owner']}=s.{mp['subs_owner']}
                    AND v.{mp['visits_time']} > NOW() - INTERVAL '14 days')""", {})
        return _q1(f"""SELECT COUNT(*) FROM {mp['clients_table']} cl WHERE NOT EXISTS (
            SELECT 1 FROM {mp['visits_table']} v WHERE v.{mp['visits_owner']}=cl.id
            AND v.{mp['visits_time']} > NOW() - INTERVAL '14 days')""", {})
    return 0.0

def _recalc_day(club_id, d, mp):
    out = {}
    with _eng().begin() as c:
        for m in ("attendance", "revenue", "new_clients", "churn_risk"):
            v = _metric(m, d, mp)
            c.execute(text("""INSERT INTO analytics_daily (club_id, metric, date, value)
                VALUES (:c,:m,:d,:v) ON CONFLICT (club_id, metric, date)
                DO UPDATE SET value=EXCLUDED.value"""), {"c": club_id, "m": m, "d": d, "v": v})
            out[m] = v
    return out

def _history(club_id, metric, days=56):
    _ensure()
    with _eng().connect() as c:
        rows = c.execute(text("""SELECT date, value FROM analytics_daily
            WHERE club_id=:c AND metric=:m AND date >= :s ORDER BY date"""),
            {"c": club_id, "m": metric, "s": date.today() - timedelta(days=days)}).all()
    return [(r[0], float(r[1])) for r in rows]

def _backfill(club_id, mp, days=56):
    today = date.today()
    for i in range(days, 0, -1):
        _recalc_day(club_id, today - timedelta(days=i), mp)

def _forecast_calc(hist, days_ahead):
    if len(hist) < 14:
        return []
    dow_sum, dow_cnt = {}, {}
    for d, v in hist:
        dow = (d.weekday() + 1) % 7
        dow_sum[dow] = dow_sum.get(dow, 0) + v
        dow_cnt[dow] = dow_cnt.get(dow, 0) + 1
    dow_avg = {k: dow_sum[k] / dow_cnt[k] for k in dow_sum}
    vals = [v for _, v in hist]
    trend = (sum(vals[-7:]) / 7) - (sum(vals[-14:-7]) / 7)
    last = hist[-1][0]
    return [{"date": str(last + timedelta(days=i)),
             "forecast": round(max(0.0, dow_avg.get(((last + timedelta(days=i)).weekday() + 1) % 7, 0) + trend * (i / 7)), 2)}
            for i in range(1, days_ahead + 1)]

@router.get("/analytics/debug-mapping")
def debug_mapping():
    return _mapping()

@router.get("/analytics/dashboard")
def dashboard(club_id: int = Query(1)):
    _ensure()
    mp = _mapping()
    today = date.today()
    cur = _recalc_day(club_id, today, mp)
    hist = _history(club_id, "revenue", 14)
    if len(hist) < 2:
        _backfill(club_id, mp, 14)
        hist = _history(club_id, "revenue", 14)
    week = sum(v for d, v in hist if d > today - timedelta(days=7))
    prev = sum(v for d, v in hist if today - timedelta(days=14) < d <= today - timedelta(days=7))
    fc = _forecast_calc(_history(club_id, "revenue"), 7)
    return {"attendance_today": cur["attendance"], "revenue_today": cur["revenue"],
            "new_clients_today": cur["new_clients"], "churn_risk_count": cur["churn_risk"],
            "forecast_week_revenue": round(sum(x["forecast"] for x in fc), 2),
            "revenue_week": round(week, 2), "revenue_prev_week": round(prev, 2),
            "vs_last_week": round(((week - prev) / prev * 100) if prev else 0, 1)}

class ForecastIn(BaseModel):
    metric: str = "attendance"
    days_ahead: int = 7

@router.post("/analytics/forecast")
def forecast(body: ForecastIn, club_id: int = Query(1)):
    _ensure()
    mp = _mapping()
    hist = _history(club_id, body.metric)
    if len(hist) < 14:
        _backfill(club_id, mp, 56)
        hist = _history(club_id, body.metric)
    fc = _forecast_calc(hist, min(body.days_ahead, 90))
    with _eng().begin() as c:
        for x in fc:
            c.execute(text("""INSERT INTO analytics_daily (club_id, metric, date, value, forecast)
                VALUES (:c,:m,:d,0,:f) ON CONFLICT (club_id, metric, date)
                DO UPDATE SET forecast=EXCLUDED.forecast"""),
                {"c": club_id, "m": body.metric, "d": x["date"], "f": x["forecast"]})
    if not fc:
        return {"metric": body.metric, "forecast": [], "note": "Мало данных даже после бэкфилла", "mapping": mp}
    return {"metric": body.metric,
            "history": [{"date": str(d), "value": v} for d, v in hist],
            "forecast": fc}

@router.post("/analytics/recalc")
def recalc(club_id: int = Query(1), days: int = Query(1)):
    _ensure()
    mp = _mapping()
    today = date.today()
    for i in range(min(days, 90) - 1, -1, -1):
        res = _recalc_day(club_id, today - timedelta(days=i), mp)
    return {"ok": True, "days": days, "last_date": str(today), "metrics": res, "mapping": mp}

def _live_snapshot(club_id):
    try:
        mp = _mapping()
        t = _recalc_day(club_id, date.today(), mp)
        return {"attendance_now": t["attendance"], "revenue_today": t["revenue"],
                "churn_alert": t["churn_risk"] > 10, "ts": str(date.today())}
    except Exception as e:
        return {"error": str(e)}

@router.get("/sse/live/{club_id}")
async def sse_live(club_id: int):
    async def gen():
        while True:
            yield "data: " + json.dumps(_live_snapshot(club_id), ensure_ascii=False) + "\n\n"
            await asyncio.sleep(30)
    return StreamingResponse(gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})


@router.get("/analytics/heatmap")
def heatmap(club_id: int = Query(1)):
    mp = _mapping()
    vt, vtm = mp["visits_table"], mp["visits_time"]
    grid = [[0] * 24 for _ in range(7)]
    if vt and vtm:
        try:
            with _eng().connect() as c:
                rows = c.execute(text(f"SELECT EXTRACT(DOW FROM {vtm}) d, EXTRACT(HOUR FROM {vtm}) h, COUNT(*) FROM {vt} GROUP BY 1,2")).all()
            for d, h, cnt in rows:
                grid[int(d)][int(h)] = int(cnt)
        except Exception as e:
            return {"ok": False, "error": str(e)}
    return {"ok": True, "grid": grid}
