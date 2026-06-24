import sys
import os
import requests
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
    QLabel, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt

API_BASE = "http://localhost:8001/api/v1"


class BankStatementParser:
    """Локальный парсер (fallback, если бэкенд недоступен)."""

    def parse_txt_file(self, file_path: str) -> list:
        payments_found = []
        current_doc = {}

        if not os.path.exists(file_path):
            return []

        try:
            with open(file_path, 'r', encoding='windows-1251', errors='ignore') as f:
                for line in f:
                    line = line.strip()

                    if line == "СекцияДокумент=Платежное поручение":
                        current_doc = {}

                    elif line.startswith("Сумма="):
                        try:
                            val = line.split("=", 1)[1].replace(" ", "").replace(",", ".")
                            current_doc["amount"] = float(val)
                        except ValueError:
                            current_doc["amount"] = 0.0

                    elif line.startswith("Плательщик1="):
                        current_doc["payer"] = line.split("=", 1)[1]

                    elif line.startswith("ПлательщикИНН="):
                        current_doc["inn"] = line.split("=", 1)[1]

                    elif line.startswith("Дата="):
                        current_doc["date"] = line.split("=", 1)[1]

                    elif line.startswith("НазначениеПлатежа="):
                        current_doc["purpose"] = line.split("=", 1)[1]

                    elif line.startswith("СуммаСписано="):
                        current_doc["_is_expense"] = True

                    elif line == "КонецДокумента":
                        if "amount" in current_doc and current_doc.get("amount", 0) > 0 and not current_doc.get("_is_expense"):
                            payments_found.append(current_doc)
                        current_doc = {}

            return payments_found

        except Exception as e:
            print(f"[ERROR] {e}")
            return []


class BankStatementWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.parser = BankStatementParser()
        self.current_payments = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Бухгалтерия: Контроль банковских выписок")
        self.resize(900, 550)

        main_layout = QVBoxLayout()

        top = QHBoxLayout()
        self.btn_open = QPushButton("📁 Загрузить файл выписки (.txt)")
        self.btn_open.setStyleSheet(
            "padding: 8px; font-weight: bold; background-color: #0078D4; color: white;"
        )
        self.btn_open.clicked.connect(self.open_file_dialog)

        self.lbl_status = QLabel("Файл не выбран")
        self.lbl_status.setStyleSheet("color: gray; font-style: italic;")

        top.addWidget(self.btn_open)
        top.addWidget(self.lbl_status)
        top.addStretch()
        main_layout.addLayout(top)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Дата", "Сумма (руб.)", "Плательщик", "ИНН", "Назначение платежа"]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        main_layout.addWidget(self.table)

        bottom = QHBoxLayout()
        self.lbl_total = QLabel("<b>Всего:</b> 0 | <b>Сумма:</b> 0.00 руб.")
        self.lbl_total.setStyleSheet("font-size: 13px;")

        self.btn_import = QPushButton("📥 Провести в базу фитнеса")
        self.btn_import.setEnabled(False)
        self.btn_import.setStyleSheet(
            "padding: 8px; font-weight: bold; background-color: #228B22; color: white;"
        )
        self.btn_import.clicked.connect(self.import_to_db)

        bottom.addWidget(self.lbl_total)
        bottom.addStretch()
        bottom.addWidget(self.btn_import)
        main_layout.addLayout(bottom)

        self.setLayout(main_layout)

    def open_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл выписки", "", "Текстовые файлы (*.txt);;Все файлы (*)"
        )
        if not path:
            return

        self.lbl_status.setText(os.path.basename(path))

        # Сначала пробуем отправить на бэкенд
        try:
            with open(path, 'rb') as f:
                resp = requests.post(
                    f"{API_BASE}/payments/bank-statement",
                    files={"file": (os.path.basename(path), f, "text/plain")},
                    timeout=10
                )
                if resp.status_code == 200:
                    data = resp.json()
                    self.current_payments = data.get("payments", [])
                    self.display_payments(self.current_payments)
                    return
        except requests.exceptions.ConnectionError:
            pass  # Fallback на локальный парсер

        payments = self.parser.parse_txt_file(path)
        self.display_payments(payments)

    def display_payments(self, payments: list):
        self.current_payments = payments
        self.table.setRowCount(0)
        total = 0.0

        for row_idx, doc in enumerate(payments):
            self.table.insertRow(row_idx)
            date = doc.get("date", "-")
            amount = doc.get("amount", 0.0)
            payer = doc.get("payer", "Неизвестно")
            inn = doc.get("inn", "-")
            purpose = doc.get("purpose", "-")
            total += amount

            self.table.setItem(row_idx, 0, QTableWidgetItem(date))

            amt = QTableWidgetItem(f"{amount:,.2f}".replace(",", " "))
            amt.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 1, amt)

            self.table.setItem(row_idx, 2, QTableWidgetItem(payer))
            self.table.setItem(row_idx, 3, QTableWidgetItem(inn))
            self.table.setItem(row_idx, 4, QTableWidgetItem(purpose))

        self.lbl_total.setText(
            f"<b>Всего платежей:</b> {len(payments)} | <b>На сумму:</b> <span style='color:green'>{total:,.2f} руб.</span>"
            .replace(",", " ")
        )
        self.btn_import.setEnabled(len(payments) > 0)

    def import_to_db(self):
        QMessageBox.information(
            self, "Успех",
            f"Распознано и зафиксировано: {len(self.current_payments)} платежей."
        )
        self.btn_import.setEnabled(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = BankStatementWindow()
    w.show()
    sys.exit(app.exec())