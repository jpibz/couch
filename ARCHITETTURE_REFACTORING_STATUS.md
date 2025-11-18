# ARCHITETTURE REFACTORING STATUS

## Documento Integrato - Strategia di Refactoring CommandExecutor

Questo documento integra le comprensioni architetturali emerse durante le sessioni di analisi e definisce lo stato del refactoring verso una struttura a due livelli.

---

## 1. ARCHITETTURA PROPOSTA: CommandExecutor a Due Livelli

### Gerarchia Complessiva

```
CommandExecutor
│
├─ PipelineStrategy (LIVELLO MACRO - analisi intera pipeline)
│  │
│  ├─ analyze_pipeline(command) → PipelineAnalysis
│  │  ├─ Detect: pipeline, chain, redirection, process_subst
│  │  ├─ Pattern matching (PIPELINE_STRATEGIES)
│  │  ├─ Identify command components
│  │  └─ Return: strategia complessiva
│  │
│  └─ decide_execution_strategy(analysis) → ExecutionStrategy
│     ├─ BASH_REQUIRED (process subst, complex chains)
│     ├─ BASH_PREFERRED (find, awk, sed pipelines)
│     ├─ HYBRID (parte bash, parte emulation)
│     ├─ NATIVE_BINS (tar, grep nativi)
│     └─ POWERSHELL (emulation completa)
│
└─ ExecuteUnixSingleCommand (LIVELLO MICRO - singolo comando)
   │
   ├─ execute_single(cmd_name, command, parts) → (cmd, use_powershell)
   │
   ├─ PRIORITY 1: SimpleTranslator (1:1 commands)
   │  └─ pwd, cd, mkdir, rm, mv, etc.
   │
   ├─ PRIORITY 2: Native Binary (best performance)
   │  └─ tar.exe, grep.exe, awk.exe, sed.exe
   │
   ├─ PRIORITY 3: Bash Passthrough (perfect compatibility)
   │  └─ find, complex awk/sed, xargs
   │
   └─ PRIORITY 4: EmulativeTranslator (fallback)
      └─ PowerShell emulation
      └─ Gestisce priorità e fallback INCROCIATI
         (se native binary fallisce → bash passthrough → emulation)
```

---

## 2. FLUSSO DI ESECUZIONE DETTAGLIATO

### Sequenza Completa

```
CommandExecutor.execute(command)
│
├─ 1. Pre-processing & Validation
│
├─ 2. PipelineStrategy.analyze_pipeline(command)
│  └─→ PipelineAnalysis {
│       has_pipeline: bool
│       has_chain: bool
│       has_redirection: bool
│       has_process_subst: bool
│       matched_pattern: str
│       complexity_level: HIGH/MEDIUM/LOW
│     }
│
├─ 3. PipelineStrategy.decide_execution_strategy(analysis)
│  └─→ ExecutionStrategy {
│       strategy_type: BASH_REQUIRED|BASH_PREFERRED|HYBRID|NATIVE|POWERSHELL
│       can_split: bool (può suddividere pipeline?)
│       split_points: [indici] (dove suddividere)
│       fallback_strategy: ExecutionStrategy
│     }
│
├─ 4a. Se strategy_type == BASH_REQUIRED/PREFERRED
│  └─→ Esegui intera pipeline con bash.exe
│
├─ 4b. Se strategy_type == HYBRID
│  └─→ Suddividi pipeline
│     ├─ Parte 1: bash.exe (find complex)
│     └─ Parte 2: PowerShell (wc simple)
│
└─ 4c. Se strategy_type == NATIVE/POWERSHELL
   └─→ Per ogni comando nella pipeline:
       ExecuteUnixSingleCommand.execute_single(cmd)
       └─→ Sceglie: Simple → Native → Bash → Emulative
```

---

## 3. DETTAGLIO CLASSI E RESPONSABILITÀ

### 3.1 PipelineStrategy

