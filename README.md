# La Capsule V3

Contrôleur hardware pour **Kerbal Space Program** : boutons/leviers/LEDs
sur Raspberry Pi, potentiomètre throttle sur Pico RP2040, UI télémétrie
Godot. Le jeu + mod kRPC tournent sur un PC distant ; le bridge Python
et Godot tournent sur la Raspi.

## Architecture

```
┌────────────────┐   kRPC (TCP)    ┌─────────────────────────────┐
│ PC  — KSP+kRPC │◄───────────────►│ Raspberry Pi                │
│  192.168.1.31  │  :50008 / :50001│                             │
└────────────────┘                 │  ┌──────────────────────┐   │
                                   │  │ bridge_python (main) │   │
                                   │  │  - krpc_handler      │   │
                                   │  │  - gpio_handler      │   │
                                   │  │  - pico_handler      │   │
                                   │  │  - websocket_server  │◄──┼──┐
                                   │  └──────────────────────┘   │  │
                                   │            │ gpiozero/pigpio│  │ ws://127.0.0.1:8080
                                   │  ┌─────────┴──────────┐     │  │
                                   │  │ GPIO + LEDs        │     │  │
                                   │  │ Pico /dev/ttyACM0  │     │  │
                                   │  └────────────────────┘     │  │
                                   │                             │  │
                                   │  ┌──────────────────────┐   │  │
                                   │  │ godot_ui (UI)        │───┘  │
                                   │  │  Scripts/main.gd     │◄─────┘
                                   │  └──────────────────────┘   │
                                   └─────────────────────────────┘
```

## Installation

**Raspberry Pi :**
```bash
sudo apt install pigpio python3-pip
sudo systemctl enable --now pigpiod
cd bridge_python
pip install -r requirements.txt
```

**PC KSP :** installer le mod [kRPC](https://krpc.github.io/krpc/) et
ouvrir le serveur (par défaut RPC 50008, Stream 50001).

**Godot :** ouvrir `godot_ui/project.godot` avec Godot 4.x.

## Lancement

```bash
# Sur la Raspi
cd bridge_python
python3 main.py

# Puis Godot (même machine)
godot godot_ui/project.godot
```

Godot se connecte automatiquement à `ws://127.0.0.1:8080`. Si le bridge
n'est pas prêt dans les 5 s, une fenêtre de saisie d'IP apparaît
(fallback).

## Configuration

Un seul fichier : `config.json` à la racine. Sections :

- `krpc` — IP/ports du PC KSP, délai de reconnexion.
- `websocket` — host/port du serveur de télémétrie, cadence `update_hz`.
- `hardware.pico` — port série + canal ADC du throttle.
- `hardware.gpio` — IP de la Raspi pour pigpio, LEDs, leviers, boutons.
- `throttle` — lissage EMA `smoothing_alpha`, `deadzone_percent`,
  `output_deadband_percent`.

### Mapping hardware (défaut)

| Type   | GPIO | Rôle |
|--------|------|------|
| Levier | 16   | SAS |
| Levier | 26   | RCS |
| Levier | 22   | THROTTLE_CONTROL (active le potar) |
| Bouton | 20   | AG 0 — Allumage moteur |
| Bouton | 23   | AG 1 — Largage boosters |
| Bouton | 8    | AG 2 — Stage 1 |
| Bouton | 4    | AG 3 — Stage 2 |
| Bouton | 19   | AG 4 — Stage 3 |
| Bouton | 13   | AG 5 — Parachute |
| Bouton | 6    | AG 6 — Bouclier thermique |
| Bouton | 7    | AG 9 — Coiffe |
| Bouton | 11   | Train d'atterrissage + freins (toggle) |
| Bouton | 5    | Toggle caméra carte / auto |
| LED R  | 24   | Stage courant ∈ {4,5,6} (boosters) |
| LED R  | 27   | Stage courant = 3 |
| LED R  | 25   | Stage courant = 2 |
| LED R  | 21   | Stage courant = 1 |
| LED V  | 18   | SAS actif |
| LED V  | 12   | RCS actif |

Les types d'action supportés pour un bouton :
- `{"type": "ag", "value": N}` → `toggle_action_group(N)` via kRPC
- `{"type": "gear_brakes"}` → toggle simultané train + freins
- `{"type": "map_toggle"}` → bascule caméra carte / auto

## Télémétrie WebSocket

Payload JSON envoyé à `update_hz` Hz :

```json
{
  "connected": true,
  "speed": 123.4, "altitude": 1200, "vertical_speed": 5.2,
  "apoapsis": 680000, "periapsis": 670000,
  "apoapsis_time": 120, "periapsis_time": 240,
  "g_force": 1.05, "temperature": 288.15,
  "current_stage": 3, "engines_active": true, "ascending": true,
  "stages": [
    {"stage": 3, "fuel_percent": 87.2, "attached": true},
    {"stage": 2, "fuel_percent": 100.0, "attached": true},
    {"stage": 1, "fuel_percent": 100.0, "attached": true},
    {"stage": 0, "fuel_percent": 0.0, "attached": true}
  ]
}
```

Apoapsis/periapsis sont en **altitude orbitale** (depuis le centre de
Kerbin) ; Godot soustrait `kerbin_radius_m = 600 000` pour l'affichage
par rapport au sol.

Les étages détachés (`attached: false`) sont grisés dans l'UI.

## Tests

```bash
cd bridge_python
# Tests unitaires (config, import API) — rapides, pas de hardware
python3 -m unittest tests.test_configuration -v

# Tests matériels (GPIO, Pico) — version rapide
python3 tests/test_gpio_interactive.py --quick
python3 tests/test_pico_interactive.py --quick
```

## Troubleshooting

| Symptôme | Cause probable |
|----------|----------------|
| `✗ config.json introuvable` | Lancer depuis `bridge_python/` ou vérifier chemin |
| `Erreur pigpio` | `sudo systemctl start pigpiod` |
| Bouton ne réagit pas | Vérifier `config.json` → `hardware.gpio.boutons` |
| Throttle oscille | Augmenter `deadzone_percent` ou `output_deadband_percent` |
| Godot reste sur fenêtre IP | Le bridge n'a pas démarré ou n'écoute pas sur localhost |
| LEDs rouges éteintes | Vérifier `vessel.control.current_stage` dans KSP |

## Structure du projet

```
La_Capsule_V3/
├── config.json                   # source unique de config
├── bridge_python/
│   ├── main.py                   # entry point
│   ├── krpc_handler.py           # connexion KSP + télémétrie
│   ├── gpio_handler.py           # boutons / LEDs
│   ├── pico_handler.py           # ADC throttle (EMA + deadzone)
│   ├── websocket_server.py       # broadcast vers Godot
│   ├── utils/config_loader.py    # chargement config.json
│   └── tests/
│       ├── test_configuration.py
│       ├── test_gpio_interactive.py
│       └── test_pico_interactive.py
└── godot_ui/
    ├── project.godot
    ├── Scenes/{main,Telemetry,menu_selector,option_box}.tscn
    └── Scripts/{main,connection_window,option_box,surrounding,v_box_container}.gd
```
