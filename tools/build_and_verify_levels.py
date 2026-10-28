"""Generate and verify 10 Sokoban levels using BFS."""
import json
from pathlib import Path
from apps.sokoban.level import Level

ASCII_LEVELS = [
    # Level 1: First Shift (Easy - 1 box)
    {
        "id": 1,
        "name": "Level 1 - First Shift",
        "map": [
            "#######",
            "#@ $ .#",
            "#######",
        ],
    },
    # Level 2: Dual Timeline (Easy - 2 boxes)
    {
        "id": 2,
        "name": "Level 2 - Dual Timeline",
        "map": [
            "#######",
            "#@ $ .#",
            "#  $ .#",
            "#######",
        ],
    },
    # Level 3: Corridor (Easy - 2 boxes)
    {
        "id": 3,
        "name": "Level 3 - Corridor",
        "map": [
            "########",
            "#@     #",
            "#  $$  #",
            "#  ..  #",
            "#      #",
            "########",
        ],
    },
    # Level 4: Quantum Knot (Medium - 2 boxes)
    {
        "id": 4,
        "name": "Level 4 - Quantum Knot",
        "map": [
            "########",
            "#  @   #",
            "# $ #  #",
            "# . #$ #",
            "#   .  #",
            "########",
        ],
    },
    # Level 5: Paradox Alley (Medium - 2 boxes)
    {
        "id": 5,
        "name": "Level 5 - Paradox Alley",
        "map": [
            "########",
            "###  ###",
            "#.@ $  #",
            "#   $ .#",
            "###  ###",
            "########",
        ],
    },
    # Level 6: Chrono Vault (Medium - 3 boxes)
    {
        "id": 6,
        "name": "Level 6 - Chrono Vault",
        "map": [
            "#########",
            "#   .   #",
            "# $ # $ #",
            "#   @   #",
            "# . $ . #",
            "#########",
        ],
    },
    # Level 7: Continuum Chamber (Medium - 3 boxes)
    {
        "id": 7,
        "name": "Level 7 - Continuum Chamber",
        "map": [
            "########",
            "#   .  #",
            "# $#$  #",
            "#  @   #",
            "#  $   #",
            "# ..   #",
            "########",
        ],
    },
    # Level 8: Time Warp (Hard - 3 boxes)
    {
        "id": 8,
        "name": "Level 8 - Time Warp",
        "map": [
            "########",
            "#  ..  #",
            "# $  $ #",
            "#  @   #",
            "#  $   #",
            "#  .   #",
            "########",
        ],
    },
    # Level 9: Event Horizon (Hard - 3 boxes)
    {
        "id": 9,
        "name": "Level 9 - Event Horizon",
        "map": [
            "#########",
            "#  #  . #",
            "# $#$   #",
            "#  @  . #",
            "#  $  # #",
            "#  .    #",
            "#########",
        ],
    },
    # Level 10: Singularity (Hard - 4 boxes)
    {
        "id": 10,
        "name": "Level 10 - Singularity",
        "map": [
            "##########",
            "#   ...  #",
            "#  $$$$  #",
            "#   @    #",
            "#   .    #",
            "#        #",
            "##########",
        ],
    },
]


def parse_ascii_level(item: dict) -> Level:
    lines = item["map"]
    height = len(lines)
    width = max(len(line) for line in lines)

    walls = set()
    targets = set()
    boxes = set()
    player_start = None

    for y, line in enumerate(lines):
        for x, ch in enumerate(line):
            if ch == "#":
                walls.add((x, y))
            elif ch == ".":
                targets.add((x, y))
            elif ch == "$":
                boxes.add((x, y))
            elif ch == "*":  # Box on target
                boxes.add((x, y))
                targets.add((x, y))
            elif ch == "@":  # Player
                player_start = (x, y)
            elif ch == "+":  # Player on target
                player_start = (x, y)
                targets.add((x, y))

    if player_start is None:
        raise ValueError(f"No player start in level {item['id']}")

    level = Level(
        level_id=item["id"],
        name=item["name"],
        width=width,
        height=height,
        walls=walls,
        targets=targets,
        boxes=boxes,
        player_start=player_start,
    )
    valid, msg = level.validate()
    if not valid:
        raise ValueError(f"Invalid level {item['id']}: {msg}")
    return level


def main():
    out_dir = Path("apps/sokoban/levels")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=== Verifying and Generating 10 Levels ===")
    for item in ASCII_LEVELS:
        lvl = parse_ascii_level(item)
        print(f"Solving Level {lvl.id}: {lvl.name} (Boxes: {len(lvl.boxes)})...", end=" ", flush=True)
        solution = lvl.solve_bfs(max_states=100000)
        if solution is None:
            print("FAILED! No solution found.")
            raise RuntimeError(f"Level {lvl.id} is unsolvable!")
        print(f"SOLVED in {len(solution)} moves!")

        filepath = out_dir / f"level_{lvl.id:02d}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(lvl.to_dict(), f, indent=2)
        print(f"  -> Saved to {filepath}")

    print("\nAll 10 levels successfully verified and generated!")


if __name__ == "__main__":
    main()