**Responsabilità MACRO - Analisi Pipeline Completa**

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

    def __init__(self, test_mode, native_and_bash_bins, logger):
        self.test_mode = test_mode
        self.native_bins = native_and_bash_bins
        self.logger = logger

        # Pattern cache (SPOSTATO da CommandExecutor)
        self.PIPELINE_STRATEGIES = {...}
        self.BASH_EXE_REQUIRED = {...}
        self.BASH_EXE_PREFERRED = {...}

    def analyze_pipeline(self, command: str) -> PipelineAnalysis:
        """
        Analizza struttura della pipeline.

        Returns:
            PipelineAnalysis con flags per pipeline, chain, redirection,
            process substitution, pattern matched e complexity level
        """
        pass

    def decide_execution_strategy(self, analysis: PipelineAnalysis) -> ExecutionStrategy:
        """
        Decide strategia ottimale basata su analisi.

        Logic Tree:
        1. Has process substitution? → BASH_REQUIRED
        2. Complex find/awk/sed pipeline? → BASH_PREFERRED
        3. Simple pipeline with native bins? → NATIVE_BINS
        4. Can split pipeline? → HYBRID
        5. Fallback → POWERSHELL
        """
        pass

    def can_split_pipeline(self, command: str) -> Tuple[bool, List[int]]:
        """
        Determina se può suddividere pipeline in parti.

        Example:
            "find . -name '*.py' | wc -l"
            → Can split: [True, [index_of_pipe]]
            → Part 1: bash.exe for find
            → Part 2: PowerShell for wc
        """
        pass

    def get_fallback_strategy(self, primary_strategy: ExecutionStrategy) -> ExecutionStrategy:
        """
        Ottiene strategia fallback se primaria fallisce.

        Fallback Chain:
        NATIVE_BINS → BASH_PREFERRED → BASH_REQUIRED
        HYBRID → BASH_PREFERRED
        BASH_PREFERRED → BASH_REQUIRED
        """
        pass
```

### 3.2 ExecuteUnixSingleCommand

**Responsabilità MICRO - Esecuzione Singolo Comando**

```python
class ExecuteUnixSingleCommand:
    """
    Esegue UN SINGOLO comando Unix con scelta intelligente della strategia.

    RESPONSABILITÀ:
    - Decidere strategia ottimale per singolo comando
    - Gestire priorità: Simple → Native → Bash → Emulative
    - Gestire fallback incrociati
    - Interfacciarsi con i 3 Translators

    NON FA:
    - Analizzare pipeline complete
    - Gestire subprocess (usa ExecutionEngine)
    - Path translation (delega ai Translators)
    """

    def __init__(self, simple_translator, emulative_translator,
                 pipeline_translator, test_mode, native_and_bash_bins,
                 execution_engine, logger):
        self.simple = simple_translator
        self.emulative = emulative_translator
        self.pipeline = pipeline_translator
        self.git_bash_exe = native_and_bash_bins['git_bash_exe']
        self.native_bins = native_and_bash_bins
        self.executor = execution_engine
        self.test_mode = test_mode
        self.logger = logger

    def execute_single(self, cmd_name: str, command: str,
                      parts: List[str]) -> Tuple[str, bool]:
        """
        Esegue singolo comando con strategia ottimale.

        PRIORITY CHAIN:
        1. SimpleTranslator (pwd, cd, mkdir) - instant 1:1
        2. Native Binary (grep.exe, awk.exe) - best performance
        3. Bash Passthrough (complex find, awk) - perfect compatibility
        4. EmulativeTranslator (fallback) - PowerShell emulation

        Returns:
            (executable_command, use_powershell)

        Example Flow:
            cmd_name = "grep"
            1. Try SimpleTranslator → not 1:1 command
            2. Try grep.exe → found! Return ("grep.exe -r pattern .", False)
            3. If grep.exe not found → Try bash.exe
            4. If bash fails → Emulate with PowerShell Select-String
        """
        pass

    def _try_simple_translation(self, cmd_name, command, parts):
        """
        Prova traduzione 1:1.

        Commands: pwd, cd, mkdir, rm, mv, cp, touch, echo, cat
        Speed: Instant (no subprocess)
        """
        pass

    def _try_native_binary(self, cmd_name, command):
        """
        Prova esecuzione con binario nativo.

        Priority:
        1. Check if native binary exists (grep.exe, awk.exe, etc.)
        2. Validate command compatibility
        3. Return native execution command

        Performance: Best (direct native execution)
        """
        pass

    def _try_bash_passthrough(self, cmd_name, command):
        """
        Prova esecuzione con bash.exe.

        Use cases:
        - Complex find expressions
        - Advanced awk/sed scripts
        - Commands with bash-specific features

        Compatibility: Perfect (100% bash compatibility)
        """
        pass

    def _try_emulative_translation(self, cmd_name, command, parts):
        """
        Prova emulazione PowerShell.

        Fallback finale quando:
        - No SimpleTranslator mapping
        - Native binary not available
        - Bash passthrough fails/unavailable

        Compatibility: ~80% (PowerShell approximation)
        """
        pass
