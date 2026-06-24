"""FitIntel Pro — Settings Tab"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QMessageBox, QFormLayout, QGroupBox, QSpinBox, QCheckBox
)
from PyQt6.QtCore import Qt
from api import ApiClient


class SettingsTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        header = QLabel("⚙️ Настройки системы")
        header.setStyleSheet("font-size: 18px; font-weight: 700; color: #0f172a;")
        layout.addWidget(header)

        # Connection group
        conn_group = QGroupBox("🔗 Подключение к серверу")
        conn_group.setStyleSheet("QGroupBox { font-weight: 600; border: 1px solid #e2e8f0; border-radius: 8px; margin-top: 12px; padding-top: 12px; } QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }")
        conn_layout = QFormLayout(conn_group)
        conn_layout.setSpacing(12)

        self.edit_url = QLineEdit("http://localhost:8001/api/v1")
        self.edit_url.setStyleSheet("padding: 8px; border: 1px solid #cbd5e1; border-radius: 6px;")
        conn_layout.addRow("API URL:", self.edit_url)

        btn_test = QPushButton("🔄 Проверить соединение")
        btn_test.setStyleSheet(self._btn_secondary())
        btn_test.clicked.connect(self._test_connection)
        conn_layout.addRow(btn_test)

        layout.addWidget(conn_group)

        # Face ID group
        face_group = QGroupBox("🎭 Face ID")
        face_group.setStyleSheet("QGroupBox { font-weight: 600; border: 1px solid #e2e8f0; border-radius: 8px; margin-top: 12px; padding-top: 12px; } QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }")
        face_layout = QFormLayout(face_group)

        self.spin_threshold = QSpinBox()
        self.spin_threshold.setRange(1, 99)
        self.spin_threshold.setValue(60)
        self.spin_threshold.setSuffix(" %")
        face_layout.addRow("Порог совпадения:", self.spin_threshold)

        self.chk_save_photos = QCheckBox("Сохранять фото при распознавании")
        self.chk_save_photos.setChecked(True)
        face_layout.addRow(self.chk_save_photos)

        layout.addWidget(face_group)

        # License group
        lic_group = QGroupBox("🔐 Лицензия")
        lic_group.setStyleSheet("QGroupBox { font-weight: 600; border: 1px solid #e2e8f0; border-radius: 8px; margin-top: 12px; padding-top: 12px; } QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }")
        lic_layout = QFormLayout(lic_group)

        self.lbl_license_info = QLabel("Лицензия не проверена")
        self.lbl_license_info.setStyleSheet("color: #64748b; font-size: 12px;")
        lic_layout.addRow("Статус:", self.lbl_license_info)

        layout.addWidget(lic_group)

        layout.addStretch()

        # Save button
        btn_save = QPushButton("💾 Сохранить настройки")
        btn_save.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 10px 24px; font-weight: 600; } QPushButton:hover { background: #059669; }")
        btn_save.clicked.connect(self._save)
        layout.addWidget(btn_save, alignment=Qt.AlignmentFlag.AlignCenter)

    def _btn_secondary(self) -> str:
        return "QPushButton { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; } QPushButton:hover { background: #e2e8f0; }"

    def _test_connection(self):
        try:
            self.api.health()
            QMessageBox.information(self, "Соединение", "✅ Сервер доступен!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"❌ Не удалось подключиться:
{e}")

    def _save(self):
        QMessageBox.information(self, "Сохранено", "Настройки сохранены (в памяти).
Для постоянного хранения добавьте JSON-конфиг.")
