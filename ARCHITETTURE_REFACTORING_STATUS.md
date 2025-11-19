# ARCHITETTURE REFACTORING STATUS

## Documento Integrato - Strategia di Refactoring CommandExecutor

Questo documento definisce l'architettura finale dopo il refactoring verso una struttura modulare a responsabilità separate.

---

## 1. ARCHITETTURA FINALE: Gerarchia a Livelli Separati

### Gerarchia Complessiva

```
CommandExecutor (Orchestratore generale)
│
├─ PathTranslator (Unix↔Windows path translation)
│  ├─ to_windows(unix_path) → Windows Path
│  ├─ to_unix(windows_path) → Unix path
│  └─ translate_paths_in_string(text, direction)
│
├─ ExecutionEngine (Unico punto esecuzione subprocess)
│  ├─ execute_cmd(command) → subprocess result
│  ├─ execute_powershell(command) → subprocess result
│  ├─ execute_bash(bash_path, command) → subprocess result
│  ├─ execute_native(bin_path, args) → subprocess result
│  ├─ Python venv detection & setup
│  ├─ Capabilities detection (available dict)
│  └─ Test mode bypass
│
├─ CommandEmulator (Unix→Windows command translation)
│  ├─ command_map: 73 comandi Unix mappati
│  │  ├─ SIMPLE (<20 linee): pwd, cd, mkdir, rm, mv, chmod, etc.
│  │  ├─ MEDIUM (20-100 linee): cat, ls, cp, grep, head, tail, wc, etc.
│  │  └─ COMPLEX (>100 linee - FALLBACK): curl, sed, awk, find, jq, etc.
│  └─ emulate_command(unix_command) → translated_command
│
├─ PipelineStrategy (LIVELLO MACRO - analisi intera pipeline)
│  ├─ analyze_pipeline(command) → PipelineAnalysis
│  │  ├─ Detect: pipeline, chain, redirection, process_subst
│  │  ├─ Pattern matching (PIPELINE_STRATEGIES)
│  │  └─ Return: strategia complessiva
│  └─ decide_execution_strategy(analysis) → ExecutionStrategy
│     ├─ BASH_REQUIRED (process subst, complex chains)
│     ├─ BASH_PREFERRED (find, awk, sed pipelines)
│     ├─ HYBRID (parte bash, parte emulation)
│     ├─ NATIVE_BINS (tar, grep nativi)
│     └─ POWERSHELL (emulation completa)
│
└─ ExecuteUnixSingleCommand (LIVELLO MICRO - singolo comando)
   ├─ Usa CommandEmulator per traduzione comandi
   ├─ Usa ExecutionEngine per esecuzione subprocess
   ├─ Gestisce priority chain e fallback tattici
   └─ execute_single(cmd_name, command, parts) → (cmd, use_powershell)
```

---

## 2. FLUSSO DI ESECUZIONE DETTAGLIATO

### Sequenza Completa

```
CommandExecutor.execute(command)
│
├─ 1. Path Translation (PathTranslator)
│  └─ Unix paths → Windows paths in command string
│
├─ 2. Pipeline Analysis (PipelineStrategy MACRO)
│  └─→ PipelineAnalysis {
│       has_pipeline, has_chain, has_redirection,
│       has_process_subst, matched_pattern, complexity_level
│     }
│
├─ 3. Strategy Decision (PipelineStrategy)
│  └─→ ExecutionStrategy {
│       strategy_type: BASH_REQUIRED|BASH_PREFERRED|HYBRID|NATIVE|POWERSHELL
│       can_split, split_points, fallback_strategy
│     }
│
├─ 4a. Se strategy_type == BASH_REQUIRED/PREFERRED
│  └─→ ExecutionEngine.execute_bash(bash_path, command)
│
├─ 4b. Se strategy_type == HYBRID
│  └─→ Suddividi pipeline + esecuzione mista
│
└─ 4c. Se strategy_type == NATIVE/POWERSHELL (MICRO level)
   └─→ ExecuteUnixSingleCommand.execute_single()
       │
       ├─ Scelta tattica comando singolo
       │
       ├─→ CommandEmulator.emulate_command()
       │   └─ Traduce Unix → Windows/PowerShell
       │
       └─→ ExecutionEngine.execute_*()
           └─ Esegue subprocess con strategia scelta
```

