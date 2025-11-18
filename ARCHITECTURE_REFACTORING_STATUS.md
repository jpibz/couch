# ARCHITETTURA - STATO ATTUALE vs TARGET

## ARCHITETTURA TARGET (dove dobbiamo arrivare)

### CONCETTO CHIAVE: DUE LIVELLI DI GESTIONE

**LIVELLO MACRO** (Pipeline completa):
- Gestisce l'INTERA pipeline come unità
- Decide strategia globale (eseguire tutta, suddividere, usare bash.exe)

**LIVELLO MICRO** (Comandi atomici):
- Gestisce SINGOLI COMANDI dentro la pipeline
- Scelta strategica per ogni comando atomico

---

### ARCHITETTURA DETTAGLIATA

```
1. BashToolExecutor.execute()
   ├─ Path translation: Unix → Windows (or skip in test)
   ├─ Security validation (or skip in test)
   └─ Calls command_executor.execute()

2. CommandExecutor.execute()
   │
   ├─ 🔍 LIVELLO MACRO: PipelineStrategy
   │   │
   │   ├─ analyze_pipeline(command)
   │   │   └─ Returns: PipelineAnalysis(
   │   │         has_pipeline=True,
   │   │         command_count=3,
   │   │         complexity_level='HIGH',
   │   │         command_names=['find', 'grep', 'wc']
   │   │       )
   │   │
   │   └─ decide_execution_strategy(analysis, command)
   │       └─ Returns: ExecutionStrategy(
   │             strategy_type='BASH_REQUIRED',  # o BASH_PREFERRED, SINGLE, POWERSHELL, FAIL
   │             reason='Pipeline with find + xargs requires bash.exe',
   │             can_split=False,
   │             fallback_strategy='EMULATION'
   │           )
   │
   └─ Based on strategy → Execute pipeline
      │
      ├─ Strategy: BASH_REQUIRED/PREFERRED
      │   └─ Passthrough → bash.exe -c "entire pipeline"
      │
      └─ Strategy: SINGLE/POWERSHELL
          │
          ├─ PipelineTranslator
          │   └─ Traduce OPERATORI pipeline Unix → Windows
          │       (|, &&, ||, ;, >, <, 2>, ecc.)
          │
          └─ ExecuteUnixSingleCommand (LIVELLO MICRO)
              │
              ├─ PRIORITY 1: Bash Passthrough (for BASH_EXE_PREFERRED commands)
              │   └─ [find, awk, sed, grep, xargs, cut, tr, tee] → bash.exe
              │
              ├─ PRIORITY 2: Native Binary (best performance)
              │   └─ [grep.exe, awk.exe, diff.exe, tar.exe] → native Windows bins
              │
              ├─ PRIORITY 3: Execution Map (complex emulation)
              │   ├─ SimpleTranslator (1:1 translation)
              │   │   └─ [pwd, cd, mkdir, rm, mv, cp, touch]
              │   │
              │   └─ EmulativeTranslator (complex PowerShell scripts)
              │       └─ [find, awk, sed, diff, sort, uniq, join]
              │
              └─ PRIORITY 4: Intelligent Fallback
                  └─ Try: Translator → Native Bin → bash.exe → Error
                                       │
                                       └─ ExecutionEngine (UNICO PUNTO subprocess)
                                           ├─ execute_cmd(command)
                                           ├─ execute_powershell(command)
                                           └─ execute_bash(bash_path, command)
                                               │
                                               └─ [TEST MODE]
                                                   └─ Returns mock CompletedProcess(
                                                         returncode=0,
                                                         stdout="[TEST MODE OUTPUT] ...",
                                                         stderr=""
                                                       )

3. Output formatted and returned
   └─ "Exit code: 0\n[TEST MODE OUTPUT] cmd: ..."
```

---

### LOGICA STRATEGICA (NON è cascata fallback universale!)

**PipelineStrategy** = "CACHE di STRATEGIE PRECONFEZIONATE"

Le strategie **NON sono mutuamente esclusive**:
- Possono lavorare INSIEME (pipeline mista: alcuni comandi nativi, altri emulati)
- Una può essere FALLBACK dell'altra
- Scelta basata su PATTERN MATCHING (non algoritmo generico)

**Esempi di decisioni strategiche:**

| Pipeline | Strategy | Motivo |
|----------|----------|--------|
| `find . -name "*.py"` | BASH_PREFERRED | find ha edge cases, meglio bash.exe |
| `ls -la \| grep foo` | POWERSHELL | Semplice, emulabile con Get-ChildItem \| Select-String |
| `find . \| xargs grep` | BASH_REQUIRED | xargs + pipeline = bash.exe obbligatorio |
| `cat file.txt \| wc -l` | POWERSHELL | Get-Content \| Measure-Object (nativo) |
| `awk '{print $1}' \| sort` | MIXED | awk → bash.exe, sort → native bin |

