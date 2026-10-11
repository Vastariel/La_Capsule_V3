#!/usr/bin/env python3
"""
Lanceur PC : KSP et/ou serveur de l'interface animateur.

    python launch.py            KSP + serveur
    python launch.py --ksp      KSP seul
    python launch.py --server   serveur seul

KSP est lancé détaché (il continue si on ferme cette fenêtre) ; le serveur
tourne dans cette fenêtre (Ctrl+C pour l'arrêter). Chemin de KSP : config.json
ou config.local.json. Sans ksp.exe, l'exécutable par défaut du système est
utilisé (KSP_x64.exe sous Windows, KSP.x86_64 sous Linux).
"""

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


DEFAULT_EXE = "KSP_x64.exe" if sys.platform == "win32" else "KSP.x86_64"


def launch_ksp() -> None:
    from server import load_config
    ksp = load_config().get("ksp", {})
    ksp_dir = Path(ksp.get("dir", ""))
    exe = ksp_dir / (ksp.get("exe") or DEFAULT_EXE)
    if not exe.is_file():
        print(f"✗ KSP introuvable : {exe}")
        print("  Corriger ksp.dir / ksp.exe dans admin_server/config.local.json")
        sys.exit(1)
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        subprocess.Popen([str(exe)], cwd=str(ksp_dir), creationflags=flags)
    else:
        subprocess.Popen([str(exe)], cwd=str(ksp_dir), start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[LAUNCH] KSP lancé : {exe}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ksp", action="store_true", help="lancer KSP")
    parser.add_argument("--server", action="store_true", help="lancer le serveur animateur")
    args = parser.parse_args()
    both = not (args.ksp or args.server)

    if args.ksp or both:
        launch_ksp()
    if args.server or both:
        import server
        server.main()


if __name__ == "__main__":
    main()
