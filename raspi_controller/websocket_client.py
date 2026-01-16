#!/usr/bin/env python3
"""
WebSocket Client - Sends data from Raspi to bridge_krpc
"""

import asyncio
import json
import websockets


class WebSocketClient:
    """WebSocket client to send data to bridge server"""
    
    def __init__(self, host="192.168.1.25", port=8081):
        """Initialize WebSocket client"""
        self.host = host
        self.port = port
        self.uri = f"ws://{host}:{port}/raspi"
        self.connected = False
    
    async def send_data(self, data):
        """Send data to bridge via WebSocket"""
        try:
            async with websockets.connect(self.uri, ping_interval=None) as websocket:
                msg = json.dumps(data)
                await websocket.send(msg)
                self.connected = True
        except Exception as e:
            if self.connected:
                print(f"✗ Perte connexion WebSocket: {e}")
                self.connected = False
    
    async def connect_and_stream(self, data_generator, interval=0.05):
        """Connect and continuously stream data"""
        try:
            async with websockets.connect(self.uri, ping_interval=None) as websocket:
                self.connected = True
                print(f"✓ Connecté à {self.uri}")
                
                while True:
                    data = data_generator()
                    msg = json.dumps(data)
                    await websocket.send(msg)
                    await asyncio.sleep(interval)
        except Exception as e:
            print(f"✗ Erreur WebSocket: {e}")
            self.connected = False
            await asyncio.sleep(2)  # Retry after 2 seconds


if __name__ == "__main__":
    import time
    
    client = WebSocketClient()
    
    async def test():
        for i in range(5):
            data = {
                "test": i,
                "timestamp": time.time()
            }
            await client.send_data(data)
            await asyncio.sleep(1)
    
    asyncio.run(test())
