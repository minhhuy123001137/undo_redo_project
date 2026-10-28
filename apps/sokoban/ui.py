"""UI components and Transition system for Time Shift."""
from typing import Callable, List, Optional, Tuple
import pygame

from apps.sokoban.theme import (
    COLOR_BG,
    COLOR_SURFACE,
    COLOR_SURFACE_LIGHT,
    COLOR_BORDER,
    COLOR_BORDER_BRIGHT,
    COLOR_CYAN,
    COLOR_PURPLE,
    COLOR_GOLD,
    COLOR_GREEN,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    COLOR_DISABLED,
    get_glow_surface,
    draw_soft_shadow,
    ease_in_out_quad,
)
from apps.sokoban.widgets import Button, ToggleSwitch, Slider

# Re-exporting legacy constants for backwards compatibility
NAVY_BG = COLOR_BG
NAVY_PANEL = COLOR_SURFACE
NAVY_BORDER = COLOR_BORDER
CYAN_ACCENT = COLOR_CYAN
PURPLE_NEON = COLOR_PURPLE
GOLD_BOX = COLOR_GOLD
GREEN_TARGET = COLOR_GREEN
TEXT_WHITE = COLOR_TEXT_MAIN


class ScreenTransition:
    """Manages smooth non-blocking fade transitions between screens."""

    def __init__(self, duration: float = 0.22) -> None:
        self.duration = max(0.05, duration)
        self.progress: float = 1.0  # 1.0 = completed / idle
        self.fade_out: bool = True  # True: fading to black, False: fading from black
        self.next_state: Optional[str] = None
        self.on_midpoint: Optional[Callable[[], None]] = None

    @property
    def is_active(self) -> bool:
        return self.progress < 1.0

    def start(self, next_state: str, on_midpoint: Optional[Callable[[], None]] = None) -> None:
        self.next_state = next_state
        self.on_midpoint = on_midpoint
        self.progress = 0.0
        self.fade_out = True

    def update(self, dt: float) -> None:
        if self.progress >= 1.0:
            return

        self.progress += dt / (self.duration / 2.0)
        if self.progress >= 1.0:
            if self.fade_out:
                # Reached midpoint black
                if self.on_midpoint:
                    self.on_midpoint()
                self.fade_out = False
                self.progress = 0.0
            else:
                # Fully faded in
                self.progress = 1.0
                self.next_state = None

    def draw(self, surface: pygame.Surface) -> None:
        if self.progress >= 1.0:
            return

        # Alpha curve
        if self.fade_out:
            alpha = int(255 * ease_in_out_quad(self.progress))
        else:
            alpha = int(255 * (1.0 - ease_in_out_quad(self.progress)))

        if alpha > 0:
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((8, 13, 28, min(255, alpha)))
            surface.blit(overlay, (0, 0))


class TimelineBar:
    """Sleek Cyberpunk Timeline representing past and future timeline states."""

    def __init__(self, rect: pygame.Rect) -> None:
        self.rect = pygame.Rect(rect)

    def draw(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        undo_count: int,
        redo_count: int,
        timeline_items: List[str],
    ) -> None:
        # Glassmorphic panel background
        draw_soft_shadow(surface, self.rect, radius=8, offset_y=3)
        pygame.draw.rect(surface, COLOR_SURFACE, self.rect, border_radius=8)
        pygame.draw.rect(surface, COLOR_BORDER, self.rect, width=1, border_radius=8)

        # Timeline status badges
        undo_txt = font.render(f"PAST: {undo_count}", True, COLOR_CYAN if undo_count > 0 else COLOR_DISABLED)
        redo_txt = font.render(f"FUTURE: {redo_count}", True, COLOR_PURPLE if redo_count > 0 else COLOR_DISABLED)

        surface.blit(undo_txt, (self.rect.x + 16, self.rect.y + 14))
        surface.blit(redo_txt, (self.rect.x + 130, self.rect.y + 14))

        # Central connecting timeline axis
        start_x = self.rect.x + 240
        axis_end_x = self.rect.right - 24
        axis_y = self.rect.centery

        if axis_end_x > start_x:
            # Gradient timeline line
            pygame.draw.line(surface, (32, 45, 72), (start_x, axis_y), (axis_end_x, axis_y), 2)

        # Draw chronological node dots
        max_visible = 10
        visible_items = timeline_items[-max_visible:] if timeline_items else []

        if visible_items and axis_end_x > start_x + 60:
            spacing = min(36, (axis_end_x - start_x - 30) // (len(visible_items) + 1))
            for i, name in enumerate(visible_items):
                nx = start_x + (i + 1) * spacing
                is_push = "Push" in name
                node_color = COLOR_GOLD if is_push else COLOR_CYAN

                # Node glowing point
                pygame.draw.circle(surface, node_color, (nx, axis_y), 4)
                pygame.draw.circle(surface, COLOR_TEXT_MAIN, (nx, axis_y), 2)

        # Current present timeline cursor marker
        if visible_items:
            curr_x = start_x + len(visible_items) * min(36, (axis_end_x - start_x - 30) // (len(visible_items) + 1))
            pygame.draw.circle(surface, COLOR_CYAN, (curr_x, axis_y), 7, 2)

        # Future branch marker if redo available
        if redo_count > 0:
            rx = axis_end_x - 12
            pygame.draw.circle(surface, COLOR_PURPLE, (rx, axis_y), 5)
            pygame.draw.circle(surface, (255, 255, 255), (rx, axis_y), 2)
