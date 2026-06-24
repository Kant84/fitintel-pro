# fix_print_simple_final.py
with open('app/services/print_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Исправляем execute_print — убираем win32print
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
        
        return {'''

new_execute = '''    def execute_print(self, job_id: str, mode: str = "auto") -> dict:
        """Универсальное выполнение печати"""
        job = self.db.query(PrintJob).filter(PrintJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Определяем принтер (без win32print — из БД или Canon по умолчанию)
        printer_name = "Canon TS3300 series"
        if job.device and job.device.connection_string:
            printer_name = job.device.connection_string
        
        # Выполняем печать
        if mode == "emulate":
            result = self._print_emulate(job)
        else:
            result = self._print_gdi(job, printer_name)
        
        return {'''

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
    
    def _print_gdi(self, job: PrintJob, printer_name: str) -> bool:
        """Печать через Windows — простой текстовый метод"""
        
        try:
            # Открываем принтер
            hprinter = win32print.OpenPrinter(printer_name)
            
            # Начинаем документ
            doc_info = ("FitIntel Pro Receipt", None, "RAW")
            job_id = win32print.StartDocPrinter(hprinter, 1, doc_info)
            win32print.StartPagePrinter(hprinter)
            
            # Формируем текст для печати
            text = job.content.replace('\\n', '\\r\\n')
            header = "\\r\\n\\r\\n          FitIntel Pro\\r\\n"
            header += "          =============\\r\\n\\r\\n"
            text = header + text
            
            # Печатаем
            win32print.WritePrinter(hprinter, text.encode('cp1251', errors='replace'))
            
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
            return False'''

    new_detect = '''    def _print_gdi(self, job: PrintJob, printer_name: str) -> bool:
        """Печать через Windows — через отдельный процесс (start, не блокирует)"""
        import subprocess
        import tempfile
        import os
        
        try:
            # Сохраняем содержимое
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(job.content)
                temp_file = f.name
            
            # Запускаем print_helper.py через start (новое окно, не ждём)
            helper_path = os.path.join(os.path.dirname(__file__), '..', '..', 'print_helper.py')
            helper_path = os.path.abspath(helper_path)
            
            # Используем start /b для фонового запуска
            subprocess.Popen(
                f'start /b python "{helper_path}" "{printer_name}" "{temp_file}"',
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Не ждём — отмечаем сразу
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
            return False'''
    
    content = content.replace(old_detect, new_detect)
    
    with open('app/services/print_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Исправлено! Убран win32print из execute_print!")
else:
    print("ERROR: Не найден execute_print")
