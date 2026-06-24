# fix_print_subprocess_v2.py
with open('app/services/print_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_gdi = '''    def _print_gdi(self, job: PrintJob, printer_name: str) -> bool:
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

new_gdi = '''    def _print_gdi(self, job: PrintJob, printer_name: str) -> bool:
        """Печать через Windows — через subprocess"""
        import subprocess
        import tempfile
        
        try:
            # Сохраняем содержимое во временный файл
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(job.content)
                temp_file = f.name
            
            # Печатаем через notepad /p (стандартная печать Windows)
            result = subprocess.run(
                ['notepad', '/p', temp_file],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Удаляем временный файл
            os.remove(temp_file)
            
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
    print("GDI печать через notepad!")
else:
    print("ERROR: Не найден _print_gdi")
