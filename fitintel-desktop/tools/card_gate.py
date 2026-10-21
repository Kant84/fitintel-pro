# -*- coding: utf-8 -*-
"""Считыватель-клиент шлюза доступа: скан карты -> POST /access/verify -> вердикт.

Работает с USB-считывателем в режиме HID-клавиатуры (вбивает UID + Enter).
Токен шлюза берётся из client_settings.json (ключ gate_token) или вводится при старте.
"""
import json, os, sys, requests

SETTINGS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'client_settings.json')

def main():
    cfg = json.load(open(SETTINGS, encoding='utf-8'))
    base = cfg['api_base']
    tok = cfg.get('gate_token') or input('Вставьте токен шлюза (sat_...): ').strip()
    gh = {'Authorization': 'Bearer ' + tok}
    try:
        r = requests.post(base + '/analytics/w12/access/verify', headers=gh,
                          json={'type': 'rfid', 'value': 'ping'}, timeout=10)
        print('шлюз отвечает:', r.status_code)
    except Exception as e:
        print('Нет связи с шлюзом:', e); return

    print('\nГОТОВ. Сканируйте карту (UID + Enter). Пустой ввод + Enter — выход.\n')
    while True:
        try:
            uid = input('> ').strip().upper()
        except (EOFError, KeyboardInterrupt):
            break
        if not uid:
            break
        try:
            r = requests.post(base + '/analytics/w12/access/verify', headers=gh,
                              json={'type': 'rfid', 'value': uid}, timeout=10)
            d = r.json()
            if d.get('allow'):
                print('ДОПУСТИТЬ ✅  клиент:', d.get('client_id'))
            else:
                print('ОТКАЗ ⛔ ', d.get('error'))
        except Exception as e:
            print('ошибка:', e)

if __name__ == '__main__':
    main()