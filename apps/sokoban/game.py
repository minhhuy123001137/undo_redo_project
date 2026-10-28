"""Sokoban core game logic and session management."""
from pathlib import Path
from typing import Callable, List, Optional
from core.history_manager import HistoryManager
from apps.sokoban.player import Player
from apps.sokoban.level import Level
from apps.sokoban.commands import MoveCommand
from apps.sokoban.save_manager import SaveManager


class SokobanGame:
    """Manages game state, active level, history manager, and rules for Time Shift."""

    def __init__(
        self,
        levels_dir: Optional[Path] = None,
        save_manager: Optional[SaveManager] = None,
        max_history: Optional[int] = 500,
    ) -> None:
        if levels_dir is None:
            levels_dir = Path(__file__).resolve().parent / "levels"
        self.levels_dir = levels_dir
        self.save_manager = save_manager or SaveManager()
        self.max_history = max_history

        self.level: Optional[Level] = None
        self.player: Optional[Player] = None
        self.history_manager: HistoryManager = HistoryManager(max_history=self.max_history)
        self.move_count: int = 0
        self.is_won: bool = False

        # Visual / sound event callbacks
        self.on_event: Optional[Callable[[str, dict], None]] = None

    def trigger_event(self, event_type: str, **kwargs) -> None:
        """Trigger an animation or sound event for the UI/renderer."""
        if self.on_event:
            self.on_event(event_type, kwargs)

    def on_move_executed(self, pushed_box: bool = False, **kwargs) -> None:
        """Called when a move is executed."""
        self.trigger_event("move", pushed_box=pushed_box, **kwargs)

    def on_move_undone(self, was_pushed: bool = False, **kwargs) -> None:
        """Called when a move is undone."""
        self.trigger_event("undo", was_pushed=was_pushed, **kwargs)

    def load_level(self, level_id: int) -> bool:
        """Load level by ID and initialize an independent HistoryManager.
        
        Returns:
            bool: True if loaded successfully, False otherwise.
        """
        filepath = self.levels_dir / f"level_{level_id:02d}.json"
        if not filepath.exists():
            return False

        self.level = Level.from_json_file(filepath)
        self.player = Player(*self.level.player_start)
        # Requirement: "Chuyển Level phải tạo lịch sử độc lập."
        self.history_manager = HistoryManager(max_history=self.max_history)
        self.move_count = 0
        self.is_won = self.level.is_completed()
        self.trigger_event("level_loaded", level_id=level_id)
        return True

    def restart_level(self) -> None:
        """Reset the current level to its starting state and clear history.
        
        Requirement: "Restart phải xóa lịch sử."
        """
        if self.level is None:
            return

        self.level.reset()
        if self.player:
            self.player.set_pos(*self.level.player_start)
            self.player.facing = "down"
        self.history_manager.clear()
        self.move_count = 0
        self.is_won = False
        self.trigger_event("restart")

    def move_player(self, dx: int, dy: int) -> bool:
        """Attempt to move the player in the specified direction.
        
        Returns:
            bool: True if move was valid and recorded, False otherwise.
        """
        if self.level is None or self.player is None:
            return False

        cmd = MoveCommand(self, dx, dy)
        success = self.history_manager.execute(cmd)
        if not success:
            self.trigger_event("bump")
            return False

        # Check win condition
        now_won = self.level.is_completed()
        if now_won and not self.is_won:
            self.is_won = True
            next_lvl = self.level.id + 1 if self.level.id < 10 else None
            self.save_manager.record_victory(self.level.id, self.move_count, next_lvl)
            self.trigger_event("victory", moves=self.move_count)
        elif not now_won:
            self.is_won = False

        return True

    def undo(self) -> bool:
        """Undo the last move. Supports undoing even after victory.
        
        Requirement: "Undo/Redo tại trạng thái chiến thắng."
        """
        if self.level is None:
            return False

        success = self.history_manager.undo()
        if success:
            self.is_won = self.level.is_completed()
            self.trigger_event("rewind")
        return success

    def redo(self) -> bool:
        """Redo the last undone move."""
        if self.level is None:
            return False

        success = self.history_manager.redo()
        if success:
            self.is_won = self.level.is_completed()
            if self.is_won:
                next_lvl = self.level.id + 1 if self.level.id < 10 else None
                self.save_manager.record_victory(self.level.id, self.move_count, next_lvl)
                self.trigger_event("victory", moves=self.move_count)
            self.trigger_event("fast_forward")
        return success

    def can_undo(self) -> bool:
        """Check if an undo action is available."""
        return self.history_manager.can_undo()

    def can_redo(self) -> bool:
        """Check if a redo action is available."""
        return self.history_manager.can_redo()
