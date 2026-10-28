"""Commands implementing player movement and box pushing in Sokoban."""
from typing import TYPE_CHECKING, Optional, Tuple
from core.command import Command

if TYPE_CHECKING:
    from apps.sokoban.game import SokobanGame


class MoveCommand(Command):
    """Reversible command for player movement and box pushing."""

    def __init__(self, game: "SokobanGame", dx: int, dy: int) -> None:
        direction_name = {
            (0, -1): "Up",
            (0, 1): "Down",
            (-1, 0): "Left",
            (1, 0): "Right",
        }.get((dx, dy), "Move")
        super().__init__(name=f"Move {direction_name}")
        self.game = game
        self.dx: int = dx
        self.dy: int = dy

        # Execution records for rollback
        self.player_from: Optional[Tuple[int, int]] = None
        self.player_to: Optional[Tuple[int, int]] = None
        self.prev_facing: Optional[str] = None
        self.pushed_box_from: Optional[Tuple[int, int]] = None
        self.pushed_box_to: Optional[Tuple[int, int]] = None

    def execute(self) -> bool:
        """Execute movement and optional box push.
        
        Returns:
            bool: True if move succeeded, False if blocked by wall or box.
        """
        player = self.game.player
        level = self.game.level

        from_pos = player.pos
        to_pos = (from_pos[0] + self.dx, from_pos[1] + self.dy)

        # Check bounds and walls
        if not level.is_inside(*to_pos) or level.is_wall(*to_pos):
            return False

        # Check if moving into a box
        if level.is_box(*to_pos):
            box_next = (to_pos[0] + self.dx, to_pos[1] + self.dy)
            # Cannot push box into wall, out of bounds, or into another box
            if (
                not level.is_inside(*box_next)
                or level.is_wall(*box_next)
                or level.is_box(*box_next)
            ):
                return False

            # Valid push
            self.pushed_box_from = to_pos
            self.pushed_box_to = box_next
            level.boxes.remove(to_pos)
            level.boxes.add(box_next)
            self._name = f"Push {self.name.split()[-1]}"
        else:
            self.pushed_box_from = None
            self.pushed_box_to = None

        # Record player state
        self.player_from = from_pos
        self.player_to = to_pos
        self.prev_facing = player.facing

        # Apply player change
        player.set_pos(*to_pos)
        player.set_facing(self.dx, self.dy)
        self.game.move_count += 1

        # Notify game of step animation or sound triggers
        self.game.on_move_executed(
            pushed_box=(self.pushed_box_from is not None),
            from_pos=self.player_from,
            to_pos=self.player_to,
            box_from=self.pushed_box_from,
            box_to=self.pushed_box_to,
        )
        return True

    def undo(self) -> bool:
        """Undo player movement and restore pushed box if any.
        
        Returns:
            bool: True if undo succeeded, False otherwise.
        """
        if self.player_from is None or self.player_to is None:
            return False

        player = self.game.player
        level = self.game.level

        # Restore box if pushed
        if self.pushed_box_from is not None and self.pushed_box_to is not None:
            if self.pushed_box_to in level.boxes:
                level.boxes.remove(self.pushed_box_to)
                level.boxes.add(self.pushed_box_from)

        # Restore player
        player.set_pos(*self.player_from)
        if self.prev_facing:
            player.facing = self.prev_facing

        self.game.move_count = max(0, self.game.move_count - 1)
        self.game.on_move_undone(
            was_pushed=(self.pushed_box_from is not None),
            from_pos=self.player_to,
            to_pos=self.player_from,
            box_from=self.pushed_box_to,
            box_to=self.pushed_box_from,
        )
        return True
