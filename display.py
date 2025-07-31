import pygame

class BaseDisplay:
    def __init__(self, screen):
        self.screen = screen
        self.background = pygame.image.load("assets'\bg16-9.png").convert()

    def render_background(self):
        self.screen.blit(self.background, (0, 0))

    def update_display(self):
        pygame.display.flip()

class LandingDisplay(BaseDisplay):
    def __init__(self, conn, vessel):
        super().__init__(conn, vessel)

    def render(self):
        self.draw_background()
        
        vertical_speed = self.vessel.flight().vertical_speed
        altitude = self.vessel.flight().surface_altitude
        
        self.screen.blit(self.font.render(f"Vertical Speed: {vertical_speed:.1f} m/s", True, self.WHITE), (50, 100))
        self.screen.blit(self.font.render(f"Altitude: {altitude / 1000:.2f} km", True, self.WHITE), (50, 150))
        
        # Additional landing-specific data can be added here
        # For example, landing gear status, fuel levels, etc.

        pygame.display.flip()

class AscentDisplay(BaseDisplay):
    
    def __init__(self, screen, vessel):
        super().__init__(screen)
        self.vessel = vessel

    def render(self):
        self.draw_background()
        self.display_ascent_data()

    def display_ascent_data(self):
        altitude = self.vessel.flight().surface_altitude
        speed = self.vessel.flight().speed
        engine_status = self.vessel.resources.amount('LiquidFuel') > 0

        self.screen.blit(self.font.render(f"Altitude: {altitude/1000:.2f} km", True, (255, 255, 255)), (50, 50))
        self.screen.blit(self.font.render(f"Speed: {speed:.1f} m/s", True, (255, 255, 255)), (50, 100))
        self.screen.blit(self.font.render(f"Engine Status: {'On' if engine_status else 'Off'}", True, (255, 255, 255)), (50, 150))

class OrbitDisplay(BaseDisplay):
    def __init__(self, screen, vessel):
        super().__init__(screen)
        self.vessel = vessel

    def render(self):
        self.draw_background()
        
        orbit = self.vessel.orbit
        apoapsis = orbit.apoapsis_altitude
        periapsis = orbit.periapsis_altitude
        orbital_speed = self.vessel.flight().speed

        self.screen.blit(self.font.render(f"APOAPSIS: {apoapsis / 1000:.2f} km", True, self.WHITE), (50, 100))
        self.screen.blit(self.font.render(f"PERIAPSIS: {periapsis / 1000:.2f} km", True, self.WHITE), (50, 140))
        self.screen.blit(self.font.render(f"ORBITAL SPEED: {orbital_speed:.1f} m/s", True, self.WHITE), (50, 180))