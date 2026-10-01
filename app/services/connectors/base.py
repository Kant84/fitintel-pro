# app/services/connectors/base.py — абстракция коннектора клубной системы
import requests


class ClubConnector:
    """Единый интерфейс для внешних клубных систем.
    Все fetch_* возвращают списки нормализованных dict (см. fitness1c.py)."""
    type = "base"

    def __init__(self, base_url: str, login: str = "", password: str = ""):
        self.base_url = base_url.rstrip("/")
        self.auth = (login, password) if login else None
        self.timeout = 30

    def _get(self, path: str, params: dict | None = None) -> list | dict:
        r = requests.get(self.base_url + path, params=params or {},
                         auth=self.auth, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            for k in ("items", "data", "result", "rows"):
                if isinstance(data.get(k), list):
                    return data[k]
            return [data]
        return data if isinstance(data, list) else []

    def test_connection(self) -> dict:
        raise NotImplementedError

    def fetch_clients(self) -> list[dict]:
        raise NotImplementedError

    def fetch_subscriptions(self) -> list[dict]:
        raise NotImplementedError

    def fetch_visits(self, date_from: str | None = None,
                     date_to: str | None = None) -> list[dict]:
        raise NotImplementedError

    def fetch_schedule(self) -> list[dict]:
        raise NotImplementedError


class HitConnectorStub(ClubConnector):
    """CRM «ХИТ» (B-Office): документацию выдаёт техподдержка по запросу клуба.
    Заполним после получения спецификации — интерфейс уже готов."""
    type = "hit"

    def _not_ready(self):
        raise RuntimeError(
            "CRM «ХИТ»: требуется документация REST API от B-Office "
            "(клуб запрашивает модуль «Доступ к облачному REST API»).")

    def test_connection(self):
        self._not_ready()

    fetch_clients = fetch_subscriptions = fetch_visits = fetch_schedule = _not_ready


_REGISTRY = {}


def get_connector(conn_type: str, base_url: str, login: str = "",
                  password: str = "") -> ClubConnector:
    from .fitness1c import Fitness1CConnector
    _REGISTRY.setdefault("fitness1c", Fitness1CConnector)
    _REGISTRY.setdefault("hit", HitConnectorStub)
    cls = _REGISTRY.get(conn_type)
    if cls is None:
        raise ValueError(f"Неизвестный тип коннектора: {conn_type}")
    return cls(base_url, login, password)