# add_print_emulation.py
with open('app/services/print_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем метод эмуляции печати
old_end = '''    def mark_job_failed(self, job_id: str, error: str) -> PrintJob:
        """Отметить задание как ошибочное"""
        job = self.db.query(PrintJob).filter(PrintJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.status = 'FAILED'
        job.error_message = error
        self.db.commit()
        self.db.refresh(job)
        return job'''

new_methods = '''
    def emulate_print(self, job_id: str, output_dir: str = "print_output") -> str:
        """Эмуляция печати — сохраняет в файл вместо реального принтера"""
        import os
        
        job = self.db.query(PrintJob).filter(PrintJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Создаём директорию
        os.makedirs(output_dir, exist_ok=True)
        
        # Формируем имя файла
        filename = f"{output_dir}/print_job_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Записываем содержимое
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"=== FitIntel Pro Print Job ===\\n")
            f.write(f"Job ID: {job_id}\\n")
            f.write(f"Document Type: {job.document_type}\\n")
            f.write(f"Created At: {job.created_at}\\n")
            f.write(f"Copies: {job.copies}\\n")
            f.write(f"Device: {job.device.name if job.device else 'Default'}\\n")
            f.write("=" * 40 + "\\n\\n")
            f.write(job.content)
            f.write("\\n\\n" + "=" * 40 + "\\n")
            f.write("=== END OF DOCUMENT ===\\n")
        
        # Отмечаем как выполненное
        job.status = 'COMPLETED'
        job.printed_at = datetime.now()
        self.db.commit()
        self.db.refresh(job)
        
        return filename
    
    def print_to_escpos(self, job_id: str) -> bool:
        """Печать на реальный ESC/POS принтер через pyusb/serial"""
        try:
            import serial
        except ImportError:
            return False
        
        job = self.db.query(PrintJob).filter(PrintJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if not job.device or not job.device.connection_string:
            raise ValueError("No printer configured")
        
        try:
            # Подключаемся к принтеру
            port = job.device.connection_string  # COM3, /dev/usb/lp0 и т.д.
            printer = serial.Serial(port, 9600, timeout=1)
            
            # ESC/POS команды
            ESC = b'\\x1b'
            INIT = ESC + b'@'  # Инициализация
            ALIGN_CENTER = ESC + b'a\\x01'
            ALIGN_LEFT = ESC + b'a\\x00'
            BOLD_ON = ESC + b'E\\x01'
            BOLD_OFF = ESC + b'E\\x00'
            CUT = ESC + b'd\\x03'  # Отрезать бумагу
            
            # Отправляем
            printer.write(INIT)
            printer.write(ALIGN_CENTER)
            printer.write(BOLD_ON)
            printer.write(b'FitIntel Pro\\n')
            printer.write(BOLD_OFF)
            printer.write(ALIGN_LEFT)
            printer.write(job.content.encode('utf-8'))
            printer.write(CUT)
            
            printer.close()
            
            # Отмечаем как выполненное
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
    
    def mark_job_failed(self, job_id: str, error: str) -> PrintJob:
        """Отметить задание как ошибочное"""
        job = self.db.query(PrintJob).filter(PrintJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.status = 'FAILED'
        job.error_message = error
        self.db.commit()
        self.db.refresh(job)
        return job'''

if old_end in content:
    content = content.replace(old_end, new_methods)
    with open('app/services/print_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Эмуляция печати добавлена!")
else:
    print("ERROR: Не найден mark_job_failed")
