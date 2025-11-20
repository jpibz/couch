"""
Command Executor - Main preprocessing and execution coordinator

ARCHITECTURE:
    execute(command_string)
        ↓
    parse_bash_command(command) → AST
        ↓
    analyze_strategy(AST) → BASH_FULL | MANUAL
        ↓
    BASH_FULL: execute_bash(original_string)
    MANUAL: walk_ast(AST) → recursive execution
        ├─ SimpleCommand → preprocess + execute_single
        ├─ Pipeline → manual pipe loop
        ├─ Sequence → execute in order
        ├─ AndList → exit code check
        ├─ OrList → exit code check
        └─ Others → bash fallback

RESPONSIBILITIES:
- Parse command into AST
- Decide execution strategy
- Walk AST recursively for manual execution
- Coordinate preprocessing and execution
- Handle all AST node types

NOT responsible for:
- Subprocess management (ExecutionEngine)
- Single command execution (ExecuteUnixSingleCommand)
- Path translation happens BEFORE this layer (in BashToolExecutor)
"""
import os
import subprocess
import re
import logging
import threading
from pathlib import Path
from typing import List, Tuple, Optional

from bash_pipeline_parser import (
    parse_bash_command,
    SimpleCommand, Pipeline, AndList, OrList, Sequence,
    Subshell, CommandGroup, Background, ProcessSubstitution
)
from execution_engine import ExecutionEngine
from pipeline_analyzer import PipelineAnalyzer
from execute_unix_single_command import ExecuteUnixSingleCommand
from bash_pipeline_preprocessor import BashPipelinePreprocessor
from bash_command_preprocessor import BashCommandPreprocessor


class ExecutionStrategy:
    """Execution strategy enum"""
    BASH_FULL = "bash_full"      # Execute entire command via bash.exe
    MANUAL = "manual"              # Manual execution (walk AST)
    HYBRID = "hybrid"              # Mix (future)

