#!/usr/bin/env python3
"""
La Capsule V3 - Serveur de l'interface animateur.

Tourne sur le PC de KSP. Sert la page web (téléphone de l'animateur) et
exécute ses commandes :
- caméra, science, parachutes, redémarrage → connexion kRPC locale ;
- calibration throttle, pannes d'instruments → bridge de la Raspi.

Protocole WebSocket (/ws), JSON :
  client → {"id": n, "cmd": "...", ...}   (le premier doit être "auth" avec le PIN)
  serveur → {"reply_to": n, "ok": bool, ...} et, chaque seconde, {"type": "state", ...}

Usage : python server.py   (config : config.json à côté de ce fichier)
"""

import asyncio
import json
import sys
from pathlib import Path

from aiohttp import WSMsgType, web

from bridge_client import BridgeClient, BridgeError
from ksp_control import KSPControl, KSPError


HERE = Path(__file__).resolve().parent
STATIC_DIR = HERE / "static"
FONTS_DIR = HERE.parent / "godot_ui" / "Fonts"


def _merge(base: dict, over: dict) -> dict:
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def load_config() -> dict:
    """config.json, surchargé par config.local.json s'il existe.

    config.local.json (ignoré par git) contient ce qui est propre à la machine :
    chemin de KSP, adresse kRPC, PIN...
    """
    with open(HERE / "config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    local = HERE / "config.local.json"
    if local.exists():
        with open(local, "r", encoding="utf-8") as f:
            _merge(config, json.load(f))
        print(f"[CONFIG] Surcharges locales : {local.name}")
    return config


class AdminServer:
    def __init__(self, config: dict):
        self.pin = str(config.get("pin", ""))
        self.ksp = KSPControl(config.get("krpc", {}), config.get("ksp", {}), config.get("camera", {}))
        bcfg = config.get("bridge", {})
        self.bridge = BridgeClient(bcfg.get("url", "ws://127.0.0.1:8080"), bcfg.get("token", ""))
        self.clients = set()

    # ---- Commandes ---------------------------------------------------

    async def dispatch(self, cmd: str, msg: dict) -> dict:
        k = self.ksp
        if cmd == "camera_map":
            return {"camera_map": await asyncio.to_thread(k.camera_toggle_map)}
        if cmd == "camera_move":
            await asyncio.to_thread(k.camera_move, msg.get("dx", 0), msg.get("dy", 0))
            return {}
        if cmd == "camera_zoom":
            await asyncio.to_thread(k.camera_zoom, int(msg.get("dir", 1)))
            return {}
        if cmd == "camera_reset":
            await asyncio.to_thread(k.camera_reset)
            return {}
        if cmd == "science_all":
            return await asyncio.to_thread(k.run_all_experiments)
        if cmd == "parachute_cut":
            idx = msg.get("index")
            return {"cut": await asyncio.to_thread(k.cut_parachutes, None if idx is None else int(idx))}
        if cmd == "revert":
            await asyncio.to_thread(k.revert_to_launch)
            return {}
        if cmd == "saves":
            return {"saves": await asyncio.to_thread(k.list_saves)}
        if cmd == "load_save":
            await asyncio.to_thread(k.load_save, str(msg.get("name", "")))
            return {}
        if cmd == "failure_set":
            return await self.bridge.request("failure_set", name=msg.get("name"),
                                             active=bool(msg.get("active")))
        if cmd == "calib_sample":
            return await self.bridge.request("calib_sample")
        if cmd == "calib_save":
            return await self.bridge.request("calib_save", points=msg.get("points"))
        raise KSPError(f"commande inconnue : {cmd}")

    async def state(self) -> dict:
        state = await asyncio.to_thread(self.ksp.status)
        state["type"] = "state"
        state["bridge"] = self.bridge.connected
        state["failures"] = self.bridge.failures
        return state

    # ---- WebSocket ---------------------------------------------------

    async def ws_handler(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=15)
        await ws.prepare(request)
        authed = False
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                continue
            try:
                data = json.loads(msg.data)
                req_id, cmd = data.get("id"), data.get("cmd")
            except (ValueError, AttributeError):
                continue

            if cmd == "auth":
                authed = str(data.get("pin", "")) == self.pin
                await ws.send_json({"reply_to": req_id, "ok": authed,
                                    **({} if authed else {"error": "code PIN incorrect"})})
                if authed:
                    self.clients.add(ws)
                    await ws.send_json(await self.state())
                continue
            if not authed:
                await ws.send_json({"reply_to": req_id, "ok": False, "error": "non authentifié"})
                continue

            try:
                result = await self.dispatch(cmd, data)
                result.pop("reply_to", None)
                reply = {"ok": True, **result}
            except (KSPError, BridgeError) as e:
                reply = {"ok": False, "error": str(e)}
            except Exception as e:
                reply = {"ok": False, "error": f"{type(e).__name__}: {e}"}
            reply["reply_to"] = req_id
            await ws.send_json(reply)
        self.clients.discard(ws)
        return ws

    async def state_loop(self) -> None:
        while True:
            await asyncio.sleep(1.0)
            if not self.clients:
                continue
            state = await self.state()
            for ws in list(self.clients):
                try:
                    await ws.send_json(state)
                except Exception:
                    self.clients.discard(ws)

    # ---- HTTP --------------------------------------------------------

    async def index(self, _request: web.Request) -> web.FileResponse:
        return web.FileResponse(STATIC_DIR / "index.html")

    def app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/", self.index)
        app.router.add_get("/ws", self.ws_handler)
        app.router.add_static("/static/", STATIC_DIR)
        app.router.add_static("/fonts/", FONTS_DIR)

        async def start_background(app_):
            app_["bridge_task"] = asyncio.create_task(self.bridge.run())
            app_["state_task"] = asyncio.create_task(self.state_loop())

        app.on_startup.append(start_background)
        return app


def main() -> None:
    config = load_config()
    if not str(config.get("pin", "")):
        print("✗ Définir un code PIN dans admin_server/config.json")
        sys.exit(1)
    server = AdminServer(config)
    http = config.get("http", {})
    host, port = http.get("host", "0.0.0.0"), int(http.get("port", 8090))
    print("=" * 60)
    print(f"Interface animateur : http://<ip-de-ce-pc>:{port}")
    print("=" * 60)
    web.run_app(server.app(), host=host, port=port, print=None)


if __name__ == "__main__":
    main()
