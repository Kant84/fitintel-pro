# fix_all_exports.py
import os

# ========== 1. Обновляем report_service.py ==========
with open('app/services/report_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Находим конец файла и добавляем новые методы
old_end = '''        bytes_output = BytesIO()
        bytes_output.write(output.getvalue().encode('utf-8-sig'))
        bytes_output.seek(0)
        return bytes_output'''

new_methods = '''
    def export_payments_pdf(
        self,
        date_from=None,
        date_to=None,
        client_id=None,
        payment_direction=None,
        payment_category=None,
        status=None,
    ):
        """Экспорт платежей в PDF"""
        from fpdf import FPDF
        
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
        
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        pdf.add_font('DejaVu', 'B', 'DejaVuSans-Bold.ttf', uni=True)
        pdf.set_font('DejaVu', 'B', 14)
        pdf.cell(0, 10, 'Отчет по платежам', ln=True, align='C')
        pdf.set_font('DejaVu', '', 10)
        pdf.cell(0, 6, f'Период: {date_from} - {date_to}', ln=True, align='C')
        pdf.ln(5)
        
        # Заголовки таблицы
        headers = ['№', 'Дата', 'Направление', 'Категория', 'ФИО', 'Сумма', 'Статус', 'Назначение']
        col_widths = [10, 25, 25, 30, 50, 25, 25, 60]
        
        pdf.set_font('DejaVu', 'B', 8)
        pdf.set_fill_color(68, 114, 196)
        pdf.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 8, h, border=1, fill=True, align='C')
        pdf.ln()
        
        # Данные
        pdf.set_font('DejaVu', '', 8)
        pdf.set_text_color(0, 0, 0)
        total = 0
        for idx, payment in enumerate(payments, 1):
            client_name = ''
            if payment.client:
                parts = [p for p in [payment.client.last_name, payment.client.first_name] if p]
                client_name = ' '.join(parts)
            
            row = [
                str(idx),
                payment.created_at.strftime('%d.%m.%Y') if payment.created_at else '',
                payment.payment_direction or 'INCOME',
                payment.payment_category or 'SUBSCRIPTION',
                client_name,
                f'{float(payment.amount):.2f}',
                payment.status or '',
                (payment.notes or '')[:30]
            ]
            
            for i, cell in enumerate(row):
                pdf.cell(col_widths[i], 6, str(cell), border=1, align='C' if i in [0, 5] else 'L')
            pdf.ln()
            total += float(payment.amount)
        
        # Итого
        pdf.set_font('DejaVu', 'B', 10)
        pdf.cell(sum(col_widths) - col_widths[5], 8, 'ИТОГО:', border=1, align='R')
        pdf.cell(col_widths[5], 8, f'{total:.2f}', border=1, align='C')
        pdf.ln()
        
        output = BytesIO()
        pdf.output(output)
        output.seek(0)
        return output
    
    def export_payments_1c(self, date_from=None, date_to=None):
        """Экспорт платежей в формате 1С (txt)"""
        query = self.db.query(Payment)
        
        if date_from:
            query = query.filter(Payment.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            query = query.filter(Payment.created_at <= datetime.combine(date_to, datetime.max.time()))
        
        payments = query.order_by(Payment.created_at.desc()).all()
        
        lines = []
        lines.append('1CCLIENTCOMMA')
        lines.append('###')
        lines.append('Дата;Время;НомерДок;ВидДок;Сумма;Валюта;Контрагент;ИНН;КПП;Назначение;Статус')
        
        for payment in payments:
            client_name = ''
            if payment.client:
                parts = [p for p in [payment.client.last_name, payment.client.first_name] if p]
                client_name = ' '.join(parts)
            
            lines.append(
                f'{payment.created_at.strftime("%d.%m.%Y") if payment.created_at else ""};'
                f'{payment.created_at.strftime("%H:%M:%S") if payment.created_at else ""};'
                f'{str(payment.id)};'
                f'Платеж;'
                f'{float(payment.amount):.2f};'
                f'{payment.currency or "RUB"};'
                f'{client_name};'
                f';;'
                f'{(payment.notes or "")[:50]};'
                f'{payment.status or ""}'
            )
        
        lines.append(f'ИТОГО;{sum(float(p.amount) for p in payments):.2f}')
        
        output = BytesIO()
        output.write('\\n'.join(lines).encode('utf-8-sig'))
        output.seek(0)
        return output
    
    def export_visits_xlsx(self, date_from=None, date_to=None, client_id=None):
        """Экспорт посещений в XLSX"""
        from app.models.visit import Visit
        
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
        ws.title = 'Посещения'
        
        headers = ['№', 'ID посещения', 'Дата входа', 'Время входа', 'Дата выхода', 
                   'Время выхода', 'Длительность (мин)', 'ФИО клиента', 'Телефон', 
                   'Абонемент', 'Статус', 'Зона', 'Метод доступа']
        
        header_font = Font(bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='70AD47', end_color='70AD47', fill_type='solid')
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                            top=Side(style='thin'), bottom=Side(style='thin'))
        
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border
        
        for row_idx, visit in enumerate(visits, 2):
            client_name = ''
            client_phone = ''
            if visit.client:
                parts = [p for p in [visit.client.last_name, visit.client.first_name] if p]
                client_name = ' '.join(parts)
                client_phone = visit.client.phone or ''
            
            sub_name = ''
            if visit.subscription:
                sub_name = visit.subscription.name or ''
            
            ws.cell(row=row_idx, column=1, value=row_idx - 1).border = thin_border
            ws.cell(row=row_idx, column=2, value=str(visit.id)).border = thin_border
            ws.cell(row=row_idx, column=3, value=visit.entry_time.strftime('%d.%m.%Y') if visit.entry_time else '').border = thin_border
            ws.cell(row=row_idx, column=4, value=visit.entry_time.strftime('%H:%M:%S') if visit.entry_time else '').border = thin_border
            ws.cell(row=row_idx, column=5, value=visit.exit_time.strftime('%d.%m.%Y') if visit.exit_time else '').border = thin_border
            ws.cell(row=row_idx, column=6, value=visit.exit_time.strftime('%H:%M:%S') if visit.exit_time else '').border = thin_border
            ws.cell(row=row_idx, column=7, value=visit.duration_minutes or 0).border = thin_border
            ws.cell(row=row_idx, column=8, value=client_name).border = thin_border
            ws.cell(row=row_idx, column=9, value=client_phone).border = thin_border
            ws.cell(row=row_idx, column=10, value=sub_name).border = thin_border
            ws.cell(row=row_idx, column=11, value=visit.status or '').border = thin_border
            ws.cell(row=row_idx, column=12, value=visit.zone or '').border = thin_border
            ws.cell(row=row_idx, column=13, value=visit.access_method or '').border = thin_border
        
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
    
    def export_visits_csv(self, date_from=None, date_to=None, client_id=None):
        """Экспорт посещений в CSV"""
        import csv
        from io import StringIO
        from app.models.visit import Visit
        
        query = self.db.query(Visit)
        
        if date_from:
            query = query.filter(Visit.entry_time >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            query = query.filter(Visit.entry_time <= datetime.combine(date_to, datetime.max.time()))
        if client_id:
            query = query.filter(Visit.client_id == client_id)
        
        visits = query.order_by(Visit.entry_time.desc()).all()
        
        output = StringIO()
        writer = csv.writer(output, delimiter=';', lineterminator='\\n')
        
        headers = ['№', 'ID посещения', 'Дата входа', 'Время входа', 'Дата выхода', 
                   'Время выхода', 'Длительность (мин)', 'ФИО клиента', 'Телефон', 
                   'Абонемент', 'Статус', 'Зона', 'Метод доступа']
        writer.writerow(headers)
        
        for idx, visit in enumerate(visits, 1):
            client_name = ''
            client_phone = ''
            if visit.client:
                parts = [p for p in [visit.client.last_name, visit.client.first_name] if p]
                client_name = ' '.join(parts)
                client_phone = visit.client.phone or ''
            
            sub_name = ''
            if visit.subscription:
                sub_name = visit.subscription.name or ''
            
            writer.writerow([
                idx,
                str(visit.id),
                visit.entry_time.strftime('%d.%m.%Y') if visit.entry_time else '',
                visit.entry_time.strftime('%H:%M:%S') if visit.entry_time else '',
                visit.exit_time.strftime('%d.%m.%Y') if visit.exit_time else '',
                visit.exit_time.strftime('%H:%M:%S') if visit.exit_time else '',
                visit.duration_minutes or 0,
                client_name,
                client_phone,
                sub_name,
                visit.status or '',
                visit.zone or '',
                visit.access_method or ''
            ])
        
        bytes_output = BytesIO()
        bytes_output.write(output.getvalue().encode('utf-8-sig'))
        bytes_output.seek(0)
        return bytes_output
'''

if old_end in content:
    content = content.replace(old_end, old_end + new_methods)
    with open('app/services/report_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('1. report_service.py обновлен!')
else:
    print('1. ERROR: Не найден конец CSV метода')

# ========== 2. Обновляем reports.py endpoint ==========
with open('app/api/v1/reports.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_pdf = '''    elif request.format == "pdf":
        # TODO: PDF export
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF export not yet implemented",
        )'''

new_pdf = '''    elif request.format == "pdf":
        output = service.export_payments_pdf(
            date_from=request.date_from,
            date_to=request.date_to,
            client_id=request.client_id,
            payment_direction=request.payment_direction,
            payment_category=request.payment_category,
            status=request.status,
        )
        
        filename = f"payments_report_{date.today().strftime('%Y%m%d')}.pdf"
        
        return StreamingResponse(
            output,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )'''

if old_pdf in content:
    content = content.replace(old_pdf, new_pdf)
    print('2. PDF endpoint добавлен!')
else:
    print('2. ERROR: Не найден PDF блок')

# Добавляем 1C endpoint
old_end_router = '''    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {request.format}",
        )'''

new_1c = '''    elif request.format == "1c":
        output = service.export_payments_1c(
            date_from=request.date_from,
            date_to=request.date_to,
        )
        
        filename = f"payments_1c_{date.today().strftime('%Y%m%d')}.txt"
        
        return StreamingResponse(
            output,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {request.format}",
        )'''

if old_end_router in content:
    content = content.replace(old_end_router, new_1c)
    print('3. 1C endpoint добавлен!')
else:
    print('3. ERROR: Не найден конец router')

# Добавляем endpoint для посещений
old_router_end = 'router = APIRouter()'

new_router = '''router = APIRouter()


@router.post("/visits/export")
def export_visits(
    request: PaymentExportRequest,
    current_user: User = Depends(require_permission("reports.export")),
    db: Session = Depends(get_db),
):
    """Экспорт посещений в XLSX/CSV"""
    service = ReportService(db)
    
    if request.format == "xlsx":
        output = service.export_visits_xlsx(
            date_from=request.date_from,
            date_to=request.date_to,
            client_id=request.client_id,
        )
        
        filename = f"visits_report_{date.today().strftime('%Y%m%d')}.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    
    elif request.format == "csv":
        output = service.export_visits_csv(
            date_from=request.date_from,
            date_to=request.date_to,
            client_id=request.client_id,
        )
        
        filename = f"visits_report_{date.today().strftime('%Y%m%d')}.csv"
        
        return StreamingResponse(
            output,
            media_type="text/csv; charset=utf-8-sig",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format for visits: {request.format}",
        )'''

if old_router_end in content:
    content = content.replace(old_router_end, new_router)
    with open('app/api/v1/reports.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('4. Visits endpoint добавлен!')
else:
    print('4. ERROR: Не найден router')

print('\\n=== Готово! Все экспорты добавлены! ===')
