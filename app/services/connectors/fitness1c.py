# app/services/connectors/fitness1c.py — коннектор «1С:Фитнес клуб» API V3
# Пути/поля — по типовой спецификации API V3; при расхождениях с вашей демо-базой
# правятся только PATHS и маппинг полей ниже.
from .base import ClubConnector

PATHS = {
    "clients": "/clients",
    "subscriptions": "/subscriptions",
    "visits": "/visits",
    "schedule": "/schedule",
}


def _norm_gender(v):
    v = str(v or "").lower()
    if v in ("м", "мужской", "male", "m"):
        return "MALE"
    if v in ("ж", "женский", "female", "f"):
        return "FEMALE"
    return "НЕ_УКАЗАН"


class Fitness1CConnector(ClubConnector):
    type = "fitness1c"

    def test_connection(self) -> dict:
        rows = self._get(PATHS["clients"], params={"limit": 1})
        return {"ok": True, "clients_available": len(rows) if isinstance(rows, list) else 1}

    def fetch_clients(self) -> list[dict]:
        out = []
        for c in self._get(PATHS["clients"]):
            fio = str(c.get("name") or c.get("fio") or "").strip().split()
            out.append({
                "external_id": str(c.get("id") or c.get("uid") or ""),
                "last_name": c.get("last_name") or (fio[0] if fio else ""),
                "first_name": c.get("first_name") or (fio[1] if len(fio) > 1 else ""),
                "middle_name": c.get("middle_name") or (fio[2] if len(fio) > 2 else ""),
                "phone": str(c.get("phone") or "").replace("+", "").strip(),
                "email": c.get("email") or "",
                "birth_date": str(c.get("birth_date") or "")[:10] or None,
                "gender": _norm_gender(c.get("gender")),
                "is_active": bool(c.get("is_active", c.get("active", True))),
            })
        return out

    def fetch_subscriptions(self) -> list[dict]:
        out = []
        for s in self._get(PATHS["subscriptions"]):
            out.append({
                "external_id": str(s.get("id") or ""),
                "client_external_id": str(s.get("client_id") or s.get("client") or ""),
                "client_phone": str(s.get("client_phone") or "").replace("+", "").strip(),
                "tariff_name": str(s.get("tariff") or s.get("tariff_name") or "Импорт 1С"),
                "start_date": str(s.get("start_date") or s.get("begin") or "")[:10],
                "end_date": str(s.get("end_date") or s.get("finish") or "")[:10],
                "status": str(s.get("status") or "ACTIVE"),
            })
        return out

    def fetch_visits(self, date_from=None, date_to=None) -> list[dict]:
        params = {}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        out = []
        for v in self._get(PATHS["visits"], params=params):
            out.append({
                "client_external_id": str(v.get("client_id") or ""),
                "client_phone": str(v.get("client_phone") or "").replace("+", "").strip(),
                "entry_time": str(v.get("entry_time") or v.get("date") or v.get("time") or ""),
                "access_method": "API",
            })
        return out

    def fetch_schedule(self) -> list[dict]:
        return self._get(PATHS["schedule"])   # прокси для виджетов: пока как есть