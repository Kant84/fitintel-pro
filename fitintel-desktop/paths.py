# -*- coding: utf-8 -*-
"""Единая точка путей приложения.
В exe (PyInstaller) настройки живут РЯДОМ с exe (папка установки),
при обычном запуске — рядом с main.py. Никаких временных папок."""
import sys
from pathlib import Path

APP_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
SETTINGS = APP_DIR / "client_settings.json"
CONNECTIONS = APP_DIR / "connections.json"
ASSETS = APP_DIR / "assets"