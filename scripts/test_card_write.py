# -*- coding: utf-8 -*-
"""Тест DirectReader.write_block на реальной карте. Безопасно: бэкап + восстановление."""
import sys, time
sys.path.insert(0, ".")
from rfid.direct_reader import DirectReader

KEY_B = "666666666666"
EMPTY = "025D000000000000000000000000005F"
LOCKER13 = "020B0000000D00000000000000000003"   # номер шкафчика 13

rd = DirectReader()
print("Считыватель:", rd.status())

print("Поднесите карту к считывателю...")
uid = None
for _ in range(20):
    uid = rd.detect_uid()
    if uid:
        break
    time.sleep(0.5)
if not uid:
    print("❌ Карта не обнаружена за 10 секунд")
    sys.exit(1)
print("UID:", uid)

before = rd.read_sector(0, "B", KEY_B)
b1 = before.get("block_1", "")
print("block_1 (было):", b1 or "(не читается)")

if b1:
    ok = rd.write_block(0, 1, "B", KEY_B, b1)
    print("1) Round-trip (запись того же):", "OK" if ok else "FAIL")
    print("   Считано после:", rd.read_sector(0, "B", KEY_B).get("block_1", ""))

ok = rd.write_block(0, 1, "B", KEY_B, EMPTY)
print("2) Очистка (EMPTY_CARD):", "OK" if ok else "FAIL")
print("   Считано:", rd.read_sector(0, "B", KEY_B).get("block_1", ""))

ok = rd.write_block(0, 1, "B", KEY_B, LOCKER13)
print("3) Номер шкафчика 13:", "OK" if ok else "FAIL")
print("   Считано:", rd.read_sector(0, "B", KEY_B).get("block_1", ""))

if b1:
    ok = rd.write_block(0, 1, "B", KEY_B, b1)
    print("4) Восстановление исходного:", "OK" if ok else "FAIL")
    print("   Финал block_1:", rd.read_sector(0, "B", KEY_B).get("block_1", ""))

print("=== Тест завершён ===")