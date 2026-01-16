# Raspi Controller

Sous-projet qui s'exécute sur la **Raspberry Pi** pour collecter les données des GPIO et du Pico, puis les envoie via WebSocket au bridge_krpc sur le PC.

## Architecture

```
Raspi:
├── GPIO Monitor (lit les leviers et boutons locaux)
├── Pico Monitor (lit les ADC du Pico branché)
└── WebSocket Client (envoie les données au PC)
      ↓
PC (Bridge KRPC):
├── Reçoit les données GPIO/Pico
└── Les envoie via Godot UI + KSP
```

## Installation

Sur la Raspi :
```bash
pip3 install -r requirements.txt
```

## Utilisation

```bash
python3 main.py
```

## Structure des données

Les données envoyées via WebSocket ont la structure suivante :

```json
{
  "timestamp": 1234567890.5,
  "gpio": {
    "leviers": {
      "SAS": true,
      "RCS": false,
      "THROTTLE_CONTROL": false
    },
    "boutons": {
      "STAGE_BOOSTERS": false,
      "STAGE_1": false,
      ...
    },
    "leds_rouges": {...},
    "leds_vertes": {...}
  },
  "pico": {
    "connected": true,
    "channels": {
      "adc_0": {"raw": 2048, "percentage": 50.0},
      "adc_1": {"raw": 1024, "percentage": 25.0},
      "adc_2": {"raw": 3072, "percentage": 75.0}
    }
  }
}
```

## Configuration

Modifier les adresses IP et ports dans `main.py` :
- `bridge_host` : Adresse IP du PC (bridge_krpc)
- `bridge_port` : Port du serveur WebSocket du bridge