---

## 3. DETTAGLIO CLASSI E RESPONSABILITÀ

### 3.1 PathTranslator

**Responsabilità**: Traduzione path Unix↔Windows

```python
class PathTranslator:
    """
    Unix↔Windows path translation layer.

    VIRTUAL UNIX STRUCTURE (Claude-side):
    /home/claude              → Claude's working directory
    /mnt/user-data/uploads    → User uploaded files
    /mnt/user-data/outputs    → Files for user download

    REAL WINDOWS STRUCTURE (Backend):
    workspace_root/claude/    → Shared Claude working directory
    workspace_root/uploads/   → Shared uploads
    workspace_root/outputs/   → Shared outputs
    """

    def to_windows(self, unix_path: str) -> Path:
        """Translate Unix path → Windows Path"""

    def to_unix(self, windows_path: Path) -> str:
        """Translate Windows Path → Unix path"""

    def translate_paths_in_string(self, text: str, direction: str) -> str:
        """Find and translate all paths in text"""
```

### 3.2 ExecutionEngine

**Responsabilità**: UNICO punto esecuzione subprocess + Environment Management

```python
class ExecutionEngine:
    """
    UNICO PUNTO di esecuzione subprocess.

    RESPONSABILITÀ:
    - Test mode: stampa comandi invece di eseguire
    - Logging: traccia tutte le execution
    - Metrics: conta tipi di execution (cmd, powershell, bash, native)
    - Python venv: setup e attivazione automatica virtual environment
    - Capabilities: detection binaries nativi e funzionalità disponibili
    - Environment: gestione variabili ambiente (PATH, PYTHONIOENCODING, etc.)

    NON FA:
    - Analizzare comandi
    - Tradurre sintassi
    - Decidere strategie
    """

    NATIVE_BINS = {
        'diff': 'diff.exe',
        'tar': 'tar.exe',
        'awk': 'awk.exe',
        'sed': 'sed.exe',
        'grep': 'grep.exe',
        'jq': 'jq.exe',
    }

    def __init__(self, test_mode: bool = False, logger = None,
                 python_executable = None, workspace_root = None,
                 virtual_env = None):
        """
        Initialize with optional Python venv configuration.

        In TEST MODE:
        - Skip detection and setup
        - Populate self.available con tutto True
        - Mock subprocess execution

        In PRODUCTION:
        - Detect Python executable
        - Setup virtual environment (BASH_TOOL_ENV)
        - Detect available capabilities (bash, native bins)
        - Configure execution environment
        """

    def execute_cmd(self, command: str, test_mode_stdout=None, **kwargs):
        """Execute via cmd.exe"""

    def execute_powershell(self, command: str, test_mode_stdout=None, **kwargs):
        """Execute via PowerShell"""

    def execute_bash(self, bash_path: str, command: str, test_mode_stdout=None, **kwargs):
        """Execute via Git Bash"""

    def execute_native(self, bin_path: str, args: List[str], test_mode_stdout=None, **kwargs):
        """
        Execute native binary directly.

        SPECIAL HANDLING FOR PYTHON:
        - Detects if bin_path is Python executable
        - If YES: uses self.environment (includes venv PATH, PYTHONIOENCODING)
        - If NO: uses default environment
        - Ensures Python scripts run in configured virtual environment
        """

    def is_available(self, name: str) -> bool:
        """
        Check if binary/functionality is available.

        Queries self.available dict (populated at init):
        - "python": Python executable configured
        - "bash": Git Bash available
        - "grep", "awk", etc.: Native binary exists in PATH
        """

    def _detect_available_capabilities(self) -> Dict[str, bool]:
        """Detect all capabilities at initialization (cached in self.available)"""

    def _setup_virtual_env(self, virtual_env) -> Optional[Path]:
        """Setup Python virtual environment (creates if missing)"""

    def _setup_environment(self) -> dict:
        """Setup execution environment with Python venv PATH"""
```

