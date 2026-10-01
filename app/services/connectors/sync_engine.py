# app/services/connectors/sync_engine.py — синхронизация в БД FitIntel с дедупликацией
from sqlalchemy import text


def _log(db, connector_id, entity, count, status, message=""):
    db.execute(text(
        "INSERT INTO connector_sync_log (connector_id, entity, records_count, status, message) "
        "VALUES (:cid, :e, :n, :s, :m)"),
        {"cid": connector_id, "e": entity, "n": count, "s": status, "m": str(message)[:400]})


def _norm_status(s):
    s = str(s or "").upper()
    return "ACTIVE" if s in ("АКТИВЕН", "ACTIVE", "ДЕЙСТВУЕТ", "ОТКРЫТ") else \
           "FROZEN" if "ЗАМОРОЗ" in s else "EXPIRED" if ("ИСТЕК" in s or "EXPIR" in s) else "ACTIVE"


def _find_client(db, phone, ext_id):
    if phone:
        row = db.execute(text(
            "SELECT id FROM clients WHERE phone=:p LIMIT 1"), {"p": phone}).first()
        if row:
            return str(row[0])
    return None


def sync_entity(db, connector_id: str, entity: str, rows: list) -> dict:
    """Синхронизирует одну сущность. Возвращает счётчики и пишет журнал."""
    created = updated = skipped = 0
    try:
        if entity == "clients":
            for r in rows:
                phone = (r.get("phone") or "").strip()
                if not phone and not r.get("external_id"):
                    skipped += 1
                    continue
                cid = _find_client(db, phone, r.get("external_id"))
                if cid:
                    db.execute(text(
                        "UPDATE clients SET last_name=:ln, first_name=:fn, middle_name=:mn, "
                        "email=COALESCE(NULLIF(:em,''), email), "
                        "birth_date=COALESCE(NULLIF(:bd,'')::date, birth_date) "
                        "WHERE id=:id"),
                        {"ln": r.get("last_name"), "fn": r.get("first_name"),
                         "mn": r.get("middle_name"), "em": r.get("email") or "",
                         "bd": r.get("birth_date") or "", "id": cid})
                    updated += 1
                else:
                    db.execute(text(
                        "INSERT INTO clients (id, last_name, first_name, middle_name, phone, email, "
                        "gender, birth_date, client_category, status, is_active, created_at, updated_at) "
                        "VALUES (gen_random_uuid(), :ln, :fn, :mn, :p, :em, :g, "
                        "NULLIF(:bd,'')::date, 'НЕ_УКАЗАНА', 'ACTIVE', :a, now(), now())"),
                        {"ln": r.get("last_name"), "fn": r.get("first_name"),
                         "mn": r.get("middle_name"), "p": phone, "em": r.get("email") or "",
                         "g": r.get("gender") or "НЕ_УКАЗАН", "bd": r.get("birth_date") or "",
                         "a": bool(r.get("is_active", True))})
                    created += 1

        elif entity == "subscriptions":
            for r in rows:
                cid = _find_client(db, r.get("client_phone") or "",
                                   r.get("client_external_id"))
                if not cid:
                    skipped += 1
                    continue
                tname = r.get("tariff_name") or "Импорт 1С"
                tid = db.execute(text(
                    "SELECT id FROM tariffs WHERE name=:n LIMIT 1"), {"n": tname}).first()
                if not tid:
                    tid = db.execute(text(
                        "INSERT INTO tariffs (id, code, name, price, currency, duration_days, "
                        "is_unlimited, is_active, created_at, updated_at) "
                        "VALUES (gen_random_uuid(), :c, :n, 0, 'RUB', 30, TRUE, TRUE, now(), now()) "
                        "RETURNING id"),
                        {"c": ("IMP_" + str(abs(hash(tname)) % 100000)), "n": tname}).first()
                exists = db.execute(text(
                    "SELECT id FROM subscriptions WHERE client_id=:c AND tariff_id=:t "
                    "AND start_date=:s LIMIT 1"),
                    {"c": cid, "t": str(tid[0]), "s": r.get("start_date") or None}).first()
                if exists:
                    db.execute(text(
                        "UPDATE subscriptions SET end_date=:e, status=:st WHERE id=:id"),
                        {"e": r.get("end_date"), "st": _norm_status(r.get("status")),
                         "id": str(exists[0])})
                    updated += 1
                else:
                    db.execute(text(
                        "INSERT INTO subscriptions (id, client_id, tariff_id, start_date, end_date, "
                        "status, price, currency, created_at, updated_at) "
                        "VALUES (gen_random_uuid(), :c, :t, :s, :e, :st, 0, 'RUB', now(), now())"),
                        {"c": cid, "t": str(tid[0]), "s": r.get("start_date"),
                         "e": r.get("end_date"), "st": _norm_status(r.get("status"))})
                    created += 1
        elif entity == "visits":
            for r in rows:
                cid = _find_client(db, r.get("client_phone") or "",
                                   r.get("client_external_id"))
                if not cid or not r.get("entry_time"):
                    skipped += 1
                    continue
                et = str(r["entry_time"]).replace("T", " ")[:19]
                dup = db.execute(text(
                    "SELECT id FROM visits WHERE client_id=:c AND entry_time=:e LIMIT 1"),
                    {"c": cid, "e": et}).first()
                if dup:
                    skipped += 1
                    continue
                db.execute(text(
                    "INSERT INTO visits (id, client_id, entry_time, access_method, "
                    "access_granted, status, created_at, updated_at) "
                    "VALUES (gen_random_uuid(), :c, :e, :m, TRUE, 'active', now(), now())"),
                    {"c": cid, "e": et, "m": r.get("access_method") or "API"})
                created += 1

        db.execute(text(
            "UPDATE connectors SET last_sync_at=now(), last_status='success', "
            "last_message=:m WHERE id=:id"),
            {"m": f"{entity}: +{created} ~{updated} пропущено {skipped}", "id": connector_id})
        _log(db, connector_id, entity, created + updated, "success",
             f"created={created} updated={updated} skipped={skipped}")
        db.commit()
        return {"entity": entity, "created": created, "updated": updated,
                "skipped": skipped, "status": "success"}
    except Exception as e:
        db.rollback()
        db.execute(text(
            "UPDATE connectors SET last_sync_at=now(), last_status='error', "
            "last_message=:m WHERE id=:id"),
            {"m": str(e)[:400], "id": connector_id})
        _log(db, connector_id, entity, 0, "error", str(e)[:400])
        db.commit()
        return {"entity": entity, "status": "error", "message": str(e)[:400]}