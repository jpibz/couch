"""
Bash Variable Context - Track bash local variables across command sequences

This module provides a context for storing bash variables that are set during
command execution (e.g., file='test.txt') and retrieved during variable expansion
(e.g., ${file%.txt}).

Architecture:
    - BashVariableContext: Simple dict-based storage for bash variables
    - Used by BashCommandPreprocessor to expand variables
    - Updated by command execution when assignments are detected

Example:
    >>> context = BashVariableContext()
    >>> context.set('file', 'test.txt')
    >>> context.get('file')
    'test.txt'
    >>> context.get('missing', 'default')
    'default'
"""

from typing import Optional, Dict


class BashVariableContext:
    """
    Context for bash local variables.

    Stores variables set during command execution (var=value)
    and provides them for variable expansion (${var}).
    """

    def __init__(self):
        """Initialize empty variable context"""
        self._variables: Dict[str, str] = {}

    def set(self, name: str, value: str) -> None:
        """
        Set a bash variable

        Args:
            name: Variable name
            value: Variable value
        """
        self._variables[name] = value

    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a bash variable value

        Args:
            name: Variable name
            default: Default value if not found

        Returns:
            Variable value or default
        """
        return self._variables.get(name, default)

    def has(self, name: str) -> bool:
        """
        Check if variable exists

        Args:
            name: Variable name

        Returns:
            True if variable exists
        """
        return name in self._variables

    def delete(self, name: str) -> None:
        """
        Delete a variable

        Args:
            name: Variable name
        """
        self._variables.pop(name, None)

    def clear(self) -> None:
        """Clear all variables"""
        self._variables.clear()

    def copy(self) -> 'BashVariableContext':
        """
        Create a copy of this context (for subshells)

        Returns:
            New context with same variables
        """
        new_context = BashVariableContext()
        new_context._variables = self._variables.copy()
        return new_context

    def __repr__(self) -> str:
        return f"BashVariableContext({self._variables})"
