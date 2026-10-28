"""Exceptions for the Undo/Redo Engine."""


class CommandError(Exception):
    """Base exception for all command-related errors."""
    pass


class CommandExecutionError(CommandError):
    """Raised when a command fails to execute."""
    pass


class CommandUndoError(CommandError):
    """Raised when a command fails to undo."""
    pass


class InvalidCommandError(CommandError):
    """Raised when a command is invalid or corrupted."""
    pass
