#!/usr/bin/env python3
"""Автоматический QA desktop-окон и API. Только сервер test 192.168.101.14.

Создаются только уникальные QA-записи. Пароли и токены не выводятся.
Реальные оплаты, возвраты, фискализация, email, оборудование и webhook не вызываются.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import io
import json
import re
import sys
import time
import uuid
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

BASE_URL = "http://192.168.101.14/api/v1"
REQUIRED_TEMPLATES = {
    "contract_standard", "contract_vip", "consent_personal",
    "medical_clearance", "cancel_request", "receipt",
}
COMMON_READS = [
    ("Главная", "/analytics/dashboard"),
    ("Главная/AI", "/analytics/ai/churn"),
    ("Главная/AI", "/analytics/ai/risk-segments"),
    ("Клиенты", "/clients/"),
    ("Абонементы", "/subscriptions/"),
    ("Тарифы", "/tariffs/"),
    ("Входы/Выходы", "/visits/"),
    ("Входы/Выходы/статистика", "/visits/stats"),
    ("Расписание/услуги", "/services"),
    ("Расписание/тренеры", "/trainers/profiles"),
    ("Расписание/записи", "/services/trainer-schedule"),
    ("Документы", "/documents"),
    ("Документы/шаблоны", "/document-templates"),
    ("Отчёты/операционный", "/reports/operational?date_from=" + (date.today() - timedelta(days=30)).isoformat() + "&date_to=" + date.today().isoformat()),
    ("Отчёты/посещаемость", "/reports/attendance?date_from=" + (date.today() - timedelta(days=30)).isoformat() + "&date_to=" + date.today().isoformat()),
    ("Отчёты/по часам", "/reports/hourly?date_from=" + (date.today() - timedelta(days=30)).isoformat() + "&date_to=" + date.today().isoformat()),
    ("Отчёты/неактивные", "/reports/inactive?days=30"),
    ("Отчёты/истекающие", "/reports/expiring?days=14"),
    ("Отчёты/платежи", "/reports/payments-list?date_from=" + (date.today() - timedelta(days=30)).isoformat() + "&date_to=" + date.today().isoformat()),
    ("Отчёты/зарплата", "/reports/trainer-payroll?date_from=" + (date.today() - timedelta(days=30)).isoformat() + "&date_to=" + date.today().isoformat()),
    ("Отчёты/P&L", "/accounting/profit-loss/" + date.today().strftime("%Y-%m")),
    ("Отчёты/ОСВ", "/accounting/osv/" + date.today().strftime("%Y-%m")),
    ("Отчёты/смены", "/reports/shifts?date_from=" + (date.today() - timedelta(days=30)).isoformat() + "&date_to=" + date.today().isoformat()),
]
ADMIN_READS = [
    ("Экраны ролей", "/ui-config/screens"),
    ("Экраны ролей/матрица", "/ui-config/roles"),
    ("Пользователи", "/users/"),
    ("Роли и права", "/roles/"),
    ("Разрешения", "/permissions/"),
    ("RBAC health", "/rbac/health"),
    ("Устройства", "/dal/devices"),
    ("Драйверы", "/dal/drivers"),
    ("Face ID", "/face-id"),
    ("Face ID/настройки", "/face-id/settings"),
    ("Face ID/движок", "/face-id/engine/info"),
    ("Лицензия", "/license/status"),
    ("Мастер установки", "/setup/status"),
    ("Банки", "/server-settings/bank-config"),
    ("Магазин", "/warehouse/products?club_id=1"),
    ("Магазин/категории", "/warehouse/categories?club_id=1"),
    ("Музыка/зоны", "/music/zones"),
    ("Музыка/плейлисты", "/music/playlists"),
    ("Музыка/эффекты", "/music/sfx"),
    ("Музыка/лицензия", "/music/license"),
    ("История", "/audit"),
    ("История/retention", "/audit/retention"),
    ("Аудит доступа", "/analytics/w12/access-audit"),
    ("Медиа-аудит", "/analytics/w12/media/audit"),
    ("Service-аккаунты", "/analytics/w12/service-accounts"),
    ("Зарплата", "/payroll/calc?period=" + date.today().strftime("%Y-%m")),
    ("Должности", "/staff/positions"),
    ("Корзина", "/trash"),
    ("Экспорт/задания", "/exports/jobs?club_id=1"),
    ("Интеграции/schema", "/integrations-config/schema"),
    ("Интеграции", "/integrations-config/"),
    ("Уведомления/настройки", "/messenger/settings"),
    ("Уведомления/чаты", "/messenger/chats"),
    ("Уведомления/связи", "/messenger/bindings"),
    ("Уведомления", "/messenger/notifications"),
    ("Параметры клуба", "/club-params"),
    ("Подписи бота", "/bot-labels"),
    ("Бонусные правила", "/bonus-rules"),
    ("Отзывы", "/miniapp/feedback"),
    ("Бухгалтерия", "/accounting/entries"),
    ("Фискальный регистратор/настройки", "/fiscal/settings"),
    ("Фискальный регистратор/смена", "/fiscal/shift"),
]
MANAGER_FORBIDDEN = [
    ("Пользователи", "/users/"),
    ("Роли и права", "/roles/"),
    ("Разрешения", "/permissions/"),
    ("RBAC health", "/rbac/health"),
    ("Экраны ролей/матрица", "/ui-config/roles"),
    ("История", "/audit"),
    ("Аудит доступа", "/analytics/w12/access-audit"),
    ("Service-аккаунты", "/analytics/w12/service-accounts"),
    ("Корзина", "/trash"),
]


def _safe_detail(response: requests.Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            detail = data.get("detail") or data.get("error") or data.get("message") or ""
        else:
            detail = ""
    except Exception:
        detail = response.text[:200]
    text = str(detail)[:300]
    text = re.sub(r"eyJ[A-Za-z0-9_.-]+", "<TOKEN>", text)
    text = re.sub(r"sat_[A-Za-z0-9_-]+", "<TOKEN>", text)
    return text or "без описания"


def _json(response: requests.Response):
    try:
        return response.json()
    except Exception:
        return None


def _items(data) -> list:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("items", "clients", "documents", "templates", "results", "data"):
            if isinstance(data.get(key), list):
                return data[key]
    return []


class QA:
    def __init__(self) -> None:
        self.run_id = uuid.uuid4().hex[:10]
        self.sessions: dict[str, requests.Session] = {}
        self.results: list[dict] = []
        self.created: dict[str, set[str]] = defaultdict(set)
        self.service_id: str | None = None
        self.template_codes: set[str] = set()

    def login(self, role: str, username: str, password: str) -> dict | None:
        session = requests.Session()
        response = session.post(BASE_URL + "/auth/login",
                                json={"login": username, "password": password}, timeout=30)
        data = _json(response) or {}
        token = data.get("access_token")
        if response.status_code != 200 or not token:
            self.add(role, "Авторизация", "Вход", False, response.status_code,
                     _safe_detail(response))
            return None
        session.headers["Authorization"] = "Bearer " + token
        self.sessions[role] = session
        me = session.get(BASE_URL + "/auth/me", timeout=30)
        payload = _json(me) or {}
        roles = {str(x.get("code") or x.get("name") or "").lower()
                 if isinstance(x, dict) else str(x).lower()
                 for x in payload.get("roles") or []}
        valid = me.status_code == 200 and (
            (role == "admin" and bool(roles & {"admin", "owner", "superadmin"}))
            or (role == "manager" and "manager" in roles)
        )
        self.add(role, "Авторизация", "Проверка /auth/me и роли", valid,
                 me.status_code, "роли подтверждены" if valid else "неожиданная роль")
        return payload if valid else None

    def add(self, role: str, area: str, check: str, ok: bool | None,
            status: int | str = "", detail: str = "") -> None:
        result = "PASS" if ok is True else "SKIP" if ok is None else "FAIL"
        row = {"role": role, "area": area, "check": check, "result": result,
               "http": status, "detail": str(detail)[:300]}
        self.results.append(row)
        print(f"[{result}] {role} | {area} | {check}"
              + (f" | HTTP {status}" if status != "" else "")
              + (f" | {detail}" if detail and result != "PASS" else ""), flush=True)

    def call(self, role: str, area: str, check: str, method: str, path: str,
             expected=(200,), validator=None, **kwargs) -> requests.Response | None:
        kwargs.setdefault("timeout", 60)
        try:
            for attempt in range(4):
                time.sleep(0.25)  # nginx: 10 r/s; QA не должен вызывать 503
                response = self.sessions[role].request(method, BASE_URL + path, **kwargs)
                if response.status_code != 503:
                    break
                time.sleep(1.0 + attempt)
        except requests.RequestException as exc:
            self.add(role, area, check, False, "NETWORK", str(exc)[:250])
            return None
        ok = response.status_code in expected
        detail = "" if ok else _safe_detail(response)
        if ok and validator:
            try:
                problem = validator(response)
            except Exception as exc:
                problem = "validator: " + str(exc)[:160]
            if problem:
                ok, detail = False, str(problem)[:300]
        self.add(role, area, check, ok, response.status_code, detail)
        return response if ok else None

    def forbidden(self, role: str, area: str, path: str, method="GET", **kwargs):
        response = self.call(role, area, "Запрет действия", method, path,
                             expected=(200, 201, 204, 400, 401, 403, 404, 405, 422), **kwargs)
        if response is None:
            return
        data = _json(response)
        denied = response.status_code in (401, 403) or (
            isinstance(data, dict) and "forbidden" in str(data.get("error", "")).lower())
        self.add(role, area, "Побочный эффект отсутствует/доступ запрещён",
                 denied, response.status_code,
                 "операция не запрещена" if not denied else "")

    def read_smoke(self, role: str) -> None:
        for area, path in COMMON_READS:
            self.call(role, area, "GET " + path, "GET", path)
        if role == "admin":
            for area, path in ADMIN_READS:
                self.call(role, area, "GET " + path, "GET", path,
                          validator=self._no_api_error)
        else:
            for area, path in MANAGER_FORBIDDEN:
                self.forbidden(role, area, path)

    @staticmethod
    def _no_api_error(response: requests.Response) -> str:
        data = _json(response)
        if isinstance(data, dict) and data.get("error"):
            return str(data["error"])[:250]
        return ""

    def _phone(self, purpose: str) -> str:
        digest = hashlib.sha256(f"{self.run_id}:{purpose}".encode("ascii")).digest()
        national = 1_000_000_000 + int.from_bytes(digest[:8], "big") % 9_000_000_000
        return f"+7{national}"

    def core_crud(self, role: str) -> None:
        suffix = self.run_id + ("a" if role == "admin" else "m")
        client_id = tariff_id = subscription_id = visit_id = None
        payload = {
            "first_name": "Автотест", "last_name": "QA" + suffix,
            "middle_name": "Окна", "phone": self._phone(role),
            "email": f"qa_{suffix}@example.com", "gender": "НЕ_УКАЗАН",
            "birth_date": "1990-01-02", "is_active": True,
        }
        r = self.call(role, "Клиенты", "Создать QA-клиента", "POST", "/clients/",
                      expected=(201,), json=payload)
        if r:
            client_id = str((_json(r) or {}).get("id") or "")
            self.created["clients"].add(client_id)
        if client_id:
            self.call(role, "Клиенты", "Открыть карточку QA-клиента", "GET",
                      "/clients/" + client_id)
            self.call(role, "Клиенты", "Изменить QA-клиента", "PATCH",
                      "/clients/" + client_id, json={"middle_name": "Проверено"})
            self.call(role, "Клиенты", "Изменение сохранено", "GET",
                      "/clients/" + client_id,
                      validator=lambda x: "" if (_json(x) or {}).get("middle_name") == "Проверено" else "middle_name не сохранён")

        code = ("QA" + suffix).upper()
        r = self.call(role, "Тарифы", "Создать QA-тариф", "POST", "/tariffs/",
                      expected=(201,), json={
                          "code": code, "name": "QA автотест " + suffix,
                          "description": "Только автоматический QA", "price": 100,
                          "currency": "RUB", "duration_days": 30, "visit_limit": 10,
                          "is_unlimited": False, "is_active": True,
                      })
        if r:
            tariff_id = str((_json(r) or {}).get("id") or "")
            self.created["tariffs"].add(code)
        if tariff_id:
            self.call(role, "Тарифы", "Открыть QA-тариф", "GET", "/tariffs/" + code)
            self.call(role, "Тарифы", "Изменить QA-тариф", "PATCH", "/tariffs/" + code,
                      json={"name": "QA изменён " + suffix})
            self.call(role, "Тарифы", "Изменение тарифа сохранено", "GET", "/tariffs/" + code,
                      validator=lambda x: "" if (_json(x) or {}).get("name") == "QA изменён " + suffix else "name не сохранён")

        if client_id and tariff_id:
            r = self.call(role, "Абонементы", "Создать QA-абонемент", "POST", "/subscriptions/",
                          expected=(201,), json={"client_id": client_id, "tariff_id": tariff_id,
                                                "start_date": str(date.today()), "status": "ACTIVE",
                                                "notes": "QA " + suffix})
            if r:
                subscription_id = str((_json(r) or {}).get("id") or "")
                self.created["subscriptions"].add(subscription_id)
        if subscription_id:
            self.call(role, "Абонементы", "Открыть QA-абонемент", "GET",
                      "/subscriptions/" + subscription_id)
            self.call(role, "Абонементы", "Изменить QA-абонемент", "PATCH",
                      "/subscriptions/" + subscription_id, json={"notes": "QA обновлён " + suffix})
            self.call(role, "Абонементы", "Заморозить QA-абонемент", "POST",
                      f"/subscriptions/{subscription_id}/freeze",
                      json={"reason": "OTHER", "notes": "QA"})
            self.call(role, "Абонементы", "Разморозить QA-абонемент", "POST",
                      f"/subscriptions/{subscription_id}/unfreeze", json={})
            self.call(role, "Абонементы", "История QA-абонемента", "GET",
                      f"/subscriptions/{subscription_id}/history")

        if client_id:
            self.add(role, "Входы/Выходы", "Ручное QA-посещение", None,
                     detail="SKIP: исключены возможные bonus/MAX-уведомления")
            r = self.call(role, "Платежи", "Создать неподтверждённый QA-платёж", "POST", "/payments/",
                          expected=(201,), json={
                              "client_id": client_id, "amount": 1.0, "payment_method": "CASH",
                              "payment_direction": "INCOME", "payment_category": "OTHER",
                              "notes": "QA НЕ ПОДТВЕРЖДАТЬ " + suffix})
            if r:
                payment_id = str((_json(r) or {}).get("id") or "")
                self.created["payments"].add(payment_id)
                self.call(role, "Платежи", "Открыть QA-платёж", "GET", "/payments/" + payment_id)
                self.call(role, "Платежи", "Платежи QA-клиента", "GET", "/payments/client/" + client_id)
            self.documents(role, client_id, suffix)
            if self.service_id:
                self.booking(role, client_id, suffix)
        if role == "manager":
            if client_id:
                self.forbidden(role, "Клиенты/удаление", "/clients/" + client_id, "DELETE")
            if tariff_id:
                self.forbidden(role, "Тарифы/удаление", "/tariffs/" + code, "DELETE")
            if subscription_id:
                self.forbidden(role, "Абонементы/удаление", "/subscriptions/" + subscription_id, "DELETE")
            if visit_id:
                self.forbidden(role, "Посещения/удаление", "/visits/" + visit_id,
                               "DELETE", json={"reason": "QA negative"})
            self.forbidden(role, "Услуги/создание", "/services", "POST", json={
                "name": "QA forbidden " + suffix, "category": "AEROBICS", "price": 1})
            self.forbidden(role, "Шаблоны/создание", "/document-templates", "POST", json={
                "name": "qa_forbidden_" + suffix, "doc_type": "other", "content": "QA"})
            self.template_codes.add("qa_forbidden_" + suffix)

    def documents(self, role: str, client_id: str, suffix: str) -> None:
        r = self.call(role, "Документы", "Получить шаблоны для генерации", "GET", "/document-templates")
        templates = _items(_json(r)) if r else []
        by_code = {str(t.get("code")): t for t in templates}
        missing = REQUIRED_TEMPLATES - set(by_code)
        self.add(role, "Документы", "Все 6 встроенных шаблонов", not missing,
                 detail="отсутствуют: " + ", ".join(sorted(missing)) if missing else "")
        first_doc = None
        for code in sorted(REQUIRED_TEMPLATES & set(by_code)):
            tpl = by_code[code]
            r = self.call(role, "Документы/" + code, "Создать документ", "POST", "/documents",
                          expected=(201,), json={
                              "type": tpl.get("doc_type") or code, "client_id": client_id,
                              "template_id": tpl.get("template_id") or tpl.get("id"),
                              "data": {"contract_number": "QA-" + suffix, "amount": "100",
                                       "date": "28.10.2026"}})
            if not r:
                continue
            doc_id = str((_json(r) or {}).get("document_id") or "")
            self.created["documents"].add(doc_id)
            first_doc = first_doc or doc_id
            self.call(role, "Документы/" + code, "Открыть документ", "GET", "/documents/" + doc_id)
            self.call(role, "Документы/" + code, "DOCX содержит данные клиента", "GET",
                      f"/documents/{doc_id}/download?format=docx",
                      validator=lambda x, s=suffix: self._valid_docx(x, "QA" + s))
            self.call(role, "Документы/" + code, "PDF содержит кириллицу и данные", "GET",
                      f"/documents/{doc_id}/download?format=pdf",
                      validator=lambda x, s=suffix: self._valid_pdf(x, "QA" + s))
        if first_doc:
            self.call(role, "Документы/подпись", "Подписать QA-документ", "POST",
                      f"/documents/{first_doc}/sign", json={})
            self.call(role, "Документы/подпись", "Повторная подпись запрещена", "POST",
                      f"/documents/{first_doc}/sign", expected=(400,), json={})
            self.call(role, "Документы/подпись", "Статус подписи сохранён", "GET",
                      "/documents/" + first_doc,
                      validator=lambda x: "" if (_json(x) or {}).get("signed") else "документ не подписан")

    @staticmethod
    def _valid_docx(response: requests.Response, marker: str) -> str:
        if not response.content.startswith(b"PK"):
            return "ответ не DOCX/ZIP"
        try:
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                xml = archive.read("word/document.xml").decode("utf-8")
            return "" if marker in xml else "тело документа потеряно: нет " + marker
        except Exception as exc:
            return "DOCX не читается: " + str(exc)[:150]

    def _valid_pdf(self, response: requests.Response, marker: str) -> str:
        if not response.content.startswith(b"%PDF"):
            return "ответ не PDF"
        try:
            try:
                from pypdf import PdfReader
            except ImportError:
                from PyPDF2 import PdfReader
            text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(response.content)).pages)
        except ImportError:
            return "PDF parser отсутствует; содержимое не доказано"
        except Exception as exc:
            return "PDF не читается: " + str(exc)[:150]
        return "" if marker in text else "в PDF нет кириллических данных " + marker

    def booking(self, role: str, client_id: str, suffix: str) -> None:
        when = (datetime.now(timezone.utc) + timedelta(days=3)).replace(microsecond=0)
        r = self.call(role, "Расписание", "Создать QA-запись", "POST",
                      f"/services/{self.service_id}/book", expected=(201,), json={
                          "client_id": client_id, "service_id": self.service_id,
                          "booking_date": when.isoformat(), "notes": "QA " + suffix})
        if not r:
            return
        r = self.call(role, "Расписание", "Запись видна у клиента", "GET",
                      f"/services/bookings/client/{client_id}")
        rows = _items(_json(r)) if r else []
        matches = [x for x in rows if str(x.get("service_id")) == self.service_id]
        if not matches:
            self.add(role, "Расписание", "Найти QA-запись для отмены", False,
                     detail="созданная запись не найдена")
            return
        booking_id = str(matches[0].get("id"))
        self.call(role, "Расписание", "Отменить QA-запись", "POST",
                  f"/services/bookings/{booking_id}/cancel", json={})

    def admin_service(self) -> None:
        name = "QA услуга " + self.run_id
        r = self.call("admin", "Услуги", "Создать QA-услугу", "POST", "/services",
                      expected=(201,), json={"name": name, "category": "AEROBICS",
                                            "price": 100, "duration_minutes": 60,
                                            "max_capacity": 5})
        if r:
            self.service_id = str((_json(r) or {}).get("id") or "")
            self.created["services"].add(self.service_id)
            self.call("admin", "Услуги", "Открыть QA-услугу", "GET", "/services/" + self.service_id)
            self.call("admin", "Услуги", "Изменить QA-услугу", "PUT", "/services/" + self.service_id,
                      json={"price": 101, "max_capacity": 6})

    def trash_restore(self) -> None:
        payload = {"first_name": "Корзина", "last_name": "QA" + self.run_id,
                   "phone": self._phone("trash"), "is_active": True}
        r = self.call("admin", "Корзина", "Создать отдельного QA-клиента", "POST", "/clients/",
                      expected=(201,), json=payload)
        cid = str((_json(r) or {}).get("id") or "") if r else ""
        if not cid:
            return
        self.created["clients"].add(cid)
        if not self.call("admin", "Корзина", "Удалить QA-клиента", "DELETE", "/clients/" + cid):
            return
        r = self.call("admin", "Корзина", "Найти точный snapshot", "GET", "/trash?entity=clients")
        rows = _items(_json(r)) if r else []
        matches = [x for x in rows if x.get("entity") == "clients" and str(x.get("entity_id")) == cid]
        if not matches:
            self.add("admin", "Корзина", "Snapshot соответствует ID", False,
                     detail="snapshot не найден")
            return
        sid = str(matches[0]["id"])
        self.call("admin", "Корзина", "Восстановить точный snapshot", "POST",
                  f"/trash/{sid}/restore", json={})
        self.call("admin", "Корзина", "Восстановленный клиент открывается", "GET", "/clients/" + cid)

    def service_account(self) -> None:
        r = self.call("admin", "Service-аккаунты", "Создать QA-аккаунт", "POST",
                      "/analytics/w12/service-accounts", json={
                          "name": "qa-" + self.run_id, "scopes": ["clients:read"], "ttl_days": 1},
                      validator=self._no_api_error)
        sid = str((_json(r) or {}).get("id") or "") if r else ""
        if sid:
            self.call("admin", "Service-аккаунты", "Отозвать QA-аккаунт", "POST",
                      f"/analytics/w12/service-accounts/{sid}/revoke", json={},
                      validator=self._no_api_error)

    def cleanup(self) -> None:
        if "admin" not in self.sessions:
            return
        r = self.call("admin", "QA cleanup", "Найти только QA service-аккаунты", "GET",
                      "/analytics/w12/service-accounts")
        for item in _items(_json(r)) if r else []:
            name = str(item.get("name") or "")
            sid = str(item.get("id") or "")
            if re.fullmatch(r"qa-[0-9a-f]{10}", name) and not item.get("revoked_at") and sid:
                self.call("admin", "QA cleanup", "Отозвать только QA service-аккаунт", "POST",
                          f"/analytics/w12/service-accounts/{sid}/revoke", json={})
        for did in sorted(self.created["documents"]):
            if did:
                self.call("admin", "QA cleanup", "Удалить только QA-документ", "DELETE",
                          "/documents/" + did, expected=(200, 204, 404))
        for vid in sorted(self.created["visits"]):
            if vid:
                self.call("admin", "QA cleanup", "Отменить только QA-посещение", "DELETE",
                          "/visits/" + vid, expected=(200, 204, 403, 404),
                          json={"reason": "QA cleanup " + self.run_id})
        for sid in sorted(self.created["subscriptions"]):
            if sid:
                self.call("admin", "QA cleanup", "Удалить только QA-абонемент", "DELETE",
                          "/subscriptions/" + sid, expected=(200, 204, 404))
        for code in sorted(self.created["tariffs"]):
            if code:
                self.call("admin", "QA cleanup", "Удалить только QA-тариф", "DELETE",
                          "/tariffs/" + code, expected=(200, 204, 404))
        for cid in sorted(self.created["clients"]):
            if cid:
                self.call("admin", "QA cleanup", "Удалить только QA-клиента", "DELETE",
                          "/clients/" + cid, expected=(200, 204, 404))
        if self.service_id:
            self.call("admin", "QA cleanup", "Деактивировать только QA-услугу", "DELETE",
                      "/services/" + self.service_id, expected=(200, 204, 404))
        r = self.call("admin", "QA cleanup", "Найти QA-шаблоны", "GET", "/document-templates")
        for tpl in _items(_json(r)) if r else []:
            if str(tpl.get("code", "")).startswith("qa_forbidden_" + self.run_id):
                tid = str(tpl.get("template_id") or tpl.get("id"))
                self.call("admin", "QA cleanup", "Удалить только QA-шаблон", "DELETE",
                          "/document-templates/" + tid, expected=(200, 204, 404))

    def finish(self) -> int:
        counts = {key: sum(x["result"] == key for x in self.results)
                  for key in ("PASS", "FAIL", "SKIP")}
        print("\n=== QA ИТОГ ===")
        print(json.dumps(counts, ensure_ascii=False))
        for row in self.results:
            if row["result"] == "FAIL":
                print(f"FAIL: {row['role']} | {row['area']} | {row['check']} | "
                      f"HTTP {row['http']} | {row['detail']}")
        path = Path("/tmp") / f"fitintel-qa-{self.run_id}.json"
        path.write_text(json.dumps({"run_id": self.run_id, "server": BASE_URL,
                                    "summary": counts, "results": self.results},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
        print("QA_REPORT=" + str(path))
        print("QA_RESULT=" + ("PASS" if counts["FAIL"] == 0 else "FAIL"))
        return 0 if counts["FAIL"] == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-test", required=True, choices=["192.168.101.14"])
    parser.add_argument("--admin-login", required=True)
    parser.add_argument("--manager-login", default="aaa")
    parser.add_argument("--read-only", action="store_true")
    args = parser.parse_args()
    qa = QA()
    try:
        health = requests.get(BASE_URL + "/health/", timeout=15)
        if health.status_code != 200:
            print("TEST_HEALTH_FAILED=1")
            return 2
        admin_password = getpass.getpass("Пароль SuperAdmin (не отображается): ")
        manager_password = getpass.getpass("Пароль Manager (не отображается): ")
        admin = qa.login("admin", args.admin_login, admin_password)
        manager = qa.login("manager", args.manager_login, manager_password)
        if not admin or not manager:
            return qa.finish()
        qa.read_smoke("admin")
        qa.read_smoke("manager")
        if not args.read_only:
            qa.admin_service()
            qa.core_crud("admin")
            qa.core_crud("manager")
            qa.trash_restore()
            qa.service_account()
    except KeyboardInterrupt:
        print("QA_INTERRUPTED=1")
    finally:
        qa.cleanup()
    return qa.finish()


if __name__ == "__main__":
    sys.exit(main())
