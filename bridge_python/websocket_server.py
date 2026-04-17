#!/usr/bin/env python3
"""
WebSocket Server - Diffuse la télémétrie kRPC aux clients Godot.

Architecture : une seule tâche broadcast lit la télémétrie à la cadence
configurée et l'envoie à tous les clients simultanément (au lieu d'une
boucle par client).
"""

import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("✗ Module 'websockets' requis: pip install websockets")
    sys.exit(1)


class WebSocketServer:
    """Serveur WebSocket broadcast-only pour la télémétrie."""

    def __init__(self, krpc=None, host: str = "0.0.0.0", port: int = 8080, update_hz: int = 10):
        self.krpc = krpc
        self.host = host
        self.port = port
        self.interval = 1.0 / max(1, update_hz)
        self.clients = set()

    # ---- Gestion clients --------------------------------------------

    async def _handler(self, websocket):
        self.clients.add(websocket)
        addr = getattr(websocket, "remote_address", "?")
        print(f"[WS] Client connecté: {addr}")
        try:
            async for _ in websocket:  # on ignore les messages entrants
                pass
        except websockets.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            print(f"[WS] Client déconnecté: {addr}")

    # ---- Broadcast ---------------------------------------------------

    def _build_payload(self) -> dict:
        if not self.krpc or not self.krpc.connected:
            return {"connected": False}
        data = self.krpc.get_telemetry()
        data["connected"] = True
        data["ascending"] = data.get("vertical_speed", 0) > 0
        return data

    async def _broadcast_loop(self):
        while True:
            if self.clients:
                msg = json.dumps(self._build_payload())
                dead = set()
                for ws in self.clients:
                    try:
                        await ws.send(msg)
                    except Exception:
                        dead.add(ws)
                self.clients -= dead
            await asyncio.sleep(self.interval)

    # ---- Lancement ---------------------------------------------------

    async def _run(self):
        async with websockets.serve(self._handler, self.host, self.port):
            print(f"[WS] Écoute sur ws://{self.host}:{self.port}")
            await self._broadcast_loop()

    def start(self):
        try:
            asyncio.run(self._run())
        except KeyboardInterrupt:
            print("[WS] Arrêt")
        except Exception as e:
            print(f"[WS] Erreur: {e}")
