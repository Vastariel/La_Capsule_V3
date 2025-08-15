import pygame
import os
from api import API
from config import *


class Display:
    def __init__(self, api: API):
        pygame.init()
        pygame.font.init()

        # Fullscreen physical screen
        self.screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
        self.width, self.height = self.screen.get_size()

        # Determine orientation and portrait canvas size
        self.is_landscape = self.width > self.height
        self.pw = min(self.width, self.height)
        self.ph = max(self.width, self.height)

        # Offscreen portrait canvas
        self.canvas = pygame.Surface((self.pw, self.ph), pygame.SRCALPHA)

        # Load and scale background to portrait canvas
        bg_path = os.path.join(os.getcwd(), BACKGROUND_PATH)
        try:
            bg_img = pygame.image.load(bg_path).convert_alpha()
            self.background = pygame.transform.smoothscale(bg_img, (self.pw, self.ph))
        except Exception:
            self.background = pygame.Surface((self.pw, self.ph)).convert()
            self.background.fill(COLOR_BG)

        # Fonts scaled to portrait height
        self.num_font = pygame.font.Font(NUM_FONT_PATH, max(12, int(self.ph * 0.05)))
        self.txt_font = pygame.font.Font(TXT_FONT_PATH, max(10, int(self.ph * 0.025)))

        self.api = api
        self.clock = pygame.time.Clock()
        self.running = False

        # Layout paddings based on portrait canvas
        self.pad_x = int(self.pw * 0.03)
        self.pad_y = int(self.ph * 0.02)
        self.line_h = int(self.ph * 0.07)

    def format_value(self, value, decimals: int = 1) -> str:
        if value is None:
            return "N/A"
        try:
            return f"{value:.{decimals}f}"
        except Exception:
            return str(value)

    def render_fixed_numeric(self, text: str, rel_x: float, rel_y: float, align: str = "center"):
        """
        Render a numeric text so that each digit occupies a fixed horizontal slot.
        Splits text into a numeric part and a unit (split on first space). The numeric
        part is drawn char-by-char with a fixed advance equal to the max digit width.
        The unit (if any) is drawn normally after the numeric block.
        rel_x/rel_y are relative positions on the portrait canvas (0..1).
        """
        # split number and unit
        if text is None:
            text = "N/A"
        if " " in text:
            num_part, unit_part = text.split(" ", 1)
            unit_part = unit_part.strip()
        else:
            num_part = text
            unit_part = ""

        # characters considered for fixed width (digits and signs)
        digit_chars = "0123456789-+,."
        # compute a fixed advance: max width among representative chars
        char_w = max(self.num_font.size(ch)[0] for ch in digit_chars)
        # small extra spacing to avoid collisions
        advance = int(char_w * 1.02)

        # surfaces for digits
        digit_surfs = [self.num_font.render(ch, True, COLOR_HL) for ch in num_part]
        unit_surf = self.num_font.render(unit_part, True, COLOR_HL) if unit_part else None

        total_w = advance * len(num_part) + (unit_surf.get_width() if unit_surf else 0)
        total_h = max([s.get_height() for s in digit_surfs] + ([unit_surf.get_height()] if unit_surf else [0]))

        abs_x = int(self.pw * rel_x)
        abs_y = int(self.ph * rel_y)
        # align horizontally
        if align == "center":
            start_x = abs_x - total_w // 2
        elif align == "right":
            start_x = abs_x - total_w
        else:  # left
            start_x = abs_x

        # vertical center
        start_y = abs_y - total_h // 2

        # blit digits with fixed advance
        x = start_x
        for surf in digit_surfs:
            self.canvas.blit(surf, (x, start_y + (total_h - surf.get_height()) // 2))
            x += advance

        # blit unit after digits (with small gap)
        if unit_surf:
            gap = int(self.ph * 0.005)
            self.canvas.blit(unit_surf, (x + gap, start_y + (total_h - unit_surf.get_height()) // 2))

    def draw_telemetry(self):
        # Draw background onto portrait canvas
        self.canvas.blit(self.background, (0, 0))

        # Header
        pad_x = int(self.pw * 0.03)
        pad_y = int(self.ph * 0.02)
        line_h = int(self.ph * 0.07)
        x = pad_x + 20
        y = pad_y + 10

        fps_text = f"Screen FPS: {round(self.clock.get_fps(),1)} | API FPS: {self.api.get_current_fps() if hasattr(self.api,'get_current_fps') else 'N/A'}"
        hdr = self.txt_font.render(fps_text, True, COLOR_HL)
        self.canvas.blit(hdr, (x, y))
        y += int(line_h * 0.6)

        # Values placed on background placeholders (relative positions)
        value_positions = [
            (0.5, 0.09),  # Speed

            (0.52, 0.46),  # Altitude
            (0.60, 0.68),  # Apoapsis
            (0.60, 0.80),  # Periapsis
        ]

        values = [
            f"{self.format_value(self.api.speed,0)}",
            
            f"{self.format_value(self.api.altitude,2)}",
            f"{self.format_value(self.api.apoapsis,2)} m",
            f"{self.format_value(self.api.periapsis,2)} m",
        ]

        for (rel_x, rel_y), value in zip(value_positions, values):
            # Use fixed-digit rendering for numeric values to preserve spacing
            try:
                # treat strings containing digits as numeric + optional unit
                self.render_fixed_numeric(value, rel_x, rel_y, align="center")
            except Exception:
                # fallback: normal render
                value_surf = self.num_font.render(value, True, COLOR_HL)
                abs_x = int(self.pw * rel_x) - value_surf.get_width() // 2
                abs_y = int(self.ph * rel_y) - value_surf.get_height() // 2
                self.canvas.blit(value_surf, (abs_x, abs_y))

        # Blit the portrait canvas to the actual screen. Rotate if physical screen is landscape
        if self.is_landscape:
            rotated = pygame.transform.rotate(self.canvas, 90)
            rw, rh = rotated.get_size()
            blit_x = (self.width - rw) // 2
            blit_y = (self.height - rh) // 2
            self.screen.blit(rotated, (blit_x, blit_y))
        else:
            if (self.width, self.height) != (self.pw, self.ph):
                scaled = pygame.transform.smoothscale(self.canvas, (self.width, self.height))
                self.screen.blit(scaled, (0, 0))
            else:
                self.screen.blit(self.canvas, (0, 0))

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
    # Standalone demo mode: do not connect to KSP. Use a lightweight MockAPI
    # that provides the attributes and get_current_fps() used by Display.
    import threading
    import time
    import math

    class MockAPI(threading.Thread):
        def __init__(self):
            super().__init__(daemon=True)
            # telemetry attributes expected by Display
            self.altitude = 0.0
            self.speed = 0.0
            self.g_force = 1.0
            self.temperature = 273.15
            self.apoapsis = 0.0
            self.periapsis = 0.0
            self._running = False
            # lightweight fps clock used by get_current_fps()
            self.clock = pygame.time.Clock()

        def get_current_fps(self) -> str:
            return str(round(self.clock.get_fps(), 1))

        def run(self) -> None:
            self._running = True
            start = time.time()
            while self._running:
                t = time.time() - start
                # simple, smooth demo signals
                self.altitude = 10000 + 3000 * math.sin(t / 5.0)
                self.speed = 200 + 80 * math.cos(t / 3.0)
                self.g_force = 1.0 + 0.3 * math.sin(t / 2.0)
                self.temperature = 250 + 15 * math.sin(t / 6.0)
                self.apoapsis = 120000 + 2000 * math.sin(t / 11.0)
                self.periapsis = 80000 + 1500 * math.cos(t / 9.0)
                # tick the clock for fps reporting
                self.clock.tick(30)

        def stop_telemetry(self) -> None:
            self._running = False

    api = MockAPI()
    api.start()

    # MockAPI intentionally implements the subset of API used by Display.
    # Type checkers may complain because MockAPI is not an API subclass.
    display = Display(api)  # type: ignore[arg-type]
    display.run()

    api.stop_telemetry()
    api.join(timeout=1)