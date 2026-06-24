# recreate_print_service_universal.py
with open('app/services/print_service.py', 'w', encoding='utf-8') as f:
    f.write('''from datetime import datetime
from typing import Optional, List
import os

from sqlalchemy.orm import Session

from app.models.hardware_device import HardwareDevice, PrintJob
from app.models.payment import Payment


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
    
    def detect_printers(self) -> List[dict]:
        """Автоопределение всех принтеров в системе"""
        import win32print
        printers = []
        
        for p in win32print.EnumPrinters(2):
            try:
                name = p[2]
                # Пропускаем виртуальные принтеры
                if any(x in name.lower() for x in ['onenote', 'fax', 'pdf', 'xps', 'microsoft print']):
                    continue
                
                # Получаем информацию
                hprinter = win32print.OpenPrinter(name)
                info = win32print.GetPrinter(hprinter, 2)
                port = info.get('pPortName', 'Unknown')
                driver = info.get('pDriverName', 'Unknown')
                status = info.get('Status', 0)
                win32print.ClosePrinter(hprinter)
                
                printers.append({
                    'name': name,
                    'port': port,
                    'driver': driver,
                    'status': 'READY' if status == 0 else f'ERROR_{status}',
                    'connection': 'USB' if 'USB' in str(port).upper() else 'NETWORK' if 'IP' in str(port) else 'OTHER'
                })
            except:
                continue
        
        return printers
    
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
    
    def execute_print(self, job_id: str, mode: str = "auto") -> dict:
        """Универсальное выполнение печати — автоопределение принтера"""
        job = self.db.query(PrintJob).filter(PrintJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Определяем принтер
        printer_name = None
        if job.device and job.device.connection_string:
            printer_name = job.device.connection_string
        else:
            import win32print
            printer_name = win32print.GetDefaultPrinter()
        
        # Определяем тип принтера по имени драйвера/порта
        printer_type = self._detect_printer_type(printer_name)
        
        if mode == "auto":
            mode = printer_type
        
        # Выполняем печать в зависимости от типа
        if mode == "escpos":
            result = self._print_escpos(job, printer_name)
        elif mode == "gdi":
            result = self._print_gdi(job, printer_name)
        elif mode == "emulate":
            result = self._print_emulate(job)
        else:
            # По умолчанию — GDI (универсально для всех принтеров)
            result = self._print_gdi(job, printer_name)
        
        return {
            "job_id": job_id,
            "status": job.status,
            "mode": mode,
            "printer": printer_name,
            "result": result
        }
    
    def _detect_printer_type(self, printer_name: str) -> str:
        """Автоопределение типа принтера"""
        import win32print
        
        try:
            hprinter = win32print.OpenPrinter(printer_name)
            info = win32print.GetPrinter(hprinter, 2)
            driver = info.get('pDriverName', '').lower()
            port = info.get('pPortName', '').lower()
            win32print.ClosePrinter(hprinter)
            
            # Чековые принтеры
            if any(x in driver for x in ['pos', 'escpos', 'tm-t', 'tm-m', 'xp-80', '80mm']):
                return 'escpos'
            if any(x in port for x in ['usb', 'com']):
                # Может быть и чековый и обычный
                if any(x in printer_name.lower() for x in ['pos', '80', '58', 'thermal']):
                    return 'escpos'
            
            # По умолчанию — GDI (Canon, HP, Epson и т.д.)
            return 'gdi'
            
        except:
            return 'gdi'
    
    def _print_gdi(self, job: PrintJob, printer_name: str) -> bool:
        """Печать через GDI — универсально для всех Windows-принтеров"""
        import win32print
        import win32gui
        import win32con
        
        try:
            hdc = win32gui.CreateDC("WINSPOOL", printer_name, None)
            
            win32print.StartDoc(hdc, ("FitIntel Pro", None, None, 0))
            win32print.StartPage(hdc)
            
            # Шрифт
            font = win32gui.CreateFont(
                -24, 0, 0, 0, win32con.FW_NORMAL,
                False, False, False,
                win32con.DEFAULT_CHARSET,
                win32con.OUT_DEFAULT_PRECIS,
                win32con.CLIP_DEFAULT_PRECIS,
                win32con.DEFAULT_QUALITY,
                win32con.DEFAULT_PITCH | win32con.FF_SWISS,
                "Arial"
            )
            win32gui.SelectObject(hdc, font)
            
            # Печать
            y = 100
            for line in job.content.split('\\n'):
                win32gui.TextOut(hdc, 100, y, line)
                y += 40
            
            win32print.EndPage(hdc)
            win32print.EndDoc(hdc)
            win32gui.DeleteDC(hdc)
            
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
    
    def _print_escpos(self, job: PrintJob, printer_name: str) -> bool:
        """Печать RAW ESC/POS для чековых принтеров"""
        import win32print
        
        try:
            hprinter = win32print.OpenPrinter(printer_name)
            
            doc_info = ("RAW", None, "RAW")
            win32print.StartDocPrinter(hprinter, 1, doc_info)
            win32print.StartPagePrinter(hprinter)
            
            # ESC/POS команды
            ESC = b'\\x1b'
            INIT = ESC + b'@'
            CENTER = ESC + b'a\\x01'
            LEFT = ESC + b'a\\x00'
            BOLD_ON = ESC + b'E\\x01'
            BOLD_OFF = ESC + b'E\\x00'
            CUT = ESC + b'd\\x03'
            
            data = INIT + CENTER + BOLD_ON + b'FitIntel Pro\\n' + BOLD_OFF + LEFT
            data += job.content.encode('cp866', errors='replace')
            data += b'\\n\\n' + CUT
            
            win32print.WritePrinter(hprinter, data)
            win32print.EndPagePrinter(hprinter)
            win32print.EndDocPrinter(hprinter)
            win32print.ClosePrinter(hprinter)
            
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
        """Эмуляция печати — сохраняет в файл"""
        output_dir = "print_output"
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"{output_dir}/print_job_{job.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"=== FitIntel Pro Print Job ===\\n")
            f.write(f"Job ID: {job.id}\\n")
            f.write(f"Document Type: {job.document_type}\\n")
            f.write(f"Printer: {job.device.name if job.device else 'Auto'}\\n")
            f.write(f"Created: {job.created_at}\\n")
            f.write("=" * 40 + "\\n\\n")
            f.write(job.content)
            f.write("\\n\\n" + "=" * 40 + "\\n")
        
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
''')

print("print_service.py пересоздан (универсальный)!")
