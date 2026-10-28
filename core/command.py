"""Command abstract base class defining the Command Pattern interface."""
from abc import ABC, abstractmethod
import sys
from typing import Optional


class Command(ABC):
    """Abstract Base Class for all reversible commands.
    
    Subclasses must implement:
        - execute(): Applies the action. Returns True if successful, False or raises error if failed.
        - undo(): Reverts the action. Returns True if successful, False or raises error if failed.
    """

    def __init__(self, name: str = "Command") -> None:
        self._name: str = name
        self._is_executed: bool = False

    @property
    def name(self) -> str:
        """User-friendly name or description of the command."""
        return self._name

    @property
    def is_executed(self) -> bool:
        """Returns True if the command has been executed and not yet undone."""
        return self._is_executed

    @abstractmethod
    def execute(self) -> bool:
        """Execute the command.
        
        Returns:
            bool: True if the operation succeeded, False if it was invalid or failed.
        Raises:
            CommandExecutionError: If execution encountered an unrecoverable failure.
        """
        raise NotImplementedError

    @abstractmethod
    def undo(self) -> bool:
        """Undo the command, restoring the previous state.
        
        Returns:
            bool: True if undo succeeded, False otherwise.
        Raises:
            CommandUndoError: If undo encountered an unrecoverable failure.
        """
        raise NotImplementedError

    def get_memory_size(self) -> int:
        """Estimate the memory consumption of this command in bytes.
        
        Useful for future applications (like Mini Photoshop) that need
        to prune history based on RAM usage.
        """
        return sys.getsizeof(self)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} executed={self._is_executed}>"