### 3.3 CommandEmulator

**Responsabilità**: Unix→Windows command translation (UNICA classe unificata)

```python
class CommandEmulator:
    """
    Unix→Windows command translation.

    UNIFICAZIONE: Prima c'erano 3 classi separate
    - SimpleTranslator (comandi 1:1)
    - PipelineTranslator (comandi pipeline)
    - EmulativeTranslator (emulazioni complesse)

    ORA: Una sola classe con 73 comandi in command_map

    CARATTERISTICHE:
    - Mapping diretto comando → metodo traduzione
    - Categorizzazione per complessità (SIMPLE/MEDIUM/COMPLEX)
    - Metodi marcati FALLBACK quando executor ha _execute_* dedicato
    """

    def __init__(self):
        """Initialize con command_map (73 comandi)"""
        self.command_map = {
            # ===== SIMPLE 1:1 TRANSLATIONS (< 20 righe) =====
            'pwd': self._translate_pwd,           # 3 lines
            'ps': self._translate_ps,             # 3 lines
            'chmod': self._translate_chmod,       # 3 lines
            'cd': self._translate_cd,             # 6 lines
            'mkdir': self._translate_mkdir,       # 9 lines
            'mv': self._translate_mv,             # 11 lines
            'export': self._translate_export,     # 19 lines
            # ... 21 comandi SIMPLE totali

            # ===== MEDIUM COMPLEXITY (20-100 righe) =====
            'touch': self._translate_touch,       # 26 lines
            'echo': self._translate_echo,         # 37 lines
            'wc': self._translate_wc,             # 34 lines
            'head': self._translate_head,         # 51 lines
            'tail': self._translate_tail,         # 56 lines
            'cat': self._translate_cat,           # 63 lines
            'cp': self._translate_cp,             # 72 lines
            'ls': self._translate_ls,             # 75 lines
            # ... 30 comandi MEDIUM totali

            # ===== COMPLEX EMULATIONS - FALLBACK ONLY (> 100 righe) =====
            'curl': self._translate_curl,         # 239 lines - FALLBACK
            'sed': self._translate_sed,           # 233 lines - FALLBACK
            'diff': self._translate_diff,         # 212 lines - FALLBACK
            'jq': self._translate_jq,             # 212 lines - FALLBACK
            'awk': self._translate_awk,           # 211 lines - FALLBACK
            'find': self._translate_find,         # 24 lines - FALLBACK (executor has _execute_find)
            'grep': self._translate_grep,         # 124 lines - FALLBACK
            # ... 22 comandi COMPLEX totali
        }

    def emulate_command(self, unix_command: str):
        """
        Translate Unix command → Windows/PowerShell.

        LOGIC:
        1. Parse command parts
        2. Check command_map for translator
        3. Call translator method
        4. Return translated command

        SPECIAL CASES:
        - python3 → python (Windows doesn't have python3)
        - Unknown commands → pass through as-is

        Returns:
            translated_command (str)
        """

    def _translate_ls(self, cmd: str, parts):
        """Translate ls → dir/Get-ChildItem with full flag support"""

    def _translate_cat(self, cmd: str, parts):
        """Translate cat → Get-Content with all flags"""

    # ... 73 metodi _translate_* totali
```

**NOTA IMPORTANTE**:
- Comandi marcati `FALLBACK` hanno anche un metodo `_execute_*` in CommandExecutor
- CommandEmulator fornisce traduzione PowerShell generica
- Executor usa metodi `_execute_*` per logica specializzata (es. _execute_find con Python)

### 3.4 PipelineStrategy

**Responsabilità MACRO**: Analisi pipeline completa e decisione strategica

