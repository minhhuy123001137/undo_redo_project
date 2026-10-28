"""Player entity for Sokoban game."""
from typing import Tuple


class Player:
    """Represents the player character in Time Shift."""

    DIRECTIONS = {
        (0, -1): "up",
        (0, 1): "down",
        (-1, 0): "left",
        (1, 0): "right",
    }

    def __init__(self, x: int = 0, y: int = 0) -> None:
        self.x: int = x
        self.y: int = y
        self.facing: str = "down"

    @property
    def pos(self) -> Tuple[int, int]:
        """Return current player position as (x, y)."""
        return self.x, self.y

    def set_pos(self, x: int, y: int) -> None:
        """Set player coordinates."""
        self.x = x
        self.y = y

    def set_facing(self, dx: int, dy: int) -> None:
        """Update player facing direction based on movement vector."""
        if (dx, dy) in self.DIRECTIONS:
            self.facing = self.DIRECTIONS[(dx, dy)]
