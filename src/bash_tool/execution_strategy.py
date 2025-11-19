"""
Execution strategy dataclass
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ExecutionStrategy:
    """
    Execution strategy decision for a command/pipeline.

    Describes HOW to execute the command and what fallbacks are available.
    """
    strategy_type: str  # BASH_REQUIRED, BASH_PREFERRED, HYBRID, NATIVE, POWERSHELL
    can_split: bool = False             # Can split pipeline into parts
    split_points: List[int] = field(default_factory=list)  # Where to split
    reason: str = ""                    # Why this strategy was chosen
    fallback_strategy: Optional['ExecutionStrategy'] = None  # Fallback if primary fails
