"""Main application entry point for TIME SHIFT – Escape the Timeline.

Features Neon Cyberpunk & Modern Pixel Art graphics, smooth character/box
interpolations, timeline waves, procedural audio, particle systems, and
non-blocking screen transitions.
"""
import math
import sys
from pathlib import Path
from typing import Optional, Tuple
import pygame

from apps.sokoban.game import SokobanGame
from apps.sokoban.particles import ParticleSystem
from apps.sokoban.renderer import Renderer
from apps.sokoban.save_manager import SaveManager
from apps.sokoban.sound import get_sound_manager
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
    COLOR_GREEN,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    COLOR_DISABLED,
    get_glow_surface,
    draw_soft_shadow,
    ease_out_quad,
)
from apps.sokoban.ui import ScreenTransition, TimelineBar
from apps.sokoban.widgets import Button, Slider, ToggleSwitch

SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 720
FPS = 60


class TimeShiftApp:
    """Manages display, state machine, inputs, and render loop for Time Shift."""

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("TIME SHIFT – Escape the Timeline")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()

        # Fonts with full Vietnamese Unicode support
        self.font_logo = pygame.font.SysFont(["Segoe UI", "Arial", "Tahoma"], 52, bold=True)
        self.font_credits = pygame.font.SysFont(["Segoe UI", "Arial", "Tahoma"], 20, bold=True)
        self.font_title = pygame.font.SysFont(["Segoe UI", "Arial", "Tahoma"], 36, bold=True)
        self.font_heading = pygame.font.SysFont(["Segoe UI", "Arial", "Tahoma"], 24, bold=True)
        self.font_ui = pygame.font.SysFont(["Segoe UI", "Arial", "Tahoma"], 18, bold=True)
        self.font_small = pygame.font.SysFont(["Segoe UI", "Arial", "Tahoma"], 15)
        self.font_mono = pygame.font.SysFont("Consolas", 16, bold=True)

        # Core systems
        self.save_manager = SaveManager()
        self.game = SokobanGame(save_manager=self.save_manager)
        self.renderer = Renderer()
        self.sound = get_sound_manager()
        self.particles = ParticleSystem()
        self.transition = ScreenTransition(duration=0.22)
        self.timeline_bar = TimelineBar(pygame.Rect(40, SCREEN_HEIGHT - 64, SCREEN_WIDTH - 80, 48))

        # Apply settings
        self._apply_loaded_settings()

        # Wire game events to animation, sounds, and particles
        self.game.on_event = self._handle_game_event

        # UI States: MAIN_MENU, LEVEL_SELECT, PLAYING, PAUSED, VICTORY, HOW_TO_PLAY, SETTINGS
        self.state = "MAIN_MENU"
        self.running = True
        self.current_level_id = 1
        self.global_time = 0.0

        # UI component groups
        self.menu_buttons = []
        self.level_select_buttons = []
        self.play_buttons = {}
        self.pause_buttons = []
        self.victory_buttons = []
        self.info_buttons = []
        self.settings_widgets = {}

        self._init_ui()

    def _apply_loaded_settings(self) -> None:
        """Apply persistent settings from save manager."""
        s = self.save_manager.settings
        self.sound.set_volume(s.get("sfx_volume", 0.8))
        self.particles.enabled = s.get("particles", True)
        self.renderer.screen_shake_enabled = s.get("screen_shake", True)
        self.renderer.glow_enabled = s.get("glow_effects", True)
        self.renderer.reduced_motion = s.get("reduced_motion", False)

    def _init_ui(self) -> None:
        """Initialize all interactive buttons and widgets."""
        btn_w, btn_h = 260, 50
        cx = SCREEN_WIDTH // 2 - btn_w // 2

        # 1. Main Menu Buttons
        self.menu_buttons = [
            Button(pygame.Rect(cx, 290, btn_w, btn_h), "PLAY GAME", self._btn_play, theme="cyan"),
            Button(pygame.Rect(cx, 355, btn_w, btn_h), "LEVEL SELECT", self._btn_level_select, theme="purple"),
            Button(pygame.Rect(cx, 420, btn_w, btn_h), "HOW TO PLAY", self._btn_how_to_play, theme="neutral"),
            Button(pygame.Rect(cx, 485, btn_w, btn_h), "SETTINGS", self._btn_settings, theme="neutral"),
            Button(pygame.Rect(cx, 550, btn_w, btn_h), "EXIT", self._btn_exit, theme="gold"),
        ]

        # 2. Gameplay Top HUD Buttons
        self.play_buttons = {
            "undo": Button(pygame.Rect(SCREEN_WIDTH - 400, 18, 90, 36), "UNDO", self._action_undo, theme="cyan"),
            "redo": Button(pygame.Rect(SCREEN_WIDTH - 302, 18, 90, 36), "REDO", self._action_redo, theme="purple"),
            "restart": Button(pygame.Rect(SCREEN_WIDTH - 204, 18, 98, 36), "RESTART", self._action_restart, theme="gold"),
            "pause": Button(pygame.Rect(SCREEN_WIDTH - 98, 18, 78, 36), "PAUSE", self._btn_pause, theme="neutral"),
        }

        # 3. Pause Menu Buttons
        pcx = SCREEN_WIDTH // 2 - btn_w // 2
        self.pause_buttons = [
            Button(pygame.Rect(pcx, 245, btn_w, btn_h), "RESUME", self._btn_resume, theme="cyan"),
            Button(pygame.Rect(pcx, 310, btn_w, btn_h), "RESTART LEVEL", self._btn_restart_from_pause, theme="gold"),
            Button(pygame.Rect(pcx, 375, btn_w, btn_h), "SETTINGS", self._btn_settings_from_pause, theme="neutral"),
            Button(pygame.Rect(pcx, 440, btn_w, btn_h), "LEVEL SELECT", self._btn_level_select, theme="purple"),
            Button(pygame.Rect(pcx, 505, btn_w, btn_h), "MAIN MENU", self._btn_main_menu, theme="neutral"),
        ]

        # 4. Victory Menu Buttons
        vcx = SCREEN_WIDTH // 2 - btn_w // 2
        self.victory_buttons = [
            Button(pygame.Rect(vcx, 360, btn_w, btn_h), "NEXT LEVEL ►", self._btn_next_level, theme="green"),
            Button(pygame.Rect(vcx, 425, btn_w, btn_h), "REPLAY LEVEL", self._action_restart, theme="cyan"),
            Button(pygame.Rect(vcx, 490, btn_w, btn_h), "LEVEL SELECT", self._btn_level_select, theme="purple"),
            Button(pygame.Rect(vcx, 555, btn_w, btn_h), "MAIN MENU", self._btn_main_menu, theme="neutral"),
        ]

        # 5. How To Play
        self.info_buttons = [
            Button(pygame.Rect(cx, 605, btn_w, btn_h), "BACK TO MENU", self._btn_main_menu, theme="cyan")
        ]

        # 6. Settings Widgets
        self._init_settings_widgets()

    def _init_settings_widgets(self) -> None:
        panel_x = 220
        self.settings_widgets = {
            "volume": Slider(pygame.Rect(panel_x + 280, 205, 180, 20), value=self.sound.sfx_volume, on_change=self._set_volume),
            "particles": ToggleSwitch(pygame.Rect(panel_x + 390, 252, 60, 28), initial_state=self.particles.enabled, on_toggle=self._toggle_particles),
            "shake": ToggleSwitch(pygame.Rect(panel_x + 390, 302, 60, 28), initial_state=self.renderer.screen_shake_enabled, on_toggle=self._toggle_shake),
            "glow": ToggleSwitch(pygame.Rect(panel_x + 390, 352, 60, 28), initial_state=self.renderer.glow_enabled, on_toggle=self._toggle_glow),
            "motion": ToggleSwitch(pygame.Rect(panel_x + 390, 402, 60, 28), initial_state=self.renderer.reduced_motion, on_toggle=self._toggle_motion),
            "reset": Button(pygame.Rect(SCREEN_WIDTH // 2 - 130, 470, 260, 42), "RESET PROGRESS", self._btn_reset_progress, theme="gold"),
            "back": Button(pygame.Rect(SCREEN_WIDTH // 2 - 130, 530, 260, 46), "BACK", self._btn_settings_back, theme="cyan"),
        }

    def _set_volume(self, val: float) -> None:
        self.sound.set_volume(val)
        self.save_manager.settings["sfx_volume"] = val
        self.save_manager.save_settings()

    def _toggle_particles(self, state: bool) -> None:
        self.particles.enabled = state
        self.save_manager.settings["particles"] = state
        self.save_manager.save_settings()

    def _toggle_shake(self, state: bool) -> None:
        self.renderer.screen_shake_enabled = state
        self.save_manager.settings["screen_shake"] = state
        self.save_manager.save_settings()

    def _toggle_glow(self, state: bool) -> None:
        self.renderer.glow_enabled = state
        self.save_manager.settings["glow_effects"] = state
        self.save_manager.save_settings()

    def _toggle_motion(self, state: bool) -> None:
        self.renderer.reduced_motion = state
        self.save_manager.settings["reduced_motion"] = state
        self.save_manager.save_settings()

    def _rebuild_level_select_buttons(self) -> None:
        """Rebuild stage cards grid with smooth hover cards, stars, and best records."""
        self.level_select_buttons = []
        cols = 5
        card_w, card_h = 135, 115
        spacing_x = 28
        spacing_y = 28
        total_w = cols * card_w + (cols - 1) * spacing_x
        start_x = (SCREEN_WIDTH - total_w) // 2
        start_y = 195

        for i in range(1, 11):
            col = (i - 1) % cols
            row = (i - 1) // cols
            x = start_x + col * (card_w + spacing_x)
            y = start_y + row * (card_h + spacing_y)
            is_unlocked = self.save_manager.is_level_unlocked(i)
            is_done = self.save_manager.is_level_completed(i)
            best = self.save_manager.get_best_moves(i)

            theme = "green" if is_done else ("cyan" if is_unlocked else "neutral")
            title = f"STAGE {i}" if is_unlocked else "LOCKED"
            subtext = f"Best: {best} moves" if best is not None else ("Cleared" if is_done else "")
            badge = "★" if is_done else ("" if is_unlocked else "🔒")

            btn = Button(
                pygame.Rect(x, y, card_w, card_h),
                title,
                on_click=lambda lvl=i: self._start_level_with_transition(lvl),
                theme=theme,
                enabled=is_unlocked,
                subtext=subtext,
                badge=badge,
            )
            self.level_select_buttons.append(btn)

        back_btn = Button(
            pygame.Rect(SCREEN_WIDTH // 2 - 130, 570, 260, 48),
            "BACK TO MENU",
            self._btn_main_menu,
            theme="neutral",
        )
        self.level_select_buttons.append(back_btn)

    def _handle_game_event(self, event_type: str, kwargs: dict) -> None:
        """Handle game callbacks and dispatch visual/sound effects."""
        tile_size = self.renderer.calculate_tile_size(
            SCREEN_WIDTH, SCREEN_HEIGHT,
            self.game.level.width if self.game.level else 8,
            self.game.level.height if self.game.level else 8
        )
        board_w = (self.game.level.width if self.game.level else 8) * tile_size
        board_h = (self.game.level.height if self.game.level else 8) * tile_size
        offset_x = (SCREEN_WIDTH - board_w) // 2
        offset_y = 75 + (SCREEN_HEIGHT - 150 - board_h) // 2

        if event_type == "move":
            from_pos = kwargs.get("from_pos")
            to_pos = kwargs.get("to_pos")
            box_from = kwargs.get("box_from")
            box_to = kwargs.get("box_to")
            pushed = kwargs.get("pushed_box", False)

            if from_pos and to_pos:
                self.renderer.trigger_move_animation(from_pos, to_pos, box_from, box_to, is_undo=False)

            if pushed and box_to:
                self.sound.play("push")
                self.renderer.trigger_screen_shake(magnitude=2.5, duration=0.1)
                bx = offset_x + box_to[0] * tile_size + tile_size // 2
                by = offset_y + box_to[1] * tile_size + tile_size // 2
                self.particles.emit_sparks(bx, by, count=14, color=COLOR_GOLD)
                if self.game.level and (box_to in self.game.level.targets):
                    self.sound.play("goal")
                    self.particles.emit_goal_burst(bx, by)
            else:
                self.sound.play("step")

        elif event_type == "undo":
            from_pos = kwargs.get("from_pos")
            to_pos = kwargs.get("to_pos")
            box_from = kwargs.get("box_from")
            box_to = kwargs.get("box_to")

            if from_pos and to_pos:
                self.renderer.trigger_move_animation(from_pos, to_pos, box_from, box_to, is_undo=True)

            self.sound.play("rewind")
            self.renderer.trigger_rewind_wave()
            if self.game.player:
                px = offset_x + self.game.player.x * tile_size + tile_size // 2
                py = offset_y + self.game.player.y * tile_size + tile_size // 2
                self.particles.emit_rewind_burst(px, py)

        elif event_type == "fast_forward":
            self.sound.play("redo")
            self.renderer.trigger_redo_wave()
            if self.game.player:
                px = offset_x + self.game.player.x * tile_size + tile_size // 2
                py = offset_y + self.game.player.y * tile_size + tile_size // 2
                self.particles.emit_redo_burst(px, py)

        elif event_type == "bump":
            self.sound.play("bump")
            self.renderer.trigger_screen_shake(magnitude=3.0, duration=0.12)

        elif event_type == "victory":
            self.sound.play("victory")
            self.particles.emit_victory_burst(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

    # -----------------------------------------------------
    # ACTION WRAPPERS
    # -----------------------------------------------------
    def _action_undo(self) -> None:
        if self.game.undo():
            if self.state == "VICTORY" and not self.game.is_won:
                self.state = "PLAYING"

    def _action_redo(self) -> None:
        if self.game.redo():
            if self.game.is_won:
                self.state = "VICTORY"

    def _action_restart(self) -> None:
        self.game.restart_level()
        if self.state == "VICTORY":
            self.state = "PLAYING"

    # -----------------------------------------------------
    # TRANSITIONS & NAVIGATION
    # -----------------------------------------------------
    def _change_state_with_transition(self, new_state: str, action: Optional[callable] = None) -> None:
        def on_mid():
            if action:
                action()
            self.state = new_state
        self.transition.start(new_state, on_midpoint=on_mid)

    def _btn_play(self) -> None:
        unlocked = self.save_manager.progress.get("unlocked_levels", [1])
        target_lvl = max(unlocked) if unlocked else 1
        self._start_level_with_transition(target_lvl)

    def _start_level_with_transition(self, level_id: int) -> None:
        def load():
            self.current_level_id = level_id
            self.game.load_level(level_id)
        self._change_state_with_transition("PLAYING", action=load)

    def _btn_level_select(self) -> None:
        self._rebuild_level_select_buttons()
        self._change_state_with_transition("LEVEL_SELECT")

    def _btn_how_to_play(self) -> None:
        self._change_state_with_transition("HOW_TO_PLAY")

    def _btn_settings(self) -> None:
        self._previous_settings_state = self.state
        self._change_state_with_transition("SETTINGS")

    def _btn_settings_from_pause(self) -> None:
        self._previous_settings_state = "PAUSED"
        self._change_state_with_transition("SETTINGS")

    def _btn_settings_back(self) -> None:
        target = getattr(self, "_previous_settings_state", "MAIN_MENU")
        self._change_state_with_transition(target)

    def _btn_exit(self) -> None:
        self.running = False

    def _btn_pause(self) -> None:
        self.state = "PAUSED"

    def _btn_resume(self) -> None:
        self.state = "PLAYING"

    def _btn_restart_from_pause(self) -> None:
        self.game.restart_level()
        self.state = "PLAYING"

    def _btn_main_menu(self) -> None:
        self._change_state_with_transition("MAIN_MENU")

    def _btn_next_level(self) -> None:
        if self.current_level_id < 10:
            self._start_level_with_transition(self.current_level_id + 1)
        else:
            self._btn_level_select()

    def _btn_reset_progress(self) -> None:
        self.save_manager.progress = {
            "unlocked_levels": [1],
            "completed_levels": [],
            "best_moves": {},
        }
        self.save_manager.save_progress()
        self._rebuild_level_select_buttons()

    # -----------------------------------------------------
    # MAIN RUN LOOP
    # -----------------------------------------------------
    def run(self) -> None:
        """Main game loop running at rock solid 60 FPS."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)  # Cap large delta spikes
            self.global_time += dt
            mouse_pos = pygame.mouse.get_pos()

            self._handle_events()
            self._update(dt, mouse_pos)
            self._draw()

        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                ctrl = bool(mods & pygame.KMOD_CTRL)
                shift = bool(mods & pygame.KMOD_SHIFT)

                # ESC Key Handling
                if event.key == pygame.K_ESCAPE:
                    if self.state == "PLAYING":
                        self.state = "PAUSED"
                        self.sound.play("hover")
                    elif self.state == "PAUSED":
                        self.state = "PLAYING"
                    elif self.state in ("LEVEL_SELECT", "HOW_TO_PLAY"):
                        self._btn_main_menu()
                    elif self.state == "SETTINGS":
                        self._btn_settings_back()
                    return

                # In-Game Hotkeys (Active in PLAYING and VICTORY)
                if self.state in ("PLAYING", "VICTORY"):
                    # Undo: Ctrl + Z
                    if ctrl and not shift and event.key == pygame.K_z:
                        self._action_undo()
                        return

                    # Redo: Ctrl + Y or Ctrl + Shift + Z
                    if (ctrl and event.key == pygame.K_y) or (ctrl and shift and event.key == pygame.K_z):
                        self._action_redo()
                        return

                    # Restart: R
                    if event.key == pygame.K_r:
                        self._action_restart()
                        return

                if self.state == "PLAYING":
                    # Movement Input
                    dx, dy = 0, 0
                    if event.key in (pygame.K_w, pygame.K_UP):
                        dx, dy = 0, -1
                    elif event.key in (pygame.K_s, pygame.K_DOWN):
                        dx, dy = 0, 1
                    elif event.key in (pygame.K_a, pygame.K_LEFT):
                        dx, dy = -1, 0
                    elif event.key in (pygame.K_d, pygame.K_RIGHT):
                        dx, dy = 1, 0

                    if dx != 0 or dy != 0:
                        self.game.move_player(dx, dy)
                        if self.game.is_won:
                            self.state = "VICTORY"
                        return

            # Interactive UI dispatching
            if self.state == "MAIN_MENU":
                for btn in self.menu_buttons:
                    btn.handle_event(event)
            elif self.state == "LEVEL_SELECT":
                for btn in self.level_select_buttons:
                    btn.handle_event(event)
            elif self.state == "PLAYING":
                for btn in self.play_buttons.values():
                    btn.handle_event(event)
            elif self.state == "PAUSED":
                for btn in self.pause_buttons:
                    btn.handle_event(event)
            elif self.state == "VICTORY":
                for btn in self.victory_buttons:
                    btn.handle_event(event)
            elif self.state == "HOW_TO_PLAY":
                for btn in self.info_buttons:
                    btn.handle_event(event)
            elif self.state == "SETTINGS":
                for w in self.settings_widgets.values():
                    w.handle_event(event)

    def _update(self, dt: float, mouse_pos: Tuple[int, int]) -> None:
        self.particles.update(dt)
        self.renderer.update(dt)
        self.transition.update(dt)

        # Ambient dust in menu states
        if self.state in ("MAIN_MENU", "LEVEL_SELECT", "SETTINGS", "HOW_TO_PLAY"):
            self.particles.emit_ambient_dust(SCREEN_WIDTH, SCREEN_HEIGHT, count=1)

        # Update buttons & widget animations
        if self.state == "MAIN_MENU":
            for btn in self.menu_buttons:
                btn.update(mouse_pos, dt)
        elif self.state == "LEVEL_SELECT":
            for btn in self.level_select_buttons:
                btn.update(mouse_pos, dt)
        elif self.state == "PLAYING":
            self.play_buttons["undo"].enabled = self.game.can_undo()
            self.play_buttons["redo"].enabled = self.game.can_redo()
            for btn in self.play_buttons.values():
                btn.update(mouse_pos, dt)
        elif self.state == "PAUSED":
            for btn in self.pause_buttons:
                btn.update(mouse_pos, dt)
        elif self.state == "VICTORY":
            self.victory_buttons[0].enabled = (self.current_level_id < 10)
            for btn in self.victory_buttons:
                btn.update(mouse_pos, dt)
        elif self.state == "HOW_TO_PLAY":
            for btn in self.info_buttons:
                btn.update(mouse_pos, dt)
        elif self.state == "SETTINGS":
            for w in self.settings_widgets.values():
                if hasattr(w, "update"):
                    w.update(mouse_pos, dt) if isinstance(w, Button) else w.update(dt)

    def _draw(self) -> None:
        self.screen.fill(COLOR_BG)

        # Moving Cyber Perspective Grid Background
        self._draw_ambient_cyber_grid()

        if self.state == "MAIN_MENU":
            self._draw_main_menu()
        elif self.state == "LEVEL_SELECT":
            self._draw_level_select()
        elif self.state == "PLAYING":
            self._draw_gameplay()
        elif self.state == "PAUSED":
            self._draw_gameplay()
            self._draw_pause_overlay()
        elif self.state == "VICTORY":
            self._draw_gameplay()
            self._draw_victory_overlay()
        elif self.state == "HOW_TO_PLAY":
            self._draw_how_to_play()
        elif self.state == "SETTINGS":
            self._draw_settings()

        # Particles & non-blocking screen transition
        self.particles.draw(self.screen)
        self.transition.draw(self.screen)
        pygame.display.flip()

    # -----------------------------------------------------
    # SCREEN RENDERERS
    # -----------------------------------------------------
    def _draw_ambient_cyber_grid(self) -> None:
        """Render a subtle ambient futuristic grid with flowing light pulse."""
        grid_col = (14, 21, 38)
        flow_offset = int((self.global_time * 16.0) % 40)
        for x in range(0, SCREEN_WIDTH + 40, 40):
            pygame.draw.line(self.screen, grid_col, (x, 0), (x, SCREEN_HEIGHT))
        for y in range(flow_offset - 40, SCREEN_HEIGHT + 40, 40):
            pygame.draw.line(self.screen, grid_col, (0, y), (SCREEN_WIDTH, y))

    def _draw_main_menu(self) -> None:
        pulse = 0.5 + 0.5 * math.sin(self.global_time * 3.5)

        # 1. Main Title Logo with Glow Shadow
        logo_y = 110
        if self.renderer.glow_enabled:
            glow_surf = self.font_logo.render("TIME SHIFT", True, COLOR_PURPLE)
            self.screen.blit(glow_surf, (SCREEN_WIDTH // 2 - glow_surf.get_width() // 2, logo_y - 2))

        logo_surf = self.font_logo.render("TIME SHIFT", True, COLOR_CYAN)
        logo_rect = logo_surf.get_rect(center=(SCREEN_WIDTH // 2, logo_y))
        self.screen.blit(logo_surf, logo_rect)

        # 2. Traveling light line beneath logo
        line_w = 360
        line_x = SCREEN_WIDTH // 2 - line_w // 2
        line_y = logo_rect.bottom + 8
        pygame.draw.line(self.screen, COLOR_BORDER, (line_x, line_y), (line_x + line_w, line_y), 2)
        beam_x = line_x + int(((self.global_time * 0.4) % 1.0) * line_w)
        pygame.draw.circle(self.screen, COLOR_CYAN, (beam_x, line_y), 3)

        # 3. Group Credits (Centered immediately below title)
        credits_surf = self.font_credits.render("Dự án hoàn thiện của Huy - Nhân - Cường", True, COLOR_TEXT_MAIN)
        credits_rect = credits_surf.get_rect(center=(SCREEN_WIDTH // 2, line_y + 30))
        self.screen.blit(credits_surf, credits_rect)

        # 4. Subtitle
        sub = self.font_small.render("— ESCAPE THE TIMELINE —", True, COLOR_CYAN)
        sub_rect = sub.get_rect(center=(SCREEN_WIDTH // 2, line_y + 64))
        self.screen.blit(sub, sub_rect)

        # 5. Draw Menu Buttons
        for btn in self.menu_buttons:
            btn.draw(self.screen, self.font_ui)

    def _draw_level_select(self) -> None:
        title = self.font_title.render("SELECT TIMELINE ANOMALY", True, COLOR_CYAN)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 85)))

        sub = self.font_small.render("Stabilize previous timeline sectors to unlock deeper temporal rifts.", True, COLOR_TEXT_MUTED)
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, 130)))

        for btn in self.level_select_buttons:
            btn.draw(self.screen, self.font_ui, self.font_small)

    def _draw_gameplay(self) -> None:
        if self.game.level is None or self.game.player is None:
            return

        # 1. Top HUD Bar
        hud_rect = pygame.Rect(40, 14, SCREEN_WIDTH - 80, 50)
        draw_soft_shadow(self.screen, hud_rect, radius=8, offset_y=3)
        pygame.draw.rect(self.screen, COLOR_SURFACE, hud_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_BORDER, hud_rect, width=1, border_radius=8)

        # Level name
        lvl_name = f"{self.game.level.name}"
        name_surf = self.font_ui.render(lvl_name, True, COLOR_CYAN)
        self.screen.blit(name_surf, (hud_rect.x + 18, hud_rect.y + 14))

        # Move Counter
        moves_str = f"MOVES: {self.game.move_count}"
        moves_surf = self.font_mono.render(moves_str, True, COLOR_TEXT_MAIN)
        self.screen.blit(moves_surf, (hud_rect.x + 280, hud_rect.y + 15))

        # Best Record
        best = self.save_manager.get_best_moves(self.game.level.id)
        best_str = f"BEST: {best if best is not None else '--'}"
        best_surf = self.font_mono.render(best_str, True, COLOR_GOLD)
        self.screen.blit(best_surf, (hud_rect.x + 400, hud_rect.y + 15))

        # Draw HUD Buttons
        for btn in self.play_buttons.values():
            btn.draw(self.screen, self.font_small)

        # 2. Centered Game Board
        tile_size = self.renderer.calculate_tile_size(
            SCREEN_WIDTH, SCREEN_HEIGHT, self.game.level.width, self.game.level.height
        )
        board_w = self.game.level.width * tile_size
        board_h = self.game.level.height * tile_size
        offset_x = (SCREEN_WIDTH - board_w) // 2
        offset_y = 75 + (SCREEN_HEIGHT - 150 - board_h) // 2

        self.renderer.render_board(
            self.screen,
            self.game.level,
            self.game.player,
            offset_x,
            offset_y,
            tile_size,
        )

        # 3. Bottom Timeline Bar
        self.timeline_bar.draw(
            self.screen,
            self.font_small,
            self.game.history_manager.undo_count,
            self.game.history_manager.redo_count,
            self.game.history_manager.get_timeline(),
        )

    def _draw_pause_overlay(self) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 10, 22, 215))
        self.screen.blit(overlay, (0, 0))

        # Glass Panel
        modal_rect = pygame.Rect(SCREEN_WIDTH // 2 - 200, 160, 400, 430)
        draw_soft_shadow(self.screen, modal_rect, radius=12, offset_y=6)
        pygame.draw.rect(self.screen, COLOR_SURFACE, modal_rect, border_radius=12)
        pygame.draw.rect(self.screen, COLOR_BORDER_BRIGHT, modal_rect, width=1, border_radius=12)

        title = self.font_title.render("TIMELINE PAUSED", True, COLOR_CYAN)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 205)))

        for btn in self.pause_buttons:
            btn.draw(self.screen, self.font_ui)

    def _draw_victory_overlay(self) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 10, 22, 225))
        self.screen.blit(overlay, (0, 0))

        modal_rect = pygame.Rect(SCREEN_WIDTH // 2 - 220, 100, 440, 530)
        draw_soft_shadow(self.screen, modal_rect, radius=12, offset_y=8)
        pygame.draw.rect(self.screen, COLOR_SURFACE, modal_rect, border_radius=12)
        pygame.draw.rect(self.screen, COLOR_GREEN, modal_rect, width=2, border_radius=12)

        title = self.font_title.render("TIMELINE STABILIZED!", True, COLOR_GREEN)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 150)))

        sub = self.font_ui.render(f"Sector Cleared in {self.game.move_count} moves!", True, COLOR_TEXT_MAIN)
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, 205)))

        best = self.save_manager.get_best_moves(self.current_level_id)
        is_new_record = (best is not None and self.game.move_count <= best)
        rec_color = COLOR_GOLD if is_new_record else COLOR_TEXT_MUTED
        rec_str = f"Personal Best: {best} moves" + (" (NEW RECORD!)" if is_new_record else "")
        rec_surf = self.font_small.render(rec_str, True, rec_color)
        self.screen.blit(rec_surf, rec_surf.get_rect(center=(SCREEN_WIDTH // 2, 245)))

        tip = self.font_small.render("(Tip: Press Ctrl+Z to undo and explore alternate moves!)", True, COLOR_CYAN)
        self.screen.blit(tip, tip.get_rect(center=(SCREEN_WIDTH // 2, 285)))

        for btn in self.victory_buttons:
            btn.draw(self.screen, self.font_ui)

    def _draw_how_to_play(self) -> None:
        title = self.font_title.render("HOW TO PLAY: TIME SHIFT", True, COLOR_CYAN)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 70)))

        panel = pygame.Rect(120, 115, SCREEN_WIDTH - 240, 460)
        draw_soft_shadow(self.screen, panel, radius=12, offset_y=6)
        pygame.draw.rect(self.screen, COLOR_SURFACE, panel, border_radius=12)
        pygame.draw.rect(self.screen, COLOR_BORDER, panel, width=1, border_radius=12)

        rules = [
            ("MISSION OBJECTIVE", "Push all Chrono-Crates (Amber) onto the glowing Temporal Target Pads (Green)."),
            ("SOKOBAN RULES", "• You can only push ONE crate at a time. No pulling is allowed."),
            ("", "• Crates cannot be pushed into walls or other crates."),
            ("", "• Blocked moves do not consume turns or corrupt history."),
            ("DUAL-STACK TIME TRAVEL", "• Every valid action is captured atomically in the Undo/Redo Engine."),
            ("", "• Press Ctrl+Z or click UNDO to shift time backward."),
            ("", "• Press Ctrl+Y or click REDO to shift time forward."),
            ("CONTROLS", "• W / A / S / D or Arrow Keys: Move / Push"),
            ("", "• Ctrl + Z: Undo  |  Ctrl + Y or Ctrl+Shift+Z: Redo"),
            ("", "• R: Restart Level  |  ESC: Pause Menu"),
        ]

        cur_y = panel.y + 25
        for header, line in rules:
            if header:
                h_surf = self.font_ui.render(header, True, COLOR_PURPLE)
                self.screen.blit(h_surf, (panel.x + 36, cur_y))
                cur_y += 26
            if line:
                l_surf = self.font_small.render(line, True, COLOR_TEXT_MAIN)
                self.screen.blit(l_surf, (panel.x + 36, cur_y))
                cur_y += 24
            if not header and not line.startswith("•"):
                cur_y += 6

        for btn in self.info_buttons:
            btn.draw(self.screen, self.font_ui)

    def _draw_settings(self) -> None:
        title = self.font_title.render("SETTINGS & ACCESSIBILITY", True, COLOR_CYAN)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 85)))

        panel = pygame.Rect(180, 145, SCREEN_WIDTH - 360, 395)
        draw_soft_shadow(self.screen, panel, radius=12, offset_y=6)
        pygame.draw.rect(self.screen, COLOR_SURFACE, panel, border_radius=12)
        pygame.draw.rect(self.screen, COLOR_BORDER, panel, width=1, border_radius=12)

        # Labels
        labels = [
            ("Master Audio Volume", 205),
            ("Ambient Particle FX", 255),
            ("Screen Shake Impacts", 305),
            ("Neon Glow Lighting", 355),
            ("Reduced Motion (Instant)", 405),
        ]
        for text, y in labels:
            lbl = self.font_ui.render(text, True, COLOR_TEXT_MAIN)
            self.screen.blit(lbl, (panel.x + 36, y))

        # Volume percentage indicator
        vol_pct = int(self.sound.sfx_volume * 100)
        vol_txt = self.font_mono.render(f"{vol_pct}%", True, COLOR_CYAN)
        self.screen.blit(vol_txt, (panel.x + 230, 205))

        # Draw Settings Widgets
        for w in self.settings_widgets.values():
            if isinstance(w, Button):
                w.draw(self.screen, self.font_ui)
            else:
                w.draw(self.screen)


def main() -> None:
    app = TimeShiftApp()
    app.run()


if __name__ == "__main__":
    main()