class CommandExecutor:
    """
    Command execution with parser integration.

    This is the CORE orchestrator that:
    1. Parses bash commands into AST
    2. Decides execution strategy
    3. Executes via manual walk or bash.exe

    """


    def __init__(self, working_dir="\\", logger=None, test_mode=False):
        """
        Initialize CommandExecutor.

        Args:
            working_dir: home directory
            logger: Logger instance
            test_mode: If True, use ExecutionEngine in test mode
        """

        self.working_dir = working_dir
        self.test_mode = test_mode
        self.logger = logging.getLogger('CommandExecutor')

        # Initialize execution components
        self.engine = ExecutionEngine(working_dir, test_mode=test_mode, logger=self.logger)

        # Initialize PREPROCESSOR
        self.pipeline_preprocessor = BashPipelinePreprocessor(
            executor=self,  # Pass self for recursive execution
            logger=self.logger
        )
        self.command_preprocessor = BashCommandPreprocessor(
            logger=self.logger
        )

        # Initialize ANALYZER (INTELLIGENZA STRATEGICA!)
        self.analyzer = PipelineAnalyzer(
            engine=self.engine,
            logger=self.logger
        )

        self.single_executor = ExecuteUnixSingleCommand(
            command_preprocessor=self.command_preprocessor,
            working_dir=working_dir,
            logger=self.logger,
            test_mode=test_mode
        )
        
        self.logger.info("CommandExecutor initialized with preprocessors + analyzer")

    # ========================================================================
    # MAIN EXECUTION ENTRY POINT
    # ========================================================================

    def execute(self, command: str, nesting_level: int = 0) -> subprocess.CompletedProcess:
        """
        Execute bash command - WITH PARSER + PREPROCESSOR INTEGRATION
        
        Flow:
        1. Parse → AST
        2. PIPELINE PREPROCESSING (command subst, process subst, heredocs)
        3. Analyze → Strategy
        4. Execute → Based on strategy
        
        Args:
            command: Bash command string (WINDOWS PATHS!)
            nesting_level: Recursion depth (for command substitution)
            
        Returns:
            CompletedProcess result
        """
        self.logger.info(f"Executing: {command[:100]}")
        
        temp_files = []
        
        try:
            # STEP 1: COMANDO PREPROCESSING CATEGORIA 1 (BEFORE parsing!)
            # This MUST happen BEFORE parse because parser destroys ${VAR} and {1..3} syntax!
            # Variables, braces, arithmetic, tilde, aliases - all SAFE expansions
            command = self.command_preprocessor.preprocess_always(command)
            self.logger.debug(f"After comando preprocessing: {command[:100]}")
            
            # STEP 2: Parse command into AST (now with expanded variables/braces)
            ast = parse_bash_command(command)
            self.logger.debug(f"AST: {ast}")
            
            # STEP 3: PIPELINE LEVEL PREPROCESSING
            # This handles command substitution, process substitution, heredocs
            # MODIFIES the command string BEFORE strategy analysis
            command, temp_files = self.pipeline_preprocessor.preprocess(command, nesting_level)
            self.logger.debug(f"After pipeline preprocessing: {command[:100]}")
            
            # Re-parse after preprocessing (structure may have changed)
            ast = parse_bash_command(command)
            
            # STEP 4: Analyze execution strategy
            strategy = self._analyze_strategy(ast)
            self.logger.debug(f"Strategy: {strategy}")
            
            # STEP 5: Execute based on strategy
            if strategy == ExecutionStrategy.BASH_FULL:
                # Execute entire command via bash.exe
                # NO more preprocessing! Already done!
                return self._execute_via_bash(command)
            
            elif strategy == ExecutionStrategy.MANUAL:
                # Walk AST and execute manually
                # NO more comando preprocessing! Already done before parse!
                return self._walk_ast(ast)
            
            else:
                # Fallback to bash
                return self._execute_via_bash(command)
        
        except Exception as e:
            self.logger.error(f"Execution error: {e}", exc_info=True)
            return subprocess.CompletedProcess(
                args=['bash', '-c', command],
                returncode=1,
                stdout="",
                stderr=f"Error: {str(e)}"
            )
        
        finally:
            # Cleanup temp files
            for temp_file in temp_files:
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                        self.logger.debug(f"Cleaned up temp file: {temp_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup {temp_file}: {e}")
    
    # ========================================================================
    # STRATEGY ANALYSIS
    # ========================================================================
    
    def _analyze_strategy(self, ast) -> str:
        """
        Analyze AST and decide execution strategy
        
        NUOVO APPROCCIO "CAZZIMMA NAPOLETANA":
        1. Usa PipelineAnalyzer per analisi intelligente
        2. Controlla disponibilità comandi
        3. Decide: BASH_FULL (passthrough) vs MANUAL
        
        BASH_FULL if:
        - Tutti i comandi disponibili (builtin o native .exe)
        - Strutture complesse (subshell, background, etc)
        
        MANUAL if:
        - Alcuni comandi need emulation
        - bash.exe non disponibile
        
        Args:
            ast: AST root node
            
        Returns:
            ExecutionStrategy enum value
        """
        # Use ANALYZER for intelligent decision
        result = self.analyzer.analyze(ast)
        
        # Log decision
        self.logger.info(f"[ANALYZER] Strategy: {result.strategy}")
        self.logger.info(f"[ANALYZER] Reason: {result.reason}")
        self.logger.debug(f"[ANALYZER] Commands: {[c.name for c in result.commands]}")
        
        # Convert to ExecutionStrategy enum
        if result.strategy == 'bash_full':
            return ExecutionStrategy.BASH_FULL
        elif result.strategy == 'hybrid':
            # FUTURE: Implement hybrid
            # For now, fallback to MANUAL
            return ExecutionStrategy.MANUAL
        else:
            return ExecutionStrategy.MANUAL
    
    def _requires_bash(self, node) -> bool:
        """Check if node requires bash.exe"""
        if isinstance(node, (Subshell, CommandGroup, Background)):
            return True
        
        if isinstance(node, Pipeline):
            return any(self._requires_bash(cmd) for cmd in node.commands)
        
        if isinstance(node, Sequence):
            return any(self._requires_bash(cmd) for cmd in node.commands)
        
        if isinstance(node, (AndList, OrList)):
            return self._requires_bash(node.left) or self._requires_bash(node.right)
        
        return False
    
    # ========================================================================
    # BASH EXECUTION
    # ========================================================================
    
    def _execute_via_bash(self, command: str) -> subprocess.CompletedProcess:
        """
        Execute entire command via bash.exe
        
        NO preprocessing needed - bash handles everything.
        """
        self.logger.debug(f"Executing via bash: {command[:100]}")
        return self.engine.execute_bash(command)
    
    # ========================================================================
    # MANUAL EXECUTION - AST WALKING
    # ========================================================================
    
    def _walk_ast(self, node, stdin: str = None) -> subprocess.CompletedProcess:
        """
        Walk AST recursively and execute manually
        
        This is the CORE manual execution logic.
        Handles all AST node types.
        
        Args:
            node: AST node
            stdin: Optional stdin data for command
            
        Returns:
            CompletedProcess result
        """
        if isinstance(node, SimpleCommand):
            return self._execute_simple_command(node, stdin=stdin)
        
        elif isinstance(node, Pipeline):
            return self._execute_pipeline_manual(node)
        
        elif isinstance(node, Sequence):
            return self._execute_sequence(node)
        
        elif isinstance(node, AndList):
            return self._execute_and_list(node)
        
        elif isinstance(node, OrList):
            return self._execute_or_list(node)
        
        elif isinstance(node, (Subshell, CommandGroup, Background)):
            # These should have been caught by strategy analysis
            # Fallback to bash
            self.logger.warning(f"Unexpected node type in manual execution: {type(node)}")
            raise RuntimeError(f"Node type {type(node)} requires bash but strategy was MANUAL")
        
        else:
            raise RuntimeError(f"Unknown AST node type: {type(node)}")
    
    def _execute_simple_command(self, node: SimpleCommand, stdin: str = None) -> subprocess.CompletedProcess:
        """
        Execute simple command (preprocessing already done!)
        
        Steps:
        1. Reconstruct command string
        2. Analyze MICRO strategy (bash/native/emulated)
        3. PREPROCESSING CATEGORIA 2 (SOLO SE EMULATED!)
        4. Execute with appropriate method
        
        NOTE: Categoria 1 preprocessing (variables, braces, etc) was ALREADY done 
              before parsing! We only do categoria 2 (dangerous translation) here if needed.
        
        Args:
            node: SimpleCommand node
            stdin: Optional stdin data
            
        Returns:
            CompletedProcess result
        """
        # Reconstruct command string from AST
        cmd_str = self._reconstruct_command(node)
        
        # Execute with MICRO strategy for this specific command
        result = self.single_executor.execute(cmd_str, stdin=stdin)
        
        # Handle redirects (simplified)
        if node.redirects:
            result = self._apply_redirects(result, node.redirects)
        
        return result
    
    def _execute_pipeline_manual(self, node: Pipeline) -> subprocess.CompletedProcess:
        """
        Execute pipeline manually: cmd1 | cmd2 | cmd3
        
        Manual pipe loop:
        - stdout of cmd1 → stdin of cmd2
        - stdout of cmd2 → stdin of cmd3
        - Return final result
        
        FIXED: Now properly passes stdin between commands!
        
        Args:
            node: Pipeline node
            
        Returns:
            CompletedProcess result
        """
        self.logger.debug(f"Manual pipeline: {len(node.commands)} commands")
        
        stdin_data = None
        result = None
        
        for i, cmd_node in enumerate(node.commands):
            self.logger.debug(f"  Pipeline stage {i+1}/{len(node.commands)}")
            
            # Execute this command WITH stdin from previous
            result = self._walk_ast(cmd_node, stdin=stdin_data)
            
            # Pass stdout to next command as stdin
            if i < len(node.commands) - 1:
                stdin_data = result.stdout
        
        return result
    
    def _execute_sequence(self, node: Sequence) -> subprocess.CompletedProcess:
        """
        Execute sequence: cmd1 ; cmd2 ; cmd3
        
        Execute all commands in order, return last result.
        
        Args:
            node: Sequence node
            
        Returns:
            CompletedProcess result (last command)
        """
        result = None
        
        for cmd_node in node.commands:
            result = self._walk_ast(cmd_node)
        
        return result
    
    def _execute_and_list(self, node: AndList) -> subprocess.CompletedProcess:
        """
        Execute AND list: cmd1 && cmd2
        
        Execute cmd2 ONLY if cmd1 succeeded (exit code 0).
        
        Args:
            node: AndList node
            
        Returns:
            CompletedProcess result
        """
        left_result = self._walk_ast(node.left)
        
        if left_result.returncode == 0:
            # Left succeeded → execute right
            return self._walk_ast(node.right)
        else:
            # Left failed → return left result
            return left_result
    
    def _execute_or_list(self, node: OrList) -> subprocess.CompletedProcess:
        """
        Execute OR list: cmd1 || cmd2
        
        Execute cmd2 ONLY if cmd1 failed (exit code != 0).
        
        Args:
            node: OrList node
            
        Returns:
            CompletedProcess result
        """
        left_result = self._walk_ast(node.left)
        
        if left_result.returncode != 0:
            # Left failed → execute right
            return self._walk_ast(node.right)
        else:
            # Left succeeded → return left result
            return left_result

    # UTILITIES
    # ========================================================================
    
    def _reconstruct_command(self, node: SimpleCommand) -> str:
        """
        Reconstruct command string from SimpleCommand node
        
        Args:
            node: SimpleCommand node
            
        Returns:
            Command string
        """
        parts = [node.command]
        
        # Add args (skip ProcessSubstitution for now - complex)
        for arg in node.args:
            if isinstance(arg, str):
                parts.append(arg)
            # ProcessSubstitution would need temp file creation
        
        return ' '.join(parts)
    
    def _apply_redirects(self, result: subprocess.CompletedProcess, redirects: list) -> subprocess.CompletedProcess:
        """
        Apply redirects to result (simplified)
        
        In real system, this would handle file I/O.
        Here we just log for testing.
        """
        for redirect in redirects:
            self.logger.debug(f"Redirect: {redirect}")
            # In real system: write stdout/stderr to files
        
        return result
