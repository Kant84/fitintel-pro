# Создаём report_service.py
 = @'
# app/services/report_service.py
from io import BytesIO
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from sqlalchemy.orm import Session
from app.models.payment import Payment
from app.models.visit import Visit
from app.models.client import Client
from app.models.subscription import Subscription


class ReportService:
    def __init__(self, db: Session):
        self.db = db
    
    def export_payments_xlsx(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        client_id: Optional[str] = None,
        payment_direction: Optional[str] = None,
        payment_category: Optional[str] = None,
        status: Optional[str] = None,
    ) -> BytesIO:
        """Экспорт платежей в XLSX"""
        query = self.db.query(Payment)
        
        if date_from:
            query = query.filter(Payment.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            query = query.filter(Payment.created_at <= datetime.combine(date_to, datetime.max.time()))
        if client_id:
            query = query.filter(Payment.client_id == client_id)
        if payment_direction:
            query = query.filter(Payment.payment_direction == payment_direction)
        if payment_category:
            query = query.filter(Payment.payment_category == payment_category)
        if status:
            query = query.filter(Payment.status == status)
        
        payments = query.order_by(Payment.created_at.desc()).all()
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Платежи"
        
        # Заголовки
        headers = [
            "№", "ID платежа", "Дата", "Время", "Направление", "Категория",
            "ФИО клиента", "Телефон", "Email", "Сумма", "Валюта",
            "Способ оплаты", "Тип платежа", "Банк/Система", "Статус",
            "Назначение", "Номер чека", "Кем создан"
        ]
        
        # Стили заголовков
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
        
        # Данные
        for row_idx, payment in enumerate(payments, 2):
            client_name = ""
            client_phone = ""
            client_email = ""
            if payment.client:
                parts = [p for p in [payment.client.last_name, payment.client.first_name, payment.client.middle_name] if p]
                client_name = " ".join(parts)
                client_phone = payment.client.phone or ""
                client_email = payment.client.email or ""
            
            payment_type = "Наличные"
            if payment.payment_method in ["CARD", "SBP", "ONLINE", "TRANSFER"]:
                payment_type = "Безналичные"
            
            bank_name = payment.payment_system or ""
            if payment.payment_method == "CASH":
                bank_name = "Наличные"
            elif payment.payment_method == "SBP":
                bank_name = "СБП"
            
            receipt_num = ""
            if payment.receipt:
                receipt_num = payment.receipt.receipt_number or ""
            
            ws.cell(row=row_idx, column=1, value=row_idx - 1).border = thin_border
            ws.cell(row=row_idx, column=2, value=str(payment.id)).border = thin_border
            ws.cell(row=row_idx, column=3, value=payment.created_at.strftime("%d.%m.%Y") if payment.created_at else "").border = thin_border
            ws.cell(row=row_idx, column=4, value=payment.created_at.strftime("%H:%M:%S") if payment.created_at else "").border = thin_border
            ws.cell(row=row_idx, column=5, value=payment.payment_direction or "INCOME").border = thin_border
            ws.cell(row=row_idx, column=6, value=payment.payment_category or "SUBSCRIPTION").border = thin_border
            ws.cell(row=row_idx, column=7, value=client_name).border = thin_border
            ws.cell(row=row_idx, column=8, value=client_phone).border = thin_border
            ws.cell(row=row_idx, column=9, value=client_email).border = thin_border
            ws.cell(row=row_idx, column=10, value=float(payment.amount)).border = thin_border
            ws.cell(row=row_idx, column=11, value=payment.currency or "RUB").border = thin_border
            ws.cell(row=row_idx, column=12, value=payment.payment_method or "").border = thin_border
            ws.cell(row=row_idx, column=13, value=payment_type).border = thin_border
            ws.cell(row=row_idx, column=14, value=bank_name).border = thin_border
            ws.cell(row=row_idx, column=15, value=payment.status or "").border = thin_border
            ws.cell(row=row_idx, column=16, value=payment.notes or "").border = thin_border
            ws.cell(row=row_idx, column=17, value=receipt_num).border = thin_border
            ws.cell(row=row_idx, column=18, value=str(payment.created_by_user_id) if payment.created_by_user_id else "").border = thin_border
        
        # Автоширина колонок
        for col_idx in range(1, len(headers) + 1):
            max_length = 0
            column = get_column_letter(col_idx)
            for cell in ws[column]:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column].width = adjusted_width
        
        # Фиксируем заголовок
        ws.freeze_panes = 'A2'
        
        # Итоги
        total_row = len(payments) + 2
        ws.cell(row=total_row, column=1, value="ИТОГО:").font = Font(bold=True)
        ws.cell(row=total_row, column=10, value=sum(float(p.amount) for p in payments)).font = Font(bold=True)
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output
    
    def export_visits_xlsx(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        client_id: Optional[str] = None,
    ) -> BytesIO:
        """Экспорт посещений в XLSX"""
        query = self.db.query(Visit)
        
        if date_from:
            query = query.filter(Visit.entry_time >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            query = query.filter(Visit.entry_time <= datetime.combine(date_to, datetime.max.time()))
        if client_id:
            query = query.filter(Visit.client_id == client_id)
        
        visits = query.order_by(Visit.entry_time.desc()).all()
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Посещения"
        
        headers = ["№", "ID посещения", "Дата входа", "Время входа", "Дата выхода", "Время выхода",
                   "Длительность (мин)", "ФИО клиента", "Телефон", "Абонемент", "Статус", "Зона", "Метод доступа"]
        
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
        thin_border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin')
        )
        
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border
        
        for row_idx, visit in enumerate(visits, 2):
            client_name = ""
            client_phone = ""
            if visit.client:
                parts = [p for p in [visit.client.last_name, visit.client.first_name, visit.client.middle_name] if p]
                client_name = " ".join(parts)
                client_phone = visit.client.phone or ""
            
            sub_name = ""
            if visit.subscription:
                sub_name = visit.subscription.name or ""
            
            ws.cell(row=row_idx, column=1, value=row_idx - 1).border = thin_border
            ws.cell(row=row_idx, column=2, value=str(visit.id)).border = thin_border
            ws.cell(row=row_idx, column=3, value=visit.entry_time.strftime("%d.%m.%Y") if visit.entry_time else "").border = thin_border
            ws.cell(row=row_idx, column=4, value=visit.entry_time.strftime("%H:%M:%S") if visit.entry_time else "").border = thin_border
            ws.cell(row=row_idx, column=5, value=visit.exit_time.strftime("%d.%m.%Y") if visit.exit_time else "").border = thin_border
            ws.cell(row=row_idx, column=6, value=visit.exit_time.strftime("%H:%M:%S") if visit.exit_time else "").border = thin_border
            ws.cell(row=row_idx, column=7, value=visit.duration_minutes or 0).border = thin_border
            ws.cell(row=row_idx, column=8, value=client_name).border = thin_border
            ws.cell(row=row_idx, column=9, value=client_phone).border = thin_border
            ws.cell(row=row_idx, column=10, value=sub_name).border = thin_border
            ws.cell(row=row_idx, column=11, value=visit.status or "").border = thin_border
            ws.cell(row=row_idx, column=12, value=visit.zone or "").border = thin_border
            ws.cell(row=row_idx, column=13, value=visit.access_method or "").border = thin_border
        
        for col_idx in range(1, len(headers) + 1):
            max_length = 0
            column = get_column_letter(col_idx)
            for cell in ws[column]:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column].width = adjusted_width
        
        ws.freeze_panes = 'A2'
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output
'@

Set-Content -Path "app/services/report_service.py" -Value  -Encoding UTF8
Write-Host "report_service.py создан!"
