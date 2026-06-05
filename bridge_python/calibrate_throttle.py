#!/usr/bin/env python3
"""
Étalonnage du potentiomètre de throttle.

Le potentiomètre n'a pas forcément une réponse linéaire (piste log, butées
mécaniques décalées...). Ce script capture la valeur brute ADC à des positions
physiques connues du levier (0 / 25 / 50 / 75 / 100 %), puis écrit la table
d'étalonnage dans config.json sous `throttle.calibration`.

Au runtime, pico_handler applique une interpolation linéaire par morceaux sur
cette table pour corriger la course.

Usage :
    python3 calibrate_throttle.py
"""

import json
import select
import sys
import time
from pathlib import Path

from pico_handler import PicoHandler


CONFIG_SEARCH_PATHS = [
    Path("/home/capsule/Desktop/La_Capsule_V3/config.json"),
    Path(__file__).resolve().parent.parent / "config.json",
]

# Positions physiques à capturer (fraction de la course).
TARGETS = [0.0, 0.25, 0.50, 0.75, 1.0]

# Nombre de lectures moyennées au moment de la capture (stabilité).
CAPTURE_SAMPLES = 30


def find_config() -> Path:
    for path in CONFIG_SEARCH_PATHS:
        if path.exists():
            return path
    print("✗ config.json introuvable. Chemins testés:")
    for p in CONFIG_SEARCH_PATHS:
        print(f"  - {p}")
    sys.exit(1)


def read_raw(pico: PicoHandler) -> int:
    """Lecture brute robuste : réessaie jusqu'à obtenir une valeur."""
    for _ in range(10):
        val = pico.read_raw()
        if val is not None:
            return val
        time.sleep(0.02)
    return -1


def capture_live(pico: PicoHandler, label: str) -> int:
    """Affiche la valeur brute en direct jusqu'à ce que l'utilisateur appuie
    sur ENTRÉE, puis retourne la moyenne de CAPTURE_SAMPLES lectures.
    """
    print(f"\n→ Place le levier à la position {label}.")
    print("  Valeur brute affichée en direct. Appuie sur ENTRÉE pour capturer.")
    while True:
        raw = read_raw(pico)
        sys.stdout.write(f"\r    Brut ADC: {raw:>5}    ")
        sys.stdout.flush()
        # ENTRÉE détectée sans bloquer la boucle d'affichage.
        dr, _, _ = select.select([sys.stdin], [], [], 0.05)
        if dr:
            sys.stdin.readline()
            break

    # Moyenne sur plusieurs lectures pour figer un point stable.
    samples = []
    for _ in range(CAPTURE_SAMPLES):
        val = read_raw(pico)
        if val >= 0:
            samples.append(val)
        time.sleep(0.01)
    avg = round(sum(samples) / len(samples)) if samples else raw
    print(f"\r    ✓ Capturé: {avg:>5} (moyenne sur {len(samples)} lectures)")
    return avg


def main() -> None:
    print("=" * 60)
    print("Étalonnage du potentiomètre de throttle")
    print("=" * 60)

    config_path = find_config()
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    pcfg = config.get("hardware", {}).get("pico", {})
    pico = PicoHandler(
        port=pcfg.get("port", "/dev/ttyACM0"),
        adc_channel=pcfg.get("adc_channel_throttle", 0),
    )

    print(f"\n[PICO] Connexion sur {pico.port}...")
    if not pico.connect():
        print("✗ Impossible de se connecter au Pico. Vérifie le câble / le port.")
        sys.exit(1)

    # Vérif de lecture.
    if read_raw(pico) < 0:
        print("✗ Aucune lecture ADC. Vérifie le canal et le branchement.")
        pico.disconnect()
        sys.exit(1)

    print("\nOn va capturer 5 points le long de la course du levier.")
    print("À chaque étape, positionne le levier puis appuie sur ENTRÉE.")

    points = []  # [fraction, raw]
    for target in TARGETS:
        label = f"{int(target * 100)} %"
        raw = capture_live(pico, label)
        points.append([target, raw])

    pico.disconnect()

    # Contrôle de cohérence : les valeurs brutes doivent être monotones.
    raws = [p[1] for p in points]
    increasing = all(raws[i] < raws[i + 1] for i in range(len(raws) - 1))
    decreasing = all(raws[i] > raws[i + 1] for i in range(len(raws) - 1))
    if not (increasing or decreasing):
        print("\n⚠ Attention : les valeurs brutes ne sont pas monotones :")
        print("   ", raws)
        print("   L'étalonnage risque d'être incorrect (levier mal positionné ?).")
        resp = input("   Enregistrer quand même ? [o/N] ").strip().lower()
        if resp not in ("o", "oui", "y", "yes"):
            print("Abandon, config.json inchangé.")
            return

    # Récap.
    print("\n" + "-" * 60)
    print("Table d'étalonnage capturée :")
    for frac, raw in points:
        print(f"   {int(frac * 100):>3} %  ->  brut {raw}")
    print("-" * 60)

    config.setdefault("throttle", {})["calibration"] = points
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"\n✓ Étalonnage enregistré dans {config_path}")
    print("  Relance main.py pour utiliser la correction.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrompu, config.json inchangé.")
