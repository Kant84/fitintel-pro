# -*- coding: utf-8 -*-
"""П1: окно «Поддержка разработчика (email)» — обращения с support@fixintel.ru.
Открывается из меню «Помощь». Список обращений, тред, ответы (SMTP, треды
склеиваются заголовками), статусы new/in_progress/done, настройки IMAP."""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QComboBox, QCheckBox, QListWidget,
                             QListWidgetItem, QPlainTextEdit, QSplitter, QWidget,
                             QMessageBox, QApplication)
from PyQt6.QtCore import Qt


class SupportDialog(QDialog):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Поддержка разработчика (email)")
        self.resize(980, 640)
        v = QVBoxLayout(self)

        grp = QHBoxLayout()
        self.sup_host = QLineEdit(); self.sup_host.setPlaceholderText("imap.fixintel.ru")
        self.sup_host.setMaximumWidth(170)
        self.sup_user = QLineEdit(); self.sup_user.setPlaceholderText("логин")
        self.sup_user.setMaximumWidth(150)
        self.sup_pass = QLineEdit(); self.sup_pass.setPlaceholderText("пароль")
        self.sup_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.sup_pass.setMaximumWidth(150)
        self.sup_email = QLineEdit("support@fixintel.ru")
        self.sup_email.setMaximumWidth(200)
        self.sup_en = QCheckBox("Включено")
        bsave = QPushButton(" Сохранить")
        grp.addWidget(QLabel("IMAP:")); grp.addWidget(self.sup_host)
        grp.addWidget(self.sup_user); grp.addWidget(self.sup_pass)
        grp.addWidget(self.sup_email); grp.addWidget(self.sup_en)
        grp.addWidget(bsave); grp.addStretch(1)
        v.addLayout(grp)

        bar = QHBoxLayout()
        self.cmb_st = QComboBox(); self.cmb_st.addItems(["Все", "new", "in_progress", "done"])
        bref = QPushButton("Обновить")
        bpoll = QPushButton(" Проверить почту")
        self.lbl = QLabel("")
        bar.addWidget(QLabel("Статус:")); bar.addWidget(self.cmb_st); bar.addWidget(bref)
        bar.addWidget(bpoll); bar.addWidget(self.lbl, 1)
        v.addLayout(bar)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.listw = QListWidget(); self.listw.setMaximumWidth(360)
        split.addWidget(self.listw)
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0, 0, 0, 0)
        self.thread = QPlainTextEdit(); self.thread.setReadOnly(True)
        rv.addWidget(self.thread, 1)
        row = QHBoxLayout()
        self.cmb_act = QComboBox(); self.cmb_act.addItems(["Ответить", "В работу", "Закрыть"])
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ответ клиенту уходит на email (тред склеивается)...")
        bgo = QPushButton("Выполнить")
        row.addWidget(self.cmb_act); row.addWidget(self.input, 1); row.addWidget(bgo)
        rv.addLayout(row)
        split.addWidget(right); split.setStretchFactor(1, 1)
        v.addWidget(split, 1)

        bsave.clicked.connect(self._save)
        bref.clicked.connect(self._load)
        bpoll.clicked.connect(self._poll)
        bgo.clicked.connect(self._action)
        self.listw.currentRowChanged.connect(self._open)
        self.cmb_st.currentTextChanged.connect(lambda _t: self._load())
        self._load_settings()
        self._load()

    def _get(self, path):
        r = self.api.session.get(self.api._url(path), timeout=20)
        r.raise_for_status()
        return r.json()

    def _load_settings(self):
        try:
            s = self._get("/support/settings")
            self.sup_host.setText(str(s.get("imap_host") or ""))
            self.sup_user.setText(str(s.get("imap_user") or ""))
            self.sup_pass.setText("" if not s.get("imap_password") else "saved")
            if s.get("support_email"):
                self.sup_email.setText(str(s.get("support_email")))
            self.sup_en.setChecked(bool(s.get("enabled")))
        except Exception as e:
            self.lbl.setText("Настройки: %s" % str(e)[:120])

    def _save(self):
        payload = {"enabled": bool(self.sup_en.isChecked()),
                   "imap_host": self.sup_host.text().strip(),
                   "imap_user": self.sup_user.text().strip(),
                   "support_email": self.sup_email.text().strip()}
        if self.sup_pass.text() and self.sup_pass.text() != "saved":
            payload["imap_password"] = self.sup_pass.text().strip()
        try:
            r = self.api.session.put(self.api._url("/support/settings"), json=payload, timeout=20)
            self.lbl.setText("Сохранено (%s). SMTP — из «Уведомления → Email»." % r.status_code)
        except Exception as e:
            self.lbl.setText("Ошибка: %s" % str(e)[:150])

    def _poll(self):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            r = self.api.session.post(self.api._url("/support/poll-now"), timeout=90)
            try:
                d = r.json()
            except Exception:
                d = {"raw": r.text[:150]}
            self.lbl.setText("Опрос: %s" % d)
        except Exception as e:
            self.lbl.setText("Опрос: %s" % str(e)[:150])
        finally:
            QApplication.restoreOverrideCursor()
        self._load()

    def _load(self):
        try:
            st = self.cmb_st.currentText()
            d = self._get("/support/tickets" + ("" if st == "Все" else "?status=" + st))
        except Exception as e:
            self.lbl.setText("Список: %s" % str(e)[:150])
            return
        rows = d.get("items", []) if isinstance(d, dict) else []
        self._rows = rows
        self.listw.clear()
        for t in rows:
            it = QListWidgetItem("%s  [%s]\n%s — %s" % (
                str(t.get("updated_at") or "")[:16], t.get("status"),
                t.get("name") or t.get("email"),
                (t.get("subject") or "")[:40]))
            it.setData(Qt.ItemDataRole.UserRole, t.get("id"))
            self.listw.addItem(it)

    def _open(self, row):
        if row < 0 or row >= len(getattr(self, "_rows", [])):
            return
        tid = self._rows[row].get("id")
        self._tid = tid
        try:
            d = self._get("/support/tickets/%s/messages" % tid)
        except Exception:
            return
        rows = d.get("items", []) if isinstance(d, dict) else []
        self.thread.setPlainText("\n\n".join(
            "[%s] %s:\n%s" % (str(m.get("created_at") or "")[:16],
                              "Клиент" if m.get("direction") == "in" else "Мы",
                              m.get("body")) for m in rows) or "(пусто)")

    def _action(self):
        tid = getattr(self, "_tid", None)
        if not tid:
            QMessageBox.information(self, "Поддержка", "Сначала выберите обращение слева.")
            return
        act = self.cmb_act.currentText()
        if act == "Ответить":
            text = self.input.text().strip()
            if not text:
                QMessageBox.information(self, "Поддержка", "Введите текст ответа.")
                return
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                r = self.api.session.post(self.api._url("/support/tickets/%s/reply" % tid),
                                          json={"text": text}, timeout=40)
            finally:
                QApplication.restoreOverrideCursor()
            if r.status_code < 300:
                self.input.clear()
                self._open(self.listw.currentRow())
                self._load()
            else:
                try:
                    detail = r.json().get("detail", r.text[:200])
                except Exception:
                    detail = r.text[:200]
                QMessageBox.warning(self, "Поддержка", "Ошибка %s: %s" % (r.status_code, detail))
        else:
            st = "in_progress" if act == "В работу" else "done"
            try:
                self.api.session.put(self.api._url("/support/tickets/%s/status" % tid),
                                     json={"status": st}, timeout=15)
                self._load()
            except Exception as e:
                QMessageBox.warning(self, "Поддержка", str(e)[:200])
