"""
Pipeline analysis dataclass
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PipelineAnalysis:
    """
    Result of pipeline strategic analysis.

    Contains all information needed to decide execution strategy.
    """
    has_pipeline: bool = False          # Contains | operator
    has_chain: bool = False             # Contains &&, ||, or ;
    has_redirection: bool = False       # Contains >, >>, <
    has_stderr_redir: bool = False      # Contains 2>, 2>&1, |&
    has_process_subst: bool = False     # Contains <(...) or >(...)
    matched_pattern: Optional[str] = None     # Regex pattern matched from PIPELINE_STRATEGIES
    complexity_level: str = 'LOW'       # HIGH, MEDIUM, LOW
    command_count: int = 1              # Number of commands in pipeline
    command_names: List[str] = field(default_factory=list)  # List of command names
