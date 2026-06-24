# add_windows_print.py
with open('app/services/print_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем print_to_escpos на print_to_windows
old_escpos = '''    def print_to_escpos(self, job_id: str) -> bool:
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
            return False'''

new_windows = '''    def print_to_windows(self, job_id: str) -> bool:
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
            return False
    
    def print_raw_escpos(self, job_id: str) -> bool:
        """Печать RAW ESC/POS команд на принтер (для POS-80)"""
        import win32print
        import win32api
        
        job = self.db.query(PrintJob).filter(PrintJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        try:
            # Получаем имя принтера
            if job.device and job.device.connection_string and job.device.connection_string != 'USB001':
                printer_name = job.device.connection_string
            else:
                printer_name = win32print.GetDefaultPrinter()
            
            # Открываем принтер
            hprinter = win32print.OpenPrinter(printer_name)
            
            # Начинаем печать RAW
            level = 1
            doc_info = ("RAW", None, "RAW")
            job_id_win = win32print.StartDocPrinter(hprinter, 1, doc_info)
            win32print.StartPagePrinter(hprinter)
            
            # ESC/POS команды
            ESC = b'\\x1b'
            INIT = ESC + b'@'
            ALIGN_CENTER = ESC + b'a\\x01'
            ALIGN_LEFT = ESC + b'a\\x00'
            BOLD_ON = ESC + b'E\\x01'
            BOLD_OFF = ESC + b'E\\x00'
            CUT = ESC + b'd\\x03'
            
            # Отправляем данные
            data = INIT
            data += ALIGN_CENTER + BOLD_ON + b'FitIntel Pro\\n' + BOLD_OFF
            data += ALIGN_LEFT
            
            # Конвертируем текст в байты (транслитерация кириллицы)
            text = job.content.encode('cp866', errors='replace')
            data += text
            
            data += b'\\n\\n' + CUT
            
            win32print.WritePrinter(hprinter, data)
            win32print.EndPagePrinter(hprinter)
            win32print.EndDocPrinter(hprinter)
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

if old_escpos in content:
    content = content.replace(old_escpos, new_windows)
    with open('app/services/print_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Windows печать добавлена!")
else:
    print("ERROR: Не найден print_to_escpos")