```python
class PipelineStrategy:
    """
    Analizza la pipeline completa e decide la strategia macro.

    RESPONSABILITÀ:
    - Analizzare struttura pipeline (|, &&, ||, ;, <(), 2>, etc.)
    - Pattern matching per riconoscere casi comuni
    - Decidere se eseguire intera pipeline o suddividerla
    - Gestire fallback strategici

    NON FA:
    - Eseguire comandi
    - Tradurre sintassi
    - Gestire subprocess
    """

    BASH_EXE_REQUIRED = {
        'process_substitution', 'complex_find_exec',
        'nested_command_substitution', 'complex_awk_pipe'
    }

    BASH_EXE_PREFERRED = {
        'find', 'xargs', 'advanced_awk', 'advanced_sed'
    }

    def analyze_pipeline(self, command: str) -> PipelineAnalysis:
        """Analizza struttura della pipeline"""

    def decide_execution_strategy(self, analysis: PipelineAnalysis) -> ExecutionStrategy:
        """Decide strategia ottimale basata su analisi"""

    def can_split_pipeline(self, command: str, analysis: PipelineAnalysis) -> Tuple[bool, List[int]]:
        """Determina se può suddividere pipeline in parti"""
```

### 3.5 ExecuteUnixSingleCommand

**Responsabilità MICRO**: Esecuzione tattica singolo comando

```python
class ExecuteUnixSingleCommand:
    """
    Single Unix command executor - MICRO level strategy.

    ARCHITETTURA SEMPLIFICATA:
    - Una sola dipendenza: CommandEmulator
    - Usa ExecutionEngine per subprocess (passato da CommandExecutor)
    - Gestisce priority chain e fallback tattici

    RESPONSABILITÀ:
    - Decidere strategia ottimale per singolo comando
    - Usare CommandEmulator per traduzione
    - Delegare esecuzione a ExecutionEngine
    - Gestire fallback tattici

    NON FA:
    - Analizzare pipeline complete (usa PipelineStrategy)
    - Gestire subprocess direttamente (usa ExecutionEngine)
    - Tradurre path (usa PathTranslator via CommandExecutor)
    """

    def __init__(self, logger = None, test_mode: bool = False):
        """
        Initialize ExecuteUnixSingleCommand.

        SEMPLIFICATO rispetto a prima:
        PRIMA: 7 parametri (3 translators + git_bash + native_bins + execution_map + converter)
        DOPO: 2 parametri (logger + test_mode)

        Dependencies:
        - self.command_emulator = CommandEmulator() (UNICA dipendenza)
        - ExecutionEngine passato da CommandExecutor al momento esecuzione
        """
        self.command_emulator = CommandEmulator()
        self.logger = logger or logging.getLogger('ExecuteUnixSingleCommand')
        self.test_mode = test_mode
        self.BASH_EXE_PREFERRED = PipelineStrategy.BASH_EXE_PREFERRED

    def execute_single(self, cmd_name: str, command: str, parts: List[str],
                      execution_engine: ExecutionEngine,
                      git_bash_exe: Optional[str] = None,
                      native_bins: Dict = None) -> Tuple[str, bool]:
        """
        Execute single Unix command with optimal strategy.

        PRIORITY CHAIN TATTICO:
        1. CommandEmulator translation (Simple/Medium/Complex)
           → Usa command_map per trovare traduzione
           → Ritorna (translated_cmd, use_powershell)

        2. Native Binary (se disponibile e command_map non ha traduzione)
           → Controlla ExecutionEngine.is_available(cmd_name)
           → Usa ExecutionEngine.execute_native()

        3. Bash Passthrough (BASH_EXE_PREFERRED o fallback)
           → Se cmd in BASH_EXE_PREFERRED e bash disponibile
           → Usa ExecutionEngine.execute_bash()

        4. Pass-through as-is (ultimo resort)
           → Ritorna comando originale

        Args:
            cmd_name: Command name (e.g., 'ls', 'grep')
            command: Full command string
            parts: Command parts [cmd, arg1, arg2, ...]
            execution_engine: ExecutionEngine instance (dependency injection)
            git_bash_exe: Path to bash.exe (optional)
            native_bins: Dict of available native binaries (optional)

        Returns:
            Tuple[str, bool]: (executable_command, use_powershell)

        ESEMPIO FLOW:
        Comando: "grep -r pattern ."

        1. Prova CommandEmulator.emulate_command()
           → command_map['grep'] exists
           → _translate_grep() → PowerShell Select-String
           → Return ("Get-ChildItem -Recurse | Select-String 'pattern'", True)

        2. Se traduzione fallisce, prova Native Binary
           → execution_engine.is_available('grep')
           → Se True: Return ("grep.exe -r pattern .", False)

        3. Se native non disponibile, prova Bash
           → Se git_bash_exe exists: Return (bash_cmd, False)

        4. Ultimo resort: Return (command, False)
        """
```

