"""
Base class for tool executors
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict


class ToolExecutor(ABC):
    """Base class per tool executors"""

    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled
        self.logger = logging.getLogger(f"ToolExecutor.{name}")

    @abstractmethod
    def execute(self, tool_input: Dict) -> str:
        """Execute tool con input"""
        pass

    @abstractmethod
    def get_definition(self) -> Dict:
        """Return tool definition per API payload"""
        pass

    def enable(self):
        """Enable tool"""
        self.enabled = True

    def disable(self):
        """Disable tool"""
        self.enabled = False
