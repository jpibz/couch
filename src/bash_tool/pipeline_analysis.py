"""
Pipeline analysis dataclass

ARCHITECTURE:
- Immutable data structure (dataclass) containing pipeline analysis results
- Output of PipelineStrategy.analyze_pipeline()
- Input to PipelineStrategy.decide_execution_strategy()
- Part of MACRO level strategic analysis layer

RESPONSIBILITIES:
- Store structural information about a command/pipeline
- Capture complexity indicators (pipes, chains, redirections)
- Track command names and count
- Record matched patterns from PIPELINE_STRATEGIES

NOT RESPONSIBLE FOR:
- Analyzing commands (done by PipelineStrategy)
- Making execution decisions (done by PipelineStrategy)
- Executing anything

DATA FLOW:
command string → PipelineStrategy.analyze_pipeline() → PipelineAnalysis →
PipelineStrategy.decide_execution_strategy() → ExecutionStrategy

USAGE PATTERN:
analysis = pipeline_strategy.analyze_pipeline("grep pattern file | sort")
# analysis.has_pipeline = True
# analysis.command_count = 2
# analysis.command_names = ['grep', 'sort']
# analysis.complexity_level = 'MEDIUM'

DESIGN PATTERN: Data Transfer Object (DTO)
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PipelineAnalysis:
    """
    Result of pipeline structural analysis.

    Contains all information extracted from command string about:
    - Pipeline structure (pipes, chains, redirections)
    - Complexity level (HIGH, MEDIUM, LOW)
    - Commands involved
    - Pattern matches from known pipeline strategies

    This is a pure data structure with no behavior - all analysis logic
    is in PipelineStrategy. This design keeps analysis logic centralized
    and makes results easily testable and serializable.

    Architecture: Part of the MACRO level strategic analysis layer.
    Created by PipelineStrategy, consumed by strategy decision logic.
    """

    # Pipeline operators
    has_pipeline: bool = False          # Contains | operator
    has_chain: bool = False             # Contains &&, ||, or ;
    has_redirection: bool = False       # Contains >, >>, <
    has_stderr_redir: bool = False      # Contains 2>, 2>&1, |&
    has_process_subst: bool = False     # Contains <(...) or >(...)

    # Pattern matching
    matched_pattern: Optional[str] = None     # Regex pattern matched from PIPELINE_STRATEGIES
                                              # e.g., r'grep.*\|.*wc' for "grep x | wc -l"

    # Complexity assessment
    complexity_level: str = 'LOW'       # HIGH (bash required), MEDIUM (bash preferred), LOW (native ok)

    # Command information
    command_count: int = 1              # Number of commands in pipeline (1 for single command)
    command_names: List[str] = field(default_factory=list)  # List of command names ['grep', 'sort', 'uniq']

    def __str__(self) -> str:
        """Human-readable representation for debugging"""
        parts = []
        if self.has_pipeline:
            parts.append(f"pipeline({self.command_count} cmds)")
        if self.has_chain:
            parts.append("chained")
        if self.has_redirection:
            parts.append("redirected")
        if self.matched_pattern:
            parts.append(f"pattern:{self.matched_pattern}")

        return f"PipelineAnalysis({self.complexity_level}: {', '.join(parts) if parts else 'simple'})"
