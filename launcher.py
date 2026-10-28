"""High-Performance Cyberpunk Launcher for PYTHON UNDO/REDO LAB.

Features dark gradient backdrop, moving grid, floating particles,
animated application cards with hover-lift & click-bounce, and
independent subprocess launching.
"""
import math
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple
import pygame

# Palette matching project specification
COLOR_BG_TOP = (8, 13, 28)       # #080D1C
COLOR_BG_BOTTOM = (14, 23, 46)   # #0E172E
COLOR_SURFACE = (18, 27, 48)     # #121B30
COLOR_SURFACE_LIGHT = (26, 38, 66)
COLOR_BORDER = (38, 52, 86)
COLOR_BORDER_BRIGHT = (59, 82, 135)
COLOR_CYAN = (0, 229, 255)       # #00E5FF
COLOR_PURPLE = (168, 85, 247)    # #A855F7
COLOR_GOLD = (245, 158, 11)      # #F59E0B
COLOR_GREEN = (16, 185, 129)     # #10B981
COLOR_TEXT_MAIN = (226, 232, 240)# #E2E8F0
COLOR_TEXT_MUTED = (148, 163, 184)
COLOR_DISABLED = (60, 75, 95)

WIDTH, HEIGHT = 840, 620
FPS = 60


def ease_out_quad(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) * (1.0 - t)


def lerp(start: float, end: float, factor: float) -> float:
    return start + (end - start) * factor