**NOTA CRUCIALE**:
- ExecuteUnixSingleCommand NON ha più attributi self.git_bash_exe, self.native_bins, self.execution_map
- Questi vengono passati come parametri a execute_single() da CommandExecutor (dependency injection)
- ExecutionEngine viene iniettato come parametro, non stored come attributo

### 3.6 CommandExecutor (REFACTORED)

**Orchestratore Semplificato**

```python
class CommandExecutor:
    """
    Orchestratore esecuzione - SEMPLIFICATO.

    ARCHITETTURA:
    - PathTranslator: path translation
    - ExecutionEngine: subprocess execution
    - CommandEmulator: command translation
    - PipelineStrategy: pipeline analysis (MACRO)
    - ExecuteUnixSingleCommand: single command execution (MICRO)

    FLUSSO:
    1. Translate paths (PathTranslator)
    2. Analyze pipeline (PipelineStrategy)
    3. Decide strategy (PipelineStrategy)
    4. Execute according to strategy:
       - BASH: ExecutionEngine.execute_bash()
       - SINGLE: ExecuteUnixSingleCommand + ExecutionEngine
    """

    def __init__(self, claude_home_unix="/home/claude", logger=None, test_mode=False):
        # Path translation
        self.path_translator = PathTranslator()

        # Execution engine (UNICO punto subprocess)
        self.execution_engine = ExecutionEngine(
            test_mode=test_mode,
            logger=logger
        )

        # Command emulator (usa CommandEmulator internamente)
        self.command_emulator = CommandEmulator()

        # Detect available binaries and bash
        self.available_bins = self._detect_native_binaries()
        self.git_bash_exe = self._detect_git_bash()

        # Pipeline strategic analyzer (MACRO level)
        self.pipeline_strategy = PipelineStrategy(
            native_bins=self.available_bins,
            logger=self.logger,
            test_mode=test_mode
        )

        # Single command executor (MICRO level)
        self.single_executor = ExecuteUnixSingleCommand(
            logger=self.logger,
            test_mode=test_mode
        )

    def execute(self, command, timeout, cwd, env, ...):
        """
        FLUSSO SEMPLIFICATO:
        1. Translate paths (PathTranslator)
        2. Analyze pipeline (PipelineStrategy)
        3. Decide strategy (PipelineStrategy)
        4. Execute:
           - BASH → ExecutionEngine.execute_bash()
           - SINGLE → ExecuteUnixSingleCommand.execute_single() + ExecutionEngine
        """
        # 1. Path translation
        command = self.path_translator.translate_paths_in_string(command, 'unix_to_windows')

        # 2-3. Pipeline analysis and strategy
        analysis = self.pipeline_strategy.analyze_pipeline(command)
        strategy = self.pipeline_strategy.decide_execution_strategy(analysis)

        # 4. Execution secondo strategia
        if strategy.strategy_type in ['BASH_REQUIRED', 'BASH_PREFERRED']:
            return self.execution_engine.execute_bash(self.git_bash_exe, command)

        else:  # NATIVE or POWERSHELL - MICRO level
            parts = command.split()
            cmd_name = parts[0]

            # Esecuzione tattica singolo comando
            translated_cmd, use_powershell = self.single_executor.execute_single(
                cmd_name=cmd_name,
                command=command,
                parts=parts,
                execution_engine=self.execution_engine,  # Dependency injection
                git_bash_exe=self.git_bash_exe,
                native_bins=self.available_bins
            )

            # Esecuzione con ExecutionEngine
            if use_powershell:
                return self.execution_engine.execute_powershell(translated_cmd)
            else:
                return self.execution_engine.execute_cmd(translated_cmd)
```

