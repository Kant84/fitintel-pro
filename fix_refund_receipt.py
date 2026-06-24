# fix_refund_receipt.py
with open('app/services/payment_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_refund = '''        self.db.add(refund_payment)
        
        # Если возврат на баланс'''

new_refund = '''        self.db.add(refund_payment)
        
        # Создаём чек возврата
        from app.models.receipt import Receipt
        import uuid
        receipt = Receipt(
            payment_id=refund_payment.id,
            receipt_number=f"REF-{uuid.uuid4().hex[:8].upper()}",
            receipt_type="REFUND",
            fiscal_sign=None,
            fiscal_document_number=None,
            fiscal_document_date=None,
            ofd_url=None,
            qr_code=None,
        )
        self.db.add(receipt)
        
        # Если возврат на баланс'''

if old_refund in content:
    content = content.replace(old_refund, new_refund)
    with open('app/services/payment_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Чек возврата добавлен!")
else:
    print("Не найден блок возврата")
