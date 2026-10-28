"""High-performance procedural pixel-art renderer for Time Shift with smooth animations.

Handles 3D extruded walls, pulsing energy targets, squash/stretch boxes,
smooth player interpolation, ghost trails, and screen effects.
"""
import math
import random
import time
from typing import Dict, List, Optional, Set, Tuple
import pygame

from apps.sokoban.level import Level
from apps.sokoban.player import Player
from apps.sokoban.theme import (
    COLOR_BG,
    COLOR_SURFACE,
    COLOR_SURFACE_LIGHT,
    COLOR_BORDER,
    COLOR_BORDER_BRIGHT,
    COLOR_CYAN,
    COLOR_CYAN_DIM,
    COLOR_PURPLE,
    COLOR_GOLD,
    COLOR_GOLD_LIGHT,
    COLOR_GOLD_DARK,
    COLOR_GREEN,
    COLOR_GREEN_LIGHT,
    COLOR_TEXT_MAIN,
    COLOR_SHADOW,
    ease_out_quad,
    get_glow_surface,
    lerp,
    lerp_color,
)

# Visual Constants
FLOOR_DARK = (14, 20, 36)
FLOOR_LIGHT = (18, 25, 45)
FLOOR_LINE = (25, 35, 60)

WALL_TOP = (45, 60, 88)
WALL_FRONT = (26, 36, 56)
WALL_BEVEL = (65, 85, 120)
WALL_NEON = COLOR_PURPLE

BOX_BODY_GOLD = (195, 105, 12)
BOX_LIGHT_GOLD = COLOR_GOLD_LIGHT
BOX_BORDER_GOLD = (251, 191, 36)

BOX_BODY_GREEN = (16, 128, 70)
BOX_LIGHT_GREEN = COLOR_GREEN_LIGHT
BOX_BORDER_GREEN = (52, 211, 153)

PLAYER_CLOAK = (40, 38, 110)
PLAYER_HOOD = (60, 52, 170)
PLAYER_VISOR = COLOR_CYAN


class BoxAnimation:
    """Tracks smooth sliding and squash/stretch for a pushed box."""

    def __init__(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int], duration: float = 0.13, is_undo: bool = False) -> None:
        self.from_pos = from_pos
        self.to_pos = to_pos
        self.duration = max(0.01, duration)
        self.time_elapsed: float = 0.0
        self.is_undo = is_undo
        self.dx = to_pos[0] - from_pos[0]
        self.dy = to_pos[1] - from_pos[1]

    @property
    def progress(self) -> float:
        return min(1.0, self.time_elapsed / self.duration)

    @property
    def is_finished(self) -> bool:
        return self.time_elapsed >= self.duration

    def update(self, dt: float) -> None:
        self.time_elapsed += dt

    def get_current_grid_pos(self) -> Tuple[float, float]:
        p = ease_out_quad(self.progress)
        gx = lerp(float(self.from_pos[0]), float(self.to_pos[0]), p)
        gy = lerp(float(self.from_pos[1]), float(self.to_pos[1]), p)
        return gx, gy

    def get_squash_stretch(self) -> Tuple[float, float]:
        """Returns (scale_x, scale_y) for organic impact deformation."""
        p = self.progress
        factor = math.sin(p * math.pi) * 0.12
        if self.dx != 0:
            return (1.0 + factor, 1.0 - factor * 0.7)
        elif self.dy != 0:
            return (1.0 - factor * 0.7, 1.0 + factor)
        return (1.0, 1.0)


