# test_e12_15_v3.py
import asyncio
import websockets

async def test_ws():
    uri = "ws://localhost:8001/ws/alerts"
    async with websockets.connect(uri) as websocket:
        print("Connected!")
        await websocket.send("test alert")
        response = await websocket.recv()
        print(f"Received: {response[:200]}")
        print("E12.15 ✅ WebSocket работает!")

asyncio.run(test_ws())
