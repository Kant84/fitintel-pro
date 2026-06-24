# fix_print_simple_v2.py
with open('app/services/print_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_gdi = '''    def _print_gdi(self, job: PrintJob, printer_name: str) -> bool:
        """Печать через GDI — универсально для всех Windows-принтеров"""
        
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
            return False'''

new_gdi = '''    def _print_gdi(self, job: PrintJob, printer_name: str) -> bool:
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

if old_gdi in content:
    content = content.replace(old_gdi, new_gdi)
    with open('app/services/print_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("GDI печать исправлена!")
else:
    print("ERROR: Не найден _print_gdi")
