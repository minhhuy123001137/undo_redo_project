"""History Manager implementing dual-stack Undo/Redo mechanism."""
from typing import List, Optional
from core.command import Command
from core.exceptions import CommandExecutionError, CommandUndoError, InvalidCommandError


class HistoryManager:
    """Manages command history with Undo and Redo stacks.
    
    Independent of any UI or game framework. Safe for reuse in other applications
    like image editors, text editors, or simulators.
    """

    def __init__(
        self,
        max_history: Optional[int] = None,
        max_memory_bytes: Optional[int] = None,
    ) -> None:
        """Initialize the HistoryManager.
        
        Args:
            max_history: Maximum number of commands to retain in undo history.
                         If exceeded, oldest commands are discarded. None for unlimited.
            max_memory_bytes: Optional maximum memory footprint in bytes for future
                              large-command use-cases (e.g., Pixel Studio).
        """
        if max_history is not None and max_history < 1:
            raise ValueError("max_history must be at least 1")
            
        self._max_history: Optional[int] = max_history
        self._max_memory_bytes: Optional[int] = max_memory_bytes
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []

    @property
    def undo_count(self) -> int:
        """Number of commands currently available to undo."""
        return len(self._undo_stack)

    @property
    def redo_count(self) -> int:
        """Number of commands currently available to redo."""
        return len(self._redo_stack)

    def can_undo(self) -> bool:
        """Check whether at least one command can be undone."""
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Check whether at least one command can be redone."""
        return len(self._redo_stack) > 0

    def execute(self, command: Command) -> bool:
        """Execute a new command and record it in the undo stack if successful.
        
        Clears the redo stack upon successful execution.
        If execution returns False or raises an error, the history stacks
        remain completely unchanged.
        
        Args:
            command: The Command instance to execute.
            
        Returns:
            bool: True if execution succeeded and was recorded, False otherwise.
        """
        if command is None or not isinstance(command, Command):
            raise InvalidCommandError("Expected an instance of Command subclass")

        try:
            success = command.execute()
        except Exception as exc:
            raise CommandExecutionError(f"Command execution failed: {exc}") from exc

        if not success:
            return False

        command._is_executed = True
        self._undo_stack.append(command)
        self._redo_stack.clear()

        self._enforce_limits()
        return True

    def undo(self) -> bool:
        """Undo the most recent command and push it onto the redo stack.
        
        Returns:
            bool: True if undo was successful, False if no commands to undo.
        """
        if not self.can_undo():
            return False

        command = self._undo_stack.pop()
        try:
            success = command.undo()
        except Exception as exc:
            # Restore stack integrity on unexpected error
            self._undo_stack.append(command)
            raise CommandUndoError(f"Command undo failed: {exc}") from exc

        if not success:
            # Restore stack integrity if command reported failure
            self._undo_stack.append(command)
            return False

        command._is_executed = False
        self._redo_stack.append(command)
        return True

    def redo(self) -> bool:
        """Redo the most recently undone command and push it back onto the undo stack.
        
        Returns:
            bool: True if redo was successful, False if no commands to redo.
        """
        if not self.can_redo():
            return False

        command = self._redo_stack.pop()
        try:
            success = command.execute()
        except Exception as exc:
            # Restore stack integrity on unexpected error
            self._redo_stack.append(command)
            raise CommandExecutionError(f"Command redo failed: {exc}") from exc

        if not success:
            # Restore stack integrity if execution failed
            self._redo_stack.append(command)
            return False

        command._is_executed = True
        self._undo_stack.append(command)
        self._enforce_limits()
        return True

    def clear(self) -> None:
        """Clear both undo and redo stacks."""
        self._undo_stack.clear()
        self._redo_stack.clear()

    def peek_undo(self) -> Optional[Command]:
        """View the top command on the undo stack without removing it."""
        return self._undo_stack[-1] if self._undo_stack else None

    def peek_redo(self) -> Optional[Command]:
        """View the top command on the redo stack without removing it."""
        return self._redo_stack[-1] if self._redo_stack else None

    def get_timeline(self) -> List[str]:
        """Return a list of command names currently in the undo stack."""
        return [cmd.name for cmd in self._undo_stack]

    def get_total_memory_bytes(self) -> int:
        """Calculate total memory consumed by commands in both stacks."""
        total = sum(cmd.get_memory_size() for cmd in self._undo_stack)
        total += sum(cmd.get_memory_size() for cmd in self._redo_stack)
        return total

    def _enforce_limits(self) -> None:
        """Enforce maximum history length and memory limits by trimming oldest items."""
        if self._max_history is not None:
            while len(self._undo_stack) > self._max_history:
                self._undo_stack.pop(0)

        if self._max_memory_bytes is not None:
            while self._undo_stack and self.get_total_memory_bytes() > self._max_memory_bytes:
                if len(self._undo_stack) <= 1:
                    break
                self._undo_stack.pop(0)
