#!/usr/bin/env python3
"""
Petit serveur WebSocket de test qui envoie des paquets JSON de télémétrie toutes les secondes.
Usage: python tools/ws_test_server.py
"""

import asyncio
import json
import signal
import sys

try:
    import websockets
except ImportError:
    print("Missing dependency 'websockets'. Installez via: pip install websockets")
    raise

from api import API



HOST = "0.0.0.0"  # listen on all interfaces so other machines can connect
PORT = 8080



async def handler(ws, path=None):
    print(f"Client connected: {ws.remote_address}")
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
                # ajouter d'autres champs
            }
            msg = json.dumps(data)
            await ws.send(msg)
            await asyncio.sleep(0.1)
    except websockets.ConnectionClosed:
        print("Client disconnected")

async def main():
    async with websockets.serve(handler, HOST, PORT):
        print(f"WebSocket server listening on ws://{HOST}:{PORT}")
        try:
            await asyncio.Future()  # wait forever until Ctrl-C
        except asyncio.CancelledError:
            pass
        except KeyboardInterrupt:
            print("Keyboard interrupt received, shutting down server")

if __name__ == "__main__":
    api = API('ecran')
    api.connect()
    api.start()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped")
        api.stop_telemetry()
        api.join()
        sys.exit(0)