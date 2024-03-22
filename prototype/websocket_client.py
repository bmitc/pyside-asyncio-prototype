import asyncio
from websockets.sync.client import connect


def hello():
    with connect("ws://localhost:8765") as websocket:
        websocket.send("Hello world!")
        message = websocket.recv(timeout=1)
        print(f"Received: {message}")


hello()
