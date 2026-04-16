#!/usr/bin/env python3
"""
⚠️ OBSOLETE FILE - Use bridge_python instead

This file was part of the old architecture and has been replaced by
the refactored bridge_python module system.

For testing components, use:
  • Scripts in bridge_python/tests/
  • python3 pico.py        (Test Pico ADC)
  • python3 gpio.py        (Test GPIO)
  • python3 main.py        (Run full system)

Migration: See README.md for the new architecture.
"""

print("⚠️ This file is obsolete. Use bridge_python/ instead.")
print("See README.md for the new architecture and testing instructions.")
    stream_v_speed = conn.add_stream(getattr, vessel.flight(), 'vertical_speed')
    stream_peri = conn.add_stream(getattr, vessel.orbit, 'periapsis_altitude')
    stream_apo = conn.add_stream(getattr, vessel.orbit, 'apoapsis_altitude')
    stream_stage = conn.add_stream(getattr, vessel.control, 'current_stage')

    while True:
        s_idx = stream_stage()
        
        # 1. Détection de réinitialisation (Q2)
        # Si on repasse à un index élevé, on arrête tout clignotement
        if s_idx >= 0:
            # Mode normal : Gestion de la LED unique
            for s_num, led in LEDS_STAGING.items():
                if s_num == s_idx: led.on()
                else: led.off()
            
            # Mise à jour télémétrie
            is_orbital = stream_peri() > 70000
            telemetry_data["telemetry"]["speed_mode"] = "orbital" if is_orbital else "surface"
            ref_frame = vessel.orbit.body_reference_frame if is_orbital else vessel.surface_reference_frame
            
            telemetry_data["telemetry"].update({
                "speed": round(vessel.flight(ref_frame).speed, 1),
                "alt": round(stream_alt(), 0),
                "apo": round(stream_apo(), 0),
                "peri": round(stream_peri(), 0)
            })

            # 2. Vitesse verticale (Zone morte 0.5 m/s)
            vs = stream_v_speed()
            if vs > 0.5: telemetry_data["telemetry"]["v_state"] = "ascending"
            elif vs < -0.5: telemetry_data["telemetry"]["v_state"] = "descending"
            else: telemetry_data["telemetry"]["v_state"] = "stable"

            # 3. Carburant
            for s_str in telemetry_data["fuel"].keys():
                s_num = int(s_str)
                if s_num > s_idx: telemetry_data["fuel"][s_str] = -1.0 # Déjà largué
                elif s_num == s_idx: telemetry_data["fuel"][s_str] = get_fuel_percentage(vessel, s_num)
                else: telemetry_data["fuel"][s_str] = 100.0 # Futur

        else:
            # Mode Fin de Mission : Clignotement (Q2)
            for led in LEDS_STAGING.values(): led.toggle()

        await asyncio.sleep(0.1)

# --- BOUTONS & RÉSEAU ---

async def main():
    # Initialisation Pico
    pico = picod.pico()
    if not pico.connected:
        print("Erreur: Pico non trouvé")
        return
    pico.reset()

    # Initialisation KSP
    global conn
    conn = krpc.connect(name='KSP_Pi_Bridge')
    vessel = conn.space_center.active_vessel

    # Initialisation Boutons Staging (avec petite sécurité)
    for pin, target in PINS_STAGING.items():
        btn = Button(pin, bounce_time=0.1)
        btn.when_pressed = lambda t=target: asyncio.run_coroutine_threadsafe(
            trigger_cascade_staging(t, vessel), asyncio.get_event_loop()
        )

    # Lancement des serveurs et boucles
    async with websockets.serve(broadcast_ws, "0.0.0.0", 8080):
        await asyncio.gather(
            update_krpc_loop(vessel),
            update_throttle(vessel, pico)
        )