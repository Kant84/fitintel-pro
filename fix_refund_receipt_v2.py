# fix_refund_receipt_v2.py
with open('app/services/payment_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Удаляем старый блок
old_block = '''        self.db.add(refund_payment)
        
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

new_block = '''        self.db.add(refund_payment)
        
        # Если возврат на баланс'''

if old_block in content:
    content = content.replace(old_block, new_block)
    
    # Находим commit и добавляем чек ПОСЛЕ
    old_commit = '''        self.db.commit()
        
        self.audit.log(
            action="payment.refunded",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="payment",
            entity_id=payment.id,
            message=f"Payment refunded: {refund_amount} RUB, reason: {reason}",
            after_data={
                "original_payment_id": payment_id,
                "refund_payment_id": refund_payment.id,
                "amount": str(refund_amount),
                "refund_to_balance": refund_to_balance,
            },
        )
        
        return PaymentRefundResponse(
            success=True,
            refund_id=refund_payment.id,
            refunded_amount=refund_amount,
            message=f"Возврат на сумму {refund_amount} RUB выполнен успешно",
        )'''

    new_commit = '''        self.db.commit()
        
        # Создаём чек возврата (после commit, ID сгенерирован)
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
        self.db.commit()
        
        self.audit.log(
            action="payment.refunded",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="payment",
            entity_id=payment.id,
            message=f"Payment refunded: {refund_amount} RUB, reason: {reason}",
            after_data={
                "original_payment_id": payment_id,
                "refund_payment_id": refund_payment.id,
                "amount": str(refund_amount),
                "refund_to_balance": refund_to_balance,
            },
        )
        
        return PaymentRefundResponse(
            success=True,
            refund_id=refund_payment.id,
            refunded_amount=refund_amount,
            message=f"Возврат на сумму {refund_amount} RUB выполнен успешно",
        )'''

    if old_commit in content:
        content = content.replace(old_commit, new_commit)
        print("Чек возврата добавлен ПОСЛЕ commit!")
    else:
        print("Не найден commit блок")
    
    with open('app/services/payment_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
else:
    print("Не найден старый блок")