```

### 3.3 CommandExecutor (REFACTORED)

**Orchestratore Semplificato**

```python
class CommandExecutor:
    """
    Orchestratore esecuzione - SEMPLIFICATO.

    PRIMA: 45 metodi, logica complessa mescolata, 1200+ righe
    DOPO: ~20 metodi, delega a PipelineStrategy + ExecuteUnixSingleCommand, ~500 righe

    PRINCIPIO: Thin orchestration layer
    - CommandExecutor coordina
    - PipelineStrategy decide strategia macro
    - ExecuteUnixSingleCommand esegue singoli comandi
    """

    def __init__(self, ...):
        # Strategia pipeline
        self.pipeline_strategy = PipelineStrategy(
            test_mode=self.test_mode,
            native_and_bash_bins=self._detect_binaries(),
            logger=self.logger
        )

        # Esecuzione comando singolo
        self.single_executor = ExecuteUnixSingleCommand(
            simple_translator=SimpleTranslator(),
            emulative_translator=EmulativeTranslator(),
            pipeline_translator=PipelineTranslator(),
            test_mode=self.test_mode,
            native_and_bash_bins=self._detect_binaries(),
            execution_engine=self.executor,
            logger=self.logger
        )

    def execute(self, command, timeout, cwd, env, ...):
        """
        NUOVO FLUSSO SEMPLIFICATO:
        1. Analizza pipeline → PipelineStrategy
        2. Decide strategia → PipelineStrategy
        3. Esegue secondo strategia:
           - BASH: intera pipeline a bash.exe
           - HYBRID: suddivide ed esegue parti
           - SINGLE: ExecuteUnixSingleCommand per ogni comando
        """
        # Pre-processing
        command = self._preprocess_command(command)

        # Analisi strategica (DELEGATA)
        analysis = self.pipeline_strategy.analyze_pipeline(command)
        strategy = self.pipeline_strategy.decide_execution_strategy(analysis)

        # Esecuzione secondo strategia (DELEGATA)
        if strategy.strategy_type in ['BASH_REQUIRED', 'BASH_PREFERRED']:
            return self._execute_with_gitbash(command, timeout, cwd, env)

        elif strategy.strategy_type == 'HYBRID':
            return self._execute_hybrid_pipeline(command, strategy.split_points,
                                                 timeout, cwd, env)

        else:  # NATIVE or POWERSHELL
            parts = command.split()
            return self.single_executor.execute_single(parts[0], command, parts)

    def execute_bash(self, command, parts):
        """
        REFACTORED: Delega a PipelineStrategy + ExecuteUnixSingleCommand

        PRIMA: 200 righe logica mista
        DOPO: 20 righe orchestrazione

        Responsabilità ridotte:
        - Gestisce SOLO la chiamata di alto livello
        - Analisi → PipelineStrategy
        - Decisione → PipelineStrategy
        - Esecuzione → ExecuteUnixSingleCommand o bash.exe
        """
        # Analisi strategica (DELEGATA)
        analysis = self.pipeline_strategy.analyze_pipeline(command)
        strategy = self.pipeline_strategy.decide_execution_strategy(analysis)

        # Esecuzione secondo strategia (DELEGATA)
        if strategy.strategy_type in ['BASH_REQUIRED', 'BASH_PREFERRED']:
            return self._execute_with_gitbash(command)

        elif strategy.strategy_type == 'HYBRID':
            return self._execute_hybrid_pipeline(command, strategy.split_points)

        else:  # NATIVE or POWERSHELL
            return self.single_executor.execute_single(parts[0], command, parts)
