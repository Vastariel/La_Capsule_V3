import pygame
import krpc

#from gpio_control import setup_gpio, handle_gpio_inputs
from display import AscentDisplay, OrbitDisplay, LandingDisplay
from config import KSP_IP, RPC_PORT, STREAM_PORT

def main():
    conn = krpc.connect(name='KSP Dashboard', address=KSP_IP, rpc_port=RPC_PORT, stream_port=STREAM_PORT)
    vessel = conn.space_center.active_vessel

    pygame.init()
    screen = pygame.display.set_mode((800, 1280))
    pygame.display.set_caption("KSP Dashboard")
    clock = pygame.time.Clock()

    # Initialize GPIO
    #setup_gpio()

    # Initialize display types
    ascent_display = AscentDisplay(screen, vessel)
    #orbit_display = OrbitDisplay(screen, vessel)
    #landing_display = LandingDisplay(screen, vessel)

    current_display = ascent_display  # Start with ascent display

    running = True
    while running:
        #handle_gpio_inputs(vessel)  # Handle GPIO inputs for controls

        # Update display based on current phase
        current_display.update(vessel)

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        pygame.display.flip()
        clock.tick(20)  # Limit to 20 FPS

    pygame.quit()

if __name__ == "__main__":
    main()