---

## 4. SEPARAZIONE RESPONSABILITÀ: Prima vs Dopo

### PRIMA (Architettura Confusa)

```
❌ 3 Translators separati (SimpleTranslator, PipelineTranslator, EmulativeTranslator)
   → Separazione arbitraria basata su "lunghezza codice"
   → Nessuna differenza concettuale (tutti emulano comandi Unix)

❌ ExecuteUnixSingleCommand con 7 parametri init
   → Dipendenze hardcoded (simple_translator, emulative_translator, pipeline_translator)
   → Attributi self.git_bash_exe, self.native_bins, self.execution_map
   → Logica fallback mescolata

❌ ExecutionEngine minimale
   → Solo wrapper subprocess
   → Nessuna gestione Python venv
   → Nessuna detection capabilities
```

### DOPO (Architettura Pulita)

```
✅ CommandEmulator UNICO (73 comandi in command_map)
   → Unificazione logica: tutti emulano comandi Unix
   → Categorizzazione chiara: SIMPLE/MEDIUM/COMPLEX
   → Metodi marcati FALLBACK quando executor ha _execute_*

✅ ExecuteUnixSingleCommand semplificato (2 parametri init)
   → Una sola dipendenza: CommandEmulator
   → ExecutionEngine iniettato a runtime (dependency injection)
   → Logica fallback pulita e lineare

✅ ExecutionEngine potenziato
   → Python venv detection & setup automatico
   → Capabilities detection (self.available dict)
   → Test mode bypass
   → execute_native() con Python environment
   → is_available(name) per query capabilities
```

---

## 5. ESEMPI DI ESECUZIONE

### Esempio 1: Comando Semplice (cat file.txt)

```bash
Input: "cat file.txt"

Flow:
1. PathTranslator.translate_paths_in_string()
   → Paths translated

2. PipelineStrategy.analyze_pipeline()
   → No pipeline, No chain, complexity: LOW
   → strategy_type: POWERSHELL

3. ExecuteUnixSingleCommand.execute_single("cat", "cat file.txt", ["cat", "file.txt"])
   → CommandEmulator.emulate_command("cat file.txt")
   → command_map['cat'] → _translate_cat()
   → Return: ("Get-Content file.txt", False)

4. ExecutionEngine.execute_powershell("Get-Content file.txt")
   → subprocess.run(['powershell', '-Command', 'Get-Content file.txt'])

Result: PowerShell Get-Content execution
```

### Esempio 2: Native Binary (grep -r pattern .)

```bash
Input: "grep -r pattern ."

Flow:
1. PipelineStrategy → strategy_type: NATIVE_BINS

2. ExecuteUnixSingleCommand.execute_single("grep", ...)
   → Check execution_engine.is_available('grep')
   → True: grep.exe detected
   → Return: ("grep.exe -r pattern .", False)

3. ExecutionEngine.execute_native("grep.exe", ["-r", "pattern", "."])
   → subprocess.run(['grep.exe', '-r', 'pattern', '.'])

Result: Native grep.exe execution (best performance)
```

### Esempio 3: Python Script con Venv

```bash
Input: "python script.py"

Flow:
1. ExecuteUnixSingleCommand.execute_single("python", ...)
   → CommandEmulator: no translation needed (python3 → python)
   → Return: ("python script.py", False)

2. ExecutionEngine.execute_native("python", ["script.py"])
   → Detect: bin_path is Python executable
   → kwargs['env'] = self.environment (includes venv PATH)
   → subprocess.run(['python', 'script.py'], env=venv_environment)

Result: Python execution in BASH_TOOL_ENV virtual environment
```

