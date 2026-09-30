@echo off
REM ?????? desktop-??????? ??? ???????? ????? (Windows).
cd /d %~dp0
pip install -q --upgrade pyinstaller opencv-python pyscard PyQt6 requests
pyinstaller --noconfirm --clean --windowed --onefile --name "FitIntelDesktop" ^
  --hidden-import PyQt6.sip --hidden-import cv2 --collect-submodules cv2 ^
  --hidden-import smartcard --collect-submodules smartcard ^
  --collect-submodules PyQt6.QtMultimedia ^
  main.py
echo.
echo ??????: dist\FitIntelDesktop.exe
pause
