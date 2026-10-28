"""Reusable UI Widgets with smooth hover/scale animations, click ripples, and sound."""
import math
import time
from typing import Callable, Optional, Tuple
import pygame

from apps.sokoban.sound import get_sound_manager
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
    ease_out_quad,
    get_glow_surface,
    draw_soft_shadow,
    lerp,
    lerp_color,
)


class RippleEffect:
    """Expanding circle ripple on button click."""

    def __init__(self, x: float, y: float, max_radius: float, color: Tuple[int, int, int]) -> None:
        self.x = x
        self.y = y
        self.max_radius = max_radius
        self.color = color
        self.progress = 0.0  # 0.0 to 1.0
        self.duration = 0.35  # seconds

    def update(self, dt: float) -> bool:
        self.progress += dt / self.duration
        return self.progress < 1.0

    def draw(self, surface: pygame.Surface, clip_rect: pygame.Rect) -> None:
        if self.progress >= 1.0:
            return
        radius = int(self.max_radius * ease_out_quad(self.progress))
        alpha = int(180 * (1.0 - self.progress))
        if radius <= 0 or alpha <= 0:
            return

        ripple_surf = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(
            ripple_surf,
            (self.color[0], self.color[1], self.color[2], alpha),
            (radius + 1, radius + 1),
            radius,
        )
        # Clip to button bounds
        old_clip = surface.get_clip()
        surface.set_clip(clip_rect)
        surface.blit(ripple_surf, (self.x - radius, self.y - radius))
        surface.set_clip(old_clip)


class Button:
    """Universal animated button supporting scale, glow, color transitions, and ripples."""

    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        on_click: Optional[Callable[[], None]] = None,
        theme: str = "cyan",  # cyan, purple, gold, green, neutral
        font_size: int = 18,
        enabled: bool = True,
        subtext: str = "",
        badge: str = "",
    ) -> None:
        self.base_rect = pygame.Rect(rect)
        self.rendered_rect = pygame.Rect(rect)
        self.text = text
        self.subtext = subtext
        self.badge = badge
        self.on_click = on_click
        self.theme = theme
        self.font_size = font_size
        self.enabled = enabled

        # Animation states
        self.hovered: bool = False
        self.pressed: bool = False
        self.hover_progress: float = 0.0  # 0.0 to 1.0
        self.press_scale: float = 1.0     # 0.95 to 1.0
        self.ripples = []
        self._font_cache = None

    def _get_theme_accent(self) -> Tuple[int, int, int]:
        if self.theme == "purple":
            return COLOR_PURPLE
        if self.theme == "gold":
            return COLOR_GOLD
        if self.theme == "green":
            return COLOR_GREEN
        if self.theme == "neutral":
            return (140, 160, 195)
        return COLOR_CYAN

    def update(self, mouse_pos: Tuple[int, int], dt: float = 0.016) -> None:
        # Update ripples
        self.ripples = [r for r in self.ripples if r.update(dt)]

        if not self.enabled:
            self.hovered = False
            self.pressed = False
            self.hover_progress = max(0.0, self.hover_progress - dt * 6.0)
            self.press_scale = lerp(self.press_scale, 1.0, dt * 12.0)
            self.rendered_rect = pygame.Rect(self.base_rect)
            return

        was_hovered = self.hovered
        self.hovered = self.base_rect.collidepoint(mouse_pos)

        # Trigger hover sound on state enter
        if self.hovered and not was_hovered:
            get_sound_manager().play("hover")

        # Smooth hover progress
        if self.hovered:
            self.hover_progress = min(1.0, self.hover_progress + dt * 7.0)
        else:
            self.hover_progress = max(0.0, self.hover_progress - dt * 6.0)

        # Smooth press scale
        target_scale = 0.96 if self.pressed else (1.03 if self.hovered else 1.0)
        self.press_scale = lerp(self.press_scale, target_scale, dt * 14.0)

        # Compute scaled rect centered on base_rect
        new_w = int(self.base_rect.width * self.press_scale)
        new_h = int(self.base_rect.height * self.press_scale)
        self.rendered_rect = pygame.Rect(
            self.base_rect.centerx - new_w // 2,
            self.base_rect.centery - new_h // 2,
            new_w,
            new_h,
        )

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.enabled:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.base_rect.collidepoint(event.pos):
                self.pressed = True
                accent = self._get_theme_accent()
                self.ripples.append(RippleEffect(event.pos[0], event.pos[1], self.base_rect.width * 0.9, accent))
                get_sound_manager().play("click")
                return True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.pressed:
                self.pressed = False
                if self.base_rect.collidepoint(event.pos) and self.on_click:
                    self.on_click()
                    return True

        return False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, font_sub: Optional[pygame.font.Font] = None) -> None:
        accent = self._get_theme_accent()
        rect = self.rendered_rect

        # 1. Soft Shadow
        if self.enabled:
            shadow_dist = int(2 + 4 * (1.0 - self.hover_progress))
            draw_soft_shadow(surface, rect, radius=8, offset_y=shadow_dist)

        # 2. Glow effect on hover
        if self.enabled and self.hover_progress > 0.05:
            glow_surf = get_glow_surface(rect.width, rect.height, accent, radius=12, alpha=int(60 * self.hover_progress))
            surface.blit(glow_surf, (rect.x - 12, rect.y - 12))

        # 3. Background surface
        if not self.enabled:
            bg_col = (14, 19, 32)
            border_col = COLOR_DISABLED
            text_col = COLOR_DISABLED
        else:
            # Interpolate background with subtle accent tint on hover
            base_bg = COLOR_SURFACE
            hover_bg = (
                int(base_bg[0] + accent[0] * 0.12),
                int(base_bg[1] + accent[1] * 0.12),
                int(base_bg[2] + accent[2] * 0.12),
            )
            bg_col = lerp_color(base_bg, hover_bg, self.hover_progress)
            border_col = lerp_color(COLOR_BORDER, accent, self.hover_progress)
            text_col = COLOR_TEXT_MAIN if self.hovered else (205, 218, 235)

        pygame.draw.rect(surface, bg_col, rect, border_radius=8)

        # Top border highlight line
        if self.enabled and rect.height > 20:
            top_line_surf = pygame.Surface((rect.width - 6, 2), pygame.SRCALPHA)
            top_line_alpha = int(90 + 130 * self.hover_progress)
            top_line_surf.fill((accent[0], accent[1], accent[2], top_line_alpha))
            surface.blit(top_line_surf, (rect.x + 3, rect.y + 2))

        # Border
        b_width = 2 if self.hovered and self.enabled else 1
        pygame.draw.rect(surface, border_col, rect, width=b_width, border_radius=8)

        # 4. Draw Ripples
        for rip in self.ripples:
            rip.draw(surface, rect)

        # 5. Text Render
        t_surf = font.render(self.text, True, text_col)
        if self.subtext and font_sub:
            # Multi-line layout
            t_rect = t_surf.get_rect(centerx=rect.centerx, centery=rect.centery - 8)
            surface.blit(t_surf, t_rect)
            sub_surf = font_sub.render(self.subtext, True, COLOR_TEXT_MUTED)
            sub_rect = sub_surf.get_rect(centerx=rect.centerx, centery=rect.centery + 12)
            surface.blit(sub_surf, sub_rect)
        else:
            t_rect = t_surf.get_rect(center=rect.center)
            surface.blit(t_surf, t_rect)

        # 6. Optional Badge
        if self.badge and font_sub:
            b_surf = font_sub.render(self.badge, True, accent if self.enabled else COLOR_DISABLED)
            b_rect = b_surf.get_rect(right=rect.right - 14, centery=rect.centery)
            surface.blit(b_surf, b_rect)


