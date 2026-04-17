#!/usr/bin/env python3
"""
La Capsule V3 - Main entry point
Orchestrates KRPC, GPIO, Pico, and WebSocket communication
"""

import sys
import time
import threading
import json
from pathlib import Path
import io

# Redirige les exceptions de threads Pico vers /dev/null
_original_excepthook = threading.excepthook
def _thread_exception_handler(args):
    """Suppress Pico serial exceptions in threads"""
    if "serial" in str(args.exc_type) or "SerialException" in str(args.exc_type):
        # Silently ignore Pico serial errors
        pass
    else:
        _original_excepthook(args)

threading.excepthook = _thread_exception_handler

# Import handlers
try:
    from krpc_handler import KRPCHandler
    from pico_handler import PicoHandler
    from gpio_handler import GPIOHandler
    from websocket_server import WebSocketServer
except ImportError as e:
    print(f"✗ Erreur import: {e}")
    print("  Assurez-vous que tous les fichiers handler sont présents")
    sys.exit(1)


def load_config():
    """Load configuration from config.json - searches multiple locations"""
    config_paths = [
        Path("/home/capsule/Desktop/La_Capsule_V3/config.json"),  # Absolute path (production)
        Path("config.json"),                                       # Current directory
        Path("../config.json"),                                    # Parent directory (from bridge_python/)
        Path("../../config.json"),                                 # Root (from bridge_python/utils/)
        Path("setup/config.json"),                                 # Legacy location
    ]
    
    for config_path in config_paths:
        resolved = config_path.resolve()
        if resolved.exists():
            try:
                with open(resolved, 'r') as f:
                    config = json.load(f)
                print(f"[CONFIG] Chargé depuis: {resolved}")
                return config
            except Exception as e:
                print(f"✗ Erreur lecture config {resolved}: {e}")
    
    print("[CONFIG] ⚠ Aucun fichier config.json trouvé")
    print("[CONFIG] Chemins cherchés:")
    for path in config_paths:
        print(f"  - {path.resolve()}")
    print("[CONFIG] Utilisation valeurs par défaut")
    return None


def main():
    """Main entry point - Initialize and run all components"""
    print("=" * 60)
    print("La Capsule V3 - KSP Hardware Control System")
    print("=" * 60)
    
    config = load_config()
    print()
    
    # ========== KRPC Handler ==========
    print("[INIT] Initialisation KRPC...")
    krpc_host = "192.168.1.31"
    krpc_rpc_port = 50008
    krpc_stream_port = 50001
    
    if config and "krpc" in config:
        krpc_host = config["krpc"].get("host", krpc_host)
        krpc_rpc_port = config["krpc"].get("rpc_port", krpc_rpc_port)
        krpc_stream_port = config["krpc"].get("stream_port", krpc_stream_port)
    
    krpc = KRPCHandler(host=krpc_host, rpc_port=krpc_rpc_port, stream_port=krpc_stream_port)
    
    # Try to connect (will retry internally if fails)
    if krpc.connect():
        print("[✓] KRPC connecté")
    else:
        print("[!] KRPC non disponible (reconnexion en arrière-plan)")
    print()
    
    # ========== Pico Handler ==========
    print("[INIT] Initialisation Pico (ADC)...")
    pico_port = "/dev/ttyACM0"
    
    if config and "hardware" in config and "pico" in config["hardware"]:
        pico_port = config["hardware"]["pico"].get("port", pico_port)
    
    pico = PicoHandler(port=pico_port)
    
    if pico.connected:
        print("[✓] Pico connecté")
    else:
        print("[!] Pico non disponible (throttle désactivé)")
    print()
    
    # ========== GPIO Handler ==========
    print("[INIT] Initialisation GPIO...")
    gpio_config = None
    if config and "hardware" in config and "gpio_raspi" in config["hardware"]:
        gpio_config = config["hardware"]["gpio_raspi"]
    
    gpio = GPIOHandler(krpc=krpc, pico=pico, config=gpio_config)
    print("[✓] GPIO initialisé")
    print()
    
    # ========== WebSocket Server ==========
    print("[INIT] Initialisation WebSocket Server...")
    ws = WebSocketServer(krpc=krpc, host="0.0.0.0", port=8080)
    
    # Start WebSocket server in background thread
    ws_thread = threading.Thread(target=ws.start, daemon=True)
    ws_thread.start()
    print("[✓] WebSocket serveur démarré (ws://0.0.0.0:8080)")
    print()
    
    # ========== Main Control Loop ==========
    print("=" * 60)
    print("Boucle principale en cours...")
    print("Appuyez sur Ctrl-C pour arrêter")
    print("=" * 60)
    print()
    
    loop_counter = 0
    try:
        while True:
            try:
                # Update KRPC (with automatic reconnection if needed)
                if krpc.connected:
                    krpc.reconnect_if_needed()
                    krpc.update_telemetry()
                else:
                    krpc.reconnect_if_needed()  # Try to reconnect
            except Exception as e:
                # KRPC errors don't stop the loop
                pass
            
            # Update GPIO (reads buttons, leviers, updates LEDs)
            try:
                gpio.update()
            except Exception as e:
                # GPIO errors don't stop the loop
                pass
            
            loop_counter += 1
            
            # Log status periodically (every 30 loops = ~3 seconds at 10 Hz)
            if loop_counter % 30 == 0:
                status = "✓" if krpc.connected else "✗"
                print(f"[LOOP] {loop_counter:6d} - KRPC: {status}, Clients WS: {len(ws.clients)}")
            
            # Sleep for consistent loop rate (10 Hz = 100ms)
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n[MAIN] Arrêt demandé (Ctrl-C)")
    except Exception as e:
        print(f"\n✗ Erreur boucle principale: {e}")
    finally:
        print("[MAIN] Nettoyage...")
        
        # Cleanup GPIO
        try:
            gpio.cleanup()
            print("[✓] GPIO nettoyé")
        except Exception as e:
            print(f"[!] Erreur cleanup GPIO: {e}")
        
        # Close Pico
        try:
            if pico.ser:
                pico.ser.close()
            print("[✓] Pico fermé")
        except Exception as e:
            print(f"[!] Erreur fermeture Pico: {e}")
        
        # Close KRPC
        try:
            if krpc.conn:
                krpc.conn.close()
            print("[✓] KRPC fermé")
        except Exception as e:
            print(f"[!] Erreur fermeture KRPC: {e}")
        
        print("\n[MAIN] Arrêt complet")
        sys.exit(0)


if __name__ == "__main__":
    main()