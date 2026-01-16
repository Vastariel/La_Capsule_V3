#!/usr/bin/env python3
"""
Serveur WebSocket pour télémétrie KSP
"""

import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("Missing dependency 'websockets'. Installez via: pip install websockets")
    raise

from api import API


HOST = "0.0.0.0"  # listen on all interfaces so other machines can connect
PORT = 8080

# Global API instance
api = None
server_task = None


async def handler(ws, path=None):
    """WebSocket handler - broadcasts telemetry data"""
    print(f"Websocket Client connected: {ws.remote_address}")
    try:
        while True:
            # Récupère les données réelles de l'API
            data = {
                "speed": api.speed if api.speed is not None else 0,
                "altitude": api.altitude if api.altitude is not None else 0,
                "apoapsis": api.apoapsis if api.apoapsis is not None else 0,
                "periapsis": api.periapsis if api.periapsis is not None else 0,
                "g_force": api.g_force if api.g_force is not None else 0,
                "temperature": api.temperature if api.temperature is not None else 0,
            }
            msg = json.dumps(data)
            await ws.send(msg)
            await asyncio.sleep(0.1)
    except websockets.ConnectionClosed:
        print("Client disconnected")


async def run_server():
    """Start the WebSocket server"""
    async with websockets.serve(handler, HOST, PORT):
        print(f"WebSocket server listening on ws://{HOST}:{PORT}")
        await asyncio.Future()  # wait forever until Ctrl-C


def init_server(api_instance):
    """Initialize server with API instance"""
    global api
    api = api_instance
    print("Server initialized with API instance")


async def start_server_async():
    """Start server (async version)"""
    global server_task
    try:
        await run_server()
    except asyncio.CancelledError:
        print("Server cancelled")
    except KeyboardInterrupt:
        print("Server stopped")


def start_server():
    """Start server in background (blocking)"""
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("Server stopped")


if __name__ == "__main__":
    from api import API
    api = API('ecran')
    api.connect()
    api.start()
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("Server stopped")
        api.stop_telemetry()
        api.join()
        sys.exit(0)