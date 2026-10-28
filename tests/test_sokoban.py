"""Comprehensive unit tests for Sokoban game logic, commands, and save management."""
import shutil
import tempfile
import unittest
from pathlib import Path

from apps.sokoban.game import SokobanGame
from apps.sokoban.level import Level, LevelValidationError
from apps.sokoban.player import Player
from apps.sokoban.save_manager import SaveManager


class TestSokoban(unittest.TestCase):
    """Test suite covering all 19 mandatory game and history integration requirements."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.save_mgr = SaveManager(base_dir=self.temp_dir)
        self.game = SokobanGame(save_manager=self.save_mgr)

        # Build a known test level:
        # #######
        # #@ $ .#
        # #  #  #
        # #######
        walls = {(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0),
                 (0, 1),                                     (6, 1),
                 (0, 2),        (2, 2),                     (6, 2),
                 (0, 3), (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3)}
        targets = {(5, 1)}
        boxes = {(3, 1)}
        player_start = (1, 1)

        self.test_level = Level(
            level_id=99,
            name="Test Level",
            width=7,
            height=4,
            walls=walls,
            targets=targets,
            boxes=boxes,
            player_start=player_start,
        )
        self.game.level = self.test_level
        self.game.player = Player(*player_start)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # 1. Di chuyển hợp lệ
    def test_01_valid_movement(self) -> None:
        self.assertEqual(self.game.player.pos, (1, 1))
        # Move right to (2, 1) - empty space
        success = self.game.move_player(1, 0)
        self.assertTrue(success)
        self.assertEqual(self.game.player.pos, (2, 1))
        self.assertEqual(self.game.move_count, 1)
        self.assertEqual(self.game.history_manager.undo_count, 1)

    # 2. Va chạm tường
    def test_02_wall_collision(self) -> None:
        self.assertEqual(self.game.player.pos, (1, 1))
        # Move left into wall at (0, 1)
        success = self.game.move_player(-1, 0)
        self.assertFalse(success)
        self.assertEqual(self.game.player.pos, (1, 1))
        self.assertEqual(self.game.move_count, 0)
        self.assertEqual(self.game.history_manager.undo_count, 0)

    # 3. Đẩy thùng hợp lệ
    def test_03_valid_box_push(self) -> None:
        # Move to (2, 1)
        self.game.move_player(1, 0)
        # Push box from (3, 1) into (4, 1)
        success = self.game.move_player(1, 0)
        self.assertTrue(success)
        self.assertEqual(self.game.player.pos, (3, 1))
        self.assertIn((4, 1), self.game.level.boxes)
        self.assertNotIn((3, 1), self.game.level.boxes)
        self.assertEqual(self.game.move_count, 2)

    # 4. Đẩy thùng bị chặn (tường hoặc thùng khác)
    def test_04_blocked_box_push(self) -> None:
        # Move to (2, 1) and push box to (4, 1)
        self.game.move_player(1, 0)
        self.game.move_player(1, 0)
        # Push box from (4, 1) to (5, 1) (target)
        self.game.move_player(1, 0)
        # Now box is at (5, 1). Behind it is wall at (6, 1).
        # Pushing right again should fail!
        success = self.game.move_player(1, 0)
        self.assertFalse(success)
        self.assertEqual(self.game.player.pos, (4, 1))
        self.assertIn((5, 1), self.game.level.boxes)
        self.assertEqual(self.game.move_count, 3)

    # 5. Undo một lần
    def test_05_undo_once(self) -> None:
        self.game.move_player(1, 0)
        self.assertEqual(self.game.player.pos, (2, 1))
        success = self.game.undo()
        self.assertTrue(success)
        self.assertEqual(self.game.player.pos, (1, 1))
        self.assertEqual(self.game.move_count, 0)
        self.assertFalse(self.game.can_undo())
        self.assertTrue(self.game.can_redo())

    # 6. Undo nhiều lần
    def test_06_undo_multiple(self) -> None:
        self.game.move_player(1, 0)  # to (2, 1)
        self.game.move_player(1, 0)  # push box to (4, 1), player at (3, 1)
        self.assertEqual(self.game.move_count, 2)

        self.assertTrue(self.game.undo())
        self.assertEqual(self.game.player.pos, (2, 1))
        self.assertIn((3, 1), self.game.level.boxes)

        self.assertTrue(self.game.undo())
        self.assertEqual(self.game.player.pos, (1, 1))
        self.assertEqual(self.game.move_count, 0)
        self.assertFalse(self.game.can_undo())

    # 7. Redo một lần
    def test_07_redo_once(self) -> None:
        self.game.move_player(1, 0)
        self.game.undo()
        self.assertEqual(self.game.player.pos, (1, 1))

        success = self.game.redo()
        self.assertTrue(success)
        self.assertEqual(self.game.player.pos, (2, 1))
        self.assertEqual(self.game.move_count, 1)

    # 8. Redo nhiều lần
    def test_08_redo_multiple(self) -> None:
        self.game.move_player(1, 0)
        self.game.move_player(1, 0)
        self.game.undo()
        self.game.undo()
        self.assertEqual(self.game.player.pos, (1, 1))

        self.assertTrue(self.game.redo())
        self.assertEqual(self.game.player.pos, (2, 1))
        self.assertTrue(self.game.redo())
        self.assertEqual(self.game.player.pos, (3, 1))
        self.assertIn((4, 1), self.game.level.boxes)
        self.assertFalse(self.game.can_redo())

    # 9. Undo rồi thực hiện hành động mới
    def test_09_undo_then_new_action(self) -> None:
        self.game.move_player(1, 0)
        self.game.undo()
        self.assertTrue(self.game.can_redo())

        # Perform a new move: move down to (1, 2)
        success = self.game.move_player(0, 1)
        self.assertTrue(success)
        self.assertEqual(self.game.player.pos, (1, 2))
        # Redo stack must be completely cleared
        self.assertFalse(self.game.can_redo())
        self.assertEqual(self.game.history_manager.redo_count, 0)

    # 10. Undo sau khi đẩy thùng
    def test_10_undo_after_push(self) -> None:
        self.game.move_player(1, 0)  # (2, 1)
        self.game.move_player(1, 0)  # push box from (3, 1) -> (4, 1), player at (3, 1)
        self.assertIn((4, 1), self.game.level.boxes)

        self.game.undo()
        self.assertEqual(self.game.player.pos, (2, 1))
        self.assertIn((3, 1), self.game.level.boxes)
        self.assertNotIn((4, 1), self.game.level.boxes)

    # 11. Redo sau khi đẩy thùng
    def test_11_redo_after_push(self) -> None:
        self.game.move_player(1, 0)
        self.game.move_player(1, 0)
        self.game.undo()
        self.assertIn((3, 1), self.game.level.boxes)

        self.game.redo()
        self.assertEqual(self.game.player.pos, (3, 1))
        self.assertIn((4, 1), self.game.level.boxes)
        self.assertNotIn((3, 1), self.game.level.boxes)

    # 12. Undo khi không có lịch sử
    def test_12_undo_empty_history(self) -> None:
        self.assertFalse(self.game.can_undo())
        self.assertFalse(self.game.undo())
        self.assertEqual(self.game.move_count, 0)

    # 13. Redo khi không có lịch sử
    def test_13_redo_empty_history(self) -> None:
        self.assertFalse(self.game.can_redo())
        self.assertFalse(self.game.redo())

    # 14. Restart phải xóa lịch sử
    def test_14_restart_clears_history(self) -> None:
        self.game.move_player(1, 0)
        self.game.move_player(1, 0)
        self.assertEqual(self.game.move_count, 2)
        self.assertTrue(self.game.can_undo())

        self.game.restart_level()
        self.assertEqual(self.game.player.pos, (1, 1))
        self.assertIn((3, 1), self.game.level.boxes)
        self.assertEqual(self.game.move_count, 0)
        self.assertFalse(self.game.can_undo())
        self.assertFalse(self.game.can_redo())

    # 15. Chuyển Level phải tạo lịch sử độc lập
    def test_15_level_change_creates_independent_history(self) -> None:
        self.game.move_player(1, 0)
        self.assertEqual(self.game.history_manager.undo_count, 1)

        # Load real level 1
        loaded = self.game.load_level(1)
        self.assertTrue(loaded)
        self.assertEqual(self.game.history_manager.undo_count, 0)
        self.assertFalse(self.game.can_undo())
        self.assertFalse(self.game.can_redo())
        self.assertEqual(self.game.move_count, 0)

    # 16. Undo/Redo tại trạng thái chiến thắng
    def test_16_undo_redo_at_victory_state(self) -> None:
        self.assertFalse(self.game.is_won)
        self.game.move_player(1, 0)  # to (2, 1)
        self.game.move_player(1, 0)  # push box to (4, 1)
        self.assertFalse(self.game.is_won)
        self.game.move_player(1, 0)  # push box to (5, 1) target!
        self.assertTrue(self.game.is_won)

        # Undo from victory
        self.game.undo()
        self.assertFalse(self.game.is_won)
        self.assertNotIn((5, 1), self.game.level.boxes)

        # Redo back to victory
        self.game.redo()
        self.assertTrue(self.game.is_won)
        self.assertIn((5, 1), self.game.level.boxes)

    # 17. Kiểm tra level hợp lệ
    def test_17_level_validation(self) -> None:
        # Valid level
        self.assertTrue(self.test_level.validate()[0])

        # Missing targets
        bad_level = Level(1, "Bad", 5, 5, set(), set(), {(1, 1)}, (2, 2))
        valid, msg = bad_level.validate()
        self.assertFalse(valid)
        self.assertIn("no target", msg.lower())

        # Mismatch box and target counts
        bad_counts = Level(1, "Bad", 5, 5, set(), {(1, 1)}, {(1, 2), (1, 3)}, (2, 2))
        valid, msg = bad_counts.validate()
        self.assertFalse(valid)
        self.assertIn("does not match", msg.lower())

    # 18. Kiểm tra lưu và tải JSON
    def test_18_json_save_and_load(self) -> None:
        self.save_mgr.record_victory(level_id=1, moves=15, next_level_id=2)
        self.assertTrue(self.save_mgr.is_level_unlocked(2))
        self.assertTrue(self.save_mgr.is_level_completed(1))
        self.assertEqual(self.save_mgr.get_best_moves(1), 15)

        # Better record
        self.save_mgr.record_victory(level_id=1, moves=10)
        self.assertEqual(self.save_mgr.get_best_moves(1), 10)

        # Create new save manager pointing to same dir
        reloaded_mgr = SaveManager(base_dir=self.temp_dir)
        self.assertTrue(reloaded_mgr.is_level_unlocked(2))
        self.assertEqual(reloaded_mgr.get_best_moves(1), 10)

    # 19. Command thất bại không làm sai lịch sử
    def test_19_failed_command_does_not_corrupt_history(self) -> None:
        self.game.move_player(1, 0)
        undo_count_before = self.game.history_manager.undo_count
        self.game.undo()
        redo_count_before = self.game.history_manager.redo_count

        # Attempt invalid move (walk into wall)
        success = self.game.move_player(0, -1)  # Wall at (1, 0)
        self.assertFalse(success)

        # Check stack counts did not change
        self.assertEqual(self.game.history_manager.undo_count, 0)
        self.assertEqual(self.game.history_manager.redo_count, redo_count_before)


if __name__ == "__main__":
    unittest.main()
