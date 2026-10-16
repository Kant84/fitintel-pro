# -*- coding: utf-8 -*-
"""Клиент HTTP API 1С:Фитнес клуб (V3) для десктопа FitIntel Pro.
Только стандартная библиотека (urllib) — PyInstaller без внешних зависимостей.
Авторизация: Basic base64(UTF-8("Пользователь:Пароль")) + заголовок apikey.
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional


class Fitness1CError(Exception):
    def __init__(self, code: Any, message: str, http_status: Optional[int] = None):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        self.http_status = http_status


@dataclass
class Fitness1CConfig:
    base_url: str = ""
    username: str = ""
    password: str = ""
    api_key: str = ""
    club_id: str = ""
    timeout: int = 25


class Fitness1CClient:
    def __init__(self, config: Fitness1CConfig):
        self.config = config

    def _headers(self) -> dict:
        pair = f"{self.config.username}:{self.config.password}".encode("utf-8")
        return {
            "Authorization": "Basic " + base64.b64encode(pair).decode("ascii"),
            "apikey": self.config.api_key,
            "Accept": "application/json",
        }

    def _request(self, method: str, path: str, params: dict = None, json_body: dict = None) -> Any:
        url = self.config.base_url.rstrip("/") + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(json_body).encode("utf-8") if json_body is not None else None
        req = urllib.request.Request(url, data=data, headers=self._headers(), method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                payload = json.loads(raw)
                if isinstance(payload, dict) and payload.get("result") is False:
                    raise Fitness1CError(payload.get("error"), payload.get("error_message", "Ошибка API"), exc.code)
            except ValueError:
                pass
            if exc.code == 401:
                raise Fitness1CError(401, "Ошибка аутентификации пользователя 1С (Basic)", 401)
            raise Fitness1CError(exc.code, f"HTTP {exc.code}: {raw[:200]}", exc.code)
        except urllib.error.URLError as exc:
            raise Fitness1CError(-2, f"Сетевая ошибка: {exc.reason}") from exc
        try:
            payload = json.loads(raw)
        except ValueError as exc:
            raise Fitness1CError(-1, f"Невалидный ответ (не JSON): {raw[:200]}") from exc
        if isinstance(payload, dict) and payload.get("result") is False:
            raise Fitness1CError(payload.get("error"), payload.get("error_message", "Ошибка API"))
        return payload.get("data") if isinstance(payload, dict) and "data" in payload else payload

    # ---------- сервисные ----------
    def test_connection(self) -> dict:
        auth_types = self._request("GET", "/auth_types")
        clubs = self._request("GET", "/clubs/") or []
        if not clubs:
            raise Fitness1CError(-3, "API ответил, но список клубов пуст (в 1С проверьте «Соответствие клубов»)")
        club_id = self.config.club_id or clubs[0]["id"]
        return {"ok": True, "auth_types": auth_types, "clubs": clubs, "club_id": club_id}

    def get_club_id(self) -> str:
        if self.config.club_id:
            return self.config.club_id
        clubs = self._request("GET", "/clubs/") or []
        if not clubs:
            raise Fitness1CError(-3, "Список клубов пуст")
        return clubs[0]["id"]

    # ---------- клиенты ----------
    def list_customers(self, changed_after: Optional[str] = None) -> list:
        params = {"club_id": self.get_club_id()}
        if changed_after:
            params["changed_after"] = changed_after
        return self._request("GET", "/customers/", params=params) or []

    def get_customer(self, customer_id: str) -> dict:
        return self._request("GET", f"/customers/{customer_id}/")

    def create_customer(self, name: str, phone: str, email: str = "",
                        birthday: str = "", sex: str = "", note: str = "") -> dict:
        body = {"name": name, "phone": phone, "club_id": self.get_club_id(),
                "email": email, "birthday": birthday, "sex": sex, "note": note}
        return self._request("POST", "/customers/", json_body=body)

    def update_customer(self, customer_id: str, **fields) -> dict:
        return self._request("PATCH", f"/customers/{customer_id}/", json_body=fields)

    def get_customer_photo(self, customer_id: str) -> bytes:
        url = self.config.base_url.rstrip("/") + f"/customers/{customer_id}/photo/"
        req = urllib.request.Request(url, headers=self._headers())
        with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
            return resp.read()

    # ---------- членства ----------
    def list_memberships(self, customer_id: str) -> list:
        return self._request("GET", f"/customers/{customer_id}/memberships/",
                             params={"club_id": self.get_club_id()}) or []

    # ---------- шкафчики ----------
    def list_cabinets(self) -> list:
        return self._request("GET", "/cabinets/", params={"club_id": self.get_club_id()}) or []

    def list_club_cabinets(self) -> list:
        return self._request("GET", "/club_cabinets/", params={"club_id": self.get_club_id()}) or []

    def assign_cabinet(self, customer_id: str, cabinet_id: str) -> dict:
        return self._request("POST", f"/customers/{customer_id}/club_cabinets/",
                             json_body={"cabinet_id": cabinet_id, "club_id": self.get_club_id()})

    def release_cabinet(self, assignment_id: str) -> dict:
        return self._request("DELETE", f"/club_cabinets/{assignment_id}/")

    # ---------- персонал / расписание / визиты ----------
    def list_employees(self) -> list:
        return self._request("GET", "/employees/") or []

    def list_schedules(self, on_date: Optional[str] = None) -> list:
        params = {"club_id": self.get_club_id()}
        if on_date:
            params["date"] = on_date
        return self._request("GET", "/schedules/", params=params) or []

    def set_person_state(self, person_id: str, state_id: int) -> dict:
        return self._request("POST", f"/persons/{person_id}/state/", json_body={"state_id": state_id})

    def get_person_state(self, person_id: str) -> Optional[dict]:
        return self._request("GET", f"/persons/{person_id}/state/")

    def list_visits(self, on_date: Optional[str] = None) -> list:
        params = {"club_id": self.get_club_id()}
        if on_date:
            params["date"] = on_date
        return self._request("GET", "/visits/", params=params) or []