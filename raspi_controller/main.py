#!/usr/bin/env python3
"""
Raspi Controller - Runs on Raspberry Pi
Collects GPIO states and Pico ADC data, sends via WebSocket to bridge_krpc
"""

import asyncio
import json
import sys
import time
from threading import Thread
from gpio_monitor import GPIOMonitor
from pico_monitor import PicoMonitor
from websocket_client import WebSocketClient


class RaspiController:
    """Main controller for Raspi - coordinates GPIO, Pico, and WebSocket"""
    
    def __init__(self, bridge_host="192.168.1.25", bridge_port=8081):
        """Initialize controller"""
        self.bridge_host = bridge_host
        self.bridge_port = bridge_port
        
        # Initialize components
        self.gpio_monitor = GPIOMonitor()
        self.pico_monitor = PicoMonitor()
        self.ws_client = WebSocketClient(host=bridge_host, port=bridge_port)
        
        self.running = False
    
    def collect_data(self):
        """Collect all data from GPIO and Pico"""
        data = {
            "timestamp": time.time(),
            "gpio": self.gpio_monitor.get_state(),
            "pico": self.pico_monitor.get_state()
        }
        return data
    
    def send_data_loop(self):
        """Loop that collects and sends data"""
        while self.running:
            try:
                data = self.collect_data()
                asyncio.run(self.ws_client.send_data(data))
                time.sleep(0.05)  # 20 Hz update rate
            except Exception as e:
                print(f"✗ Erreur envoi données: {e}")
                time.sleep(1)
    
    def run(self):
        """Start the controller"""
        self.running = True
        print(f"✓ Raspi Controller démarré")
        print(f"  - GPIO Monitor actif")
        print(f"  - Pico Monitor actif")
        print(f"  - Connexion WebSocket vers {self.bridge_host}:{self.bridge_port}")
        
        # Start data sending thread
        send_thread = Thread(target=self.send_data_loop, daemon=True)
        send_thread.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n✓ Arrêt gracieux...")
            self.stop()
    
    def stop(self):
        """Stop the controller"""
        self.running = False
        self.gpio_monitor.cleanup()
        self.pico_monitor.close()
        print("✓ Controller arrêté")


if __name__ == "__main__":
    controller = RaspiController()
    controller.run()
