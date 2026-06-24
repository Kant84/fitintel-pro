# fix_report_csv.py
with open('app/services/report_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_end = '''        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output'''

new_end = '''        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output
    
    def export_payments_csv(
        self,
        date_from=None,
        date_to=None,
        client_id=None,
        payment_direction=None,
        payment_category=None,
        status=None,
    ):
        """Экспорт платежей в CSV"""
        import csv
        from io import StringIO
        
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
        
        output = StringIO()
        writer = csv.writer(output, delimiter=';', lineterminator='\\n')
        
        headers = [
            "№", "ID платежа", "Дата", "Время", "Направление", "Категория",
            "ФИО клиента", "Телефон", "Email", "Сумма", "Валюта",
            "Способ оплаты", "Тип платежа", "Банк/Система", "Статус",
            "Назначение", "Номер чека", "Кем создан"
        ]
        writer.writerow(headers)
        
        for idx, payment in enumerate(payments, 1):
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
            
            writer.writerow([
                idx,
                str(payment.id),
                payment.created_at.strftime("%d.%m.%Y") if payment.created_at else "",
                payment.created_at.strftime("%H:%M:%S") if payment.created_at else "",
                payment.payment_direction or "INCOME",
                payment.payment_category or "SUBSCRIPTION",
                client_name,
                client_phone,
                client_email,
                float(payment.amount),
                payment.currency or "RUB",
                payment.payment_method or "",
                payment_type,
                bank_name,
                payment.status or "",
                payment.notes or "",
                receipt_num,
                str(payment.created_by_user_id) if payment.created_by_user_id else "",
            ])
        
        writer.writerow([
            "ИТОГО:", "", "", "", "", "", "", "", "",
            sum(float(p.amount) for p in payments),
            "", "", "", "", "", "", "", ""
        ])
        
        bytes_output = BytesIO()
        bytes_output.write(output.getvalue().encode('utf-8-sig'))
        bytes_output.seek(0)
        return bytes_output'''

if old_end in content:
    content = content.replace(old_end, new_end)
    with open('app/services/report_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("CSV экспорт добавлен!")
else:
    print("Не найден конец метода")
