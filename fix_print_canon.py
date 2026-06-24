# fix_print_canon.py
with open('app/services/print_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Обновляем print_to_windows для работы с обычным принтером
old_windows = '''    def print_to_windows(self, job_id: str) -> bool:
        """Печать через Windows API (win32print) — работает с любым USB принтером"""
        import win32print
        import win32api
        
        job = self.db.query(PrintJob).filter(PrintJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        try:
            # Получаем имя принтера по умолчанию или из настроек
            if job.device and job.device.connection_string and job.device.connection_string != 'USB001':
                printer_name = job.device.connection_string
            else:
                printer_name = win32print.GetDefaultPrinter()
            
            # Открываем принтер
            hprinter = win32print.OpenPrinter(printer_name)
            
            # Начинаем документ
            job_info = win32print.GetJob(hprinter, 1)
            
            # Создаём DC (Device Context)
            hdc = win32print.CreateDC(printer_name)
            
            # Печать текста
            win32print.StartDoc(hdc, ("FitIntel Pro Receipt", None, None, 0))
            win32print.StartPage(hdc)
            
            # Настройки шрифта
            import win32gui
            import win32con
            
            # Простая печать текста через GDI
            font = win32gui.CreateFont(24, 0, 0, 0, win32con.FW_NORMAL, False, False, False, 
                                      win32con.DEFAULT_CHARSET, win32con.OUT_DEFAULT_PRECIS,
                                      win32con.CLIP_DEFAULT_PRECIS, win32con.DEFAULT_QUALITY,
                                      win32con.DEFAULT_PITCH | win32con.FF_SWISS, "Arial")
            
            win32gui.SelectObject(hdc, font)
            
            # Печатаем строки
            y = 100
            for line in job.content.split('\\n'):
                win32gui.TextOut(hdc, 100, y, line)
                y += 30
            
            win32print.EndPage(hdc)
            win32print.EndDoc(hdc)
            win32print.DeleteDC(hdc)
            win32print.ClosePrinter(hprinter)
            
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
            return False'''

new_windows = '''    def print_to_windows(self, job_id: str) -> bool:
        """Печать через Windows API — работает с любым принтером (Canon, HP, Epson)"""
        import win32print
        import win32gui
        import win32con
        
        job = self.db.query(PrintJob).filter(PrintJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        try:
            # Получаем имя принтера
            if job.device and job.device.connection_string and job.device.connection_string != 'USB001':
                printer_name = job.device.connection_string
            else:
                printer_name = win32print.GetDefaultPrinter()
            
            # Создаём DC для принтера
            hdc = win32gui.CreateDC("WINSPOOL", printer_name, None)
            
            # Начинаем документ
            doc_name = "FitIntel Pro Receipt"
            win32print.StartDoc(hdc, (doc_name, None, None, 0))
            win32print.StartPage(hdc)
            
            # Настройки шрифта
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
            
            # Печатаем текст
            y = 100
            for line in job.content.split('\\n'):
                # Транслитерация для принтера
                safe_line = self._translit(line) if hasattr(self, '_translit') else line
                win32gui.TextOut(hdc, 100, y, safe_line)
                y += 40
            
            # Заканчиваем печать
            win32print.EndPage(hdc)
            win32print.EndDoc(hdc)
            win32gui.DeleteDC(hdc)
            
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
            return False'''

if old_windows in content:
    content = content.replace(old_windows, new_windows)
    with open('app/services/print_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Windows print обновлён для Canon!")
else:
    print("ERROR: Не найден print_to_windows")