def lerp_color(c1: Tuple[int, int, int], c2: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    f = max(0.0, min(1.0, factor))
    return (
        int(c1[0] + (c2[0] - c1[0]) * f),
        int(c1[1] + (c2[1] - c1[1]) * f),
        int(c1[2] + (c2[2] - c1[2]) * f),
    )


class LauncherParticle:
    """Ambient floating particle for launcher backdrop."""

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.vx = (-0.5 + pygame.math.Vector2().x) * 10
        self.vy = -18.0
        self.radius = 2.0
        self.lifetime = 6.0
        self.max_lifetime = 6.0
        self.color = COLOR_CYAN

    def update(self, dt: float) -> bool:
        self.y += self.vy * dt
        self.lifetime -= dt
        return self.lifetime > 0

    def draw(self, surface: pygame.Surface) -> None:
        alpha = int(180 * (self.lifetime / self.max_lifetime))
        if alpha <= 0:
            return
        p_surf = pygame.Surface((6, 6), pygame.SRCALPHA)
        pygame.draw.circle(p_surf, (self.color[0], self.color[1], self.color[2], alpha), (3, 3), 2)
        surface.blit(p_surf, (int(self.x - 3), int(self.y - 3)))


class AppCard:
    """Interactive card for launching applications with hover-lift and click bounce."""

    def __init__(
        self,
        rect: pygame.Rect,
        title: str,
        subtitle: str,
        on_click=None,
        enabled: bool = True,
        badge: str = "",
        theme: str = "cyan",
    ) -> None:
        self.base_rect = pygame.Rect(rect)
        self.title = title
        self.subtitle = subtitle
        self.on_click = on_click
        self.enabled = enabled
        self.badge = badge
        self.theme = theme

        self.hovered = False
        self.pressed = False
        self.hover_progress = 0.0
        self.scale = 1.0
        self.ripples = []

    def update(self, mouse_pos: Tuple[int, int], dt: float) -> None:
        if not self.enabled:
            self.hovered = False
            self.pressed = False
            self.hover_progress = max(0.0, self.hover_progress - dt * 6.0)
            self.scale = lerp(self.scale, 1.0, dt * 10.0)
            return

        self.hovered = self.base_rect.collidepoint(mouse_pos)
        if self.hovered:
            self.hover_progress = min(1.0, self.hover_progress + dt * 7.0)
        else:
            self.hover_progress = max(0.0, self.hover_progress - dt * 6.0)

        target_scale = 0.97 if self.pressed else (1.02 if self.hovered else 1.0)
        self.scale = lerp(self.scale, target_scale, dt * 14.0)

        # Update ripples
        new_ripples = []
        for r in self.ripples:
            r[2] += dt / 0.35  # progress
            if r[2] < 1.0:
                new_ripples.append(r)
        self.ripples = new_ripples

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.enabled:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.base_rect.collidepoint(event.pos):
                self.pressed = True
                self.ripples.append([event.pos[0], event.pos[1], 0.0])
                return True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.pressed:
                self.pressed = False
                if self.base_rect.collidepoint(event.pos) and self.on_click:
                    self.on_click()
                    return True
        return False

    def draw(
        self,
        surface: pygame.Surface,
        font_title: pygame.font.Font,
        font_sub: pygame.font.Font,
        font_badge: pygame.font.Font,
    ) -> None:
        accent = COLOR_PURPLE if self.theme == "purple" else COLOR_CYAN

        # Calculate lifted / scaled position
        lift = int(4 * self.hover_progress) if self.enabled else 0
        w = int(self.base_rect.width * self.scale)
        h = int(self.base_rect.height * self.scale)
        rect = pygame.Rect(
            self.base_rect.centerx - w // 2,
            self.base_rect.centery - h // 2 - lift,
            w,
            h,
        )

        # Soft drop shadow
        if self.enabled:
            shadow_rect = pygame.Rect(rect.x + 4, rect.y + 6, rect.width - 8, rect.height)
            shadow_surf = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(shadow_surf, (0, 0, 0, 110), shadow_surf.get_rect(), border_radius=10)
            surface.blit(shadow_surf, shadow_rect.topleft)

        # Surface colors
        if not self.enabled:
            bg_col = (13, 18, 30)
            border_col = (35, 45, 65)
            title_col = COLOR_DISABLED
            sub_col = (55, 68, 88)
        else:
            base_bg = COLOR_SURFACE
            hover_bg = (
                int(base_bg[0] + accent[0] * 0.12),
                int(base_bg[1] + accent[1] * 0.12),
                int(base_bg[2] + accent[2] * 0.12),
            )
            bg_col = lerp_color(base_bg, hover_bg, self.hover_progress)
            border_col = lerp_color(COLOR_BORDER, accent, self.hover_progress)
            title_col = COLOR_TEXT_MAIN if self.hovered else (215, 228, 245)
            sub_col = COLOR_CYAN if self.hovered else COLOR_TEXT_MUTED

        pygame.draw.rect(surface, bg_col, rect, border_radius=10)

        # Glowing accent border
        border_w = 2 if self.hovered and self.enabled else 1
        pygame.draw.rect(surface, border_col, rect, width=border_w, border_radius=10)

        # Ripples
        old_clip = surface.get_clip()
        surface.set_clip(rect)
        for r in self.ripples:
            rx, ry, prog = r
            radius = int(rect.width * 0.8 * ease_out_quad(prog))
            alpha = int(150 * (1.0 - prog))
            if radius > 0 and alpha > 0:
                rip_s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(rip_s, (accent[0], accent[1], accent[2], alpha), (radius, radius), radius)
                surface.blit(rip_s, (rx - radius, ry - radius))
        surface.set_clip(old_clip)

        # Top border sheen
        if self.enabled:
            sheen_s = pygame.Surface((rect.width - 6, 2), pygame.SRCALPHA)
            sheen_alpha = int(70 + 130 * self.hover_progress)
            sheen_s.fill((accent[0], accent[1], accent[2], sheen_alpha))
            surface.blit(sheen_s, (rect.x + 3, rect.y + 2))

        # Text render
        t_surf = font_title.render(self.title, True, title_col)
        surface.blit(t_surf, (rect.x + 28, rect.y + 18))

        s_surf = font_sub.render(self.subtitle, True, sub_col)
        surface.blit(s_surf, (rect.x + 28, rect.y + 48))

        # Badge render
        if self.badge:
            badge_col = COLOR_PURPLE if self.theme == "purple" else (COLOR_GREEN if self.enabled else COLOR_DISABLED)
            b_surf = font_badge.render(self.badge, True, badge_col)
            b_rect = b_surf.get_rect(right=rect.right - 24, centery=rect.centery)
            surface.blit(b_surf, b_rect)


class Launcher:
    """Master application launcher with animated cyber visuals."""

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("TIME SHIFT")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()

        self.font_logo = pygame.font.SysFont(["Segoe UI", "Arial", "Tahoma"], 48, bold=True)
        self.font_subtitle = pygame.font.SysFont(["Segoe UI", "Arial", "Tahoma"], 18, bold=True)
        self.font_card_title = pygame.font.SysFont(["Segoe UI", "Arial", "Tahoma"], 22, bold=True)
        self.font_card_sub = pygame.font.SysFont(["Segoe UI", "Arial", "Tahoma"], 14)
        self.font_badge = pygame.font.SysFont(["Segoe UI", "Arial", "Tahoma"], 14, bold=True)
        self.font_footer = pygame.font.SysFont("Consolas", 13)

        self.running = True
        self.global_time = 0.0
        self.particles: List[LauncherParticle] = []
        self.launch_flash_timer = 0.0

        card_w = 580
        card_h = 82
        cx = (WIDTH - card_w) // 2

        self.card_sokoban = AppCard(
            pygame.Rect(cx, 215, card_w, card_h),
            "1. TIME SHIFT – Escape the Timeline",
            "Sokoban Puzzle Game • Rewind timelines with dual-stack Undo/Redo Engine",
            on_click=self.launch_sokoban,
            enabled=True,
            badge="PLAY NOW ►",
            theme="cyan",
        )

        self.card_photoshop = AppCard(
            pygame.Rect(cx, 315, card_w, card_h),
            "2. PIXEL STUDIO – Mini Photoshop",
            "Layered Raster Image Editor • (Future application in Phase 2)",
            on_click=None,
            enabled=False,
            badge="COMING SOON",
            theme="purple",
        )

        self.card_exit = AppCard(
            pygame.Rect(cx, 415, card_w, 60),
            "EXIT LAB",
            "Close launcher window",
            on_click=self.quit,
            enabled=True,
            badge="",
            theme="cyan",
        )

        self.cards = [self.card_sokoban, self.card_photoshop, self.card_exit]

    def launch_sokoban(self) -> None:
        """Launch Sokoban in an independent subprocess using sys.executable."""
        self.launch_flash_timer = 0.35
        project_root = Path(__file__).resolve().parent
        cmd = [sys.executable, "-m", "apps.sokoban.main"]
        subprocess.Popen(cmd, cwd=str(project_root))

    def quit(self) -> None:
        self.running = False

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            self.global_time += dt
            mouse_pos = pygame.mouse.get_pos()

            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                for card in self.cards:
                    card.handle_event(event)

            # Update cards & particles
            for card in self.cards:
                card.update(mouse_pos, dt)

            if len(self.particles) < 25 and self.global_time % 0.2 < dt:
                import random
                p = LauncherParticle(random.uniform(20, WIDTH - 20), HEIGHT + 5)
                p.color = COLOR_PURPLE if random.random() > 0.5 else COLOR_CYAN
                self.particles.append(p)

            self.particles = [p for p in self.particles if p.update(dt)]

            if self.launch_flash_timer > 0:
                self.launch_flash_timer = max(0.0, self.launch_flash_timer - dt)

            self._draw()

        pygame.quit()

    def _draw(self) -> None:
        # 1. Dark Gradient Background
        for y in range(HEIGHT):
            ratio = y / HEIGHT
            r = int(COLOR_BG_TOP[0] + (COLOR_BG_BOTTOM[0] - COLOR_BG_TOP[0]) * ratio)
            g = int(COLOR_BG_TOP[1] + (COLOR_BG_BOTTOM[1] - COLOR_BG_TOP[1]) * ratio)
            b = int(COLOR_BG_TOP[2] + (COLOR_BG_BOTTOM[2] - COLOR_BG_TOP[2]) * ratio)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (WIDTH, y))

        # 2. Moving Cyber Perspective Grid Lines
        grid_col = (18, 27, 48)
        flow_offset = int((self.global_time * 16.0) % 40)
        for x in range(0, WIDTH + 40, 40):
            pygame.draw.line(self.screen, grid_col, (x, 0), (x, HEIGHT))
        for y in range(flow_offset - 40, HEIGHT + 40, 40):
            pygame.draw.line(self.screen, grid_col, (0, y), (WIDTH, y))

        # 3. Floating Particles
        for p in self.particles:
            p.draw(self.screen)

        # 4. Animated Glowing Logo & Credits
        logo_y = 90
        glow_surf = self.font_logo.render("TIME SHIFT", True, COLOR_PURPLE)
        self.screen.blit(glow_surf, (WIDTH // 2 - glow_surf.get_width() // 2, logo_y - 2))

        logo_surf = self.font_logo.render("TIME SHIFT", True, COLOR_CYAN)
        logo_rect = logo_surf.get_rect(center=(WIDTH // 2, logo_y))
        self.screen.blit(logo_surf, logo_rect)

        # Traveling light line beneath logo
        line_w = 360
        lx = WIDTH // 2 - line_w // 2
        ly = logo_rect.bottom + 8
        pygame.draw.line(self.screen, COLOR_BORDER, (lx, ly), (lx + line_w, ly), 2)
        beam_x = lx + int(((self.global_time * 0.35) % 1.0) * line_w)
        pygame.draw.circle(self.screen, COLOR_CYAN, (beam_x, ly), 3)

        sub_surf = self.font_subtitle.render("Dự án hoàn thiện của Huy - Nhân - Cường", True, COLOR_TEXT_MAIN)
        sub_rect = sub_surf.get_rect(center=(WIDTH // 2, ly + 28))
        self.screen.blit(sub_surf, sub_rect)

        # 5. Draw Application Cards
        for card in self.cards:
            card.draw(self.screen, self.font_card_title, self.font_card_sub, self.font_badge)

        # 6. Footer
        foot_str = "Independent Subprocess Execution • Powered by core/history_manager.py"
        foot_surf = self.font_footer.render(foot_str, True, (80, 95, 125))
        self.screen.blit(foot_surf, foot_surf.get_rect(center=(WIDTH // 2, HEIGHT - 35)))

        # 7. Flash Overlay on Launch
        if self.launch_flash_timer > 0:
            alpha = int(160 * (self.launch_flash_timer / 0.35))
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 229, 255, alpha))
            self.screen.blit(overlay, (0, 0))

        pygame.display.flip()


def main() -> None:
    launcher = Launcher()
    launcher.run()


if __name__ == "__main__":
    main()
