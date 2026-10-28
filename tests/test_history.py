"""Unit tests for the Core Undo/Redo Engine."""
import unittest
from core.command import Command
from core.history_manager import HistoryManager
from core.exceptions import CommandExecutionError, CommandUndoError, InvalidCommandError


class CounterAddCommand(Command):
    """Test command that increments a counter on execute and decrements on undo."""

    def __init__(self, target_obj: dict, delta: int = 1, should_fail: bool = False, raise_on_exec: bool = False, raise_on_undo: bool = False) -> None:
        super().__init__(f"Add {delta}")
        self.target = target_obj
        self.delta = delta
        self.should_fail = should_fail
        self.raise_on_exec = raise_on_exec
        self.raise_on_undo = raise_on_undo

    def execute(self) -> bool:
        if self.raise_on_exec:
            raise RuntimeError("Execution boom")
        if self.should_fail:
            return False
        self.target["value"] += self.delta
        return True

    def undo(self) -> bool:
        if self.raise_on_undo:
            raise RuntimeError("Undo boom")
        self.target["value"] -= self.delta
        return True

    def get_memory_size(self) -> int:
        return 100


class TestHistoryManager(unittest.TestCase):
    """Test suite for HistoryManager."""

    def setUp(self) -> None:
        self.history = HistoryManager()
        self.state = {"value": 0}

    def test_initial_state(self) -> None:
        self.assertFalse(self.history.can_undo())
        self.assertFalse(self.history.can_redo())
        self.assertEqual(self.history.undo_count, 0)
        self.assertEqual(self.history.redo_count, 0)
        self.assertIsNone(self.history.peek_undo())
        self.assertIsNone(self.history.peek_redo())

    def test_execute_success(self) -> None:
        cmd = CounterAddCommand(self.state, 5)
        res = self.history.execute(cmd)
        self.assertTrue(res)
        self.assertEqual(self.state["value"], 5)
        self.assertTrue(self.history.can_undo())
        self.assertFalse(self.history.can_redo())
        self.assertEqual(self.history.undo_count, 1)
        self.assertEqual(self.history.peek_undo(), cmd)

    def test_execute_failure_returns_false_and_preserves_stacks(self) -> None:
        # Pre-populate history
        self.history.execute(CounterAddCommand(self.state, 1))
        self.history.undo()  # Now 1 in redo
        self.assertEqual(self.history.redo_count, 1)

        # Execute failed command
        fail_cmd = CounterAddCommand(self.state, 10, should_fail=True)
        res = self.history.execute(fail_cmd)
        self.assertFalse(res)
        self.assertEqual(self.state["value"], 0)
        # Redo stack should NOT be cleared if command failed!
        self.assertEqual(self.history.redo_count, 1)
        self.assertEqual(self.history.undo_count, 0)

    def test_execute_exception_raises_and_preserves_stacks(self) -> None:
        boom_cmd = CounterAddCommand(self.state, 10, raise_on_exec=True)
        with self.assertRaises(CommandExecutionError):
            self.history.execute(boom_cmd)
        self.assertEqual(self.history.undo_count, 0)

    def test_invalid_command_type(self) -> None:
        with self.assertRaises(InvalidCommandError):
            self.history.execute("not a command")  # type: ignore

    def test_undo_once(self) -> None:
        cmd = CounterAddCommand(self.state, 3)
        self.history.execute(cmd)
        self.assertEqual(self.state["value"], 3)

        success = self.history.undo()
        self.assertTrue(success)
        self.assertEqual(self.state["value"], 0)
        self.assertFalse(self.history.can_undo())
        self.assertTrue(self.history.can_redo())
        self.assertEqual(self.history.redo_count, 1)
        self.assertEqual(self.history.peek_redo(), cmd)

    def test_undo_multiple_times(self) -> None:
        for val in [1, 2, 3]:
            self.history.execute(CounterAddCommand(self.state, val))
        self.assertEqual(self.state["value"], 6)

        self.assertTrue(self.history.undo())
        self.assertEqual(self.state["value"], 3)
        self.assertTrue(self.history.undo())
        self.assertEqual(self.state["value"], 1)
        self.assertTrue(self.history.undo())
        self.assertEqual(self.state["value"], 0)
        self.assertFalse(self.history.can_undo())

    def test_redo_once(self) -> None:
        cmd = CounterAddCommand(self.state, 4)
        self.history.execute(cmd)
        self.history.undo()
        self.assertEqual(self.state["value"], 0)

        success = self.history.redo()
        self.assertTrue(success)
        self.assertEqual(self.state["value"], 4)
        self.assertTrue(self.history.can_undo())
        self.assertFalse(self.history.can_redo())

    def test_redo_multiple_times(self) -> None:
        for val in [2, 4, 6]:
            self.history.execute(CounterAddCommand(self.state, val))
        self.assertEqual(self.state["value"], 12)

        self.history.undo()
        self.history.undo()
        self.history.undo()
        self.assertEqual(self.state["value"], 0)

        self.assertTrue(self.history.redo())
        self.assertEqual(self.state["value"], 2)
        self.assertTrue(self.history.redo())
        self.assertEqual(self.state["value"], 6)
        self.assertTrue(self.history.redo())
        self.assertEqual(self.state["value"], 12)
        self.assertFalse(self.history.can_redo())

    def test_undo_then_new_action_clears_redo(self) -> None:
        self.history.execute(CounterAddCommand(self.state, 5))
        self.history.undo()
        self.assertEqual(self.history.redo_count, 1)

        # New action
        self.history.execute(CounterAddCommand(self.state, 10))
        self.assertEqual(self.state["value"], 10)
        self.assertEqual(self.history.undo_count, 1)
        self.assertEqual(self.history.redo_count, 0)
        self.assertFalse(self.history.can_redo())

    def test_undo_on_empty_history(self) -> None:
        self.assertFalse(self.history.undo())

    def test_redo_on_empty_history(self) -> None:
        self.assertFalse(self.history.redo())

    def test_clear_history(self) -> None:
        self.history.execute(CounterAddCommand(self.state, 5))
        self.history.execute(CounterAddCommand(self.state, 10))
        self.history.undo()
        self.assertEqual(self.history.undo_count, 1)
        self.assertEqual(self.history.redo_count, 1)

        self.history.clear()
        self.assertEqual(self.history.undo_count, 0)
        self.assertEqual(self.history.redo_count, 0)
        self.assertFalse(self.history.can_undo())
        self.assertFalse(self.history.can_redo())

    def test_max_history_limit(self) -> None:
        limited_history = HistoryManager(max_history=3)
        for i in range(1, 6):
            limited_history.execute(CounterAddCommand(self.state, i))

        self.assertEqual(limited_history.undo_count, 3)
        # Should only have Add 3, Add 4, Add 5
        self.assertEqual(limited_history.get_timeline(), ["Add 3", "Add 4", "Add 5"])

    def test_memory_limit(self) -> None:
        # Each test cmd reports 100 bytes
        mem_history = HistoryManager(max_memory_bytes=250)
        mem_history.execute(CounterAddCommand(self.state, 1))  # 100
        mem_history.execute(CounterAddCommand(self.state, 2))  # 200
        mem_history.execute(CounterAddCommand(self.state, 3))  # 300 > 250 -> trims oldest
        self.assertLessEqual(mem_history.get_total_memory_bytes(), 250)
        self.assertEqual(mem_history.undo_count, 2)

    def test_undo_exception_preserves_stack_integrity(self) -> None:
        bad_undo_cmd = CounterAddCommand(self.state, 1, raise_on_undo=True)
        self.history.execute(bad_undo_cmd)
        self.assertEqual(self.history.undo_count, 1)

        with self.assertRaises(CommandUndoError):
            self.history.undo()

        # The command should have been restored to undo_stack
        self.assertEqual(self.history.undo_count, 1)
        self.assertEqual(self.history.redo_count, 0)


if __name__ == "__main__":
    unittest.main()