```

---

## 4. BENEFICI DELL'ARCHITETTURA A DUE LIVELLI

### 4.1 Separazione delle Responsabilità

**PRIMA (Monolitico)**
- CommandExecutor gestiva tutto: analisi, decisione, esecuzione
- Logica complessa intrecciata
- Difficile testare singole parti
- 45 metodi, 1200+ righe

**DOPO (Due Livelli)**
- **PipelineStrategy**: Analisi strategica MACRO (pipeline completa)
- **ExecuteUnixSingleCommand**: Esecuzione tattica MICRO (singolo comando)
- **CommandExecutor**: Thin orchestration layer
- Ogni classe ha responsabilità chiare e testabili
- ~20 metodi in CommandExecutor, ~500 righe

### 4.2 Fallback Intelligenti e Incrociati

```
Scenario: "grep -r 'pattern' ."

ExecuteUnixSingleCommand flow:
1. Try SimpleTranslator
   → grep non è 1:1 command → SKIP

2. Try Native Binary
   → Check if grep.exe exists
   → YES: Return "grep.exe -r 'pattern' ."
   → NO: Continue to step 3

3. Try Bash Passthrough
   → Check if bash.exe available
   → YES: Return "bash.exe -c 'grep -r pattern .'"
   → NO: Continue to step 4

4. Try Emulative Translation
   → Return "Get-ChildItem -Recurse | Select-String 'pattern'"
```

### 4.3 Strategia Hybrid per Pipeline Complesse

```
Scenario: "find . -type f -name '*.py' | wc -l"

PipelineStrategy.analyze_pipeline():
→ has_pipeline: True
→ complexity_level: MEDIUM
→ matched_pattern: "find_with_simple_pipe"

PipelineStrategy.decide_execution_strategy():
→ can_split: True
→ split_points: [index_of_pipe]
→ strategy_type: HYBRID

Execution:
Part 1: bash.exe -c "find . -type f -name '*.py'"
  → Output: list of files

Part 2: PowerShell "Measure-Object -Line"
  → Input: from Part 1
  → Output: file count
```

### 4.4 Testabilità Migliorata

**Unit Testing Isolato**
```python
# Test PipelineStrategy (NO esecuzione)
def test_pipeline_analysis():
    strategy = PipelineStrategy(test_mode=True, ...)
    analysis = strategy.analyze_pipeline("find . | grep .py")
    assert analysis.has_pipeline == True
    assert analysis.complexity_level == "MEDIUM"

# Test ExecuteUnixSingleCommand (NO analisi pipeline)
def test_single_command_execution():
    executor = ExecuteUnixSingleCommand(...)
    cmd, use_ps = executor.execute_single("pwd", "pwd", ["pwd"])
    assert cmd == "Get-Location"
    assert use_ps == True

# Test CommandExecutor (integration)
def test_full_command_execution():
    executor = CommandExecutor(...)
    result = executor.execute("ls -la")
    assert result.exit_code == 0
