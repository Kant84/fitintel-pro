# test_e12_15_v2.py
import websocket
import time

def on_message(ws, message):
    print(f"Received: {message[:200]}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"Closed: {close_status_code} - {close_msg}")

def on_open(ws):
    print("Connected!")
    # Отправляем тестовое сообщение
    ws.send("test alert")
    # Ждём ответ
    time.sleep(2)
    ws.close()

ws = websocket.WebSocketApp("ws://localhost:8001/ws/alerts",
                            on_open=on_open,
                            on_message=on_message,
                            on_error=on_error,
                            on_close=on_close)

ws.run_forever()
