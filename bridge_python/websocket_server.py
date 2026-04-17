#!/usr/bin/env python3
"""
WebSocket Server - Sends telemetry data to Godot UI
Broadcasts real-time KSP telemetry via WebSocket
"""

import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("✗ Module 'websockets' non installé. Installez: pip install websockets")
    sys.exit(1)


class WebSocketServer:
    """WebSocket server for broadcasting telemetry to Godot clients"""
    
    def __init__(self, krpc=None, host: str = "0.0.0.0", port: int = 8080, path: str = "/telemetry"):
        """Initialize WebSocket server
        
        Args:
            krpc: KRPCHandler instance for telemetry
            host: Server host (0.0.0.0 = all interfaces)
            port: Server port
            path: WebSocket path (clients connect to ws://host:port/path)
        """
        self.krpc = krpc
        self.host = host
        self.port = port
        self.path = path
        self.clients = set()
        self.server = None
    
    async def handler(self, websocket):
        """Handle WebSocket client connections"""
        if not self.krpc:
            await websocket.close()
            return
        
        self.clients.add(websocket)
        try:
            remote_addr = websocket.remote_address if hasattr(websocket, 'remote_address') else "unknown"
        except:
            remote_addr = "unknown"
        print(f"[WS] Client connecté: {remote_addr}")
        
        try:
            # Connection keeps alive, sending telemetry every 100ms
            while True:
                if self.krpc.connected:
                    # Get telemetry and add ascending flag
                    data = self.krpc.get_telemetry()
                    data['ascending'] = data.get('vertical_speed', 0) > 0
                    
                    msg = json.dumps(data)
                    await websocket.send(msg)
                
                await asyncio.sleep(0.1)  # 10 Hz update rate
        
        except websockets.ConnectionClosed:
            print(f"[WS] Client déconnecté: {remote_addr}")
        except Exception as e:
            print(f"[WS] Erreur client {remote_addr}: {e}")
        finally:
            self.clients.discard(websocket)
    
    async def run_server(self):
        """Start the WebSocket server (async)"""
        async with websockets.serve(self.handler, self.host, self.port):
            print(f"[WS] Serveur écoute sur ws://{self.host}:{self.port}{self.path}")
            await asyncio.Future()  # Run forever
    
    def start(self):
        """Start server in blocking mode
        
        Call this from main thread - will block
        """
        try:
            asyncio.run(self.run_server())
        except KeyboardInterrupt:
            print("[WS] Serveur arrêté")
        except Exception as e:
            print(f"[WS] Erreur serveur: {e}")
    
    async def broadcast(self, data: dict):
        """Broadcast data to all connected clients (advanced usage)"""
        if not self.clients:
            return
        
        msg = json.dumps(data)
        disconnected = set()
        
        for websocket in self.clients:
            try:
                await websocket.send(msg)
            except websockets.ConnectionClosed:
                disconnected.add(websocket)
        
        self.clients -= disconnected
