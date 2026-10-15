#scripts\music\fitintel_player_agent.py
# -*- coding: utf-8 -*-
"""Обёртка совместимости: прежнее имя скрипта, теперь запускает пакетный agent.py.
Все аргументы (--server, --token, --dry-run, --lib, --mic ...) — без изменений."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import main  # noqa: E402

if __name__ == "__main__":
    main()