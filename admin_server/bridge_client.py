#!/usr/bin/env python3
"""
Bridge Client - Lien WebSocket vers le bridge de la Raspi.

Sert à ce qui n'existe que côté Raspi : calibration du throttle (Pico) et
pannes d'instruments (écran Godot). Reconnexion automatique ; les requêtes
sont corrélées à leur réponse par un id. Les diffusions de télémétrie du
bridge sont utilisées pour connaître l'état des pannes.
"""

import asyncio
import itertools
import json
from typing import Dict, Optional

import aiohttp


class BridgeError(Exception):
    pass


class BridgeClient:
    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token
        self.connected = False
        self.failures: Dict[str, bool] = {}
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._pending: Dict[int, asyncio.Future] = {}
        self._ids = itertools.count(1)

    async def run(self) -> None:
        """Boucle de connexion, à lancer en tâche de fond."""
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    async with session.ws_connect(self.url, heartbeat=10) as ws:
                        self._ws = ws
                        self.connected = True
                        print(f"[BRIDGE] Connecté à {self.url}")
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                self._on_message(msg.data)
                except Exception as e:
                    if self.connected:
                        print(f"[BRIDGE] Déconnecté : {e}")
                self._ws = None
                self.connected = False
                for fut in self._pending.values():
                    if not fut.done():
                        fut.set_exception(BridgeError("liaison capsule perdue"))
                self._pending.clear()
                await asyncio.sleep(3)

    def _on_message(self, data: str) -> None:
        try:
            msg = json.loads(data)
        except ValueError:
            return
        if "reply_to" in msg:
            fut = self._pending.pop(msg["reply_to"], None)
            if fut and not fut.done():
                fut.set_result(msg)
        elif isinstance(msg.get("failures"), dict):
            self.failures = msg["failures"]

    async def request(self, cmd: str, **params) -> dict:
        if self._ws is None:
            raise BridgeError("capsule (Raspi) injoignable")
        req_id = next(self._ids)
        fut = asyncio.get_running_loop().create_future()
        self._pending[req_id] = fut
        await self._ws.send_str(json.dumps({"id": req_id, "cmd": cmd, "token": self.token, **params}))
        try:
            reply = await asyncio.wait_for(fut, timeout=5)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            raise BridgeError("pas de réponse de la capsule")
        if not reply.get("ok"):
            raise BridgeError(reply.get("error", "erreur inconnue"))
        if isinstance(reply.get("failures"), dict):
            self.failures = reply["failures"]
        return reply
