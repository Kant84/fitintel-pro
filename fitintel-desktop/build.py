"""Build script for FitIntel Pro Desktop (.exe)

Usage:
    python build.py

Output:
    dist/FitIntelPro.exe
"""
import PyInstaller.__main__
import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")
BUILD_DIR = os.path.join(BASE_DIR, "build")

# Очистка старых сборок
if os.path.exists(DIST_DIR):
    shutil.rmtree(DIST_DIR)
if os.path.exists(BUILD_DIR):
    shutil.rmtree(BUILD_DIR)

PyInstaller.__main__.run([
    "main.py",
    "--name=FitIntelPro",
    "--onefile",
    "--windowed",
    "--icon=NONE",  # Замените на путь к .ico если есть
    "--add-data", f"windows{os.pathsep}windows",
    "--add-data", f"api{os.pathsep}api",
    "--hidden-import", "PyQt6.sip",
    "--hidden-import", "requests",
    "--clean",
    "--noconfirm",
])

print("\n✅ Сборка завершена!")
print(f"📁 EXE находится в: {os.path.join(DIST_DIR, 'FitIntelPro.exe')}")
