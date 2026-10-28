"""Visual theme constants, palette, typography, and easing helpers for Time Shift."""
import math
from typing import Callable, Tuple
import pygame

# ---------------------------------------------------------
# PALETTE DEFINITION (Neon Cyberpunk & Modern Pixel Art)
# ---------------------------------------------------------
COLOR_BG = (8, 13, 28)           # #080D1C - Deep Void Navy
COLOR_SURFACE = (18, 27, 48)     # #121B30 - Dark Tech Surface
COLOR_SURFACE_LIGHT = (26, 38, 66)
COLOR_SURFACE_GLASS = (18, 27, 48, 210)
COLOR_BORDER = (38, 52, 86)
COLOR_BORDER_BRIGHT = (59, 82, 135)

COLOR_CYAN = (0, 229, 255)       # #00E5FF - Time stream & Primary Accent
COLOR_CYAN_DIM = (0, 160, 185)
COLOR_CYAN_GLOW = (0, 229, 255, 60)

COLOR_PURPLE = (168, 85, 247)    # #A855F7 - Neon Chrono Energy
COLOR_PURPLE_DIM = (126, 34, 206)
COLOR_PURPLE_GLOW = (168, 85, 247, 60)

COLOR_GOLD = (245, 158, 11)      # #F59E0B - Chrono-Crate Gold
COLOR_GOLD_LIGHT = (251, 191, 36)
COLOR_GOLD_DARK = (180, 83, 9)

COLOR_GREEN = (16, 185, 129)     # #10B981 - Temporal Goal Pad
COLOR_GREEN_LIGHT = (52, 211, 153)
COLOR_GREEN_GLOW = (16, 185, 129, 65)

COLOR_TEXT_MAIN = (226, 232, 240) # #E2E8F0 - Crisp White Text
COLOR_TEXT_MUTED = (148, 163, 184)
COLOR_TEXT_DARK = (100, 116, 139)
COLOR_DISABLED = (51, 65, 85)
COLOR_SHADOW = (4, 7, 16, 140)

# ---------------------------------------------------------
# EASING FUNCTIONS
# ---------------------------------------------------------
def ease_out_quad(t: float) -> float:
    """Fast start, smooth deceleration."""
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) * (1.0 - t)

def ease_in_out_quad(t: float) -> float:
    """Smooth acceleration and deceleration."""
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        return 2.0 * t * t
    return 1.0 - ((-2.0 * t + 2.0) ** 2) / 2.0

def ease_out_back(t: float, s: float = 1.70158) -> float:
    """Over-shoots target slightly then settles for juicy bounce."""
    t = max(0.0, min(1.0, t))
    t -= 1.0
    return (t * t * ((s + 1.0) * t + s) + 1.0)

def lerp(start: float, end: float, factor: float) -> float:
    return start + (end - start) * factor

def lerp_color(c1: Tuple[int, int, int], c2: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    f = max(0.0, min(1.0, factor))
    return (
        int(c1[0] + (c2[0] - c1[0]) * f),
        int(c1[1] + (c2[1] - c1[1]) * f),
        int(c1[2] + (c2[2] - c1[2]) * f),
    )

# ---------------------------------------------------------
# DRAWING HELPERS (Soft shadows, glows, gradients)
# ---------------------------------------------------------
_glow_cache = {}

def get_glow_surface(width: int, height: int, color: Tuple[int, int, int], radius: int = 8, alpha: int = 50) -> pygame.Surface:
    """Generate or retrieve cached glow halo surface."""
    key = (width, height, color, radius, alpha)
    if key in _glow_cache:
        return _glow_cache[key]
    
    # Create surface with padding for the glow blur
    surf = pygame.Surface((width + radius * 2, height + radius * 2), pygame.SRCALPHA)
    for i in range(radius, 0, -2):
        layer_alpha = int(alpha * (1.0 - (i / radius) ** 0.5))
        rect = pygame.Rect(radius - i, radius - i, width + i * 2, height + i * 2)
        pygame.draw.rect(surf, (color[0], color[1], color[2], layer_alpha), rect, border_radius=radius + 4)
    
    if len(_glow_cache) > 200:
        _glow_cache.clear()
    _glow_cache[key] = surf
    return surf

def draw_soft_shadow(surface: pygame.Surface, rect: pygame.Rect, radius: int = 6, offset_y: int = 4) -> None:
    """Render a subtle soft ambient occlusion drop shadow."""
    shadow_rect = pygame.Rect(rect.x + 2, rect.y + offset_y, rect.width - 4, rect.height)
    shadow_surf = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
    pygame.draw.rect(shadow_surf, (0, 0, 0, 90), shadow_surf.get_rect(), border_radius=radius)
    surface.blit(shadow_surf, shadow_rect.topleft)

def draw_gradient_rect(surface: pygame.Surface, rect: pygame.Rect, color1: Tuple[int, int, int], color2: Tuple[int, int, int]) -> None:
    """Draw a smooth vertical gradient rectangle."""
    grad_surf = pygame.Surface((rect.width, rect.height))
    for y in range(rect.height):
        ratio = y / max(1, rect.height - 1)
        r = int(color1[0] + (color2[0] - color1[0]) * ratio)
        g = int(color1[1] + (color2[1] - color1[1]) * ratio)
        b = int(color1[2] + (color2[2] - color1[2]) * ratio)
        pygame.draw.line(grad_surf, (r, g, b), (0, y), (rect.width, y))
    surface.blit(grad_surf, rect.topleft)
