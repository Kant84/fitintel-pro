# fix_remove_detection.py
with open('app/services/print_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Убираем _detect_printer_type и всегда используем GDI
old_execute = '''    def execute_print(self, job_id: str, mode: str = "auto") -> dict:
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
        }'''

new_execute = '''    def execute_print(self, job_id: str, mode: str = "auto") -> dict:
        """Универсальное выполнение печати"""
        job = self.db.query(PrintJob).filter(PrintJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Определяем принтер
        printer_name = None
        if job.device and job.device.connection_string:
            printer_name = job.device.connection_string
        
        # Выполняем печать
        if mode == "emulate":
            result = self._print_emulate(job)
        else:
            # По умолчанию — GDI (универсально для всех принтеров)
            result = self._print_gdi(job, printer_name or "Canon TS3300 series")
        
        return {
            "job_id": job_id,
            "status": job.status,
            "mode": mode,
            "printer": printer_name,
            "result": result
        }'''

if old_execute in content:
    content = content.replace(old_execute, new_execute)
    
    # Убираем _detect_printer_type
    old_detect = '''    def _detect_printer_type(self, printer_name: str) -> str:
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
    
    def _print_gdi(self, job: PrintJob, printer_name: str) -> bool:'''
    
    new_detect = '''    def _print_gdi(self, job: PrintJob, printer_name: str) -> bool:'''
    
    content = content.replace(old_detect, new_detect)
    
    with open('app/services/print_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Убрано автоопределение, всегда GDI!")
else:
    print("ERROR: Не найден execute_print")