class PlayerAnimation:
    """Tracks smooth movement interpolation and ghost trails for the player."""

    def __init__(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int], duration: float = 0.12, is_undo: bool = False, is_redo: bool = False) -> None:
        self.from_pos = from_pos
        self.to_pos = to_pos
        self.duration = max(0.01, duration)
        self.time_elapsed: float = 0.0
        self.is_undo = is_undo
        self.is_redo = is_redo
        self.ghost_trail: List[Tuple[float, float, float]] = []  # (x, y, alpha)

    @property
    def progress(self) -> float:
        return min(1.0, self.time_elapsed / self.duration)

    @property
    def is_finished(self) -> bool:
        return self.time_elapsed >= self.duration

    def update(self, dt: float) -> None:
        self.time_elapsed += dt
        # Add ghost trail points if undoing or redoing
        if (self.is_undo or self.is_redo) and not self.is_finished:
            gx, gy = self.get_current_grid_pos()
            self.ghost_trail.append((gx, gy, 1.0))

        # Fade ghost trail
        updated_trail = []
        for x, y, a in self.ghost_trail:
            new_a = a - dt * 4.5
            if new_a > 0.05:
                updated_trail.append((x, y, new_a))
        self.ghost_trail = updated_trail

    def get_current_grid_pos(self) -> Tuple[float, float]:
        p = ease_out_quad(self.progress)
        gx = lerp(float(self.from_pos[0]), float(self.to_pos[0]), p)
        gy = lerp(float(self.from_pos[1]), float(self.to_pos[1]), p)
        return gx, gy


