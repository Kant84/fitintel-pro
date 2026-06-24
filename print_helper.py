# print_helper.py
import sys
import os
import time

def print_file(file_path, printer_name):
    """Печать файла через win32print"""
    try:
        import win32print
        import win32api
        
        # Печать через ShellExecute
        win32api.ShellExecute(0, "print", file_path, f'/d:"{printer_name}"', ".", 0)
        
        # Ждём 3 секунды
        time.sleep(3)
        
        # Удаляем файл
        try:
            os.remove(file_path)
        except:
            pass
            
        print("OK")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python print_helper.py <printer> <file>")
        sys.exit(1)
    
    print_file(sys.argv[2], sys.argv[1])
