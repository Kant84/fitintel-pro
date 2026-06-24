from datetime import datetime
from typing import Optional, List
import os

from sqlalchemy.orm import Session

from app.models.hardware_device import HardwareDevice, PrintJob
from app.models.payment import Payment


class PrintService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_devices(self, device_type: Optional[str] = None) -> List[HardwareDevice]:
        query = self.db.query(HardwareDevice)
        if device_type:
            query = query.filter(HardwareDevice.device_type == device_type)
        return query.order_by(HardwareDevice.is_default.desc()).all()
    
    def get_default_printer(self) -> Optional[HardwareDevice]:
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
        import uuid
        
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
        payment = self.db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")
        
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
        
        content = "\n".join(lines)
        
        return self.create_print_job(
            document_type='REPORT',
            content=content,
            actor_user_id=actor_user_id,
        )
    
    def get_print_jobs(self, status: Optional[str] = None, limit: int = 50) -> List[PrintJob]:
        query = self.db.query(PrintJob)
        if status:
            query = query.filter(PrintJob.status == status)
        return query.order_by(PrintJob.created_at.desc()).limit(limit).all()
    
    def execute_print(self, job_id: str, mode: str = "auto") -> dict:
        job = self.db.query(PrintJob).filter(PrintJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        printer_name = "Canon TS3300 series"
        if job.device and job.device.connection_string:
            printer_name = job.device.connection_string
        
        if mode == "emulate":
            result = self._print_emulate(job)
        else:
            result = self._print_gdi(job, printer_name)
        
        return {
            "job_id": job_id,
            "status": job.status,
            "mode": mode,
            "printer": printer_name,
            "result": result
        }
    
    def _print_gdi(self, job: PrintJob, printer_name: str) -> bool:
        import subprocess
        import tempfile
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(job.content)
                temp_file = f.name
            
            helper_path = os.path.join(os.path.dirname(__file__), '..', '..', 'print_helper.py')
            helper_path = os.path.abspath(helper_path)
            
            subprocess.Popen(
                f'start /b python "{helper_path}" "{printer_name}" "{temp_file}"',
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            job.status = 'COMPLETED'
            job.printed_at = datetime.now()
            self.db.commit()
            self.db.refresh(job)
            
            return True
            
        except Exception as e:
            job.status = 'FAILED'
            job.error_message = str(e)
            self.db.commit()
            self.db.refresh(job)
            return False
    
    def _print_emulate(self, job: PrintJob) -> str:
        output_dir = "print_output"
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"{output_dir}/print_job_{job.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"=== FitIntel Pro Print Job ===\n")
            f.write(f"Job ID: {job.id}\n")
            f.write(f"Document Type: {job.document_type}\n")
            f.write(f"Printer: {job.device.name if job.device else 'Auto'}\n")
            f.write(f"Created: {job.created_at}\n")
            f.write("=" * 40 + "\n\n")
            f.write(job.content)
            f.write("\n\n" + "=" * 40 + "\n")
        
        job.status = 'COMPLETED'
        job.printed_at = datetime.now()
        self.db.commit()
        self.db.refresh(job)
        
        return filename
    
    def mark_job_completed(self, job_id: str) -> PrintJob:
        job = self.db.query(PrintJob).filter(PrintJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        job.status = 'COMPLETED'
        job.printed_at = datetime.now()
        self.db.commit()
        self.db.refresh(job)
        return job
    
    def mark_job_failed(self, job_id: str, error: str) -> PrintJob:
        job = self.db.query(PrintJob).filter(PrintJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        job.status = 'FAILED'
        job.error_message = error
        self.db.commit()
        self.db.refresh(job)
        return job
