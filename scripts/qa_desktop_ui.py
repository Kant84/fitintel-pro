#!/usr/bin/env python3
"""Read-only QA всех PyQt-окон и вложенных вкладок. Только test 192.168.101.14.

Проверяет построение экранов, загрузку данных, вложенные вкладки, фильтры и
открытие карточек клиента/пользователя. Не нажимает опасные действия и не
создаёт, не изменяет и не удаляет серверные записи. Пароли и токены не пишет
в отчёт. Функциональные CRUD-операции проверяются отдельным API QA.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
DESKTOP = Path(__file__).resolve().parents[1] / "fitintel-desktop"
sys.path.insert(0, str(DESKTOP))

import requests
from PyQt6.QtCore import QThread, QTimer, Qt
from PyQt6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QLabel, QMessageBox, QTabWidget,
    QTableWidget,
)

from api import ApiClient
from windows.main_window import MainWindow

BASE_URL = "http://192.168.101.14/api/v1"
ROLE_MATRIX = {
    "admin": {"accounting": 1, "ai_center": 1, "analytics": 1, "audit": 1, "banks": 1, "clients": 1, "club_params": 1, "commerce": 1, "connections": 1, "credentials": 1, "dashboard": 1, "devices": 1, "documents": 1, "export": 1, "face_id": 1, "integrations": 1, "license": 1, "messenger": 1, "notifications": 1, "payments": 1, "reports": 1, "roles": 1, "schedule": 1, "services": 1, "settings": 1, "setup": 1, "shop": 1, "subscriptions": 1, "tariffs": 1, "ui_config": 1, "users": 1, "visits": 1},
    "accountant": {"accounting": 1, "ai_center": 1, "analytics": 1, "audit": 0, "banks": 0, "clients": 1, "commerce": 1, "connections": 1, "credentials": 1, "dashboard": 1, "devices": 1, "documents": 1, "export": 1, "face_id": 1, "integrations": 1, "license": 1, "messenger": 1, "notifications": 1, "payments": 1, "reports": 1, "roles": 1, "schedule": 1, "services": 1, "settings": 1, "setup": 1, "shop": 0, "subscriptions": 1, "tariffs": 1, "ui_config": 1, "users": 1, "visits": 1},
    "cashier": {"accounting": 1, "ai_center": 1, "analytics": 1, "audit": 0, "banks": 0, "clients": 1, "commerce": 1, "connections": 1, "credentials": 1, "dashboard": 1, "devices": 1, "documents": 1, "export": 1, "face_id": 1, "integrations": 1, "license": 1, "messenger": 1, "notifications": 1, "payments": 1, "reports": 1, "roles": 1, "schedule": 1, "services": 1, "settings": 1, "setup": 1, "shop": 0, "subscriptions": 1, "tariffs": 1, "ui_config": 1, "users": 1, "visits": 1},
    "owner": {"accounting": 1, "ai_center": 1, "analytics": 1, "audit": 0, "banks": 0, "clients": 1, "commerce": 1, "connections": 1, "credentials": 1, "dashboard": 1, "devices": 1, "documents": 1, "export": 1, "face_id": 1, "integrations": 1, "license": 1, "messenger": 1, "notifications": 1, "payments": 1, "reports": 1, "roles": 1, "schedule": 1, "services": 1, "settings": 1, "setup": 1, "shop": 0, "subscriptions": 1, "tariffs": 1, "ui_config": 1, "users": 1, "visits": 1},
    "support": {"accounting": 1, "ai_center": 1, "analytics": 1, "audit": 0, "banks": 0, "clients": 1, "commerce": 1, "connections": 1, "credentials": 1, "dashboard": 1, "devices": 1, "documents": 1, "export": 1, "face_id": 1, "integrations": 1, "license": 1, "messenger": 1, "notifications": 1, "payments": 1, "reports": 1, "roles": 1, "schedule": 1, "services": 1, "settings": 1, "setup": 1, "shop": 0, "subscriptions": 1, "tariffs": 1, "ui_config": 1, "users": 1, "visits": 1},
    "manager": {
        "accounting": 0, "ai_center": 0, "analytics": 0, "audit": 0,
        "banks": 0, "clients": 1, "club_params": 0, "commerce": 0,
        "connections": 0, "credentials": 0, "dashboard": 1, "devices": 0,
        "documents": 1, "export": 0, "face_id": 0, "integrations": 0,
        "license": 0, "messenger": 0, "notifications": 0, "payments": 1,
        "reports": 1, "roles": 0, "schedule": 1, "services": 0, "settings": 0,
        "setup": 0, "shop": 0, "subscriptions": 1, "tariffs": 1, "ui_config": 0,
        "users": 0, "visits": 1},
    "trainer": {"audit": 0, "banks": 0, "shop": 0, "dashboard": 1,
        "clients": 1, "schedule": 1, "visits": 1},
}

def expected_screens(role):
    matrix = ROLE_MATRIX.get(role)
    if matrix is None:
        return None
    return {code for code, visible in matrix.items() if visible}

# Топ-уровневые коды desktop (TAB_REGISTRY в main_window.py).
# Суб-вкладки (payments/reports/documents/tariffs и пр.) не являются
# пунктами меню и в этой проверке не участвуют.
DESKTOP_TOP_LEVEL = {
    "dashboard", "clients", "subscriptions", "services", "visits",
    "schedule", "music", "users", "face_id", "settings", "banks",
    "connections", "accounting", "ai_center", "shop", "messenger",
    "notifications", "credentials", "audit",
}
# Коды desktop, которых нет в матрице вообще: desktop добавляет их
# по имени пользователя (superadmin), матрицей не управляются.
UNRESTRICTED_CODES = DESKTOP_TOP_LEVEL - set().union(
    *(m.keys() for m in ROLE_MATRIX.values()))


class UIQA:
    def __init__(self, app: QApplication) -> None:
        self.app = app
        self.run_id = uuid.uuid4().hex[:10]
        self.results: list[dict] = []
        self.area = "Запуск"
        self.windows: list[MainWindow] = []
        self._originals: dict[str, object] = {}

    def add(self, role: str, area: str, check: str, ok: bool | None,
            detail: str = "") -> None:
        result = "PASS" if ok is True else "SKIP" if ok is None else "FAIL"
        detail = re.sub(r"eyJ[A-Za-z0-9_.-]+", "<TOKEN>", str(detail))[:400]
        self.results.append({"role": role, "area": area, "check": check,
                             "result": result, "detail": detail})
        print(f"{result}: {role} | {area} | {check}" +
              (f" | {detail}" if detail and result != "PASS" else ""), flush=True)

    def pump(self, seconds: float = 0.08) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.01)
        self.app.processEvents()

    def wait_workers(self, widget, seconds: float = 25) -> bool:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.app.processEvents()
            workers = []
            objects = [widget] + widget.findChildren(QDialog)
            for obj in objects:
                for value in vars(obj).values():
                    if isinstance(value, QThread) and value.isRunning():
                        workers.append(value)
            if not workers:
                self.pump()
                return True
            time.sleep(0.03)
        return False

    @staticmethod
    def _error_text(widget) -> str:
        if isinstance(widget, QLabel):
            text = widget.text().strip()
            if text.startswith("Не удалось загрузить"):
                return text
        for label in widget.findChildren(QLabel):
            text = label.text().strip()
            if text.startswith("Не удалось загрузить"):
                return text
        for table in widget.findChildren(QTableWidget):
            for row in range(table.rowCount()):
                for column in range(table.columnCount()):
                    item = table.item(row, column)
                    if item and item.text().startswith("Ошибка загрузки"):
                        return item.text()
        return ""

    def _dialog_exec(self, dialog: QDialog) -> int:
        # Защита от зависания: автоматический прогон не подтверждает диалоги,
        # поэтому ни одно изменение после exec() не выполняется.
        return int(QDialog.DialogCode.Rejected)

    def _message(self, kind: str, args) -> int:
        title = str(args[1]) if len(args) > 1 else kind
        text = str(args[2]) if len(args) > 2 else ""
        if kind in {"warning", "critical"}:
            self.add("ui", self.area, title, False, text)
        if kind == "question":
            return int(QMessageBox.StandardButton.No)
        return int(QMessageBox.StandardButton.Ok)

    def install_guards(self) -> None:
        self._originals["exec"] = QDialog.exec
        QDialog.exec = lambda dialog: self._dialog_exec(dialog)
        for kind in ("information", "warning", "critical", "question"):
            self._originals[kind] = getattr(QMessageBox, kind)
            setattr(QMessageBox, kind,
                    lambda *args, _kind=kind, **kwargs: self._message(_kind, args))
        QFileDialog.getOpenFileName = staticmethod(lambda *args, **kwargs: ("", ""))
        QFileDialog.getOpenFileNames = staticmethod(lambda *args, **kwargs: ([], ""))
        QFileDialog.getSaveFileName = staticmethod(lambda *args, **kwargs: ("", ""))
        QFileDialog.getExistingDirectory = staticmethod(lambda *args, **kwargs: "")

    def login(self, role: str, username: str, password: str) -> tuple[ApiClient, dict] | None:
        api = ApiClient(BASE_URL)
        try:
            response = api.session.post(BASE_URL + "/auth/login",
                                        json={"login": username, "password": password},
                                        timeout=30)
            data = response.json() if response.content else {}
            token = data.get("access_token")
            if response.status_code != 200 or not token:
                self.add(role, "Авторизация", "Вход", False,
                         f"HTTP {response.status_code}")
                return None
            api.set_token(token)
            user = api.me()
            api.undo = None
            self.add(role, "Авторизация", "Вход и /auth/me", True)
            return api, user
        except Exception as exc:
            self.add(role, "Авторизация", "Вход", False, str(exc))
            api.clear_token()
            return None

    def walk_nested(self, role: str, widget, path: str, visited: set[int]) -> None:
        for tabs in widget.findChildren(QTabWidget):
            marker = id(tabs)
            if marker in visited:
                continue
            visited.add(marker)
            for index in range(tabs.count()):
                title = tabs.tabText(index).strip() or str(index + 1)
                area = f"{path}/{title}"
                self.area = area
                try:
                    tabs.setCurrentIndex(index)
                    self.pump()
                    page = tabs.widget(index)
                    loaded = self.wait_workers(page)
                    error = self._error_text(page)
                    self.add(role, area, "Вкладка и данные загружены",
                             loaded and not error,
                             error or ("поток загрузки не завершился" if not loaded else ""))
                    if page.__class__.__name__ == "DocumentsTab":
                        self.add(role, area, "Обработчики двойного клика подключены",
                                 callable(getattr(page, "_doc_dbl", None))
                                 and callable(getattr(page, "_tpl_dbl", None)))
                    if page.__class__.__name__ == "NotificationsTab":
                        self.add(role, area, "Контакты уведомлений загружены",
                                 page.cmb_contacts.count() > 0,
                                 "список контактов пуст")
                    if page.__class__.__name__ == "ExportTab":
                        try:
                            export_loaded = page.load_log() is True
                        except Exception:
                            export_loaded = False
                        self.add(role, area, "Журнал экспорта загружается", export_loaded)
                    if hasattr(page, "refresh"):
                        page.refresh()
                        refreshed = self.wait_workers(page)
                        error = self._error_text(page)
                        self.add(role, area, "Обновление вкладки",
                                 refreshed and not error,
                                 error or ("поток обновления не завершился" if not refreshed else ""))
                    self.walk_nested(role, page, area, visited)
                except Exception as exc:
                    self.add(role, area, "Открытие вкладки", False, str(exc))

    def client_checks(self, role: str, widget) -> None:
        self.area = "Клиенты"
        if not self.wait_workers(widget):
            self.add(role, "Клиенты", "Завершение загрузки", False)
            return
        total = widget.table.rowCount()
        if total:
            widget.edit_filter.setText("QA_НЕТ_ТАКОГО_КЛИЕНТА_" + self.run_id)
            self.pump(0.45)
            filtered = widget.table.rowCount() == 0
            widget.edit_filter.clear()
            self.pump(0.45)
            restored = widget.table.rowCount() == total
            self.add(role, "Клиенты", "Поиск и сброс фильтра", filtered and restored,
                     f"строк до={total}, после сброса={widget.table.rowCount()}")
            widget.table.selectRow(0)
            try:
                widget._open_card()
                self.pump(0.3)
                cards = getattr(widget, "_open_cards", [])
                card = cards[-1] if cards else None
                error = self._error_text(card) if card else "карточка не создана"
                self.add(role, "Клиенты", "Карточка клиента открывается",
                         bool(card and card.isVisible() and not error), error)
                if card:
                    card.close()
                    self.pump()
            except Exception as exc:
                self.add(role, "Клиенты", "Карточка клиента открывается", False, str(exc))
        else:
            self.add(role, "Клиенты", "Поиск и карточка", None, "нет клиентов для проверки")

    def user_checks(self, role: str, widget) -> None:
        self.area = "Пользователи"
        if not self.wait_workers(widget):
            self.add(role, "Пользователи", "Завершение загрузки", False)
            return
        total = widget.table.rowCount()
        if total:
            widget.edit_filter.setText("QA_НЕТ_ТАКОГО_ПОЛЬЗОВАТЕЛЯ_" + self.run_id)
            self.pump(0.45)
            filtered = widget.table.rowCount() == 0
            widget.edit_filter.clear()
            self.pump(0.45)
            restored = widget.table.rowCount() == total
            self.add(role, "Пользователи", "Поиск и сброс фильтра", filtered and restored,
                     f"строк до={total}, после сброса={widget.table.rowCount()}")
            widget.table.selectRow(0)
            try:
                widget._open_card()
                self.pump(0.3)
                cards = getattr(widget, "_open_cards", [])
                card = cards[-1] if cards else None
                error = self._error_text(card) if card else "карточка не создана"
                self.add(role, "Пользователи", "Карточка пользователя открывается",
                         bool(card and card.isVisible() and not error), error)
                if card:
                    card.close()
                    self.pump()
            except Exception as exc:
                self.add(role, "Пользователи", "Карточка пользователя открывается", False, str(exc))
        else:
            self.add(role, "Пользователи", "Поиск и карточка", None, "нет пользователей")

    def run_role(self, role: str, username: str, password: str) -> None:
        logged = self.login(role, username, password)
        if not logged:
            return
        api, user = logged
        window = None
        try:
            window = MainWindow(api, user, api.token)
            self.windows.append(window)
            codes = list(window._codes)
            titles = [window.sidebar.item(i).text().strip()
                      for i in range(window.sidebar.count())]
            self.add(role, "Главное окно", "Нет дублей экранов",
                     len(codes) == len(set(codes)) and len(titles) == len(set(titles)),
                     ", ".join(titles))
            expected = expected_screens(role)
            if expected is None:
                self.add(role, "Главное окно", "Матрица экранов роли", None,
                         "роль не описана в ROLE_MATRIX")
            else:
                expected_top = expected & DESKTOP_TOP_LEVEL
                missing = sorted(expected_top - set(codes))
                extra = sorted(set(codes) - expected - UNRESTRICTED_CODES)
                self.add(role, "Главное окно", "Все обязательные экраны доступны",
                         not missing, "нет: " + ", ".join(missing) if missing else "")
                self.add(role, "Главное окно", "Нет экранов сверх матрицы",
                         not extra, "лишние: " + ", ".join(extra) if extra else "")
            for row, code in enumerate(codes):
                area = dict(zip(codes, titles)).get(code, code)
                self.area = area
                try:
                    window.sidebar.setCurrentRow(row)
                    self.pump()
                    widget = window._built.get(code)
                    error = self._error_text(widget) if widget else "виджет не создан"
                    self.add(role, area, "Основной экран открывается", bool(widget and not error), error)
                    if widget:
                        self.walk_nested(role, widget, area, set())
                        if code == "clients":
                            self.client_checks(role, widget)
                        elif code == "users":
                            self.user_checks(role, widget)
                except Exception as exc:
                    self.add(role, area, "Открытие основного экрана", False, str(exc))
        except Exception as exc:
            self.add(role, "Главное окно", "Построение", False, str(exc))
        finally:
            if window is not None:
                for timer in window.findChildren(QTimer):
                    timer.stop()
                window.close()
                self.pump()
            api.clear_token()

    def finish(self) -> int:
        counts = {key: sum(row["result"] == key for row in self.results)
                  for key in ("PASS", "FAIL", "SKIP")}
        print("\n=== UI QA ИТОГ ===")
        print(json.dumps(counts, ensure_ascii=False))
        path = Path(os.environ.get("TEMP", "/tmp")) / f"fitintel-ui-qa-{self.run_id}.json"
        path.write_text(json.dumps({"run_id": self.run_id, "server": BASE_URL,
                                    "mode": "read-only PyQt", "summary": counts,
                                    "results": self.results}, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        print("UI_QA_REPORT=" + str(path))
        print("UI_QA_RESULT=" + ("PASS" if counts["FAIL"] == 0 else "FAIL"))
        return 0 if counts["FAIL"] == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-test", required=True, choices=["192.168.101.14"])
    parser.add_argument("--admin-login", required=True)
    parser.add_argument("--manager-login", default="aaa")
    parser.add_argument("--role-login", action="append", default=[],
                        help="role=login, может повторяться")
    args = parser.parse_args()
    health = requests.get(BASE_URL + "/health/", timeout=15)
    if health.status_code != 200:
        print("TEST_HEALTH_FAILED=1")
        return 2
    admin_password = getpass.getpass("Пароль SuperAdmin (не отображается): ")
    manager_password = getpass.getpass("Пароль Manager (не отображается): ")
    app = QApplication([])
    qa = UIQA(app)
    qa.install_guards()
    try:
        qa.run_role("admin", args.admin_login, admin_password)
        qa.run_role("manager", args.manager_login, manager_password)
        for svc_role in ("client", "device", "platform"):
            qa.add(svc_role, "Запуск", "Сервисная роль без UI-входа", None, "пропуск")
        for spec in args.role_login:
            role, sep, login = spec.partition("=")
            if not sep or not login:
                qa.add(role or spec, "Запуск", "Некорректный --role-login", False, spec)
                continue
            qa.run_role(role, login,
                        getpass.getpass(f"Пароль {role} (не отображается): "))
    finally:
        for window in qa.windows:
            for timer in window.findChildren(QTimer):
                timer.stop()
            window.close()
        app.quit()
    return qa.finish()


if __name__ == "__main__":
    sys.exit(main())
