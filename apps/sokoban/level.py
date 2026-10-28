"""Level representation and validation for Sokoban."""
from collections import deque
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class LevelValidationError(Exception):
    """Raised when a level definition is invalid."""
    pass


class Level:
    """Represents a Sokoban level with grid, walls, targets, boxes, and player starting position."""

    def __init__(
        self,
        level_id: int,
        name: str,
        width: int,
        height: int,
        walls: Set[Tuple[int, int]],
        targets: Set[Tuple[int, int]],
        boxes: Set[Tuple[int, int]],
        player_start: Tuple[int, int],
    ) -> None:
        self.id: int = level_id
        self.name: str = name
        self.width: int = width
        self.height: int = height
        self.walls: Set[Tuple[int, int]] = set(walls)
        self.targets: Set[Tuple[int, int]] = set(targets)
        self.initial_boxes: Set[Tuple[int, int]] = set(boxes)
        self.boxes: Set[Tuple[int, int]] = set(boxes)
        self.player_start: Tuple[int, int] = player_start

    def reset(self) -> None:
        """Reset the level boxes to their starting layout."""
        self.boxes = set(self.initial_boxes)

    def is_completed(self) -> bool:
        """Check if all targets have boxes on them."""
        return self.boxes == self.targets

    def is_inside(self, x: int, y: int) -> bool:
        """Check if coordinates are inside the map bounds."""
        return 0 <= x < self.width and 0 <= y < self.height

    def is_wall(self, x: int, y: int) -> bool:
        """Check if coordinates are a wall."""
        return (x, y) in self.walls

    def is_box(self, x: int, y: int) -> bool:
        """Check if coordinates currently contain a box."""
        return (x, y) in self.boxes

    def is_target(self, x: int, y: int) -> bool:
        """Check if coordinates are a target tile."""
        return (x, y) in self.targets

    def validate(self) -> Tuple[bool, str]:
        """Validate level integrity according to game rules.
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if self.width <= 2 or self.height <= 2:
            return False, f"Level dimensions too small: {self.width}x{self.height}"

        if not self.targets:
            return False, "Level has no target positions"

        if len(self.initial_boxes) != len(self.targets):
            return (
                False,
                f"Number of boxes ({len(self.initial_boxes)}) does not match targets ({len(self.targets)})",
            )

        if not self.is_inside(*self.player_start):
            return False, f"Player start {self.player_start} is outside the grid"

        if self.player_start in self.walls:
            return False, f"Player start {self.player_start} is inside a wall"

        if self.player_start in self.initial_boxes:
            return False, f"Player start {self.player_start} collides with a box"

        for b in self.initial_boxes:
            if not self.is_inside(*b):
                return False, f"Box {b} is outside the grid"
            if b in self.walls:
                return False, f"Box {b} overlaps with a wall"

        for t in self.targets:
            if not self.is_inside(*t):
                return False, f"Target {t} is outside the grid"
            if t in self.walls:
                return False, f"Target {t} overlaps with a wall"

        return True, ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Level":
        """Construct Level from dictionary."""
        level_id = data.get("id", 1)
        name = data.get("name", f"Level {level_id}")
        grid = data.get("grid_size", [8, 8])
        width, height = grid[0], grid[1]

        walls = {tuple(p) for p in data.get("walls", [])}
        targets = {tuple(p) for p in data.get("targets", [])}
        boxes = {tuple(p) for p in data.get("boxes", [])}
        player_start = tuple(data.get("player_start", [1, 1]))

        level = cls(
            level_id=level_id,
            name=name,
            width=width,
            height=height,
            walls=walls,
            targets=targets,
            boxes=boxes,
            player_start=player_start,
        )

        valid, err = level.validate()
        if not valid:
            raise LevelValidationError(f"Invalid level {level_id}: {err}")

        return level

    @classmethod
    def from_json_file(cls, filepath: Path) -> "Level":
        """Load Level from JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize Level to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "grid_size": [self.width, self.height],
            "player_start": list(self.player_start),
            "walls": sorted([[x, y] for x, y in self.walls]),
            "targets": sorted([[x, y] for x, y in self.targets]),
            "boxes": sorted([[x, y] for x, y in self.initial_boxes]),
        }

    def solve_bfs(self, max_states: int = 50000) -> Optional[List[Tuple[int, int]]]:
        """Breadth-First Search solver to verify that this level is solvable.
        
        Returns:
            List of move directions [(dx, dy), ...] reaching victory, or None if unsolvable.
        """
        initial_state = (self.player_start, frozenset(self.initial_boxes))
        target_set = frozenset(self.targets)

        if initial_state[1] == target_set:
            return []

        queue = deque([(initial_state, [])])
        visited = {initial_state}

        moves = [(0, -1), (0, 1), (-1, 0), (1, 0)]

        states_explored = 0
        while queue and states_explored < max_states:
            (curr_player, curr_boxes), path = queue.popleft()
            states_explored += 1

            for dx, dy in moves:
                nx = curr_player[0] + dx
                ny = curr_player[1] + dy

                # Check wall
                if (nx, ny) in self.walls or not self.is_inside(nx, ny):
                    continue

                # Check pushing a box
                if (nx, ny) in curr_boxes:
                    nbx = nx + dx
                    nby = ny + dy
                    # Box blocked by wall, map edge, or another box
                    if (nbx, nby) in self.walls or not self.is_inside(nbx, nby) or (nbx, nby) in curr_boxes:
                        continue

                    # Box can be pushed
                    new_boxes = (curr_boxes - {(nx, ny)}) | {(nbx, nby)}
                    new_player = (nx, ny)
                else:
                    new_boxes = curr_boxes
                    new_player = (nx, ny)

                if new_boxes == target_set:
                    return path + [(dx, dy)]

                new_state = (new_player, new_boxes)
                if new_state not in visited:
                    visited.add(new_state)
                    queue.append((new_state, path + [(dx, dy)]))

        return None
