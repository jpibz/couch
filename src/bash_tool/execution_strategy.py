"""
Execution strategy dataclass

ARCHITECTURE:
- Immutable data structure (dataclass) describing HOW to execute a command
- Output of PipelineStrategy.decide_execution_strategy()
- Input to CommandExecutor execution dispatch logic
- Part of MACRO level strategic decision layer

RESPONSIBILITIES:
- Store execution strategy decision (BASH_REQUIRED, HYBRID, NATIVE, etc.)
- Capture splitting information for HYBRID strategies
- Record decision rationale for debugging/logging
- Provide fallback strategy chain

NOT RESPONSIBLE FOR:
- Making strategy decisions (done by PipelineStrategy)
- Executing commands (done by CommandExecutor/ExecutionEngine)
- Analyzing pipelines (done by PipelineStrategy)

STRATEGY TYPES:
- BASH_REQUIRED: Must use bash.exe (complex features, no alternative)
- BASH_PREFERRED: Prefer bash.exe but can fallback to emulation
- HYBRID: Split pipeline, execute parts separately with coordination
- NATIVE: Use native Windows binary (grep.exe, awk.exe)
- POWERSHELL: Use PowerShell emulation script
- FAIL: Cannot execute (explain in reason)

DATA FLOW:
PipelineAnalysis → PipelineStrategy.decide_execution_strategy() → ExecutionStrategy →
CommandExecutor dispatch → actual execution

USAGE PATTERN:
strategy = pipeline_strategy.decide_execution_strategy(analysis, command)
# strategy.strategy_type = 'BASH_PREFERRED'
# strategy.reason = 'Complex awk with BEGIN/END blocks'
# strategy.fallback_strategy = ExecutionStrategy('POWERSHELL', reason='...')

if strategy.strategy_type == 'HYBRID':
    segments = split_pipeline(command, strategy.split_points)

DESIGN PATTERN: Data Transfer Object (DTO) + Chain of Responsibility (fallback)
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ExecutionStrategy:
    """
    Execution strategy decision for a command/pipeline.

    Describes HOW to execute a command after analyzing its structure.
    Contains:
    - Strategy type (BASH_REQUIRED, HYBRID, NATIVE, etc.)
    - Splitting information for HYBRID strategies
    - Rationale for the decision
    - Fallback strategy if primary fails

    This is a decision data structure that drives CommandExecutor's
    execution dispatch logic. The strategy is chosen by PipelineStrategy
    based on command complexity, available tools, and pattern matching.

    Architecture: Bridge between MACRO analysis (PipelineStrategy) and
    execution dispatch (CommandExecutor). Separates "what to do" decision
    from "how to do it" implementation.

    Design: Immutable value object that can be passed through call stack
    without side effects. Fallback chain enables graceful degradation.
    """

    # Primary strategy
    strategy_type: str  # BASH_REQUIRED, BASH_PREFERRED, HYBRID, NATIVE, POWERSHELL, FAIL

    # Splitting information (for HYBRID)
    can_split: bool = False             # True if pipeline can be divided into segments
    split_points: List[int] = field(default_factory=list)  # Indices where to split (e.g., [1, 2] for 3-segment pipeline)

    # Decision metadata
    reason: str = ""                    # Human-readable explanation of strategy choice
                                        # e.g., "Complex awk with arrays requires bash.exe"
                                        # Useful for debugging and logging

    # Fallback chain
    fallback_strategy: Optional['ExecutionStrategy'] = None  # Alternative if primary fails
                                                              # e.g., BASH_PREFERRED might fallback to POWERSHELL

    def __str__(self) -> str:
        """Human-readable representation for debugging"""
        parts = [self.strategy_type]
        if self.can_split:
            parts.append(f"split@{self.split_points}")
        if self.reason:
            parts.append(f"({self.reason})")
        if self.fallback_strategy:
            parts.append(f"→ fallback:{self.fallback_strategy.strategy_type}")
        return f"ExecutionStrategy[{' '.join(parts)}]"

    def has_fallback(self) -> bool:
        """Check if fallback strategy is available"""
        return self.fallback_strategy is not None

    def is_bash_strategy(self) -> bool:
        """Check if this strategy uses bash.exe"""
        return self.strategy_type in ['BASH_REQUIRED', 'BASH_PREFERRED']

    def requires_splitting(self) -> bool:
        """Check if this strategy requires pipeline splitting"""
        return self.strategy_type == 'HYBRID' and self.can_split and len(self.split_points) > 0