**Fattori di decisione:**
1. **Complessità**: pipeline complessa vs singolo comando
2. **Comandi coinvolti**: BASH_EXE_PREFERRED vs traducibili
3. **Disponibilità risorse**: bash.exe disponibile? Native bins?
4. **Performance**: native bin > translator > bash.exe
5. **Compatibilità**: alcuni comandi DEVONO usare bash.exe

---

### SEPARAZIONE RESPONSABILITÀ

**PipelineStrategy** (MACRO - strategia globale):
- Analizza struttura completa pipeline
- Decide strategia di esecuzione globale
- Pattern matching su scenari noti
- Gestisce split pipeline se necessario

**ExecuteUnixSingleCommand** (MICRO - comando atomico):
- Incapsula le 4 strategie atomiche:
  1. SimpleTranslator (1:1)
  2. EmulativeTranslator (complesso)
  3. Native Binary (grep.exe, awk.exe, ecc.)
  4. Passthrough bash.exe
- Priorità e fallback incrociati PER SINGOLO COMANDO
- Scelta intelligente basata su comando specifico

**PipelineTranslator** (operatori):
- Traduce SOLO operatori pipeline Unix → Windows
- `|` → `|`
- `&&` → `;`
- `||` → PowerShell logic
- `>`, `<`, `2>` → redirection Windows

**CommandExecutor** (orchestratore):
- Usa PipelineStrategy (decide COSA fare)
- Usa ExecuteUnixSingleCommand (esegue comandi atomici)
- Usa PipelineTranslator (traduce operatori)
- Coordina esecuzione finale

---

## STATO ATTUALE (cosa abbiamo ora)

### CLASSI PRESENTI

**File: bash_tool_executor.py**
1. ✅ **ExecutionEngine** - CORRETTO (unico punto subprocess)
2. ✅ **PipelineStrategy** - CORRETTO (analisi strategica macro)
3. ✅ **ExecuteUnixSingleCommand** - CORRETTO (esecuzione micro con strategia)
4. ✅ **CommandExecutor** - PARZIALE (ha logic ma chiama ancora CommandTranslator)
5. ✅ **BashToolExecutor** - CORRETTO (entry point, path translation, security)

**File: unix_translator.py**
6. ✅ **SimpleTranslator** - CORRETTO (traduzioni 1:1)
7. ✅ **PipelineTranslator** - CORRETTO (traduzioni pipeline-aware)
8. ✅ **EmulativeTranslator** - CORRETTO (traduzioni complesse)
9. ❌ **CommandTranslator** - DA ELIMINARE (legacy monolitico, duplica tutto)

### PROBLEMI IDENTIFICATI

**PROBLEMA 1: CommandTranslator NON è stata eliminata**
- DOVEVA essere splittata → ✅ FATTO (Simple/Pipeline/Emulative esistono)
- DOVEVA essere rimossa → ❌ NON FATTO (ancora presente con 113 metodi)
- Contiene 107 metodi DUPLICATI dalle altre classi

**PROBLEMA 2: CommandExecutor usa ancora CommandTranslator**
```python
# ATTUALE (bash_tool_executor.py:1086)
translated_cmd, use_shell, method = self.command_translator.translate(command)
```
- CommandExecutor chiama `self.command_translator.translate()`
- Questo usa la classe legacy CommandTranslator
- DOVREBBE usare i 3 translator specializzati (Simple/Pipeline/Emulative)

**PROBLEMA 3: BashToolExecutor ha metodi preprocessing duplicati**
- BashToolExecutor ha 21 metodi preprocessing
- CommandTranslator ha gli STESSI 21 metodi (quasi-identici)
- DUPLICAZIONE: i metodi preprocessing dovrebbero stare SOLO in BashToolExecutor

**PROBLEMA 4: Metodi MULTISTEP duplicati**
- `_process_heredocs` esiste in BashToolExecutor (6483) E CommandTranslator (9737)
- `_process_substitution` esiste in BashToolExecutor (6663) E CommandTranslator (9907)
- Sono quasi-identici (diff: `_setup_environment()` vs `_get_default_environment()`)

---

## DUPLICATI TROVATI (107 metodi)

