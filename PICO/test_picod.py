"""programme utilisable pour une raspi branchée directement sur le PC. A adapter :


# TODO sur la rapsi
sudo apt install socat
# Redirige le port série du Pico vers le port réseau 12345
socat TCP-LISTEN:12345,reuseaddr,fork FILE:/dev/ttyACM0,raw,echo=0


#TODO dans le programme : 
import picod
# Au lieu de pico(), on spécifie l'URL réseau vers le Pi 4
pico = picod.pico(device="socket://<IP_DU_RASPI4>:12345")

valeur = pico.read_adc(26)
print(f"Valeur du potentiomètre lue depuis le PC : {valeur}")

"""
import picod
import time

pico = picod.pico()
if not pico.connected:
    exit()

pico.reset()
LED_PIN = 0
POT_CHANNEL = 0 

# Variables pour le filtrage
historique = []
taille_moyenne = 10 # Plus ce nombre est grand, plus c'est stable (mais lent)
derniere_valeur_envoyee = -1
seuil_tolerance = 0.5 # On ne change pas la LED si l'écart est < 0.5%

print("Contrôle stabilisé actif...")

try:
    while True:
        status, ch, val = pico.adc_read(POT_CHANNEL)
        
        if status == picod.STATUS_OKAY:
            # A. Calcul de la moyenne glissante
            historique.append(val)
            if len(historique) > taille_moyenne:
                historique.pop(0)
            
            val_moyenne = sum(historique) / len(historique)
            
            # B. Conversion en pourcentage
            pourcentage = (val_moyenne / 4095.0) * 100.0
            pourcentage = min(100.0, max(0.0, pourcentage))
            
            # C. Application du seuil de tolérance
            # On ne met à jour que si le changement est significatif
            if abs(pourcentage - derniere_valeur_envoyee) > seuil_tolerance:
                pico.tx_pwm(LED_PIN, 1000.0, pourcentage)
                derniere_valeur_envoyee = pourcentage
                print(f"Luminosité stable : {pourcentage:.1f}%    ", end="\r")
        
        time.sleep(0.02) # On peut lire un peu plus vite avec le filtre

except KeyboardInterrupt:
    pico.tx_pwm(LED_PIN, 1000.0, 0)
    pico.close()