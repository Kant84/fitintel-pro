# test_e12_15.py
import websocket
import json

def on_message(ws, message):
    print(f"Received: {message[:200]}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Closed")

def on_open(ws):
    print("Connected")
    ws.close()

ws = websocket.WebSocketApp("ws://localhost:8001/ws/alerts",
                            on_open=on_open,
                            on_message=on_message,
                            on_error=on_error,
                            on_close=on_close)

ws.run_forever()
