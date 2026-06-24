report_service_code = '''from io import BytesIO
from datetime import datetime, date
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from sqlalchemy.orm import Session
from app.models.payment import Payment


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
        
        headers = [
            "№", "ID платежа", "Дата", "Время", "Направление", "Категория",
            "ФИО клиента", "Телефон", "Email", "Сумма", "Валюта",
            "Способ оплаты", "Тип платежа", "Банк/Система", "Статус",
            "Назначение", "Номер чека", "Кем создан"
        ]
        
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border
        
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
        
        total_row = len(payments) + 2
        ws.cell(row=total_row, column=1, value="ИТОГО:").font = Font(bold=True)
        ws.cell(row=total_row, column=10, value=sum(float(p.amount) for p in payments)).font = Font(bold=True)
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output
'''

with open('app/services/report_service.py', 'w', encoding='utf-8') as f:
    f.write(report_service_code)

print("report_service.py создан!")
''' | Set-Content -Path "create_report_service.py" -Encoding UTF8

python create_report_service.py