| Coppia Classi | Metodi Duplicati | Tipo |
|---------------|------------------|------|
| BashToolExecutor ↔ CommandTranslator | 21 | Preprocessing |
| SimpleTranslator ↔ CommandTranslator | 22 | _translate_* semplici |
| PipelineTranslator ↔ CommandTranslator | 23 | _translate_* pipeline |
| EmulativeTranslator ↔ CommandTranslator | 32 | _translate_* complessi |
| Altri | 9 | Helpers vari |

---

## REFACTORING NECESSARIO

### STEP 1: Rimuovere dipendenza CommandTranslator da CommandExecutor
**File:** `bash_tool_executor.py`
**Metodo:** `CommandExecutor.execute()` (line ~1086)

**DA:**
```python
translated_cmd, use_shell, method = self.command_translator.translate(command)
```

**A:**
```python
# Usare i 3 translator specializzati tramite strategia
# (SimpleTranslator, PipelineTranslator, EmulativeTranslator)
```

### STEP 2: Rimuovere CommandTranslator
**File:** `unix_translator.py`
**Azione:** Eliminare completamente la classe CommandTranslator (113 metodi)

### STEP 3: Rimuovere metodi preprocessing duplicati
**File:** `unix_translator.py` (in CommandTranslator - se non eliminata)
**Azione:** I 21 metodi preprocessing devono stare SOLO in BashToolExecutor

### STEP 4: Aggiungere testmode AS IF workaround
**File:** `bash_tool_executor.py`
**Metodi:** Solo 2 metodi ATTIVI in BashToolExecutor
- `_process_heredocs` (line 6483)
- `_process_substitution` (line 6663)

**Pattern:**
```python
result = self.command_executor.executor.execute_bash(...)

# TESTMODE EXECUTOR: simula output realistico per step successivo
if self.TESTMODE:
    result = subprocess.CompletedProcess(
        args=result.args,
        returncode=0,
        stdout="REALISTIC OUTPUT AS IF",  # ← Realistico per step 2
        stderr=""
    )

# Step 2 usa result.stdout
if result.returncode == 0:
    content = result.stdout
```

---

## ARCHITETTURA CORRENTE vs TARGET

### ATTUALE (PROBLEMATICA)
```
BashToolExecutor.execute()
  └─ CommandExecutor.execute()
       └─ CommandTranslator.translate()  ← LEGACY MONOLITICO
            ├─ Ha TUTTI i _translate_* (98 metodi)
            └─ Ha TUTTI i preprocessing (21 metodi)
```

### TARGET (DA REALIZZARE)
```
BashToolExecutor.execute()
  └─ CommandExecutor.execute()
       ├─ PipelineStrategy (strategia)
       └─ ExecuteUnixSingleCommand
            ├─ SimpleTranslator      ← SPECIALIZZATI
            ├─ PipelineTranslator    ← SPECIALIZZATI
            └─ EmulativeTranslator   ← SPECIALIZZATI
```

---

## STATO REFACTORING

| Componente | Stato | Note |
|------------|-------|------|
| ExecutionEngine | ✅ COMPLETO | Unico punto subprocess, testmode OK |
| PipelineStrategy | ✅ COMPLETO | Analisi strategica macro |
| ExecuteUnixSingleCommand | ✅ COMPLETO | Esecuzione micro con strategia |
| SimpleTranslator | ✅ COMPLETO | Traduzioni 1:1 |
| PipelineTranslator | ✅ COMPLETO | Traduzioni pipeline |
| EmulativeTranslator | ✅ COMPLETO | Traduzioni complesse |
| BashToolExecutor | ✅ COMPLETO | Entry point, preprocessing |
| CommandExecutor | ⚠️ PARZIALE | Usa ancora CommandTranslator |
| CommandTranslator | ❌ DA ELIMINARE | Legacy monolitico, 113 metodi duplicati |

---

## AZIONI IMMEDIATE

1. ❌ **NON** modificare CommandTranslator (verrà eliminata)
2. ✅ **Modificare** CommandExecutor per usare i 3 translator specializzati
3. ✅ **Eliminare** CommandTranslator completamente
4. ✅ **Aggiungere** testmode AS IF solo ai 2 metodi in BashToolExecutor

---

## PRIORITÀ

**PRIORITÀ 1:** Aggiungere testmode AS IF ai 2 metodi ATTIVI
- BashToolExecutor._process_heredocs (6483)
- BashToolExecutor._process_substitution (6663)

**PRIORITÀ 2:** Refactoring CommandExecutor per eliminare dipendenza da CommandTranslator

**PRIORITÀ 3:** Eliminare CommandTranslator completamente

**PRIORITÀ 4:** Cleanup e test
