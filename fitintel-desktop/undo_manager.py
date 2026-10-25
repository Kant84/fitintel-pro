# -*- coding: utf-8 -*-
"""Global HTTP-level undo history for FitIntel Desktop.

Only explicitly reversible operations are registered. History is in-memory and
contains no authentication requests or password/secret changes.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import threading
from typing import Any
from urllib.parse import urlsplit


@dataclass
class UndoEntry:
    label: str
    method: str
    path: str
    payload: Any = None
    entity: str | None = None
    entity_id: str | None = None


class UndoManager:
    MAX_HISTORY = 100

    # Creating a record is undone by deleting that new record.
    CREATE_RULES = (
        (r"^/clients/$", "id", "/clients/{value}"),
        (r"^/users/$", "id", "/users/{value}"),
        (r"^/tariffs/$", "code", "/tariffs/{value}"),
        (r"^/services$", "id", "/services/{value}"),
        (r"^/documents$", "document_id", "/documents/{value}"),
        (r"^/document-templates$", "id", "/document-templates/{value}"),
        (r"^/subscriptions/$", "id", "/subscriptions/{value}"),
        (r"^/zones$", "id", "/zones/{value}"),
        (r"^/warehouse/(?:products|products-create)$", "id", "/warehouse/products/{value}"),
        (r"^/bonus-rules$", "id", "/bonus-rules/{value}"),
        (r"^/credentials/(?:card|bracelet)$", "id", "/credentials/{value}"),
        (r"^/staff/positions$", "id", "/staff/positions/{value}"),
        (r"^/connectors$", "id", "/connectors/{value}"),
        (r"^/playlists$", "id", "/playlists/{value}"),
        (r"^/schedule$", "id", "/schedule/{value}"),
        (r"^/sfx$", "id", "/sfx/{value}"),
        (r"^/roles$", "id", "/roles/{value}"),
        (r"^/face-id/register$", "template_id", "/face-id/{value}"),
    )

    # Creating these records has a compensating action instead of DELETE.
    CREATE_ACTION_RULES = (
        (r"^/services/[^/]+/book$", "booking_id", "/services/bookings/{value}/cancel"),
        (r"^/miniapp/booking$", "booking_id", "/miniapp/booking/{value}"),
        (r"^/visits/manual$", "visit_id", "/visits/{value}"),
    )

    # Physical deletion is undone through the server-side snapshot.
    TRASH_DELETE_RULES = (
        (r"^/clients/[^/]+$", "clients"),
        (r"^/users/[^/]+$", "users"),
        (r"^/tariffs/[^/]+$", "tariffs"),
        (r"^/document-templates/[^/]+$", "document_templates"),
        (r"^/zones/[^/]+$", "music_zones"),
        (r"^/documents/[^/]+$", "documents"),
        (r"^/subscriptions/[^/]+$", "subscriptions"),
        (r"^/credentials/[^/]+$", "credentials"),
        (r"^/bonus-rules/[^/]+$", "bonus_rules"),
        (r"^/staff/positions/[^/]+$", "staff_positions"),
        (r"^/connectors/[^/]+$", "connectors"),
        (r"^/roles/[^/]+$", "roles"),
        (r"^/playlists/[^/]+$", "music_playlists"),
        (r"^/schedule/[^/]+$", "music_schedule"),
        (r"^/sfx/[^/]+$", "music_sfx"),
        (r"^/analytics/clients/[^/]+/contacts/[^/]+$", "client_contacts"),
        (r"^/analytics/clients/[^/]+/cars/[^/]+$", "client_cars"),
    )

    SOFT_DELETE_RULES = (
        (r"^/services/[^/]+$", "PUT"),
        (r"^/warehouse/products/[^/]+$", "PUT"),
    )

    POST_UPDATE_EXACT = {
        "/settings": "POST",
        "/max-bot/config": "POST",
    }

    SENSITIVE_KEYS = {
        "password", "password_hash", "new_password", "old_password",
        "token", "access_token", "refresh_token", "secret", "secret_key",
        "auth_password", "api_key", "private_key",
    }

    def __init__(self, api):
        self.api = api
        self._history: list[UndoEntry] = []
        self._lock = threading.RLock()
        self._original_request = None
        self._undo_lock = threading.RLock()

    def install(self):
        if self._original_request is not None:
            return
        self._original_request = self.api.session.request
        manager = self

        def request_with_undo(method, url, **kwargs):
            return manager._request(method, url, **kwargs)

        self.api.session.request = request_with_undo

    def count(self) -> int:
        with self._lock:
            return len(self._history)

    def last_label(self) -> str:
        with self._lock:
            return self._history[-1].label if self._history else ""

    def clear(self):
        with self._lock:
            self._history.clear()

    def undo_last(self) -> str:
        # Network compensation is serialized: two clicks cannot undo one entry twice.
        with self._undo_lock:
            with self._lock:
                if not self._history:
                    raise RuntimeError("История действий пуста")
                entry = self._history[-1]

            path = entry.path
            if entry.entity and entry.entity_id:
                # Snapshot ids change after restore -> delete cycles. Resolve the
                # current snapshot by stable entity identity instead of reusing
                # a stale /trash/{snapshot_id}/restore URL.
                snapshot = self._find_snapshot(entry.entity, entry.entity_id)
                if snapshot is None:
                    raise RuntimeError(
                        "Не удалось отменить действие: снимок уже восстановлен "
                        "или срок его хранения в корзине истёк"
                    )
                path = "/trash/%s/restore" % snapshot["id"]

            response = self._call(entry.method, path, entry.payload)
            if not 200 <= response.status_code < 300:
                raise RuntimeError(
                    "Не удалось отменить действие: HTTP %s — %s"
                    % (response.status_code, response.text[:400])
                )

            with self._lock:
                if self._history and self._history[-1] is entry:
                    self._history.pop()
                elif entry in self._history:
                    self._history.remove(entry)
            return entry.label

    # ---------- request capture ----------

    def _request(self, method, url, **kwargs):
        method = str(method).upper()
        path = self._path(url)
        if self._original_request is None:
            raise RuntimeError("UndoManager is not installed")

        if method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return self._original_request(method, url, **kwargs)
        # A new user's password is never copied into history: only the new id
        # and the inverse DELETE path are retained. Password changes stay excluded.
        allow_user_create = method == "POST" and path == "/users/"
        if self._is_sensitive(path, kwargs.get("json"), allow_user_create):
            return self._original_request(method, url, **kwargs)

        try:
            context = self._before(method, path, kwargs)
        except Exception:
            context = None

        response = self._original_request(method, url, **kwargs)

        if context is not None and 200 <= response.status_code < 300:
            try:
                self._after(context, response)
            except Exception:
                # Undo must never break the original successful operation.
                pass
        return response

    def _before(self, method, path, kwargs):
        payload = kwargs.get("json")

        if method in {"PUT", "PATCH"}:
            if not isinstance(payload, dict) or not payload:
                return None
            return self._update_context(method, path, path, payload)

        if method == "POST":
            if re.match(r"^/trash/[^/]+/restore$", path):
                return {"kind": "trash_restore", "path": path}

            if path in self.POST_UPDATE_EXACT and isinstance(payload, dict):
                return self._update_context(
                    self.POST_UPDATE_EXACT[path], path, path, payload
                )

            m = re.match(r"^/ui-config/roles/([^/]+)/reset$", path)
            if m:
                screens_path = "/ui-config/roles/%s/screens" % m.group(1)
                return self._update_context("PUT", path, screens_path, {"screens": None},
                                            undo_path=screens_path)

            m = re.match(r"^/(?:analytics/)?users/([^/]+)/department$", path)
            if m and isinstance(payload, dict):
                return self._update_context(
                    "POST", path, "/users/%s" % m.group(1), payload
                )

            m = re.match(r"^/analytics/users/[^/]+/position$", path)
            if m and isinstance(payload, dict):
                return self._update_context("POST", path, path, payload)

            m = re.match(r"^/users/([^/]+)/deactivate$", path)
            if m:
                user_path = "/users/%s" % m.group(1)
                before = self._get_resource(user_path)
                if before is not None:
                    return {
                        "entry": UndoEntry(
                            "Деактивация пользователя", "PATCH", user_path,
                            {"is_active": before.get("is_active", True)},
                        )
                    }
                return None

            m = re.match(r"^/zones/([^/]+)/volume$", path)
            if m and isinstance(payload, dict):
                zone_path = "/zones/%s" % m.group(1)
                before = self._get_resource(zone_path)
                if before is not None:
                    return {
                        "entry": UndoEntry(
                            "Изменение громкости", "POST", path,
                            {"level": before.get("volume", 50)},
                        )
                    }
                return None

            # Role permissions are reversible in both directions.
            m = re.match(r"^/roles/([^/]+)/permissions$", path)
            if m and isinstance(payload, dict) and payload.get("permission_id"):
                return {"entry": UndoEntry(
                    "Изменение прав роли", "DELETE",
                    "/roles/%s/permissions/%s" % (m.group(1), payload["permission_id"]),
                )}

            m = re.match(r"^/users/([^/]+)/roles/(assign|revoke)$", path)
            if m and isinstance(payload, dict):
                inverse = "revoke" if m.group(2) == "assign" else "assign"
                return {"entry": UndoEntry(
                    "Изменение ролей пользователя", "POST",
                    "/users/%s/roles/%s" % (m.group(1), inverse), payload,
                )}

            m = re.match(r"^/credentials/([^/]+)/(block|unblock)$", path)
            if m:
                inverse = "unblock" if m.group(2) == "block" else "block"
                inverse_payload = None if inverse == "unblock" else {"reason": "Отмена действия"}
                return {"entry": UndoEntry(
                    "Изменение блокировки доступа", "POST",
                    "/credentials/%s/%s" % (m.group(1), inverse), inverse_payload,
                )}

            m = re.match(r"^/subscriptions/([^/]+)/freeze$", path)
            if m:
                return {"entry": UndoEntry(
                    "Заморозка абонемента", "POST",
                    "/subscriptions/%s/unfreeze" % m.group(1),
                )}

            m = re.match(r"^/lockers/([^/]+)/assign$", path)
            if m:
                return {"entry": UndoEntry(
                    "Назначение ячейки", "POST",
                    "/lockers/%s/release" % m.group(1),
                )}

            # Contacts/cars return no id: detect the new row by collection diff.
            m = re.match(r"^(/analytics/clients/[^/]+/(?:contacts|cars))$", path)
            if m:
                before = self._get_collection(m.group(1))
                if before is not None:
                    return {
                        "kind": "create_diff",
                        "path": path,
                        "before_ids": self._collection_ids(before),
                        "response": None,
                    }
                return None

            for pattern, _key, _template in self.CREATE_RULES + self.CREATE_ACTION_RULES:
                if re.match(pattern, path):
                    return {"kind": "create", "path": path, "response": None}
            return None

        if method == "DELETE":
            for pattern, inverse_method in self.SOFT_DELETE_RULES:
                if re.match(pattern, path):
                    before = self._get_resource(path)
                    if before is None:
                        return None
                    return {"entry": UndoEntry(
                        self._label("Удаление", path), inverse_method, path,
                        {"is_active": before.get("is_active", True)},
                    )}

            m = re.match(r"^/roles/([^/]+)/permissions/([^/]+)$", path)
            if m:
                return {"entry": UndoEntry(
                    "Изменение прав роли", "POST",
                    "/roles/%s/permissions" % m.group(1),
                    {"permission_id": m.group(2)},
                )}

            for pattern, entity in self.TRASH_DELETE_RULES:
                if re.match(pattern, path):
                    before = self._get_resource(path)
                    entity_id = path.rstrip("/").split("/")[-1]
                    if isinstance(before, dict):
                        entity_id = before.get("id") or before.get("key") or entity_id
                    return {
                        "kind": "trash_delete", "path": path,
                        "entity": entity, "entity_id": str(entity_id),
                    }
        return None

    def _find_snapshot(self, entity, entity_id):
        data = self._get_json("/trash", params={"entity": entity, "limit": 100})
        items = (data or {}).get("items", [])
        # Never fall back to an arbitrary latest row when ids do not match.
        return next(
            (x for x in items if self._same_id(x.get("entity_id"), entity_id)),
            None,
        )

    def _after(self, context, response):
        if "entry" in context:
            self._push(context["entry"])
            return

        kind = context.get("kind")
        if kind == "trash_restore":
            data = self._json(response)
            undo_path = (data or {}).get("undo_path") if isinstance(data, dict) else None
            if undo_path:
                self._push(UndoEntry(
                    "Восстановление из корзины", "DELETE", undo_path,
                ))
            return

        if kind == "trash_delete":
            snapshot = self._find_snapshot(context["entity"], context["entity_id"])
            if snapshot is None:
                return
            self._push(UndoEntry(
                self._label("Удаление", context["path"]), "POST",
                "/trash/%s/restore" % snapshot["id"],
                entity=context["entity"], entity_id=context["entity_id"],
            ))
            return

        if kind == "create_diff":
            after = self._get_collection(context["path"])
            if after is None:
                return
            new_ids = self._collection_ids(after) - context["before_ids"]
            if len(new_ids) != 1:
                return
            value = new_ids.pop()
            self._push(UndoEntry(
                self._label("Создание", context["path"]), "DELETE",
                context["path"] + "/" + value,
            ))
            return

        if kind == "create":
            data = self._json(response)
            path = context["path"]
            for pattern, key, template in self.CREATE_ACTION_RULES:
                if re.match(pattern, path):
                    value = self._find_value(data, key)
                    if value is not None:
                        inverse_payload = (
                            {"reason": "Отмена последнего действия"}
                            if path == "/visits/manual" else None
                        )
                        self._push(UndoEntry(
                            self._label("Создание", path),
                            "DELETE" if template.startswith("/miniapp/") or template.startswith("/visits/") else "POST",
                            template.format(value=value), inverse_payload,
                        ))
                    return
            for pattern, key, template in self.CREATE_RULES:
                if re.match(pattern, path):
                    value = self._find_value(data, key)
                    if value is not None:
                        self._push(UndoEntry(
                            self._label("Создание", path), "DELETE",
                            template.format(value=value),
                        ))
                    return

    # ---------- undo-entry builders ----------

    def _update_context(self, method, original_path, get_path, payload, undo_path=None):
        before = self._get_resource(get_path)
        if before is None:
            return None
        old = {key: before.get(key) for key in payload}
        return {"entry": UndoEntry(
            self._label("Изменение", original_path), method,
            undo_path or original_path, old,
        )}

    def _push(self, entry):
        with self._lock:
            self._history.append(entry)
            if len(self._history) > self.MAX_HISTORY:
                del self._history[:-self.MAX_HISTORY]

    # ---------- HTTP and response helpers ----------

    def _call(self, method, path, payload=None, **kwargs):
        if payload is not None:
            kwargs["json"] = payload
        kwargs.setdefault("timeout", 30)
        return self._original_request(method, self.api._url(path), **kwargs)

    def _get_json(self, path, **kwargs):
        response = self._call("GET", path, **kwargs)
        if not 200 <= response.status_code < 300:
            return None
        data = self._json(response)
        return data if isinstance(data, (dict, list)) else None

    def _get_resource(self, path):
        data = self._get_json(path)
        if isinstance(data, dict):
            return self._unwrap_resource(data)

        # Many routers expose only a collection GET, not GET item.
        parts = path.rstrip("/").split("/")
        if len(parts) < 3:
            return None
        value = parts[-1]
        collection = "/".join(parts[:-1])
        data = self._get_json(collection)
        return self._find_in_collection(data, value)

    def _get_collection(self, path):
        data = self._get_json(path)
        if data is not None:
            return data
        return None

    @staticmethod
    def _unwrap_resource(data):
        for key in ("item", "data", "user", "client", "service", "product"):
            value = data.get(key)
            if isinstance(value, dict):
                return value
        return data

    @classmethod
    def _find_in_collection(cls, data, wanted):
        if isinstance(data, list):
            for item in data:
                found = cls._find_in_collection(item, wanted)
                if found is not None:
                    return found
        elif isinstance(data, dict):
            for key in ("id", "key", "code", "username"):
                if cls._same_id(data.get(key), wanted):
                    return data
            for value in data.values():
                if isinstance(value, (list, dict)):
                    found = cls._find_in_collection(value, wanted)
                    if found is not None:
                        return found
        return None

    @classmethod
    def _collection_ids(cls, data):
        result = set()
        if isinstance(data, list):
            for item in data:
                result |= cls._collection_ids(item)
        elif isinstance(data, dict):
            if data.get("id") is not None:
                result.add(str(data["id"]))
            for value in data.values():
                if isinstance(value, (list, dict)):
                    result |= cls._collection_ids(value)
        return result

    @classmethod
    def _find_value(cls, data, preferred):
        if isinstance(data, dict):
            for key in (preferred, "id", preferred + "_id"):
                value = data.get(key)
                if isinstance(value, (str, int)) and str(value):
                    return str(value)
            for value in data.values():
                if isinstance(value, (dict, list)):
                    found = cls._find_value(value, preferred)
                    if found is not None:
                        return found
        elif isinstance(data, list):
            for item in data:
                found = cls._find_value(item, preferred)
                if found is not None:
                    return found
        return None

    @staticmethod
    def _json(response):
        try:
            return response.json()
        except Exception:
            return None

    @staticmethod
    def _same_id(left, right):
        return str(left or "").replace("-", "") == str(right or "").replace("-", "")

    @staticmethod
    def _path(url):
        path = urlsplit(str(url)).path
        marker = "/api/v1"
        if marker in path:
            path = path.split(marker, 1)[1]
        return path or "/"

    @classmethod
    def _is_sensitive(cls, path, payload, allow_create=False):
        lowered = path.lower()
        if any(x in lowered for x in (
            "/auth/", "reset-password", "change-password", "integrations-config",
        )):
            return True
        if any(x in lowered for x in ("secret", "password", "token")):
            return True
        if not allow_create and isinstance(payload, dict):
            return any(str(key).lower() in cls.SENSITIVE_KEYS for key in payload)
        return False

    @staticmethod
    def _label(action, path):
        rules = (
            ("clients", "клиента"), ("users", "пользователя"),
            ("tariffs", "тарифа"), ("services", "услуги"),
            ("documents", "документа"), ("subscriptions", "абонемента"),
            ("credentials", "доступа"), ("warehouse", "товара"),
            ("bonus-rules", "бонусного правила"), ("staff/positions", "должности"),
            ("roles", "роли"), ("zones", "музыкальной зоны"),
            ("playlists", "плейлиста"), ("schedule", "расписания"),
            ("sfx", "звука"), ("settings", "настроек"),
            ("club-params", "параметра клуба"), ("ui-config", "прав доступа к экранам"),
            ("connectors", "коннектора"), ("contacts", "контакта"),
            ("cars", "автомобиля"), ("face-id", "Face ID"),
        )
        resource = "данных"
        for marker, name in rules:
            if marker in path:
                resource = name
                break
        return "%s: %s" % (action, resource)
