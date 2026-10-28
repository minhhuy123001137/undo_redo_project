"""High-performance Particle Engine with cached surfaces and delta-time simulation."""
import math
import random
from typing import Dict, List, Optional, Tuple
import pygame
from apps.sokoban.theme import (
    COLOR_CYAN,
    COLOR_PURPLE,
    COLOR_GOLD,
    COLOR_GREEN,
    COLOR_TEXT_MAIN,
)

# Surface cache to avoid creating surfaces every frame
_circle_cache: Dict[Tuple[int, int, int, int, int], pygame.Surface] = {}


def _get_cached_circle(color: Tuple[int, int, int], radius: int, alpha: int) -> pygame.Surface:
    """Retrieve pre-rendered alpha circle surface."""
    # Quantize alpha and radius to keep cache compact
    q_alpha = max(0, min(255, (alpha // 8) * 8))
    q_radius = max(1, min(40, radius))
    key = (color[0], color[1], color[2], q_radius, q_alpha)
    if key in _circle_cache:
        return _circle_cache[key]

    surf = pygame.Surface((q_radius * 2 + 2, q_radius * 2 + 2), pygame.SRCALPHA)
    pygame.draw.circle(
        surf,
        (color[0], color[1], color[2], q_alpha),
        (q_radius + 1, q_radius + 1),
        q_radius,
    )
    if len(_circle_cache) > 400:
        _circle_cache.clear()
    _circle_cache[key] = surf
    return surf


class Particle:
    """Lightweight 2D particle with velocity, drag, and decay."""

    __slots__ = ("x", "y", "vx", "vy", "color", "radius", "lifetime", "max_lifetime", "drag", "gravity", "wave_freq", "wave_amp")

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        color: Tuple[int, int, int],
        radius: float,
        lifetime: float,
        drag: float = 0.98,
        gravity: float = 0.0,
        wave_freq: float = 0.0,
        wave_amp: float = 0.0,
    ) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.radius = radius
        self.lifetime = lifetime
        self.max_lifetime = max(0.01, lifetime)
        self.drag = drag
        self.gravity = gravity
        self.wave_freq = wave_freq
        self.wave_amp = wave_amp

    def update(self, dt: float) -> bool:
        self.lifetime -= dt
        if self.lifetime <= 0:
            return False

        self.vx *= self.drag
        self.vy = self.vy * self.drag + self.gravity * dt

        if self.wave_freq > 0:
            self.x += (self.vx + math.sin(self.lifetime * self.wave_freq) * self.wave_amp) * dt
        else:
            self.x += self.vx * dt
        self.y += self.vy * dt
        return True

    def draw(self, surface: pygame.Surface) -> None:
        if self.lifetime <= 0:
            return
        progress = self.lifetime / self.max_lifetime
        alpha = int(255 * progress)
        curr_radius = max(1, int(self.radius * (0.4 + 0.6 * progress)))

        circle_surf = _get_cached_circle(self.color, curr_radius, alpha)
        surface.blit(circle_surf, (int(self.x - curr_radius), int(self.y - curr_radius)))


class ParticleSystem:
    """Particle manager with capped density and specialized emitters."""

    def __init__(self, max_particles: int = 250, enabled: bool = True) -> None:
        self.particles: List[Particle] = []
        self.max_particles = max_particles
        self.enabled = enabled

    def clear(self) -> None:
        self.particles.clear()

    def update(self, dt: float) -> None:
        if not self.enabled and not self.particles:
            return
        # In-place filtering for speed
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw(self, surface: pygame.Surface) -> None:
        if not self.enabled and not self.particles:
            return
        for p in self.particles:
            p.draw(surface)

    def _can_emit(self, count: int) -> bool:
        return self.enabled and (len(self.particles) + count <= self.max_particles)

    # 1. Ambient Background Dust
    def emit_ambient_dust(self, screen_w: int, screen_h: int, count: int = 1) -> None:
        if not self._can_emit(count):
            return
        for _ in range(count):
            x = random.uniform(0, screen_w)
            y = random.uniform(0, screen_h)
            vx = random.uniform(-10, 10)
            vy = random.uniform(-18, -6)  # Gently floats upward
            color = random.choice([COLOR_CYAN, COLOR_PURPLE, (140, 160, 200)])
            radius = random.uniform(1.5, 3.0)
            lifetime = random.uniform(4.0, 8.0)
            self.particles.append(Particle(x, y, vx, vy, color, radius, lifetime, drag=0.99, wave_freq=2.0, wave_amp=12.0))

    # 2. Contact Sparks (Box Pushing / Impact)
    def emit_sparks(self, x: float, y: float, count: int = 12, color: Tuple[int, int, int] = COLOR_GOLD) -> None:
        if not self._can_emit(count):
            return
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 180)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            radius = random.uniform(2.0, 4.0)
            lifetime = random.uniform(0.2, 0.45)
            self.particles.append(Particle(x, y, vx, vy, color, radius, lifetime, drag=0.92))

    # 3. Goal Pad Activated Burst
    def emit_goal_burst(self, cx: float, cy: float) -> None:
        if not self._can_emit(24):
            return
        for _ in range(24):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(60, 220)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            radius = random.uniform(2.5, 5.0)
            color = random.choice([COLOR_GREEN, COLOR_CYAN, (200, 255, 230)])
            lifetime = random.uniform(0.35, 0.65)
            self.particles.append(Particle(cx, cy, vx, vy, color, radius, lifetime, drag=0.93))

    # 4. Rewind (Undo) Wave & Cyan Vortex
    def emit_rewind_burst(self, cx: float, cy: float) -> None:
        if not self._can_emit(30):
            return
        for _ in range(30):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(40, 140)
            # Spawn outward, velocity pointing inward (rewind suction effect)
            x = cx + math.cos(angle) * dist
            y = cy + math.sin(angle) * dist
            vx = -math.cos(angle + 0.3) * random.uniform(100, 240)
            vy = -math.sin(angle + 0.3) * random.uniform(100, 240)
            color = random.choice([COLOR_CYAN, (180, 245, 255), COLOR_PURPLE])
            lifetime = random.uniform(0.25, 0.5)
            self.particles.append(Particle(x, y, vx, vy, color, radius=3.5, lifetime=lifetime, drag=0.95))

    # 5. Redo (Fast-Forward) Wave
    def emit_redo_burst(self, cx: float, cy: float) -> None:
        if not self._can_emit(25):
            return
        for _ in range(25):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(80, 220)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            color = random.choice([COLOR_PURPLE, COLOR_GOLD, (240, 200, 255)])
            lifetime = random.uniform(0.3, 0.55)
            self.particles.append(Particle(cx, cy, vx, vy, color, radius=3.5, lifetime=lifetime, drag=0.92))

    # 6. Victory Celebration Fireworks
    def emit_victory_burst(self, cx: float, cy: float) -> None:
        if not self._can_emit(45):
            return
        colors = [COLOR_CYAN, COLOR_PURPLE, COLOR_GOLD, COLOR_GREEN, (255, 255, 255)]
        for _ in range(45):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(90, 320)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            radius = random.uniform(3.0, 6.0)
            color = random.choice(colors)
            lifetime = random.uniform(0.5, 1.0)
            self.particles.append(Particle(cx, cy, vx, vy, color, radius, lifetime, drag=0.94, gravity=80.0))
