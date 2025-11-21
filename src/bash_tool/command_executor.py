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

from .bash_pipeline_parser import (
    parse_bash_command,
    SimpleCommand, Pipeline, AndList, OrList, Sequence,
    Subshell, CommandGroup, Background, ProcessSubstitution
)
from .execution_engine import ExecutionEngine
from .pipeline_analyzer import PipelineAnalyzer
from .execute_unix_single_command import ExecuteUnixSingleCommand
from .bash_pipeline_preprocessor import BashPipelinePreprocessor
from .bash_command_preprocessor import BashCommandPreprocessor
from .bash_variable_context import BashVariableContext


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


    def __init__(self, working_dir: Path, logger=None, test_mode=False, test_capabilities=None):
        """
        Initialize CommandExecutor.

        Args:
            working_dir: home directory
            logger: Logger instance
            test_mode: If True, use ExecutionEngine in test mode
            test_capabilities: Dict for TEST MODE ONLY - control availability
                Example: {'bash': False, 'grep': True} to force manual execution
        """

        self.working_dir = working_dir
        self.test_mode = test_mode
        self.test_capabilities = test_capabilities
        self.logger = logging.getLogger('CommandExecutor')

        # Initialize bash variable context (persists across command sequences)
        self.bash_context = BashVariableContext()

        # Initialize execution components
        self.engine = ExecutionEngine(working_dir, test_mode=test_mode, logger=self.logger, test_capabilities=test_capabilities)

        # Initialize PREPROCESSOR with context
        self.pipeline_preprocessor = BashPipelinePreprocessor(
            executor=self,  # Pass self for recursive execution
            logger=self.logger,
            temp_dir= self.working_dir / 'tmp'
        )
        self.command_preprocessor = BashCommandPreprocessor(
            logger=self.logger,
            context=self.bash_context,  # Pass context for variable tracking
            working_dir=self.working_dir  # Pass working dir for tilde expansion
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
            test_mode=test_mode,
            test_capabilities=test_capabilities
        )
        
        self.logger.info("CommandExecutor initialized with preprocessors + analyzer")

    # ========================================================================
    # MAIN EXECUTION ENTRY POINT
    # ========================================================================

    def execute(self, command: str, nesting_level: int = 0) -> subprocess.CompletedProcess:
        """
        Execute bash command - WITH PARSER + PREPROCESSOR INTEGRATION

        Flow:
        1. Parse (MINIMAL) → Detect Sequence
        2. If Sequence: Process each command separately with context
        3. Else: Normal flow (preprocess → parse → execute)

        Args:
            command: Bash command string (WINDOWS PATHS!)
            nesting_level: Recursion depth (for command substitution)

        Returns:
            CompletedProcess result
        """
        self.logger.info(f"Executing: {command[:100]}")

        temp_files = []

        try:
            # STEP 0: Parse MINIMALLY to detect structure (WITHOUT preprocessing!)
            # This allows us to detect sequences and handle them specially
            try:
                preliminary_ast = parse_bash_command(command)
                if isinstance(preliminary_ast, Sequence):
                    # Special handling for sequences to support bash variable tracking
                    self.logger.debug("Detected sequence - using per-command preprocessing")
                    return self._execute_sequence_with_context(preliminary_ast, command, nesting_level, temp_files)
            except Exception as e:
                self.logger.debug(f"Preliminary parse failed (expected for some commands): {e}")
                # Continue with normal flow

            # NORMAL FLOW: STEP 1: COMANDO PREPROCESSING CATEGORIA 1 (BEFORE parsing!)
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
                result = self._execute_via_bash(command)

            elif strategy == ExecutionStrategy.MANUAL:
                # Walk AST and execute manually
                # NO more comando preprocessing! Already done before parse!
                result = self._walk_ast(ast)

            else:
                # Fallback to bash
                result = self._execute_via_bash(command)

            # STEP 6: Process post-commands (output process substitution >(cmd))
            # These commands consume the temp files created by >(cmd) syntax
            if hasattr(temp_files, 'post_commands') and temp_files.post_commands:
                self.logger.debug(f"Processing {len(temp_files.post_commands)} post-commands")
                for temp_file, cmd in temp_files.post_commands:
                    try:
                        # Execute cmd with temp_file as stdin via redirection
                        # The main command wrote to temp_file, now cmd reads from it
                        self.logger.debug(f"Post-command: {cmd} < {temp_file}")

                        # Build command with stdin redirection
                        post_cmd = f"{cmd} < {temp_file}"

                        # Execute the post-command
                        post_result = self.execute(post_cmd, nesting_level + 1)

                        # If post-command fails, log but don't fail main command
                        if post_result.returncode != 0:
                            self.logger.warning(f"Post-command failed: {cmd}, exit={post_result.returncode}")

                    except Exception as e:
                        self.logger.error(f"Post-command execution failed: {e}")

            return result
        
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
    # SEQUENCE WITH CONTEXT - Special handling for bash variable tracking
    # ========================================================================

    def _execute_sequence_with_context(self, seq_ast: Sequence, original_command: str, nesting_level: int, temp_files: list) -> subprocess.CompletedProcess:
        """
        Execute sequence with bash variable context tracking

        This method processes each command in the sequence individually,
        allowing bash variable assignments to be tracked and used in subsequent commands.

        Example: file='test.txt'; echo ${file%.txt}.log
        - First command sets 'file' variable in context
        - Second command uses 'file' from context

        Args:
            seq_ast: Sequence AST node (for structure)
            original_command: Original command string (unparsed)
            nesting_level: Recursion depth
            temp_files: List of temp files to cleanup

        Returns:
            CompletedProcess result (last command)
        """
        self.logger.debug(f"Executing sequence with context tracking: {len(seq_ast.commands)} commands")

        # Split original command on ';' (simple split, we already know it's a sequence)
        commands = self._split_sequence_commands(original_command)
        self.logger.debug(f"Split into {len(commands)} commands: {commands}")

        result = None

        for cmd_str in commands:
            cmd_str = cmd_str.strip()
            if not cmd_str:
                continue

            self.logger.debug(f"Processing sequence command: {cmd_str}")

            # Check if this is a bash variable assignment (var=value)
            assignment_match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', cmd_str)
            if assignment_match:
                var_name = assignment_match.group(1)
                var_value = assignment_match.group(2).strip()

                # Remove quotes if present
                if (var_value.startswith("'") and var_value.endswith("'")) or \
                   (var_value.startswith('"') and var_value.endswith('"')):
                    var_value = var_value[1:-1]

                # Store in context
                self.bash_context.set(var_name, var_value)
                self.logger.debug(f"Set bash variable: {var_name}={var_value}")

                # Create a successful result
                result = subprocess.CompletedProcess(
                    args=['bash', '-c', cmd_str],
                    returncode=0,
                    stdout="",
                    stderr=""
                )
            else:
                # Normal command - preprocess and execute
                preprocessed = self.command_preprocessor.preprocess_always(cmd_str)
                self.logger.debug(f"Preprocessed: {preprocessed}")

                # Execute the command (recursively, without detecting sequences again)
                result = self._execute_non_sequence(preprocessed, nesting_level, temp_files)

        return result if result else subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    def _split_sequence_commands(self, command: str) -> List[str]:
        """
        Split command string on ';' respecting quotes and escapes

        Args:
            command: Command string with semicolons

        Returns:
            List of individual commands
        """
        commands = []
        current = []
        in_single_quote = False
        in_double_quote = False
        escape_next = False

        for char in command:
            if escape_next:
                current.append(char)
                escape_next = False
                continue

            if char == '\\':
                current.append(char)
                escape_next = True
                continue

            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
                current.append(char)
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
                current.append(char)
            elif char == ';' and not in_single_quote and not in_double_quote:
                # Found a command separator
                commands.append(''.join(current))
                current = []
            else:
                current.append(char)

        # Add last command
        if current:
            commands.append(''.join(current))

        return commands

    def _execute_non_sequence(self, command: str, nesting_level: int, temp_files: list) -> subprocess.CompletedProcess:
        """
        Execute a single (non-sequence) command

        This is the normal execution flow, extracted to avoid infinite recursion
        when processing sequences.

        Args:
            command: Preprocessed command string
            nesting_level: Recursion depth
            temp_files: List of temp files

        Returns:
            CompletedProcess result
        """
        # Parse
        ast = parse_bash_command(command)

        # Pipeline preprocessing
        command, new_temp_files = self.pipeline_preprocessor.preprocess(command, nesting_level)
        temp_files.extend(new_temp_files)

        # Re-parse after pipeline preprocessing
        ast = parse_bash_command(command)

        # Analyze strategy
        strategy = self._analyze_strategy(ast)
        self.logger.debug(f"Strategy: {strategy}")

        # Execute
        if strategy == ExecutionStrategy.BASH_FULL:
            return self._execute_via_bash(command)
        elif strategy == ExecutionStrategy.MANUAL:
            return self._walk_ast(ast)
        else:
            return self._execute_via_bash(command)

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
