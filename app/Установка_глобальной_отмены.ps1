param(
    [string]$RepoRoot = (Get-Location).Path
)

$ErrorActionPreference = "Stop"

function Read-Utf8([string]$Path) {
    return [IO.File]::ReadAllText($Path, [Text.Encoding]::UTF8)
}

function Write-Utf8([string]$Path, [string]$Text) {
    $parent = Split-Path -Parent $Path
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    [IO.File]::WriteAllText($Path, $Text, (New-Object Text.UTF8Encoding($false)))
}

$required = @(
    "app\api\v1\trash.py",
    "app\services\user_service.py",
    "app\api\v1\warehouse.py",
    "fitintel-desktop\api\client.py",
    "fitintel-desktop\windows\main_window.py",
    "fitintel-desktop\windows\clients_tab.py"
)
foreach ($relative in $required) {
    if (-not (Test-Path (Join-Path $RepoRoot $relative))) {
        throw "Файл не найден: $relative. Запустите скрипт из корня репозитория FitIntel."
    }
}

$backup = Join-Path $RepoRoot (".undo-backup\" + (Get-Date -Format "yyyyMMdd-HHmmss"))
foreach ($relative in $required) {
    $destination = Join-Path $backup $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item (Join-Path $RepoRoot $relative) $destination
}
Write-Host "Резервная копия: $backup"


$undoManager = @'
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

            response = self._call(entry.method, entry.path, entry.payload)
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
            data = self._get_json("/trash", params={"entity": context["entity"], "limit": 100})
            items = (data or {}).get("items", [])
            if not items:
                return
            path_id = context["entity_id"]
            snapshot = next(
                (x for x in items if self._same_id(x.get("entity_id"), path_id)),
                None,
            )
            # Never restore an arbitrary latest row when ids do not match.
            if snapshot is None:
                return
            self._push(UndoEntry(
                self._label("Удаление", context["path"]), "POST",
                "/trash/%s/restore" % snapshot["id"],
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
                        self._push(UndoEntry(
                            self._label("Создание", path),
                            "DELETE" if template.startswith("/miniapp/") or template.startswith("/visits/") else "POST",
                            template.format(value=value),
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

'@
Write-Utf8 (Join-Path $RepoRoot "fitintel-desktop\undo_manager.py") $undoManager

$trashRouter = @'
# -*- coding: utf-8 -*-
"""Корзина: просмотр снимков удалённых сущностей и их восстановление."""
import json
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from app.api.dependencies import get_current_user

router = APIRouter(prefix="/trash", tags=["trash"])

ALLOWED = {
    "clients",
    "users",
    "tariffs",
    "document_templates",
    "music_zones",
    "documents",
    "subscriptions",
    "credentials",
    "bonus_rules",
    "staff_positions",
    "connectors",
    "roles",
    "music_playlists",
    "music_schedule",
    "music_sfx",
    "client_contacts",
    "client_cars",
}


def _admin(user):
    if not (
        getattr(user, "is_superuser", False)
        or str(getattr(user, "username", "")).lower() == "superadmin"
    ):
        raise HTTPException(status_code=403, detail="superadmin required")
    return user


def _undo_path(entity, entity_id, payload):
    """Path of the inverse deletion used by global desktop Undo."""
    value = quote(str(payload.get("code") if entity == "tariffs" else entity_id), safe="")
    routes = {
        "clients": "/clients/%s",
        "users": "/users/%s",
        "tariffs": "/tariffs/%s",
        "document_templates": "/document-templates/%s",
        "music_zones": "/zones/%s",
        "documents": "/documents/%s",
        "subscriptions": "/subscriptions/%s",
        "credentials": "/credentials/%s",
        "bonus_rules": "/bonus-rules/%s",
        "staff_positions": "/staff/positions/%s",
        "connectors": "/connectors/%s",
        "roles": "/roles/%s",
        "music_playlists": "/playlists/%s",
        "music_schedule": "/schedule/%s",
        "music_sfx": "/sfx/%s",
    }
    if entity in ("client_contacts", "client_cars"):
        collection = "contacts" if entity == "client_contacts" else "cars"
        return "/analytics/clients/%s/%s/%s" % (
            quote(str(payload.get("client_id") or ""), safe=""), collection, value,
        )
    template = routes.get(entity)
    return template % value if template else None


@router.get("")
def trash_list(
    entity: str = "",
    limit: int = Query(default=200, ge=1, le=500),
    user=Depends(get_current_user),
):
    _admin(user)

    if entity and entity not in ALLOWED:
        raise HTTPException(status_code=400, detail="unknown entity")

    from app.db.session import engine

    sql = """
        SELECT id::text, entity, entity_id, payload, deleted_at
        FROM deletion_snapshots
        WHERE deleted_at > now() - interval '30 days'
    """
    params = {"limit": limit}

    if entity:
        sql += " AND entity = :entity"
        params["entity"] = entity

    sql += " ORDER BY deleted_at DESC LIMIT :limit"

    with engine.begin() as connection:
        rows = connection.execute(text(sql), params).mappings().all()

    items = []
    for row in rows:
        payload = row["payload"] or {}
        name = (
            (payload.get("last_name") or "")
            + " "
            + (payload.get("first_name") or "")
        ).strip()
        name = (
            name
            or payload.get("username")
            or payload.get("name")
            or payload.get("code")
            or row["entity_id"]
        )
        items.append({
            "id": row["id"],
            "entity": row["entity"],
            "entity_id": row["entity_id"],
            "name": str(name)[:80],
            "deleted_at": row["deleted_at"].isoformat(),
        })

    return {"ok": True, "items": items}


@router.post("/{sid}/restore")
def trash_restore(sid: str, user=Depends(get_current_user)):
    _admin(user)

    from app.db.session import engine

    with engine.begin() as connection:
        snapshot = connection.execute(
            text("""
                SELECT entity, entity_id, payload
                FROM deletion_snapshots
                WHERE id::text = :sid
                FOR UPDATE
            """),
            {"sid": sid},
        ).mappings().first()

        if not snapshot:
            raise HTTPException(status_code=404, detail="snapshot not found")

        entity = snapshot["entity"]
        if entity not in ALLOWED:
            raise HTTPException(status_code=400, detail="entity not restorable")

        payload = snapshot["payload"] or {}
        payload_json = json.dumps(payload, ensure_ascii=False)
        restored = None

        if entity == "clients":
            # A soft-deleted client still exists; restore its original state.
            restored = connection.execute(
                text("""
                    UPDATE clients
                    SET is_active = COALESCE(
                            (CAST(:payload AS jsonb)->>'is_active')::boolean,
                            TRUE
                        ),
                        status = COALESCE(
                            CAST(:payload AS jsonb)->>'status',
                            'ACTIVE'
                        ),
                        updated_at = now()
                    WHERE id::text = :entity_id
                    RETURNING id
                """),
                {"payload": payload_json, "entity_id": snapshot["entity_id"]},
            ).first()

        elif entity == "users":
            # User deletion anonymizes the existing row instead of physically
            # deleting it. Restore login, e-mail, active flag and original hash.
            restored = connection.execute(
                text("""
                    UPDATE users
                    SET username = CAST(:payload AS jsonb)->>'username',
                        email = CAST(:payload AS jsonb)->>'email',
                        is_active = COALESCE(
                            (CAST(:payload AS jsonb)->>'is_active')::boolean,
                            TRUE
                        ),
                        password_hash = COALESCE(
                            CAST(:payload AS jsonb)->>'password_hash',
                            password_hash
                        )
                    WHERE id::text = :entity_id
                    RETURNING id
                """),
                {"payload": payload_json, "entity_id": snapshot["entity_id"]},
            ).first()

            if not restored:
                restored = connection.execute(
                    text("""
                        INSERT INTO users
                        SELECT * FROM jsonb_populate_record(
                            NULL::users,
                            CAST(:payload AS jsonb) - '_roles'
                        )
                        ON CONFLICT (id) DO NOTHING
                        RETURNING id
                    """),
                    {"payload": payload_json},
                ).first()

            if restored:
                connection.execute(
                    text("DELETE FROM user_roles WHERE user_id::text = :entity_id"),
                    {"entity_id": snapshot["entity_id"]},
                )
                connection.execute(
                    text("""
                        INSERT INTO user_roles
                        SELECT (parsed.role_row).*
                        FROM (
                            SELECT jsonb_populate_record(
                                NULL::user_roles, value
                            ) AS role_row
                            FROM jsonb_array_elements(
                                COALESCE(
                                    CAST(:payload AS jsonb)->'_roles',
                                    '[]'::jsonb
                                )
                            )
                        ) AS parsed
                        ON CONFLICT DO NOTHING
                    """),
                    {"payload": payload_json},
                )

        else:
            restored = connection.execute(
                text(f"""
                    INSERT INTO "{entity}"
                    SELECT * FROM jsonb_populate_record(
                        NULL::"{entity}",
                        CAST(:payload AS jsonb)
                    )
                    ON CONFLICT (id) DO NOTHING
                    RETURNING id
                """),
                {"payload": payload_json},
            ).first()

        # A physically deleted client/user may be restored by the generic INSERT.
        if not restored and entity in ("clients", "users"):
            restored = connection.execute(
                text(f"""
                    INSERT INTO "{entity}"
                    SELECT * FROM jsonb_populate_record(
                        NULL::"{entity}",
                        CAST(:payload AS jsonb) - '_roles'
                    )
                    ON CONFLICT (id) DO NOTHING
                    RETURNING id
                """),
                {"payload": payload_json},
            ).first()

        if not restored:
            raise HTTPException(
                status_code=409,
                detail="entity already exists; snapshot kept",
            )

        connection.execute(
            text("DELETE FROM deletion_snapshots WHERE id::text = :sid"),
            {"sid": sid},
        )

    return {
        "ok": True,
        "restored": entity,
        "entity_id": snapshot["entity_id"],
        "undo_path": _undo_path(entity, snapshot["entity_id"], payload),
    }

'@
Write-Utf8 (Join-Path $RepoRoot "app\api\v1\trash.py") $trashRouter

$trashSql = @'
BEGIN;

CREATE TABLE IF NOT EXISTS deletion_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    deleted_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_deletion_snapshots_entity
    ON deletion_snapshots (entity, entity_id, deleted_at DESC);

CREATE OR REPLACE FUNCTION trash_snapshot() RETURNS trigger AS $$
BEGIN
    INSERT INTO deletion_snapshots (entity, entity_id, payload)
    VALUES (TG_TABLE_NAME, COALESCE(OLD.id::text, ''), row_to_json(OLD));
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    entity_table TEXT;
BEGIN
    FOREACH entity_table IN ARRAY ARRAY[
        'clients',
        'users',
        'tariffs',
        'document_templates',
        'music_zones',
        'documents',
        'subscriptions',
        'credentials',
        'bonus_rules',
        'staff_positions',
        'connectors',
        'roles',
        'music_playlists',
        'music_schedule',
        'music_sfx',
        'client_contacts',
        'client_cars'
    ]
    LOOP
        -- Some optional modules create their tables lazily. They are skipped
        -- here and will be picked up by a repeated execution of this script.
        IF to_regclass('public.' || entity_table) IS NOT NULL
           AND NOT EXISTS (
               SELECT 1
               FROM pg_trigger
               WHERE tgrelid = to_regclass('public.' || entity_table)
                 AND tgname = 'trash_snapshot_trigger'
                 AND NOT tgisdisabled
           )
        THEN
            EXECUTE format(
                'CREATE TRIGGER trash_snapshot_trigger '
                || 'BEFORE DELETE ON public.%I '
                || 'FOR EACH ROW EXECUTE FUNCTION trash_snapshot()',
                entity_table
            );
        END IF;
    END LOOP;
END;
$$;

COMMIT;

SELECT
    c.relname AS table_name,
    t.tgname AS trigger_name
FROM pg_trigger AS t
JOIN pg_class AS c ON c.oid = t.tgrelid
WHERE t.tgname = 'trash_snapshot_trigger'
  AND NOT t.tgisdisabled
ORDER BY c.relname;

'@
Write-Utf8 (Join-Path $RepoRoot "deploy\trash_undo.sql") $trashSql

$mainWindowUndo = @'


# === GLOBAL UNDO: header icon + Edit menu + application-wide Ctrl+Z ===
def _global_undo_install(self):
    if getattr(self, "_global_undo_ready", False):
        return
    self._global_undo_ready = True
    self._global_undo_busy = False

    from pathlib import Path as _UndoPath
    from PyQt6.QtCore import Qt as _UndoQt, QTimer as _UndoTimer, QSize as _UndoSize
    from PyQt6.QtGui import QAction as _UndoAction, QIcon as _UndoIcon
    from PyQt6.QtWidgets import QToolButton as _UndoButton

    icon_path = _UndoPath(__file__).parents[1] / "assets" / "undo.png"
    icon = _UndoIcon(str(icon_path)) if icon_path.exists() else _UndoIcon()

    self._undo_action = _UndoAction(icon, "Отмена последнего действия", self)
    self._undo_action.setShortcut("Ctrl+Z")
    # ApplicationShortcut also works while a modal child dialog is active.
    self._undo_action.setShortcutContext(_UndoQt.ShortcutContext.ApplicationShortcut)
    self._undo_action.triggered.connect(self._global_undo)
    self.addAction(self._undo_action)

    edit_menu = None
    view_menu_action = None
    for action in self.menuBar().actions():
        title = action.text().strip().lower()
        if title.startswith("правка"):
            edit_menu = action.menu()
        elif title.startswith("вид"):
            view_menu_action = action
    if edit_menu is None:
        edit_menu = self.menuBar().addMenu("Правка")
        if view_menu_action is not None:
            self.menuBar().removeAction(edit_menu.menuAction())
            self.menuBar().insertMenu(view_menu_action, edit_menu)
    edit_menu.addAction(self._undo_action)

    self._undo_button = _UndoButton(self._header)
    self._undo_button.setDefaultAction(self._undo_action)
    self._undo_button.setToolButtonStyle(_UndoQt.ToolButtonStyle.ToolButtonIconOnly)
    self._undo_button.setIconSize(_UndoSize(30, 24))
    self._undo_button.setFixedSize(42, 38)
    self._undo_button.setCursor(_UndoQt.CursorShape.PointingHandCursor)
    self._undo_button.setStyleSheet(
        "QToolButton { border: 1px solid transparent; border-radius: 6px; padding: 4px; }"
        "QToolButton:hover { background: rgba(59,130,246,0.14); border-color: #3b82f6; }"
        "QToolButton:disabled { opacity: 0.35; }"
    )
    # After the stretch, before user information and Logout.
    self._header.layout().insertWidget(2, self._undo_button)

    self._undo_timer = _UndoTimer(self)
    self._undo_timer.setInterval(250)
    self._undo_timer.timeout.connect(self._global_undo_sync)
    self._undo_timer.start()
    self._global_undo_sync()


def _global_undo_sync(self):
    manager = getattr(self.api, "undo", None)
    count = manager.count() if manager is not None else 0
    label = manager.last_label() if manager is not None and count else ""
    enabled = bool(count) and not getattr(self, "_global_undo_busy", False)
    self._undo_action.setEnabled(enabled)
    tooltip = "Отмена последнего действия (Ctrl+Z)"
    tooltip += ("\n" + label) if label else "\nИстория действий пуста"
    self._undo_action.setToolTip(tooltip)
    self._undo_button.setToolTip(tooltip)
    self._undo_action.setStatusTip(tooltip.replace("\n", ": "))


def _global_undo(self, _checked=False):
    if getattr(self, "_global_undo_busy", False):
        return
    manager = getattr(self.api, "undo", None)
    if manager is None or not manager.count():
        return

    self._global_undo_busy = True
    self._global_undo_sync()
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        label = manager.undo_last()
        self._refresh_current()
        self.status.showMessage("Отменено: " + label, 6000)
    except Exception as exc:
        QMessageBox.warning(self, "Отмена последнего действия", str(exc)[:600])
    finally:
        QApplication.restoreOverrideCursor()
        self._global_undo_busy = False
        self._global_undo_sync()


MainWindow._global_undo_install = _global_undo_install
MainWindow._global_undo_sync = _global_undo_sync
MainWindow._global_undo = _global_undo

_global_undo_orig_init = MainWindow.__init__


def _global_undo_init(self, *args, **kwargs):
    _global_undo_orig_init(self, *args, **kwargs)
    self._global_undo_install()


MainWindow.__init__ = _global_undo_init
# === GLOBAL UNDO END ===

'@
$path = Join-Path $RepoRoot "fitintel-desktop\windows\main_window.py"
$text = Read-Utf8 $path
if (-not $text.Contains("# === GLOBAL UNDO: header icon")) {
    Write-Utf8 $path ($text + $mainWindowUndo)
}

$apiUndo = @'


# === GLOBAL UNDO: outermost API request interceptor ===
from undo_manager import UndoManager as _GlobalUndoManager

_global_undo_orig_api_init = ApiClient.__init__


def _global_undo_api_init(self, base_url="http://localhost:8001/api/v1"):
    _global_undo_orig_api_init(self, base_url)
    self.undo = _GlobalUndoManager(self)
    # Installed after all earlier wrappers, so every tab/dialog uses one history.
    self.undo.install()


ApiClient.__init__ = _global_undo_api_init

_global_undo_orig_clear_token = ApiClient.clear_token


def _global_undo_clear_token(self):
    # Never carry reversible actions into another authenticated session.
    if getattr(self, "undo", None) is not None:
        self.undo.clear()
    return _global_undo_orig_clear_token(self)


ApiClient.clear_token = _global_undo_clear_token
# === GLOBAL UNDO API END ===

'@
$path = Join-Path $RepoRoot "fitintel-desktop\api\client.py"
$text = Read-Utf8 $path
if (-not $text.Contains("# === GLOBAL UNDO: outermost API")) {
    Write-Utf8 $path ($text + $apiUndo)
}

$userDeleteMethod = @'
    def delete_user(self, user):
        """Soft-delete with a complete restorable user and role snapshot."""
        # === USER TRASH SNAPSHOT ===
        import uuid as _uuid
        from sqlalchemy import text as _text
        from app.core.security import get_password_hash

        uid = str(user.id)
        self.db.execute(_text("""
            INSERT INTO deletion_snapshots (entity, entity_id, payload)
            SELECT 'users', :uid,
                   row_to_json(u)::jsonb || jsonb_build_object(
                       '_roles', COALESCE((
                           SELECT jsonb_agg(row_to_json(ur))
                           FROM user_roles AS ur
                           WHERE ur.user_id = u.id
                       ), '[]'::jsonb)
                   )
            FROM users AS u
            WHERE u.id::text = :uid
              AND NOT EXISTS (
                  SELECT 1
                  FROM deletion_snapshots AS s
                  WHERE s.entity = 'users'
                    AND s.entity_id = :uid
                    AND s.deleted_at > now() - interval '30 days'
              )
        """), {"uid": uid})

        # Keep historical FK references, but make the account unusable.
        self.db.execute(_text("DELETE FROM user_roles WHERE user_id = :uid"),
                        {"uid": uid})
        user.is_active = False
        user.username = f"deleted_{uid[:8]}"
        user.email = f"deleted_{uid[:8]}@deleted.local"
        user.password_hash = get_password_hash(_uuid.uuid4().hex)
        self.db.commit()


'@
$path = Join-Path $RepoRoot "app\services\user_service.py"
$text = Read-Utf8 $path
if (-not $text.Contains("# === USER TRASH SNAPSHOT ===")) {
    $pattern = "(?ms)^    def delete_user\(self, user\):.*?(?=^    def build_user_response\(self, user\) -> dict:)"
    $rx = [Text.RegularExpressions.Regex]::new($pattern)
    if ($rx.Matches($text).Count -ne 1) {
        throw "Не найден единственный метод UserService.delete_user; файл не изменён."
    }
    Write-Utf8 $path ($rx.Replace($text, $userDeleteMethod, 1))
}

$path = Join-Path $RepoRoot "fitintel-desktop\windows\clients_tab.py"
$text = Read-Utf8 $path
if ($text.Contains("# === UNDO LAST CLIENT DELETE ===")) {
    $text = [regex]::Replace(
        $text,
        "(?s)\r?\n        # === UNDO LAST CLIENT DELETE ===.*?(?=\r?\n        b_ref =)",
        ""
    )
    $text = $text.Replace(
        "        for b in (`r`n            b_add, b_edit, b_deact, b_del, b_trash,`r`n            self._undo_delete_btn, b_ref,`r`n        ):`r`n".Replace("`r`n", [Environment]::NewLine),
        "        for b in (b_add, b_edit, b_deact, b_del, b_trash, b_ref):" + [Environment]::NewLine
    )
    # Handle both CRLF and LF source checkouts.
    $text = [regex]::Replace(
        $text,
        "(?s)        for b in \(\s*b_add, b_edit, b_deact, b_del, b_trash,\s*self\._undo_delete_btn, b_ref,\s*\):",
        "        for b in (b_add, b_edit, b_deact, b_del, b_trash, b_ref):"
    )
    $text = [regex]::Replace(
        $text,
        "(?s)\r?\n    def _undo_delete\(self\):.*?(?=\r?\n    def _delete\(self\):)",
        ""
    )
    $text = [regex]::Replace(
        $text,
        "(?m)^\s*self\._last_deleted_client_id = str\(c\[\"id\"\]\)\r?\n\s*self\._undo_delete_btn\.setEnabled\(True\)\r?\n",
        ""
    )
    if ($text.Contains("_undo_delete") -or $text.Contains("Отменить удаление")) {
        throw "Локальная отмена в ClientsTab удалена не полностью."
    }
    Write-Utf8 $path $text
}

$path = Join-Path $RepoRoot "app\api\v1\warehouse.py"
$text = Read-Utf8 $path
$old = 'for k in ("name", "article", "sale_price", "quantity", "unit", "photo_url"):'
$new = 'for k in ("name", "article", "sale_price", "quantity", "unit", "photo_url", "is_active"):'
if ($text.Contains($old)) {
    Write-Utf8 $path $text.Replace($old, $new)
} elseif (-not $text.Contains($new)) {
    throw "Не найден блок обновления WarehouseProduct; файл не изменён."
}


$undoIconBase64 = "iVBORw0KGgoAAAANSUhEUgAAACMAAAAcCAYAAADr9QYhAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAAEnQAABJ0Ad5mH3gAAAGVSURBVFhH7ZR9T4JQFId/qIiiRpr4Ukvr7z5Q360vV/ayGZiKygAV6Z4jbc2JKcrmGs/G7oXL4Nk5v3ulh8enAGdCJhzPglQmiv8jUyjk0bnT0b1v4LajIydnw5V4xJZRlBwaTQ2SJCEQ+9Ewxlgu/HA1HrFk5LwQaVUhZSS+/zIn8NwFz4/h4HOGWtFu15DJrkW2sVoFXCXPm2MycfauWCIBzoiK5UUbKxcqrm+uoGmlcGU3sU5gykuzLdok8kIMRJvsmctzgmXyspApQi0p/MzoW3Acj+eb1OoVVCrFeJXxvCV/nIJL1PULqOr6pwS1yXXnMA0Ls6nDz7RLlcdtDAdTTMV7sdtEP6Pg/lBvaLzVNxkNZzxS23ZBQkdlxrZd9J4Nvl5fDBaMZI8wJBLg31RrZR6dXaIhicjQ+aMUZeiidWURTMqWNbbD1WhOLkMina6OljgUaSf5vg/z08JchP4vEqkM7SbPWWA8svHxPozc0pucXCYQIm89E/3+iFtD9/uSeIAPIZWJIpWJIpWJIpXZDvANsc+T4LNM66kAAAAASUVORK5CYII="
$assets = Join-Path $RepoRoot "fitintel-desktop\assets"
New-Item -ItemType Directory -Force -Path $assets | Out-Null
[IO.File]::WriteAllBytes(
    (Join-Path $assets "undo.png"),
    [Convert]::FromBase64String($undoIconBase64)
)

$python = (Get-Command python -ErrorAction Stop).Source
$validation = @'
import ast
from pathlib import Path
files = [
    "fitintel-desktop/undo_manager.py",
    "fitintel-desktop/api/client.py",
    "fitintel-desktop/windows/main_window.py",
    "fitintel-desktop/windows/clients_tab.py",
    "app/api/v1/trash.py",
    "app/services/user_service.py",
    "app/api/v1/warehouse.py",
]
for name in files:
    path = Path(name)
    ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    print("SYNTAX OK", name)
'@
Push-Location $RepoRoot
try {
    $validation | & $python -
    if ($LASTEXITCODE -ne 0) { throw "Проверка Python завершилась с ошибкой." }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "ГЛОБАЛЬНАЯ ОТМЕНА УСТАНОВЛЕНА" -ForegroundColor Green
Write-Host "Значок: fitintel-desktop\assets\undo.png"
Write-Host "Действие: Отмена последнего действия / Ctrl+Z / меню Правка"
Write-Host "Следующий шаг: выполните SQL-триггеры на nfs, затем пересоберите backend и desktop."