### Esempio 4: Pipeline Complessa

```bash
Input: "find . -type f -name '*.py' -exec grep -l 'import' {} \;"

Flow:
1. PipelineStrategy.analyze_pipeline()
   → Has -exec, complexity: HIGH
   → strategy_type: BASH_REQUIRED

2. ExecutionEngine.execute_bash(bash_path, command)
   → subprocess.run([bash_path, '-c', "find . -type f -name '*.py' -exec grep -l 'import' {} \;"])

Result: Full bash.exe execution (perfect compatibility)
```

---

## 6. MIGRATION STATUS

### ✅ Phase 1: Extract PipelineStrategy - COMPLETATO
- [x] Creare classe PipelineStrategy
- [x] Spostare logica analyze_pipeline
- [x] Spostare logica decide_execution_strategy
- [x] Spostare PIPELINE_STRATEGIES patterns

### ✅ Phase 2: Unify Translators → CommandEmulator - COMPLETATO
- [x] Eliminare SimpleTranslator, PipelineTranslator, EmulativeTranslator
- [x] Creare CommandEmulator unico con command_map (73 comandi)
- [x] Categorizzare: SIMPLE/MEDIUM/COMPLEX
- [x] Implementare emulate_command() pubblico

### ✅ Phase 3: Enhance ExecutionEngine - COMPLETATO
- [x] NATIVE_BINS detection
- [x] _detect_available_capabilities()
- [x] is_available(name) method
- [x] Python venv detection & setup
- [x] _setup_virtual_env() con creazione automatica
- [x] _setup_environment() con PATH venv
- [x] execute_native() con Python environment handling
- [x] Test mode bypass completo

### 🔄 Phase 4: Refactor ExecuteUnixSingleCommand - IN CORSO
- [x] Semplificare __init__ (da 7 a 2 parametri)
- [x] Una sola dipendenza: CommandEmulator
- [ ] Implementare execute_single() con dependency injection
- [ ] Rimuovere codice vecchio (self.simple, self.pipeline, self.emulative)
- [ ] Implementare priority chain pulito
- [ ] Unit tests

### 📋 Phase 5: Refactor CommandExecutor - PROSSIMO
- [ ] Rimuovere logica delegata a PipelineStrategy
- [ ] Rimuovere logica delegata a ExecuteUnixSingleCommand
- [ ] Implementare dependency injection per ExecutionEngine
- [ ] Ridurre a thin orchestration layer
- [ ] Integration tests

---

## 7. DECISIONI ARCHITETTURALI KEY

### 7.1 Perché CommandEmulator Unificato?

**PRIMA**: 3 classi separate (SimpleTranslator, PipelineTranslator, EmulativeTranslator)
- Separazione basata su "lunghezza codice" (< 20, 20-100, > 100 linee)
- NESSUNA differenza concettuale
- Tutti emulano comandi Unix → Windows/PowerShell
- Gestione pipeline (`$input`) comune a tutti

**DOPO**: CommandEmulator unico
- 73 comandi in un solo command_map
- Categorizzazione chiara ma non strutturale (SIMPLE/MEDIUM/COMPLEX)
- Metodo pubblico unificato: emulate_command()
- Logica comune per tutti i comandi

**Beneficio**: Eliminata separazione arbitraria, architettura più coerente

### 7.2 Perché ExecutionEngine Potenziato?

**Responsabilità Unica Violata PRIMA**:
- ExecutionEngine: solo wrapper subprocess
- Python venv: gestito altrove (non chiaro dove)
- Capabilities detection: sparsa in più classi

**Responsabilità Unica DOPO**:
- ExecutionEngine: TUTTO ciò che riguarda subprocess + environment
- Python venv: detection, setup, activation in ExecutionEngine
- Capabilities: cached in self.available, query con is_available()

**Beneficio**: Single point of truth per execution environment

### 7.3 Perché Dependency Injection in ExecuteUnixSingleCommand?

