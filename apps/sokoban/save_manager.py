"""Safe JSON Save and Settings Manager for Time Shift."""
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional


class SaveManager:
    """Manages player progress and game settings with atomic file writes."""

    DEFAULT_PROGRESS = {
        "unlocked_levels": [1],
        "completed_levels": [],
        "best_moves": {},
    }

    DEFAULT_SETTINGS = {
        "music_volume": 0.7,
        "sfx_volume": 0.8,
        "screen_shake": True,
        "particles": True,
        "glow_effects": True,
        "reduced_motion": False,
    }

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        if base_dir is None:
            base_dir = Path(__file__).resolve().parent.parent.parent / "data"
        self.save_dir = base_dir / "saves"
        self.settings_dir = base_dir / "settings"

        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.settings_dir.mkdir(parents=True, exist_ok=True)

        self.progress_file = self.save_dir / "progress.json"
        self.settings_file = self.settings_dir / "settings.json"

        self.progress: Dict[str, Any] = self.load_progress()
        self.settings: Dict[str, Any] = self.load_settings()

    def _safe_write_json(self, filepath: Path, data: Dict[str, Any]) -> None:
        """Atomically write JSON data using a temporary file and replace."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        # Use temp file in the same directory to ensure same filesystem for atomic rename
        temp_fd, temp_path = tempfile.mkstemp(dir=filepath.parent, prefix="tmp_save_", suffix=".json")
        try:
            with open(temp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            # Atomically replace target file
            os.replace(temp_path, filepath)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def load_progress(self) -> Dict[str, Any]:
        """Load player progress or return defaults if file missing or corrupt."""
        if not self.progress_file.exists():
            data = dict(self.DEFAULT_PROGRESS)
            self._safe_write_json(self.progress_file, data)
            return data

        try:
            with open(self.progress_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Ensure all required keys exist
                for k, v in self.DEFAULT_PROGRESS.items():
                    if k not in data:
                        data[k] = v
                return data
        except (json.JSONDecodeError, OSError):
            # Backup corrupted file if possible
            backup = self.progress_file.with_suffix(".corrupt.bak")
            try:
                os.replace(self.progress_file, backup)
            except OSError:
                pass
            data = dict(self.DEFAULT_PROGRESS)
            self._safe_write_json(self.progress_file, data)
            return data

    def save_progress(self) -> None:
        """Persist current progress to disk."""
        self._safe_write_json(self.progress_file, self.progress)

    def load_settings(self) -> Dict[str, Any]:
        """Load settings or return defaults if file missing or corrupt."""
        if not self.settings_file.exists():
            data = dict(self.DEFAULT_SETTINGS)
            self._safe_write_json(self.settings_file, data)
            return data

        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in self.DEFAULT_SETTINGS.items():
                    if k not in data:
                        data[k] = v
                return data
        except (json.JSONDecodeError, OSError):
            data = dict(self.DEFAULT_SETTINGS)
            self._safe_write_json(self.settings_file, data)
            return data

    def save_settings(self) -> None:
        """Persist settings to disk."""
        self._safe_write_json(self.settings_file, self.settings)

    def is_level_unlocked(self, level_id: int) -> bool:
        """Check if a level is unlocked."""
        return level_id in self.progress.get("unlocked_levels", [1])

    def is_level_completed(self, level_id: int) -> bool:
        """Check if a level was completed."""
        return level_id in self.progress.get("completed_levels", [])

    def unlock_level(self, level_id: int) -> None:
        """Unlock a new level."""
        unlocked: List[int] = self.progress.setdefault("unlocked_levels", [1])
        if level_id not in unlocked:
            unlocked.append(level_id)
            unlocked.sort()
            self.save_progress()

    def record_victory(self, level_id: int, moves: int, next_level_id: Optional[int] = None) -> None:
        """Record level completion, update best moves, and unlock next level."""
        completed: List[int] = self.progress.setdefault("completed_levels", [])
        if level_id not in completed:
            completed.append(level_id)
            completed.sort()

        best_moves_map: Dict[str, int] = self.progress.setdefault("best_moves", {})
        key = str(level_id)
        if key not in best_moves_map or moves < best_moves_map[key]:
            best_moves_map[key] = moves

        if next_level_id is not None:
            unlocked: List[int] = self.progress.setdefault("unlocked_levels", [1])
            if next_level_id not in unlocked:
                unlocked.append(next_level_id)
                unlocked.sort()

        self.save_progress()

    def get_best_moves(self, level_id: int) -> Optional[int]:
        """Get personal best move count for a level."""
        return self.progress.get("best_moves", {}).get(str(level_id))
