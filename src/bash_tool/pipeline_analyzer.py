"""
PipelineAnalyzer - PRIMO LAYER DI INTELLIGENZA STRATEGICA

RESPONSABILITÀ:
- Analizza AST della pipeline
- Estrae TUTTI i comandi
- Controlla disponibilità (bash builtin, native .exe, emulazione needed)
- Decide strategia: BASH_FULL | HYBRID | MANUAL

FILOSOFIA "CAZZIMMA NAPOLETANA":
Se bash.exe è disponibile E tutti i comandi sono eseguibili (builtin o .exe),
allora PASSTHROUGH DIRETTO a bash.exe = MASSIMA PERFORMANCE!

Altrimenti, intelligentemente decide dove spezzare.
"""
import logging
from typing import List, Tuple, Set
from dataclasses import dataclass

# AST node types
from bash_pipeline_parser import (
    SimpleCommand, Pipeline, AndList, OrList, Sequence,
    Subshell, CommandGroup, Background, ProcessSubstitution
)


@dataclass
class CommandInfo:
    """Info about a command in the pipeline"""
    name: str                    # Command name (e.g., 'grep', 'ls')
    is_builtin: bool = False     # Bash builtin?
    is_native: bool = False      # Native .exe available?
    needs_emulation: bool = False  # Needs PowerShell emulation?
    ast_node: any = None         # Reference to AST node


@dataclass
class AnalysisResult:
    """Result of pipeline analysis"""
    strategy: str                # 'bash_full', 'manual', 'hybrid'
    commands: List[CommandInfo]  # All commands found
    reason: str                  # Why this strategy?
    can_passthrough: bool        # Can we passthrough to bash?


