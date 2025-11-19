"""
Base class for tool executors

ARCHITECTURE:
- Abstract base class (ABC) for all tool executors in the system
- Provides common interface and logging infrastructure
- Concrete implementations: BashToolExecutor, (future: PythonToolExecutor, etc.)

RESPONSIBILITIES:
- Define execute() contract for all tools
- Define get_definition() contract for API schema
- Provide enable/disable functionality
- Initialize logging per tool

NOT RESPONSIBLE FOR:
- Actual command execution (delegated to concrete classes)
- Tool-specific logic
- Configuration management

USAGE PATTERN:
class MyTool(ToolExecutor):
    def __init__(self):
        super().__init__('my_tool', enabled=True)

    def execute(self, tool_input: Dict) -> str:
        # Implementation
        pass

    def get_definition(self) -> Dict:
        # Return OpenAI function schema
        pass

DESIGN PATTERN: Template Method + Strategy
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict


class ToolExecutor(ABC):
    """
    Base class for all tool executors.

    Provides common infrastructure for tool execution including:
    - Name and enabled state management
    - Per-tool logger initialization
    - Abstract methods that subclasses must implement

    Architecture: This is the top-level interface in the tool execution hierarchy.
    All concrete tools (BashToolExecutor, etc.) inherit from this base.
    """

    def __init__(self, name: str, enabled: bool = True):
        """
        Initialize tool executor.

        Args:
            name: Unique tool identifier (e.g., 'bash_tool', 'python_tool')
            enabled: Whether tool is active (default: True)
        """
        self.name = name
        self.enabled = enabled
        self.logger = logging.getLogger(f"ToolExecutor.{name}")

    @abstractmethod
    def execute(self, tool_input: Dict) -> str:
        """
        Execute tool with given input.

        Args:
            tool_input: Dictionary with tool-specific parameters
                       (schema defined by get_definition())

        Returns:
            str: Execution result (stdout, error message, etc.)

        Architecture: This is the main entry point called by the agent.
        Concrete implementations handle all tool-specific logic here.
        """
        pass

    @abstractmethod
    def get_definition(self) -> Dict:
        """
        Return tool definition for API payload.

        Returns:
            Dict: OpenAI function calling schema with:
                  - name: tool name
                  - description: what the tool does
                  - parameters: JSON schema for tool_input

        Architecture: This schema tells the LLM how to use the tool.
        Must follow OpenAI function calling specification.
        """
        pass

    def enable(self):
        """Enable tool execution"""
        self.enabled = True
        self.logger.info(f"Tool '{self.name}' enabled")

    def disable(self):
        """Disable tool execution"""
        self.enabled = False
        self.logger.info(f"Tool '{self.name}' disabled")
