# create_print_service.py
with open('app/services/print_service.py', 'w', encoding='utf-8') as f:
    f.write('''from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.hardware_device import HardwareDevice, PrintJob
from app.models.payment import Payment
from app.models.receipt import Receipt


class PrintService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_devices(self, device_type: Optional[str] = None) -> List[HardwareDevice]:
        """Получить список устройств"""
        query = self.db.query(HardwareDevice)
        if device_type:
            query = query.filter(HardwareDevice.device_type == device_type)
        return query.order_by(HardwareDevice.is_default.desc()).all()
    
    def get_default_printer(self) -> Optional[HardwareDevice]:
        """Получить принтер по умолчанию"""
        return self.db.query(HardwareDevice).filter(
            HardwareDevice.device_type == 'PRINTER',
            HardwareDevice.is_default == True,
            HardwareDevice.status == 'ACTIVE'
        ).first()
    
    def create_print_job(
        self,
        document_type: str,
        content: str,
        content_type: str = 'TEXT',
        device_id: Optional[str] = None,
        payment_id: Optional[str] = None,
        receipt_id: Optional[str] = None,
        copies: int = 1,
        actor_user_id: Optional[str] = None,
    ) -> PrintJob:
        """Создать задание на печать"""
        import uuid
        
        # Если устройство не указано — берём по умолчанию
        if not device_id:
            default_printer = self.get_default_printer()
            if default_printer:
                device_id = str(default_printer.id)
        
        job = PrintJob(
            id=str(uuid.uuid4()),
            device_id=device_id,
            document_type=document_type,
            content=content,
            content_type=content_type,
            status='PENDING',
            copies=copies,
            payment_id=payment_id,
            receipt_id=receipt_id,
            created_by_user_id=actor_user_id,
        )
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        return job
    
    def print_receipt(self, payment_id: str, actor_user_id: Optional[str] = None) -> PrintJob:
        """Печать чека по платежу"""
        payment = self.db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")
        
        # Формируем содержимое чека
        client_name = ""
        if payment.client:
            parts = [p for p in [payment.client.last_name, payment.client.first_name] if p]
            client_name = " ".join(parts)
        
        content = f"""
================================
        FitIntel Pro
================================
Date: {payment.created_at.strftime('%d.%m.%Y %H:%M') if payment.created_at else ''}
Receipt No: {payment.receipt.receipt_number if payment.receipt else 'N/A'}
Payment ID: {payment.id}

Client: {client_name}
Phone: {payment.client.phone if payment.client else ''}

--------------------------------
Amount: {payment.amount} {payment.currency}
Method: {payment.payment_method}
Status: {payment.status}
--------------------------------
Purpose: {payment.notes or ''}

================================
  Thank you for your visit!
================================
"""
        
        return self.create_print_job(
            document_type='RECEIPT',
            content=content,
            payment_id=payment_id,
            actor_user_id=actor_user_id,
        )
    
    def print_payment_report(self, payment_ids: List[str], actor_user_id: Optional[str] = None) -> PrintJob:
        """Печать выписки по платежам"""
        payments = self.db.query(Payment).filter(Payment.id.in_(payment_ids)).all()
        
        lines = [
            "=" * 40,
            "        PAYMENT REPORT",
            "=" * 40,
            f"Date: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            "-" * 40,
        ]
        
        total = 0
        for idx, payment in enumerate(payments, 1):
            client_name = ""
            if payment.client:
                parts = [p for p in [payment.client.last_name, payment.client.first_name] if p]
                client_name = " ".join(parts)
            
            lines.append(f"{idx}. {client_name}")
            lines.append(f"   Amount: {payment.amount} {payment.currency}")
            lines.append(f"   Method: {payment.payment_method}")
            lines.append(f"   Status: {payment.status}")
            lines.append("-" * 40)
            total += float(payment.amount)
        
        lines.append(f"TOTAL: {total:.2f}")
        lines.append("=" * 40)
        
        content = "\\n".join(lines)
        
        return self.create_print_job(
            document_type='REPORT',
            content=content,
            actor_user_id=actor_user_id,
        )
    
    def get_print_jobs(self, status: Optional[str] = None, limit: int = 50) -> List[PrintJob]:
        """Получить задания на печать"""
        query = self.db.query(PrintJob)
        if status:
            query = query.filter(PrintJob.status == status)
        return query.order_by(PrintJob.created_at.desc()).limit(limit).all()
    
    def mark_job_completed(self, job_id: str) -> PrintJob:
        """Отметить задание как выполненное"""
        job = self.db.query(PrintJob).filter(PrintJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.status = 'COMPLETED'
        job.printed_at = datetime.now()
        self.db.commit()
        self.db.refresh(job)
        return job
    
    def mark_job_failed(self, job_id: str, error: str) -> PrintJob:
        """Отметить задание как ошибочное"""
        job = self.db.query(PrintJob).filter(PrintJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.status = 'FAILED'
        job.error_message = error
        self.db.commit()
        self.db.refresh(job)
        return job
''')

print("print_service.py создан!")
