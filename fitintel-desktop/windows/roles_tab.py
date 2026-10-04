"""FitIntel Pro — Роли и права: редактируемая матрица (галочки + сохранение)."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from api import ApiClient
from windows import theme
from windows.form_dialog import FormDialog


def _err_text(e) -> str:
    resp = getattr(e, "response", None)
    if resp is not None:
        try:
            d = resp.json().get("detail")
            if d:
                return str(d)
        except Exception:
            pass
        return "Ошибка сервера %s" % resp.status_code
    return str(e)


class _Get(QThread):
    done = pyqtSignal(object)
    fail = pyqtSignal(object)
    def __init__(self, api, path):
        super().__init__()
        self.api, self.path = api, path
    def run(self):
        try:
            r = self.api.session.get(self.api._url(self.path), timeout=20)
            r.raise_for_status()
            self.done.emit(r.json())
        except Exception as e:
            self.fail.emit(e)


class RolesTab(QWidget):
    """Слева — роли, справа — все права с галочками. Сохранение = diff на сервер."""

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._roles = []          # [{id, code, name, perms:set(perm_id)}]
        self._perms = []          # [{id, code, name}]
        self._edits = {}          # role_id -> set(perm_id) (рабочая копия)
        self._loading = False
        self._build_ui()
        self.refresh()

    # ---------- UI ----------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        top = QHBoxLayout()
        self.lbl_hint = QLabel("Выберите роль слева → отметьте права галочками → «💾 Сохранить»")
        top.addWidget(self.lbl_hint, 1)
        b = QPushButton("🔄 Обновить")
        b.clicked.connect(self.refresh)
        top.addWidget(b)
        self.b_save = QPushButton("💾 Сохранить изменения")
        self.b_save.setEnabled(False)
        self.b_save.clicked.connect(self._save)
        top.addWidget(self.b_save)
        layout.addLayout(top)

        split = QSplitter(Qt.Orientation.Horizontal)

        self.tbl_roles = QTableWidget(0, 2)
        self.tbl_roles.setHorizontalHeaderLabels(["Роль", "Код"])
        self.tbl_roles.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_roles.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_roles.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_roles.setAlternatingRowColors(True)
        self.tbl_roles.setStyleSheet(theme.table_style())
        self.tbl_roles.itemSelectionChanged.connect(self._on_role_selected)
        split.addWidget(self.tbl_roles)

        self.tbl_perms = QTableWidget(0, 2)
        self.tbl_perms.setHorizontalHeaderLabels(["✓", "Право"])
        self.tbl_perms.setColumnWidth(0, 40)
        self.tbl_perms.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_perms.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_perms.setAlternatingRowColors(True)
        self.tbl_perms.setStyleSheet(theme.table_style())
        self.tbl_perms.itemChanged.connect(self._on_perm_toggled)
        split.addWidget(self.tbl_perms)
        split.setSizes([300, 520])
        layout.addWidget(split, 1)

        self.status = QLabel("")
        layout.addWidget(self.status)

    # ---------- загрузка ----------
    def refresh(self):
        self.status.setText("Загрузка ролей и прав…")
        self._loading = True
        w1 = _Get(self.api, "/roles/")
        w1.done.connect(self._roles_loaded)
        w1.fail.connect(self._load_fail)
        w1.start()
        self._w1 = w1

    def _roles_loaded(self, data):
        roles = data if isinstance(data, list) else []
        self._roles = []
        for r in roles:
            perms = set()
            for rp in (r.get("role_permissions") or []):
                p = rp.get("permission") if isinstance(rp, dict) else None
                if p and p.get("id"):
                    perms.add(str(p["id"]))
            self._roles.append({
                "id": str(r.get("id")),
                "code": r.get("code") or "",
                "name": r.get("name") or r.get("code") or "—",
                "perms": perms,
            })
        self._edits = {r["id"]: set(r["perms"]) for r in self._roles}
        w2 = _Get(self.api, "/permissions/")
        w2.done.connect(self._perms_loaded)
        w2.fail.connect(self._load_fail)
        w2.start()
        self._w2 = w2

    def _perms_loaded(self, data):
        perms = data if isinstance(data, list) else []
        self._perms = [{"id": str(p.get("id")), "code": p.get("code") or "",
                        "name": p.get("name") or p.get("code") or ""}
                       for p in perms if p.get("id")]
        self._render_roles()
        self._loading = False
        self.status.setText("Готово: %d ролей, %d прав. Права применяются сразу после сохранения."
                            % (len(self._roles), len(self._perms)))

    def _load_fail(self, e):
        self._loading = False
        self.status.setText("Ошибка загрузки: %s" % _err_text(e))

    # ---------- отрисовка ----------
    def _render_roles(self):
        self.tbl_roles.setRowCount(len(self._roles))
        for i, r in enumerate(self._roles):
            self.tbl_roles.setItem(i, 0, QTableWidgetItem(r["name"]))
            self.tbl_roles.setItem(i, 1, QTableWidgetItem(r["code"]))

    def _current_role(self):
        row = self.tbl_roles.currentRow()
        if 0 <= row < len(self._roles):
            return self._roles[row]
        return None

    def _on_role_selected(self):
        role = self._current_role()
        self._render_perms(role)

    def _render_perms(self, role):
        self._loading = True
        self.tbl_perms.setRowCount(len(self._perms))
        checked = self._edits.get(role["id"], set()) if role else set()
        for i, p in enumerate(self._perms):
            it = QTableWidgetItem()
            it.setData(Qt.ItemDataRole.UserRole, p["id"])
            it.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            it.setCheckState(Qt.CheckState.Checked if p["id"] in checked
                             else Qt.CheckState.Unchecked)
            self.tbl_perms.setItem(i, 0, it)
            name = "%s — %s" % (p["code"], p["name"]) if p["name"] and p["name"] != p["code"] else p["code"]
            self.tbl_perms.setItem(i, 1, QTableWidgetItem(name))
        self._loading = False
        self.b_save.setEnabled(role is not None)

    def _on_perm_toggled(self, item):
        if self._loading:
            return
        role = self._current_role()
        if not role or item.column() != 0:
            return
        pid = item.data(Qt.ItemDataRole.UserRole)
        if item.checkState() == Qt.CheckState.Checked:
            self._edits[role["id"]].add(pid)
        else:
            self._edits[role["id"]].discard(pid)

    # ---------- сохранение ----------
    def _save(self):
        role = self._current_role()
        if not role:
            return
        if role["code"] == "admin":
            ret = QMessageBox.question(self, "Роль admin",
                "Вы редактируете системную роль admin. Продолжить?")
            if ret != QMessageBox.StandardButton.Yes:
                return
        orig, now = role["perms"], self._edits[role["id"]]
        to_add = [p for p in (now - orig)]
        to_del = [p for p in (orig - now)]
        if not to_add and not to_del:
            self.status.setText("Изменений нет.")
            return
        self.b_save.setEnabled(False)
        self.status.setText("Сохранение: +%d / −%d прав…" % (len(to_add), len(to_del)))
        self._save_role(role, to_add, to_del, ok=0, fail=0)

    def _save_role(self, role, to_add, to_del, ok, fail):
        if to_add:
            pid = to_add[0]
            try:
                r = self.api.session.post(self.api._url("/roles/%s/permissions" % role["id"]),
                                          json={"permission_id": pid}, timeout=15)
                r.raise_for_status()
                ok += 1
            except Exception:
                fail += 1
            self._save_role(role, to_add[1:], to_del, ok, fail)
            return
        if to_del:
            pid = to_del[0]
            try:
                r = self.api.session.delete(
                    self.api._url("/roles/%s/permissions/%s" % (role["id"], pid)), timeout=15)
                r.raise_for_status()
                ok += 1
            except Exception:
                fail += 1
            self._save_role(role, [], to_del[1:], ok, fail)
            return
        # всё применено
        self._edits[role["id"]] = set(role["perms"])  # перечитаем ниже
        msg = "Сохранено. Применено изменений: %d" % ok
        if fail:
            msg += ", ошибок: %d (проверьте право roles.manage)" % fail
        self.status.setText(msg)
        self.refresh()