**PRIMA**: ExecuteUnixSingleCommand con 7 attributi instance
```python
self.git_bash_exe = git_bash_exe
self.native_bins = native_bins
self.execution_map = execution_map
# Accoppiamento forte
```

**DOPO**: Dependency injection a runtime
```python
def execute_single(self, ..., execution_engine, git_bash_exe, native_bins):
    # Accoppiamento debole, testabilità migliorata
```

**Beneficio**: Testabilità, flessibilità, nessuno stato mutabile

---

## 8. LAYERING ARCHITECTURE

### Layer 1: Translation Layer
- **PathTranslator**: Unix↔Windows paths
- **CommandEmulator**: Unix→Windows commands

### Layer 2: Execution Layer
- **ExecutionEngine**: subprocess wrapper + environment

### Layer 3: Strategy Layer (MACRO)
- **PipelineStrategy**: pipeline analysis + decision

### Layer 4: Tactical Layer (MICRO)
- **ExecuteUnixSingleCommand**: single command execution

### Layer 5: Orchestration Layer
- **CommandExecutor**: thin coordinator

**Flusso**: Orchestration → Strategy (MACRO) → Tactical (MICRO) → Translation → Execution

---

## 9. METRICS & KPIs

### Complessità del Codice

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Num. Translator Classes | 3 | 1 | -67% |
| ExecuteUnixSingleCommand init params | 7 | 2 | -71% |
| ExecutionEngine responsibilities | 1 | 5 | +400% (appropriate) |
| CommandExecutor LOC | ~1200 | TBD | Target: -60% |

### Performance

| Scenario | Strategy | Execution Method |
|----------|----------|------------------|
| Simple commands (pwd, cd) | CommandEmulator | PowerShell cmdlet (instant) |
| Native binaries (grep.exe) | Native Binary | Direct subprocess (best perf) |
| Python scripts | execute_native | With venv environment |
| Complex find pipelines | Bash Passthrough | Git Bash (perfect compat) |

---

## 10. NEXT STEPS

### Immediate (High Priority)
1. **Completare ExecuteUnixSingleCommand.execute_single()**
   - Implementare chiamata a CommandEmulator.emulate_command()
   - Implementare fallback a native binary
   - Implementare fallback a bash passthrough
   - Rimuovere codice vecchio (self.simple, etc.)

2. **Unit Tests**
   - CommandEmulator: 20+ test cases
   - ExecuteUnixSingleCommand: 15+ test cases
   - ExecutionEngine: 10+ test cases (venv, capabilities)

### Medium Priority
3. **Refactor CommandExecutor**
   - Implementare dependency injection
   - Ridurre logica interna
   - Delegare tutto a Strategy + Tactical layers

4. **Integration Tests**
   - End-to-end scenarios: 30+ test cases
   - Performance benchmarks
   - Compatibility tests

### Low Priority (Future)
5. **Advanced Features**
   - Hybrid pipeline execution
   - Dynamic fallback based on success rate
   - Performance profiling per strategy

---

## CONCLUSIONI

L'architettura finale rappresenta una significativa semplificazione e chiarificazione rispetto all'approccio precedente:

**Unificazioni**:
- 3 Translators → 1 CommandEmulator
- Logica subprocess sparsa → ExecutionEngine centralizzato

**Separazioni**:
- MACRO (PipelineStrategy) vs MICRO (ExecuteUnixSingleCommand)
- Translation (CommandEmulator) vs Execution (ExecutionEngine)
- Strategy vs Orchestration

**Benefici Chiave**:
1. Single Responsibility: ogni classe una responsabilità chiara
2. Dependency Injection: accoppiamento debole, testabilità alta
3. Layering: separazione netta tra livelli architetturali
4. Unificazione logica: eliminata separazione arbitraria translators

**Status**: Phase 3 completato (ExecutionEngine), Phase 4 in corso (ExecuteUnixSingleCommand)

---

*Documento aggiornato con architettura finale post-refactoring*
*Ultima modifica: 2025-11-19*
