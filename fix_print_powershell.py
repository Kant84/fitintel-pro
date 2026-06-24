# fix_print_powershell.py
with open('app/services/print_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_gdi = '''    def _print_gdi(self, job: PrintJob, printer_name: str) -> bool:
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

new_gdi = '''    def _print_gdi(self, job: PrintJob, printer_name: str) -> bool:
        """Печать через PowerShell Start-Process (не блокирует)"""
        import subprocess
        import tempfile
        
        try:
            # Сохраняем содержимое во временный файл
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(job.content)
                temp_file = f.name
            
            # Запускаем печать через PowerShell в фоне (не ждём завершения!)
            subprocess.Popen(
                ['powershell', '-Command', f'Start-Process notepad -ArgumentList \"/p\",\"{temp_file}\" -WindowStyle Hidden'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Не ждём завершения — отмечаем сразу
            job.status = 'COMPLETED'
            job.printed_at = datetime.now()
            self.db.commit()
            self.db.refresh(job)
            
            # Удаляем файл через 30 секунд (в фоне)
            def cleanup():
                import time
                time.sleep(30)
                try:
                    os.remove(temp_file)
                except:
                    pass
            
            import threading
            threading.Thread(target=cleanup, daemon=True).start()
            
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
    print("GDI печать через Popen (не блокирует)!")
else:
    print("ERROR: Не найден _print_gdi")
