import pygame
import os                       #TODO - Is it needed?
from api import API
from config import *

class Display:
    def __init__(self, api: API):
        pygame.init()
        pygame.font.init()

        # Always open fullscreen window (0,0 lets SDL pick the current display resolution)
        self.screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
        self.width, self.height = self.screen.get_size()
        print(self.width, self.height)

        # Load and scale background to actual screen size
        bg_path = os.path.join(os.getcwd(), BACKGROUND_PATH)
        try:
            self.background = pygame.image.load(bg_path).convert_alpha()
            #self.background = pygame.transform.smoothscale(self.background, (self.width, self.height))
        except Exception:
            # Fallback: plain fill if asset missing
            self.background = pygame.Surface((self.width, self.height)).convert()
            self.background.fill(COLOR_BG)

        # Fonts: size scaled to screen height
        self.num_font = pygame.font.Font(NUM_FONT_PATH, max(12, int(self.height * 0.05)))
        self.txt_font = pygame.font.Font(TXT_FONT_PATH, max(10, int(self.height * 0.025)))

        self.api = api
        self.clock = pygame.time.Clock()
        self.running = False

        # Layout paddings (responsive)
        self.pad_x = int(self.width * 0.03)
        self.pad_y = int(self.height * 0.02)
        self.line_h = int(self.height * 0.07)

    def format_value(self, value, decimals: int = 1) -> str:
        if value is None:
            return "N/A"
        try:
            return f"{value:.{decimals}f}"
        except Exception:
            return str(value)

    def draw_telemetry(self):
        # Draw background
        self.screen.blit(self.background, (0, 0))

        # Semi-transparent panel for readability
        panel_w = int(self.width * 0.45)
        panel_h = int(self.line_h * 7.5)
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 120))  # black, alpha 120
        self.screen.blit(panel, (self.pad_x, self.pad_y))

        x = self.pad_x + 20
        y = self.pad_y + 10

        # Header: FPS
        fps_text = f"Screen FPS: {round(self.clock.get_fps(),1)} | API FPS: {self.api.get_current_fps() if hasattr(self.api,'get_current_fps') else 'N/A'}"
        hdr = self.txt_font.render(fps_text, True, COLOR_HL)
        self.screen.blit(hdr, (x, y))
        y += int(self.line_h * 0.6)

        # Telemetry lines (larger font for main values)
        lines = [
            ("Altitude", f"{self.format_value(self.api.altitude,1)} m"),
            ("Speed", f"{self.format_value(self.api.speed,1)} m/s"),
            ("G-Force", f"{self.format_value(self.api.g_force,2)} G"),
            ("Temp", f"{self.format_value(self.api.temperature,1)} K"),
            ("Apoapsis", f"{self.format_value(self.api.apoapsis,1)} m"),
            ("Periapsis", f"{self.format_value(self.api.periapsis,1)} m"),
        ]

        for label, value in lines:
            label_surf = self.txt_font.render(f"{label} :", True, COLOR_HL)
            value_surf = self.num_font.render(value, True, COLOR_HL)
            self.screen.blit(label_surf, (x, y))
            self.screen.blit(value_surf, (x + int(panel_w*0.38), y - 4))
            y += self.line_h * 0.9

    def run(self):
        """
        Main display loop.
        """
        self.running = True
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    # ESC to quit fullscreen display
                    if event.key == pygame.K_ESCAPE:
                        self.running = False

            self.draw_telemetry()
            pygame.display.flip()
            self.clock.tick(FPS)

        self.stop()

    def stop(self):
        self.running = False
        pygame.quit()

if __name__ == "__main__":
    api = API()
    api.connect()
    api.start()

    display = Display(api)
    display.run()

    api.stop_telemetry()
    api.join()