class ToggleSwitch:
    """Modern slider switch for Settings (On/Off)."""

    def __init__(self, rect: pygame.Rect, initial_state: bool = True, on_toggle: Optional[Callable[[bool], None]] = None) -> None:
        self.rect = pygame.Rect(rect)
        self.state = initial_state
        self.on_toggle = on_toggle
        self.knob_pos = 1.0 if initial_state else 0.0

    def update(self, dt: float) -> None:
        target = 1.0 if self.state else 0.0
        self.knob_pos = lerp(self.knob_pos, target, dt * 14.0)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.state = not self.state
                get_sound_manager().play("click")
                if self.on_toggle:
                    self.on_toggle(self.state)
                return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        track_col = lerp_color((30, 42, 65), COLOR_GREEN, self.knob_pos)
        pygame.draw.rect(surface, track_col, self.rect, border_radius=self.rect.height // 2)
        pygame.draw.rect(surface, COLOR_BORDER_BRIGHT, self.rect, width=1, border_radius=self.rect.height // 2)

        # Knob
        knob_r = (self.rect.height - 6) // 2
        start_x = self.rect.x + 3 + knob_r
        end_x = self.rect.right - 3 - knob_r
        cx = int(start_x + (end_x - start_x) * self.knob_pos)
        cy = self.rect.centery

        # Soft shadow under knob
        pygame.draw.circle(surface, (0, 0, 0, 80), (cx, cy + 2), knob_r)
        # Knob body
        pygame.draw.circle(surface, COLOR_TEXT_MAIN, (cx, cy), knob_r)
        pygame.draw.circle(surface, COLOR_BORDER, (cx, cy), knob_r, 1)


class Slider:
    """Horizontal slider for volume / values."""

    def __init__(self, rect: pygame.Rect, value: float = 0.8, on_change: Optional[Callable[[float], None]] = None) -> None:
        self.rect = pygame.Rect(rect)
        self.value = max(0.0, min(1.0, value))
        self.on_change = on_change
        self.dragging = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
                self._update_val(event.pos[0])
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False
                return True
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._update_val(event.pos[0])
            return True
        return False

    def _update_val(self, mouse_x: int) -> None:
        ratio = (mouse_x - self.rect.x) / max(1, self.rect.width)
        self.value = max(0.0, min(1.0, ratio))
        if self.on_change:
            self.on_change(self.value)

    def draw(self, surface: pygame.Surface) -> None:
        track_y = self.rect.centery - 3
        # Background bar
        pygame.draw.rect(surface, (25, 35, 55), (self.rect.x, track_y, self.rect.width, 6), border_radius=3)
        # Active filled bar
        fill_w = int(self.rect.width * self.value)
        if fill_w > 0:
            pygame.draw.rect(surface, COLOR_CYAN, (self.rect.x, track_y, fill_w, 6), border_radius=3)

        # Handle knob
        hx = self.rect.x + fill_w
        hy = self.rect.centery
        pygame.draw.circle(surface, (0, 0, 0, 90), (hx, hy + 2), 9)
        pygame.draw.circle(surface, COLOR_TEXT_MAIN, (hx, hy), 8)
        pygame.draw.circle(surface, COLOR_CYAN, (hx, hy), 8, 2)