```

---

## 5. MIGRATION PLAN

### Phase 1: Extract PipelineStrategy ✅ **COMPLETATO**
- [x] Creare classe PipelineStrategy
- [x] Spostare logica analyze_pipeline
- [x] Spostare logica decide_execution_strategy
- [x] Spostare PIPELINE_STRATEGIES patterns
- [x] Unit tests per PipelineStrategy

### Phase 2: Extract ExecuteUnixSingleCommand 🔄 **IN CORSO**
- [x] Creare classe ExecuteUnixSingleCommand
- [ ] Implementare priority chain (Simple → Native → Bash → Emulative)
- [ ] Spostare logica singolo comando da CommandExecutor
- [ ] Gestire fallback incrociati
- [ ] Unit tests per ExecuteUnixSingleCommand

### Phase 3: Refactor CommandExecutor 📋 **PROSSIMO**
- [ ] Rimuovere logica delegata a PipelineStrategy
- [ ] Rimuovere logica delegata a ExecuteUnixSingleCommand
- [ ] Ridurre a thin orchestration layer
- [ ] Target: da 45 metodi a ~20 metodi
- [ ] Integration tests

### Phase 4: Advanced Hybrid Execution 📋 **FUTURO**
- [ ] Implementare split_pipeline intelligente
- [ ] Gestire piping tra bash e PowerShell
- [ ] Ottimizzare performance per pipeline miste
- [ ] Advanced test coverage

---

## 6. METRICS & KPIs

### Complessità del Codice

| Metric | Before | Target | Current |
|--------|--------|--------|---------|
| CommandExecutor LOC | 1200+ | ~500 | 1200 |
| CommandExecutor Methods | 45 | ~20 | 45 |
| Cyclomatic Complexity | High | Low | High |
| Test Coverage | 60% | 85% | 65% |

### Performance

| Scenario | Strategy | Expected Improvement |
|----------|----------|---------------------|
| Simple commands (pwd, cd) | SimpleTranslator | Instant (no subprocess) |
| Native binaries (grep.exe) | Native Binary | Best performance |
| Complex find pipelines | Bash Passthrough | Perfect compatibility |
| Fallback emulation | PowerShell | ~80% compatibility |

---

## 7. ESEMPI DI ESECUZIONE

### Esempio 1: Comando Semplice
```bash
Input: "pwd"

Flow:
1. PipelineStrategy.analyze_pipeline()
   → No pipeline, No chain, complexity: LOW

2. PipelineStrategy.decide_execution_strategy()
   → strategy_type: POWERSHELL (simple 1:1)

3. ExecuteUnixSingleCommand.execute_single()
   → _try_simple_translation()
   → SUCCESS: "Get-Location"

Result: PowerShell Get-Location (instant, no subprocess)
```

### Esempio 2: Native Binary
```bash
Input: "grep -r 'pattern' ."

Flow:
1. PipelineStrategy.analyze_pipeline()
   → No pipeline, complexity: LOW

2. PipelineStrategy.decide_execution_strategy()
   → strategy_type: NATIVE_BINS

3. ExecuteUnixSingleCommand.execute_single()
   → _try_simple_translation() → SKIP
   → _try_native_binary() → SUCCESS: "grep.exe -r 'pattern' ."

Result: Native grep.exe execution (best performance)
```

### Esempio 3: Pipeline Complessa
```bash
Input: "find . -type f -name '*.py' -exec grep -l 'import' {} \;"

Flow:
1. PipelineStrategy.analyze_pipeline()
   → Has -exec, complexity: HIGH

2. PipelineStrategy.decide_execution_strategy()
   → strategy_type: BASH_REQUIRED

3. CommandExecutor._execute_with_gitbash()
   → bash.exe -c "find . -type f -name '*.py' -exec grep -l 'import' {} \;"

Result: Full bash.exe execution (perfect compatibility)
```

### Esempio 4: Hybrid Pipeline
```bash
Input: "find . -name '*.log' | wc -l"

Flow:
1. PipelineStrategy.analyze_pipeline()
   → has_pipeline: True, complexity: MEDIUM

2. PipelineStrategy.decide_execution_strategy()
   → can_split: True
   → strategy_type: HYBRID

3. CommandExecutor._execute_hybrid_pipeline()
   Part 1: bash.exe -c "find . -name '*.log'"
   Part 2: PowerShell Measure-Object