class Renderer:
    """Master procedural renderer with animation state management."""

    def __init__(self) -> None:
        # Settings hooks
        self.glow_enabled: bool = True
        self.screen_shake_enabled: bool = True
        self.reduced_motion: bool = False

        # Active Animations
        self.player_anim: Optional[PlayerAnimation] = None
        self.box_anims: Dict[Tuple[int, int], BoxAnimation] = {}

        # Screen Effects
        self.shake_timer: float = 0.0
        self.shake_magnitude: float = 0.0
        self.rewind_wave_timer: float = 0.0
        self.redo_wave_timer: float = 0.0

        # Target pulse cycle
        self.global_time: float = 0.0

    def trigger_move_animation(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int], box_from: Optional[Tuple[int, int]] = None, box_to: Optional[Tuple[int, int]] = None, is_undo: bool = False, is_redo: bool = False) -> None:
        """Trigger smooth movement interpolation for player and optionally pushed box."""
        duration = 0.001 if self.reduced_motion else 0.12
        self.player_anim = PlayerAnimation(from_pos, to_pos, duration=duration, is_undo=is_undo, is_redo=is_redo)

        if box_from is not None and box_to is not None:
            box_duration = 0.001 if self.reduced_motion else 0.13
            self.box_anims[box_to] = BoxAnimation(box_from, box_to, duration=box_duration, is_undo=is_undo)

    def trigger_screen_shake(self, magnitude: float = 3.5, duration: float = 0.15) -> None:
        if self.screen_shake_enabled and not self.reduced_motion:
            self.shake_magnitude = magnitude
            self.shake_timer = duration

    def trigger_rewind_wave(self) -> None:
        self.rewind_wave_timer = 0.28
        self.trigger_screen_shake(magnitude=2.0, duration=0.12)

    def trigger_redo_wave(self) -> None:
        self.redo_wave_timer = 0.22

    def update(self, dt: float) -> None:
        self.global_time += dt

        # Update player animation
        if self.player_anim:
            self.player_anim.update(dt)
            if self.player_anim.is_finished and not self.player_anim.ghost_trail:
                self.player_anim = None

        # Update box animations
        finished_boxes = []
        for key, anim in self.box_anims.items():
            anim.update(dt)
            if anim.is_finished:
                finished_boxes.append(key)
        for key in finished_boxes:
            del self.box_anims[key]

        # Update screen timers
        if self.shake_timer > 0:
            self.shake_timer = max(0.0, self.shake_timer - dt)
        if self.rewind_wave_timer > 0:
            self.rewind_wave_timer = max(0.0, self.rewind_wave_timer - dt)
        if self.redo_wave_timer > 0:
            self.redo_wave_timer = max(0.0, self.redo_wave_timer - dt)

    def calculate_tile_size(self, screen_w: int, screen_h: int, level_w: int, level_h: int) -> int:
        """Compute optimal square tile size."""
        available_w = screen_w - 60
        available_h = screen_h - 190
        max_w = available_w // max(1, level_w)
        max_h = available_h // max(1, level_h)
        return max(32, min(76, min(max_w, max_h)))

    def render_board(
        self,
        surface: pygame.Surface,
        level: Level,
        player: Player,
        offset_x: int,
        offset_y: int,
        tile_size: int,
    ) -> None:
        """Render complete game board with 3D walls, glowing targets, and animations."""
        shake_dx, shake_dy = 0, 0
        if self.shake_timer > 0:
            decay = self.shake_timer / 0.15
            shake_dx = int(random.uniform(-1, 1) * self.shake_magnitude * decay)
            shake_dy = int(random.uniform(-1, 1) * self.shake_magnitude * decay)

        base_ox = offset_x + shake_dx
        base_oy = offset_y + shake_dy

        # 1. Floor tiles
        for y in range(level.height):
            for x in range(level.width):
                px = base_ox + x * tile_size
                py = base_oy + y * tile_size
                is_alt = (x + y) % 2 == 0
                f_color = FLOOR_LIGHT if is_alt else FLOOR_DARK
                pygame.draw.rect(surface, f_color, (px, py, tile_size, tile_size))
                pygame.draw.rect(surface, FLOOR_LINE, (px, py, tile_size, tile_size), 1)

        # 2. Target pads
        pulse = 0.5 + 0.5 * math.sin(self.global_time * 4.2)
        target_rad = int(tile_size * (0.30 + 0.04 * pulse))

        for tx, ty in level.targets:
            cpx = base_ox + tx * tile_size + tile_size // 2
            cpy = base_oy + ty * tile_size + tile_size // 2

            if self.glow_enabled:
                glow_r = int(tile_size * 0.46)
                g_surf = get_glow_surface(glow_r * 2, glow_r * 2, COLOR_GREEN, radius=8, alpha=int(45 + 35 * pulse))
                surface.blit(g_surf, (cpx - glow_r - 8, cpy - glow_r - 8))

            pygame.draw.circle(surface, (20, 80, 50), (cpx, cpy), int(tile_size * 0.38), 2)
            pygame.draw.circle(surface, COLOR_GREEN, (cpx, cpy), target_rad)
            rot = self.global_time * 2.0
            for i in range(4):
                angle = rot + i * (math.pi / 2.0)
                tx_point = cpx + math.cos(angle) * (target_rad * 0.7)
                ty_point = cpy + math.sin(angle) * (target_rad * 0.7)
                pygame.draw.circle(surface, COLOR_CYAN, (int(tx_point), int(ty_point)), 2)

            pygame.draw.circle(surface, (220, 255, 240), (cpx, cpy), max(2, int(target_rad * 0.35)))

        # 3. 3D extruded wall blocks
        bevel = max(3, tile_size // 7)
        for wx, wy in level.walls:
            px = base_ox + wx * tile_size
            py = base_oy + wy * tile_size

            shadow_rect = pygame.Rect(px + 3, py + tile_size - 4, tile_size - 6, bevel + 4)
            s_surf = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(s_surf, (0, 0, 0, 110), s_surf.get_rect(), border_radius=4)
            surface.blit(s_surf, shadow_rect.topleft)

            pygame.draw.rect(surface, WALL_FRONT, (px, py, tile_size, tile_size))
            pygame.draw.polygon(
                surface,
                WALL_TOP,
                [(px, py), (px + tile_size, py), (px + tile_size - bevel, py + bevel), (px + bevel, py + bevel)],
            )
            pygame.draw.polygon(
                surface,
                WALL_BEVEL,
                [(px, py), (px + bevel, py + bevel), (px + bevel, py + tile_size - bevel), (px, py + tile_size)],
            )
            pygame.draw.rect(
                surface,
                (20, 28, 44),
                (px + bevel, py + bevel, tile_size - 2 * bevel, tile_size - 2 * bevel),
            )
            pygame.draw.line(
                surface,
                WALL_NEON,
                (px + bevel + 2, py + bevel),
                (px + tile_size - bevel - 2, py + bevel),
                2,
            )

        # 4. Chrono-Crates
        for bx, by in level.boxes:
            if (bx, by) in self.box_anims:
                anim = self.box_anims[(bx, by)]
                gx, gy = anim.get_current_grid_pos()
                scale_x, scale_y = anim.get_squash_stretch()
                is_undo_box = anim.is_undo
            else:
                gx, gy = float(bx), float(by)
                scale_x, scale_y = 1.0, 1.0
                is_undo_box = False

            cpx = base_ox + gx * tile_size + tile_size / 2.0
            cpy = base_oy + gy * tile_size + tile_size / 2.0

            is_on_target = (bx, by) in level.targets
            self._draw_box(surface, cpx, cpy, tile_size, scale_x, scale_y, is_on_target, is_undo_box)

        # 5. Time Traveler
        if self.player_anim and not self.player_anim.is_finished:
            pgx, pgy = self.player_anim.get_current_grid_pos()
            is_undo_p = self.player_anim.is_undo
            is_redo_p = self.player_anim.is_redo
            ghost_trail = self.player_anim.ghost_trail
        else:
            pgx, pgy = float(player.x), float(player.y)
            is_undo_p = False
            is_redo_p = False
            ghost_trail = self.player_anim.ghost_trail if self.player_anim else []

        for gx, gy, alpha in ghost_trail:
            trail_cx = base_ox + gx * tile_size + tile_size / 2.0
            trail_cy = base_oy + gy * tile_size + tile_size / 2.0
            trail_color = COLOR_CYAN if is_undo_p else COLOR_PURPLE
            self._draw_player_ghost(surface, trail_cx, trail_cy, tile_size, player.facing, trail_color, alpha)

        pl_cx = base_ox + pgx * tile_size + tile_size / 2.0
        pl_cy = base_oy + pgy * tile_size + tile_size / 2.0
        self._draw_player(surface, pl_cx, pl_cy, tile_size, player.facing)

        # 6. Screen Wave Overlays
        if self.rewind_wave_timer > 0:
            alpha = int(140 * (self.rewind_wave_timer / 0.28))
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 229, 255, alpha))
            surface.blit(overlay, (0, 0))

        if self.redo_wave_timer > 0:
            alpha = int(110 * (self.redo_wave_timer / 0.22))
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((168, 85, 247, alpha))
            surface.blit(overlay, (0, 0))

    def _draw_box(
        self,
        surface: pygame.Surface,
        cx: float,
        cy: float,
        size: int,
        scale_x: float,
        scale_y: float,
        on_target: bool,
        is_undo: bool,
    ) -> None:
        margin = max(3, size // 10)
        box_w = int((size - 2 * margin) * scale_x)
        box_h = int((size - 2 * margin) * scale_y)
        bx = int(cx - box_w / 2)
        by = int(cy - box_h / 2)

        s_rect = pygame.Rect(bx + 2, by + box_h - 4, box_w - 4, 8)
        s_surf = pygame.Surface((s_rect.width, s_rect.height), pygame.SRCALPHA)
        pygame.draw.ellipse(s_surf, (0, 0, 0, 100), s_surf.get_rect())
        surface.blit(s_surf, s_rect.topleft)

        if on_target:
            body_col = BOX_BODY_GREEN
            light_col = BOX_LIGHT_GREEN
            border_col = BOX_BORDER_GREEN
            core_col = COLOR_CYAN
        else:
            body_col = BOX_BODY_GOLD
            light_col = BOX_LIGHT_GOLD
            border_col = BOX_BORDER_GOLD
            core_col = (255, 235, 160)

        pygame.draw.rect(surface, body_col, (bx, by, box_w, box_h), border_radius=6)
        pygame.draw.line(surface, light_col, (bx + 2, by + 2), (bx + box_w - 3, by + box_h - 3), 2)
        pygame.draw.line(surface, light_col, (bx + box_w - 3, by + 2), (bx + 2, by + box_h - 3), 2)
        pygame.draw.rect(surface, border_col, (bx, by, box_w, box_h), width=2, border_radius=6)

        pulse = 0.5 + 0.5 * math.sin(self.global_time * 6.5) if on_target else 0.5
        core_r = max(3, int(min(box_w, box_h) * (0.16 + 0.04 * pulse)))

        if on_target and self.glow_enabled:
            cg_surf = get_glow_surface(core_r * 4, core_r * 4, COLOR_GREEN, radius=6, alpha=int(80 * pulse))
            surface.blit(cg_surf, (int(cx - core_r * 2 - 6), int(cy - core_r * 2 - 6)))

        pygame.draw.circle(surface, core_col, (int(cx), int(cy)), core_r)
        pygame.draw.circle(surface, (255, 255, 255), (int(cx), int(cy)), max(1, core_r // 2))

    def _draw_player_ghost(
        self,
        surface: pygame.Surface,
        cx: float,
        cy: float,
        size: int,
        facing: str,
        color: Tuple[int, int, int],
        alpha: float,
    ) -> None:
        ghost_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        gcx = size // 2
        gcy = size // 2

        body_w = int(size * 0.52)
        body_h = int(size * 0.58)
        body_rect = pygame.Rect(gcx - body_w // 2, gcy - body_h // 2 + 3, body_w, body_h)
        col_alpha = (color[0], color[1], color[2], int(150 * alpha))
        pygame.draw.rect(ghost_surf, col_alpha, body_rect, border_radius=6)

        head_r = max(6, int(size * 0.22))
        pygame.draw.circle(ghost_surf, col_alpha, (gcx, gcy - int(size * 0.16)), head_r)

        surface.blit(ghost_surf, (int(cx - size // 2), int(cy - size // 2)))

    def _draw_player(
        self,
        surface: pygame.Surface,
        cx: float,
        cy: float,
        size: int,
        facing: str,
    ) -> None:
        bob = math.sin(self.global_time * 6.0) * 2.0

        sh_w = int(size * 0.55)
        sh_h = int(size * 0.22)
        sh_rect = pygame.Rect(int(cx - sh_w // 2), int(cy + size * 0.28), sh_w, sh_h)
        sh_surf = pygame.Surface((sh_w, sh_h), pygame.SRCALPHA)
        pygame.draw.ellipse(sh_surf, (0, 0, 0, 110), sh_surf.get_rect())
        surface.blit(sh_surf, sh_rect.topleft)

        if self.glow_enabled:
            halo_r = int(size * 0.45)
            h_surf = get_glow_surface(halo_r * 2, halo_r * 2, COLOR_CYAN, radius=10, alpha=35)
            surface.blit(h_surf, (int(cx - halo_r - 10), int(cy - halo_r - 10)))

        body_w = int(size * 0.54)
        body_h = int(size * 0.58)
        body_rect = pygame.Rect(int(cx - body_w // 2), int(cy - body_h // 2 + 4 + bob), body_w, body_h)
        pygame.draw.rect(surface, PLAYER_CLOAK, body_rect, border_radius=6)

        reactor_y = int(cy + 6 + bob)
        pygame.draw.circle(surface, COLOR_PURPLE, (int(cx), reactor_y), max(3, size // 8))
        pygame.draw.circle(surface, (240, 220, 255), (int(cx), reactor_y), max(1, size // 15))

        head_radius = max(8, int(size * 0.24))
        head_cy = int(cy - int(size * 0.16) + bob)
        pygame.draw.circle(surface, PLAYER_HOOD, (int(cx), head_cy), head_radius)

        visor_w = int(head_radius * 1.35)
        visor_h = max(3, int(head_radius * 0.45))

        offset_vx = 0
        offset_vy = 0
        if facing == "left":
            offset_vx = -3
        elif facing == "right":
            offset_vx = 3
        elif facing == "up":
            offset_vy = -3
        else:
            offset_vy = 2

        visor_rect = pygame.Rect(
            int(cx - visor_w // 2 + offset_vx),
            int(head_cy - visor_h // 2 + offset_vy),
            visor_w,
            visor_h,
        )
        pygame.draw.rect(surface, PLAYER_VISOR, visor_rect, border_radius=3)
        pygame.draw.rect(surface, (255, 255, 255), visor_rect, width=1, border_radius=3)
