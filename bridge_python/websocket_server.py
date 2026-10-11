#!/usr/bin/env python3
"""
WebSocket Server - Diffuse la télémétrie kRPC aux clients Godot.

Architecture : une seule tâche broadcast lit la télémétrie à la cadence
configurée et l'envoie à tous les clients simultanément (au lieu d'une
boucle par client).

Messages entrants : seules les commandes de l'interface animateur sont
traitées ({"id", "cmd", "token", ...} → réponse {"reply_to": id, ...} au seul
émetteur, voir admin_commands.py). Le reste est ignoré.
"""

import asyncio
import json
import sys
from typing import Optional

try:
    import websockets
except ImportError:
    print("✗ Module 'websockets' requis: pip install websockets")
    sys.exit(1)


class WebSocketServer:
    """Serveur WebSocket broadcast-only pour la télémétrie."""

    def __init__(self, krpc=None, host: str = "0.0.0.0", port: int = 8080, update_hz: int = 10,
                 admin=None):
        self.krpc = krpc
        self.admin = admin
        self.host = host
        self.port = port
        self.interval = 1.0 / max(1, update_hz)
        self.clients = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._new_data_event: Optional[asyncio.Event] = None

    # ---- Gestion clients --------------------------------------------

    async def _handler(self, websocket):
        self.clients.add(websocket)
        addr = getattr(websocket, "remote_address", "?")
        print(f"[WS] Client connecté: {addr}")
        try:
            async for raw in websocket:
                await self._on_message(websocket, raw)
        except websockets.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            print(f"[WS] Client déconnecté: {addr}")

    async def _on_message(self, websocket, raw) -> None:
        if self.admin is None:
            return
        try:
            msg = json.loads(raw)
        except (TypeError, ValueError):
            return
        if not isinstance(msg, dict) or "cmd" not in msg:
            return
        reply = self.admin.handle(msg)
        reply["reply_to"] = msg.get("id")
        try:
            await websocket.send(json.dumps(reply))
        except Exception:
            pass
        # Une panne change l'écran Godot : on rediffuse sans attendre la télémétrie.
        if msg.get("cmd") == "failure_set" and self._new_data_event:
            self._new_data_event.set()

    # ---- Broadcast ---------------------------------------------------

    def _build_payload(self) -> dict:
        if not self.krpc or not self.krpc.connected:
            data = {"connected": False}
        else:
            data = self.krpc.get_telemetry()
            data["connected"] = True
            data["ascending"] = data.get("vertical_speed", 0) > 0
        if self.admin is not None:
            data["failures"] = self.admin.get_failures()
        return data

    def notify_new_data(self) -> None:
        """Signale depuis le thread télémétrie qu'une nouvelle donnée est disponible."""
        if self._loop and self._new_data_event:
            self._loop.call_soon_threadsafe(self._new_data_event.set)

    async def _broadcast_loop(self):
        while True:
            await self._new_data_event.wait()
            self._new_data_event.clear()
            if self.clients:
                msg = json.dumps(self._build_payload())
                dead = set()
                for ws in self.clients:
                    try:
                        await ws.send(msg)
                    except Exception:
                        dead.add(ws)
                self.clients -= dead

    # ---- Lancement ---------------------------------------------------

    async def _run(self):
        self._loop = asyncio.get_running_loop()
        self._new_data_event = asyncio.Event()
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