Result: Optimized hybrid execution (bash for find, PowerShell for wc)
```

---

## 8. DECISIONI ARCHITETTURALI KEY

### 8.1 Perché Due Livelli (Macro + Micro)?

**Livello MACRO (PipelineStrategy)**
- Analizza struttura COMPLETA della pipeline
- Decide strategia GLOBALE (bash vs native vs hybrid)
- Gestisce ottimizzazioni cross-command
- Identifica pattern comuni

**Livello MICRO (ExecuteUnixSingleCommand)**
- Esegue SINGOLO comando
- Decide strategia LOCALE (simple vs native vs bash vs emulative)
- Gestisce fallback per comando specifico
- Interfaccia con Translators

**Vantaggio**: Separazione chiara tra decisioni strategiche (pipeline) e tattiche (comando)

### 8.2 Perché Mantenere CommandExecutor?

**Alternativa Considerata**: Eliminare CommandExecutor, far diventare PipelineStrategy il punto di ingresso

**Decisione**: Mantenere CommandExecutor come thin orchestration layer

**Motivazioni**:
1. **Backward Compatibility**: BashToolExecutor già dipende da CommandExecutor
2. **Single Responsibility**: CommandExecutor coordina, non decide
3. **Punto di Estensione**: Facile aggiungere pre/post-processing
4. **Testing**: Layer di integrazione per test end-to-end

### 8.3 Priority Chain in ExecuteUnixSingleCommand

**Ordine Scelto**:
1. SimpleTranslator (instant)
2. Native Binary (best performance)
3. Bash Passthrough (perfect compatibility)
4. EmulativeTranslator (fallback)

**Rationale**:
- Instant > Performance > Compatibility > Fallback
- Simple commands devono essere IMMEDIATE (no subprocess overhead)
- Native binaries offrono best performance quando disponibili
- Bash garantisce 100% compatibility per casi complessi
- PowerShell emulation come ultima risorsa

---

## 9. PROSSIMI STEP IMMEDIATI

### High Priority
1. **Completare ExecuteUnixSingleCommand**
   - Implementare _try_native_binary()
   - Implementare _try_bash_passthrough()
   - Gestire fallback chain completo

2. **Refactoring CommandExecutor.execute_bash()**
   - Rimuovere logica interna
   - Delegare a PipelineStrategy + ExecuteUnixSingleCommand
   - Ridurre da 200 righe a ~20 righe

3. **Unit Tests Completi**
   - PipelineStrategy: 10+ test cases
   - ExecuteUnixSingleCommand: 15+ test cases
   - Integration tests: 20+ scenarios

### Medium Priority
4. **Implementare Hybrid Execution**
   - Splitting intelligente pipeline
   - Piping tra bash e PowerShell
   - Gestione errori inter-process

5. **Ottimizzazioni Performance**
   - Caching strategia per comandi ripetuti
   - Parallel execution per pipeline indipendenti
   - Lazy initialization binaries

### Low Priority
6. **Advanced Features**
   - Auto-detection best strategy (machine learning?)
   - Profiling execution time per strategy
   - Dynamic fallback basato su success rate

---

## 10. LESSONS LEARNED

### Cosa Ha Funzionato
✅ **Separazione MACRO/MICRO**: Chiara distinzione tra analisi pipeline e esecuzione comando
✅ **Priority Chain**: Ordine logico Simple → Native → Bash → Emulative
✅ **Thin Orchestration**: CommandExecutor come coordinator, non executor
✅ **Testabilità**: Ogni classe testabile in isolamento

### Cosa NON Ha Funzionato (da evitare)
❌ **Logica Mescolata**: Analisi + Decisione + Esecuzione nella stessa classe
❌ **Metodi Giganti**: execute_bash() con 200 righe di logica mista
❌ **Pattern Duplicati**: PIPELINE_STRATEGIES, BASH_EXE_REQUIRED in più classi
❌ **Hard-coded Paths**: Path binaries hard-coded invece di dependency injection

### Principi Guida per il Futuro
1. **Single Responsibility**: Ogni classe UNA responsabilità chiara
2. **Dependency Injection**: Pass dependencies, non hard-code
3. **Fail Fast**: Validation all'inizio, execution alla fine
4. **Fallback Chain**: Sempre avere strategia alternativa
5. **Test First**: Scrivere test PRIMA di implementare

---

## CONCLUSIONI

L'architettura a due livelli (PipelineStrategy + ExecuteUnixSingleCommand) rappresenta un significativo miglioramento rispetto all'approccio monolitico precedente. La separazione chiara delle responsabilità, i fallback intelligenti e la testabilità migliorata sono i benefici principali.

**Status Attuale**: Phase 2 (50% completato)
**Target Completion**: Phase 3 end (thin orchestration layer)
**Long-term Vision**: Phase 4 (hybrid execution avanzato)

---

*Documento mantenuto e aggiornato durante il refactoring di CommandExecutor*
*Ultima modifica: 2025-11-18*