class PipelineAnalyzer:
    """
    Analizza pipeline e decide strategia INTELLIGENTEMENTE
    
    FIRST LAYER: Check command availability
    - In BLACKLIST (unsupported)? ❌
    - Native .exe in PATH? ✅
    - Else: ✅ (assume bash supporta, degrada se fallisce)
    
    FUTURE LAYERS:
    - Complexity analysis (how many commands?)
    - Performance prediction (emulation cost vs bash overhead)
    - Sub-pipeline optimization (where to split?)
    """
    
    # BLACKLIST: Commands Git Bash does NOT support
    # SHORT LIST = Better performance + More robust
    BASH_UNSUPPORTED = {
        # System/service management (systemd/init specific)
        'systemctl', 'service', 'chkconfig', 'update-rc.d',
        
        # Package managers (OS-specific)
        'apt', 'apt-get', 'aptitude', 'dpkg',
        'yum', 'dnf', 'rpm', 'zypper',
        'pacman', 'emerge',
        
        # SELinux/AppArmor (security)
        'setenforce', 'getenforce', 'sestatus',
        'aa-status', 'aa-enforce',
        
        # Kernel modules (OS-specific)
        'modprobe', 'rmmod', 'insmod', 'lsmod',
        
        # Network configuration (OS-specific)
        'ifconfig', 'ip', 'netstat', 'ss',
        'ufw', 'firewall-cmd', 'iptables',
        
        # Other OS-specific
        'useradd', 'userdel', 'groupadd', 'groupdel',
        'mount', 'umount', 'fdisk', 'parted',
    }
    
    def __init__(self, engine, logger=None):
        """
        Initialize analyzer
        
        Args:
            engine: ExecutionEngine instance (for bin availability check)
            logger: Logger instance
        """
        self.engine = engine
        self.logger = logger or logging.getLogger('PipelineAnalyzer')
    
    def analyze(self, ast) -> AnalysisResult:
        """
        Analyze pipeline AST and decide strategy
        
        LOGIC:
        1. Extract ALL commands from AST
        2. For each command, check:
           - Is bash builtin? ✅ available
           - Is native .exe? ✅ available (if bash.exe can call it)
           - Needs emulation? ❌ not available via bash
        3. Decide:
           - ALL available → BASH_FULL (passthrough!)
           - SOME missing → HYBRID (future) or MANUAL (now)
           - Complex structure (subshell, etc) → BASH_FULL (bash handles it)
        
        Args:
            ast: Parsed AST from BashPipelineParser
            
        Returns:
            AnalysisResult with strategy decision
        """
        # Extract all commands
        commands = self._extract_commands(ast)
        
        # Check availability for each
        for cmd_info in commands:
            self._check_availability(cmd_info)
        
        # Decide strategy
        strategy, reason = self._decide_strategy(ast, commands)
        
        # Check if we can passthrough
        can_passthrough = strategy == 'bash_full' and self.engine.bash_available
        
        return AnalysisResult(
            strategy=strategy,
            commands=commands,
            reason=reason,
            can_passthrough=can_passthrough
        )
    
    def _extract_commands(self, node) -> List[CommandInfo]:
        """
        Extract ALL commands from AST recursively
        
        Args:
            node: AST node
            
        Returns:
            List of CommandInfo
        """
        commands = []
        
        if isinstance(node, SimpleCommand):
            # Simple command - extract command name
            # CRITICAL: Use node.command (not node.args[0])!
            # node.command = 'python3'
            # node.args = ['script.py']
            if node.command:
                cmd_name = node.command
                commands.append(CommandInfo(
                    name=cmd_name,
                    ast_node=node
                ))
        
        elif isinstance(node, Pipeline):
            # Pipeline - extract from all commands
            for cmd in node.commands:
                commands.extend(self._extract_commands(cmd))
        
        elif isinstance(node, (AndList, OrList)):
            # Logical operators - extract from both sides
            commands.extend(self._extract_commands(node.left))
            commands.extend(self._extract_commands(node.right))
        
        elif isinstance(node, Sequence):
            # Sequence - extract from all commands
            for cmd in node.commands:
                commands.extend(self._extract_commands(cmd))
        
        elif isinstance(node, (Subshell, CommandGroup)):
            # Subshell/group - extract from inner command
            commands.extend(self._extract_commands(node.command))
        
        elif isinstance(node, Background):
            # Background - extract from command
            commands.extend(self._extract_commands(node.command))
        
        # ProcessSubstitution: skip for now (bash handles it)
        
        return commands
    
    def _check_availability(self, cmd_info: CommandInfo):
        """
        Check if command is available
        
        LOGIC (BLACKLIST approach):
        1. python3 → translate to python (Windows compat)
        2. In BASH_UNSUPPORTED? → needs_emulation = True
        3. Native .exe in PATH? → is_native = True
        4. Else: → is_builtin = True (assume bash supports)
        
        PHILOSOPHY:
        - Git Bash supports 95% of commands
        - Faster to check SHORT blacklist than LONG whitelist
        - If forgotten in blacklist → tries bash → degrades gracefully if fails
        - If forgotten in whitelist → says "not available" → BREAKS
        
        Args:
            cmd_info: CommandInfo to check
        """
        cmd_name = cmd_info.name
        
        # SPECIAL CASE: python3 → python (Windows doesn't have python3)
        if cmd_name == 'python3':
            cmd_name = 'python'
        
        # Check BLACKLIST first (fast!)
        if cmd_name in self.BASH_UNSUPPORTED:
            cmd_info.needs_emulation = True
            return
        
        # Check native binary availability
        # If found → mark as native (bash can call it via PATH)
        if self.engine.is_available(cmd_name):
            cmd_info.is_native = True
            return
        
        # Default: assume bash builtin/supported
        # If wrong, bash will fail → degrades gracefully
        cmd_info.is_builtin = True
    
    def _decide_strategy(self, ast, commands: List[CommandInfo]) -> Tuple[str, str]:
        """
        Decide execution strategy based on analysis
        
        DECISION TREE:
        1. Complex structure (subshell, background)? → BASH_FULL (let bash handle)
        2. No bash.exe available? → MANUAL
        3. ALL commands available (builtin or native)? → BASH_FULL (passthrough!)
        4. SOME commands need emulation? → MANUAL (for now, HYBRID in future)
        
        Args:
            ast: Root AST node
            commands: List of CommandInfo
            
        Returns:
            (strategy, reason)
        """
        # Check if bash.exe is available
        if not self.engine.bash_available:
            return ('manual', 'bash.exe not available')
        
        # Check for complex structures that bash should handle
        if self._has_complex_structure(ast):
            return ('bash_full', 'complex structure (subshell/background/etc)')
        
        # Check command availability
        all_available = all(
            cmd.is_builtin or cmd.is_native 
            for cmd in commands
        )
        
        if all_available:
            # ALL commands available! PASSTHROUGH!
            return ('bash_full', f'all {len(commands)} commands available (builtin or native)')
        
        # Some commands need emulation
        missing_count = sum(1 for cmd in commands if cmd.needs_emulation)
        missing_names = [cmd.name for cmd in commands if cmd.needs_emulation]
        
        # For now: MANUAL
        # Future: HYBRID (split pipeline at emulation points)
        return (
            'manual', 
            f'{missing_count} commands need emulation: {", ".join(missing_names[:3])}'
        )
    
    def _has_complex_structure(self, node) -> bool:
        """
        Check if AST has complex structures that bash should handle
        
        Complex structures:
        - Subshell ()
        - Background &
        - Command groups {}
        - Process substitution <() >()
        
        These are better handled by bash.exe directly.
        
        Args:
            node: AST node
            
        Returns:
            True if complex
        """
        if isinstance(node, (Subshell, Background, CommandGroup, ProcessSubstitution)):
            return True
        
        # Recursively check children
        if isinstance(node, Pipeline):
            return any(self._has_complex_structure(cmd) for cmd in node.commands)
        
        if isinstance(node, (AndList, OrList)):
            return (self._has_complex_structure(node.left) or 
                    self._has_complex_structure(node.right))
        
        if isinstance(node, Sequence):
            return any(self._has_complex_structure(cmd) for cmd in node.commands)
        
        return False
