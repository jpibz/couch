# DUPLICATE METHODS MAPPING - Architettura Finale

## Analisi Metodi Duplicati e Destinazione Finale

Questo documento identifica i metodi duplicati tra **CommandTranslator** e **CommandExecutor** e definisce la loro destinazione finale nell'architettura refactored.

**PREMESSA IMPORTANTE**: CommandTranslator verrà **ELIMINATA** dall'architettura finale.

---

## ARCHITETTURA FINALE (Target)

```
CommandExecutor (thin orchestration)
│
├─ PipelineStrategy (MACRO - analisi pipeline)
├─ ExecuteUnixSingleCommand (MICRO - singolo comando)
│
└─ Translators (3 classi specializzate)
   ├─ SimpleTranslator (1:1 mappings: pwd→Get-Location)
   ├─ EmulativeTranslator (PowerShell emulation: grep→Select-String)
   └─ PipelineTranslator (pipeline operators: |, &&, ||, etc.)
```

---

## METODI DUPLICATI IDENTIFICATI

Dalla analisi del file `METHOD_ANALYSIS.csv`:

| # | Metodo | CommandTranslator (Row) | CommandExecutor (Row) | Lines | Funzione |
|---|--------|------------------------|---------------------|-------|----------|
| 1 | `_awk_to_ps_statement` | 44 | 101 | 32 | Converte statement awk in PowerShell |
| 2 | `_awk_to_ps_condition` | 45 | 102 | 7 | Converte condizioni awk in PowerShell |
| 3 | `_parse_size` | 76 | 110 | 26 | Parser dimensioni (10M, 1G, etc.) |
| 4 | `_is_simple_jq_pattern` | 80 | 112 | 36 | Detecta se pattern jq è semplice |
| 5 | `_jq_to_powershell` | 81 | 113 | 66 | Converte jq in PowerShell |
| 6 | `_parse_duration` | 74 | 115 | 24 | Parser durate (10s, 5m, 1h, etc.) |

**TOTALE DUPLICAZIONI**: 6 metodi helper, ~191 righe duplicate

---

## MAPPING ALLA DESTINAZIONE FINALE

### Decisione Strategica

Tutti questi metodi sono **UTILITY per traduzione/emulazione PowerShell**. Anche se alcuni (_parse_size, _parse_duration) sono più "generici" (parsing input), sono SEMPRE usati nel contesto di emulazione PowerShell.

**DESTINAZIONE**: Tutti i 6 metodi vanno in **EmulativeTranslator**

---

## DETTAGLIO MAPPING

### 1. AWK Emulation Helpers → EmulativeTranslator

| Metodo | Destinazione Finale | Rationale |
|--------|-------------------|-----------|
| `_awk_to_ps_statement` | **EmulativeTranslator** | Converte statement awk in PowerShell. Core emulation logic. |
| `_awk_to_ps_condition` | **EmulativeTranslator** | Converte condizioni awk in PowerShell. Core emulation logic. |

**Utilizzo**:
- Chiamato da `_translate_awk()` / `_execute_awk()`
- Converte costrutti awk come `{print $1}` in PowerShell `| ForEach-Object {$_.Split()[0]}`

**Esempio**:
```python
# AWK command
"awk '{print $1}' file.txt"

# PowerShell emulation
"Get-Content file.txt | ForEach-Object {$_.Split()[0]}"

# Helper chiamato
_awk_to_ps_statement("{print $1}") → "$_.Split()[0]"
```

**Posizione finale in EmulativeTranslator**:
```python
class EmulativeTranslator:
    def translate_awk(self, command, parts):
        """Emula awk con PowerShell."""
        # ... parsing logic ...
        statement = self._awk_to_ps_statement(awk_script)
        condition = self._awk_to_ps_condition(awk_pattern)
        # ...

    def _awk_to_ps_statement(self, script: str) -> str:
        """Converte awk statement in PowerShell."""
        # 32 lines implementation
        pass

    def _awk_to_ps_condition(self, pattern: str) -> str:
        """Converte awk condition in PowerShell Where-Object."""
        # 7 lines implementation
        pass
```

---

### 2. JQ Emulation Helpers → EmulativeTranslator

| Metodo | Destinazione Finale | Rationale |
|--------|-------------------|-----------|
| `_is_simple_jq_pattern` | **EmulativeTranslator** | Detecta pattern jq semplici (emulabili con ConvertFrom-Json). |
| `_jq_to_powershell` | **EmulativeTranslator** | Converte pattern jq in PowerShell JSON manipulation. |

**Utilizzo**:
- Chiamato da `_translate_jq()` / `_execute_jq()`
- Emula jq JSON query language con PowerShell

**Esempio**:
```python
# JQ command
"jq '.name' data.json"

# PowerShell emulation
"(Get-Content data.json | ConvertFrom-Json).name"

# Helper chiamato
_is_simple_jq_pattern(".name") → True
_jq_to_powershell(".name") → "(Get-Content data.json | ConvertFrom-Json).name"
```

**Posizione finale in EmulativeTranslator**:
```python
class EmulativeTranslator:
    def translate_jq(self, command, parts):
        """Emula jq con PowerShell ConvertFrom-Json."""
        pattern = parts[1]
        if self._is_simple_jq_pattern(pattern):
            return self._jq_to_powershell(command, parts)
        else:
            # Fallback a bash.exe o errore
            return None

    def _is_simple_jq_pattern(self, pattern: str) -> bool:
        """Detecta se pattern jq è emulabile in PowerShell."""
        # 36 lines implementation
        pass

    def _jq_to_powershell(self, command: str, parts: List[str]) -> str:
        """Converte jq pattern in PowerShell."""
        # 66 lines implementation
        pass
```

---

### 3. Parsing Helpers → EmulativeTranslator

| Metodo | Destinazione Finale | Rationale |
|--------|-------------------|-----------|
| `_parse_size` | **EmulativeTranslator** | Parser dimensioni Unix (10M, 1G). Usato da split, dd, etc. |
| `_parse_duration` | **EmulativeTranslator** | Parser durate Unix (10s, 5m, 1h). Usato da timeout, sleep. |

**Nota**: Questi sono helper più "generici" (parsing input), ma vengono SEMPRE usati nel contesto di emulazione PowerShell, quindi vanno in **EmulativeTranslator**.

**Alternativa considerata**: Classe separata `ParsingUtils` o `CommandParsingUtils`
**Decisione**: NO. Seguiamo YAGNI (You Aren't Gonna Need It). Teniamo tutto in EmulativeTranslator finché non emerge pattern chiaro di riuso cross-Translator.

**Utilizzo _parse_size**:
- Comandi: `split -b 10M`, `dd bs=1G`, `head -c 100K`
- Converte "10M" → 10485760 bytes

**Esempio**:
```python
# Unix command
"split -b 10M file.txt"

# PowerShell emulation (necessita conversione size)
# "10M" → 10485760 bytes per PowerShell

# Helper chiamato
_parse_size("10M") → 10485760
```

**Utilizzo _parse_duration**:
- Comandi: `timeout 10s`, `sleep 5m`
- Converte "10s" → 10 secondi, "5m" → 300 secondi

**Esempio**:
```python
# Unix command
"timeout 5m python script.py"

# PowerShell emulation
# "5m" → 300 secondi per Start-Sleep / timeout

# Helper chiamato
_parse_duration("5m") → 300
```

**Posizione finale in EmulativeTranslator**:
```python
class EmulativeTranslator:
    def translate_split(self, command, parts):
        """Emula split con PowerShell."""
        # Parse -b 10M
        if '-b' in parts:
            idx = parts.index('-b')
            size_bytes = self._parse_size(parts[idx + 1])
            # Usa size_bytes per split logic
        # ...

    def translate_timeout(self, command, parts):
        """Emula timeout con PowerShell."""
        # Parse 10s duration
        duration_str = parts[1]
        duration_sec = self._parse_duration(duration_str)
        # Usa duration_sec per timeout logic
        # ...

    def _parse_size(self, size_str: str) -> int:
        """
        Parser dimensioni Unix-style.

        Examples:
            "10M" → 10485760
            "1G" → 1073741824
            "100K" → 102400
        """
        # 26 lines implementation
        pass

    def _parse_duration(self, duration_str: str) -> int:
        """
        Parser durate Unix-style.

        Examples:
            "10s" → 10
            "5m" → 300
            "1h" → 3600
        """
        # 24 lines implementation
        pass
```

---

## PIANO DI MIGRAZIONE

### Step 1: Crea EmulativeTranslator con i 6 metodi ✅

**File**: `couch/translators/emulative_translator.py`

```python
class EmulativeTranslator:
    """
    PowerShell emulation per comandi Unix complessi.

    Gestisce traduzione di comandi che richiedono emulazione
    con cmdlet PowerShell (grep, awk, sed, jq, etc.).
    """

    def __init__(self):
        pass

    # === AWK Emulation ===
    def translate_awk(self, command, parts): ...
    def _awk_to_ps_statement(self, script: str) -> str: ...
    def _awk_to_ps_condition(self, pattern: str) -> str: ...

    # === JQ Emulation ===
    def translate_jq(self, command, parts): ...
    def _is_simple_jq_pattern(self, pattern: str) -> bool: ...
    def _jq_to_powershell(self, command, parts) -> str: ...

    # === Parsing Utilities ===
    def _parse_size(self, size_str: str) -> int: ...
    def _parse_duration(self, duration_str: str) -> int: ...

    # === Altri comandi emulated ===
    def translate_grep(self, command, parts): ...
    def translate_sed(self, command, parts): ...
    def translate_find(self, command, parts): ...
    # ... (tutti gli altri comandi "Simulation/Workaround" dal CSV)
```

### Step 2: Copia implementazione da CommandTranslator ✅

**Fonte**: `couch/unix_translator.py` (CommandTranslator)

Copia i 6 metodi duplicati:
1. `_awk_to_ps_statement` (32 lines) - row 44
2. `_awk_to_ps_condition` (7 lines) - row 45
3. `_parse_size` (26 lines) - row 76
4. `_is_simple_jq_pattern` (36 lines) - row 80
5. `_jq_to_powershell` (66 lines) - row 81
6. `_parse_duration` (24 lines) - row 74

**Azione**: Copy/paste implementazione da CommandTranslator → EmulativeTranslator

### Step 3: Update chiamanti in CommandExecutor 🔄

**File**: `couch/bash_tool_executor.py` (CommandExecutor)

**PRIMA**:
```python
class CommandExecutor:
    def _execute_awk(self, command, parts):
        # Logica duplicata
        statement = self._awk_to_ps_statement(script)
        condition = self._awk_to_ps_condition(pattern)
        # ...

    def _awk_to_ps_statement(self, script): ...  # DUPLICATO
    def _awk_to_ps_condition(self, pattern): ...  # DUPLICATO
```

**DOPO**:
```python
class CommandExecutor:
    def __init__(self, ...):
        self.emulative = EmulativeTranslator()  # Dependency injection

    def _execute_awk(self, command, parts):
        # Delega a EmulativeTranslator
        return self.emulative.translate_awk(command, parts)

    # RIMUOVI metodi duplicati _awk_to_ps_statement, _awk_to_ps_condition
```

### Step 4: Elimina duplicati da CommandExecutor ✅

**Rimuovi i 6 metodi da CommandExecutor**:
- `_awk_to_ps_statement` (row 101)
- `_awk_to_ps_condition` (row 102)
- `_parse_size` (row 110)
- `_is_simple_jq_pattern` (row 112)
- `_jq_to_powershell` (row 113)
- `_parse_duration` (row 115)

**Risultato**: -191 righe da CommandExecutor

### Step 5: Elimina CommandTranslator ⚠️ **FUTURO**

Quando tutti i metodi di CommandTranslator saranno migrati a SimpleTranslator, EmulativeTranslator, PipelineTranslator:

1. Rimuovi `couch/unix_translator.py`
2. Rimuovi import di CommandTranslator
3. Verifica che tutti i test passino

---

## IMPATTO SULLA STRUTTURA

### Before (Stato Attuale)

```
CommandTranslator (81 metodi)
├─ _awk_to_ps_statement     ← DUPLICATO
├─ _awk_to_ps_condition     ← DUPLICATO
├─ _parse_size              ← DUPLICATO
├─ _is_simple_jq_pattern    ← DUPLICATO
├─ _jq_to_powershell        ← DUPLICATO
├─ _parse_duration          ← DUPLICATO
└─ ... (altri 75 metodi)

CommandExecutor (45 metodi)
├─ _awk_to_ps_statement     ← DUPLICATO
├─ _awk_to_ps_condition     ← DUPLICATO
├─ _parse_size              ← DUPLICATO
├─ _is_simple_jq_pattern    ← DUPLICATO
├─ _jq_to_powershell        ← DUPLICATO
├─ _parse_duration          ← DUPLICATO
└─ ... (altri 39 metodi)
```

**Problemi**:
- 6 metodi duplicati (~191 righe duplicate)
- Manutenzione doppia (bug fix in 2 posti)
- Logica mescolata (translator + executor)

### After (Target Finale)

```
EmulativeTranslator (nuovo)
├─ _awk_to_ps_statement     ✅ UNICA FONTE
├─ _awk_to_ps_condition     ✅ UNICA FONTE
├─ _parse_size              ✅ UNICA FONTE
├─ _is_simple_jq_pattern    ✅ UNICA FONTE
├─ _jq_to_powershell        ✅ UNICA FONTE
├─ _parse_duration          ✅ UNICA FONTE
└─ translate_awk, translate_jq, translate_grep, ...

CommandExecutor (refactored)
├─ __init__(emulative=EmulativeTranslator())
├─ _execute_awk → self.emulative.translate_awk()
├─ _execute_jq → self.emulative.translate_jq()
└─ ... (delega a translators)

CommandTranslator
└─ [ELIMINATO]
```

**Benefici**:
- ✅ Zero duplicazioni
- ✅ Single source of truth
- ✅ Separazione responsabilità (executor vs translator)
- ✅ Testabilità migliorata (test EmulativeTranslator isolato)

---

## METRICS

### Riduzione Duplicazioni

| Metodo | Lines | Duplicazioni | Lines Eliminate |
|--------|-------|--------------|-----------------|
| _awk_to_ps_statement | 32 | 2x | 32 |
| _awk_to_ps_condition | 7 | 2x | 7 |
| _parse_size | 26 | 2x | 26 |
| _is_simple_jq_pattern | 36 | 2x | 36 |
| _jq_to_powershell | 66 | 2x | 66 |
| _parse_duration | 24 | 2x | 24 |
| **TOTALE** | **191** | **12 occorrenze** | **191 lines** |

### Riduzione Complessità

| Classe | Before | After | Delta |
|--------|--------|-------|-------|
| CommandTranslator | 81 metodi | **ELIMINATO** | -81 |
| CommandExecutor | 45 metodi | ~39 metodi | -6 |
| EmulativeTranslator | 0 | ~30 metodi | +30 |
| **TOTALE** | 126 metodi | ~69 metodi | **-57** |

**Nota**: Il totale metodi si riduce perché eliminiamo duplicazioni e CommandTranslator viene decomposto in 3 classi specializzate (Simple, Emulative, Pipeline), ognuna con MENO metodi della monolitica CommandTranslator.

---

## TESTING STRATEGY

### Unit Tests per EmulativeTranslator

```python
# test_emulative_translator.py

def test_awk_to_ps_statement():
    translator = EmulativeTranslator()

    # Test print column
    assert translator._awk_to_ps_statement("{print $1}") == "$_.Split()[0]"

    # Test multiple columns
    assert translator._awk_to_ps_statement("{print $1, $3}") == "$_.Split()[0], $_.Split()[2]"

def test_awk_to_ps_condition():
    translator = EmulativeTranslator()

    # Test numeric condition
    assert translator._awk_to_ps_condition("$1 > 10") == "$_.Split()[0] -gt 10"

    # Test string match
    assert translator._awk_to_ps_condition("/pattern/") == "$_ -match 'pattern'"

def test_parse_size():
    translator = EmulativeTranslator()

    assert translator._parse_size("10M") == 10485760
    assert translator._parse_size("1G") == 1073741824
    assert translator._parse_size("100K") == 102400

def test_parse_duration():
    translator = EmulativeTranslator()

    assert translator._parse_duration("10s") == 10
    assert translator._parse_duration("5m") == 300
    assert translator._parse_duration("1h") == 3600

def test_is_simple_jq_pattern():
    translator = EmulativeTranslator()

    assert translator._is_simple_jq_pattern(".name") == True
    assert translator._is_simple_jq_pattern(".data[0].value") == True
    assert translator._is_simple_jq_pattern(".[] | select(.age > 10)") == False

def test_jq_to_powershell():
    translator = EmulativeTranslator()

    result = translator._jq_to_powershell("jq '.name' data.json", ["jq", ".name", "data.json"])
    assert "ConvertFrom-Json" in result
    assert ".name" in result
```

### Integration Tests

```python
# test_command_executor_integration.py

def test_execute_awk_delegates_to_emulative():
    executor = CommandExecutor()

    # Esegui awk command
    result = executor.execute_bash("awk '{print $1}' file.txt", ["awk", ...])

    # Verifica che delega a EmulativeTranslator
    assert "ForEach-Object" in result.command
    assert "$_.Split()[0]" in result.command

def test_execute_jq_delegates_to_emulative():
    executor = CommandExecutor()

    result = executor.execute_bash("jq '.name' data.json", ["jq", ...])

    assert "ConvertFrom-Json" in result.command
```

---

## DECISIONI ARCHITETTURALI

### Decisione 1: EmulativeTranslator vs ParsingUtils

**Opzione A**: Tutti i 6 metodi in EmulativeTranslator
**Opzione B**: _parse_size e _parse_duration in classe separata ParsingUtils

**SCELTA**: Opzione A (EmulativeTranslator)

**Rationale**:
1. **YAGNI**: Non creare classi finché non emerge pattern chiaro di riuso
2. **Context**: _parse_size e _parse_duration sono SEMPRE usati nel contesto di emulazione PowerShell
3. **Semplicità**: Meno classi = meno complessità
4. **Refactoring futuro**: Se emerge riuso cross-Translator, facile estrarre in Utils

### Decisione 2: Copy/Paste vs Inheritance

**Opzione A**: Copiare implementazione da CommandTranslator → EmulativeTranslator
**Opzione B**: EmulativeTranslator eredita da CommandTranslator durante transizione

**SCELTA**: Opzione A (Copy/Paste)

**Rationale**:
1. **Clean Break**: CommandTranslator verrà eliminato, non vogliamo dipendenze
2. **Indipendenza**: EmulativeTranslator deve essere standalone
3. **Testing**: Test isolati senza dipendenze da classi deprecate

### Decisione 3: Timing - Quando Eliminare CommandTranslator?

**SCELTA**: FASE FINALE (dopo Step 5 migration plan)

**Rationale**:
1. Prima migriamo TUTTI i metodi da CommandTranslator ai 3 nuovi Translators
2. Poi aggiorniamo tutti i chiamanti
3. Poi verifichiamo che tutti i test passino
4. Solo ALLA FINE eliminiamo CommandTranslator

**Timeline**:
- Phase 1: ✅ Crea EmulativeTranslator con 6 metodi duplicati
- Phase 2: 🔄 Migra altri metodi "Simulation/Workaround" da CommandTranslator
- Phase 3: 🔄 Migra metodi "Simple 1:1" a SimpleTranslator
- Phase 4: 🔄 Migra metodi "Pipeline/Operators" a PipelineTranslator
- Phase 5: ⚠️ Elimina CommandTranslator

---

## CHECKLIST IMPLEMENTAZIONE

### Phase 1: Crea EmulativeTranslator
- [ ] Crea file `couch/translators/emulative_translator.py`
- [ ] Implementa skeleton classe EmulativeTranslator
- [ ] Copia 6 metodi duplicati da CommandTranslator:
  - [ ] _awk_to_ps_statement
  - [ ] _awk_to_ps_condition
  - [ ] _parse_size
  - [ ] _is_simple_jq_pattern
  - [ ] _jq_to_powershell
  - [ ] _parse_duration
- [ ] Scrivi unit tests per i 6 metodi
- [ ] Verifica che tests passino

### Phase 2: Update CommandExecutor
- [ ] Aggiungi dependency injection: `self.emulative = EmulativeTranslator()`
- [ ] Update chiamate ai 6 metodi:
  - [ ] _execute_awk → delega a emulative.translate_awk
  - [ ] _execute_jq → delega a emulative.translate_jq
  - [ ] _execute_split → usa emulative._parse_size
  - [ ] _execute_timeout → usa emulative._parse_duration
- [ ] Rimuovi i 6 metodi duplicati da CommandExecutor
- [ ] Verifica che integration tests passino

### Phase 3: Verifica & Cleanup
- [ ] Run full test suite
- [ ] Verifica che CommandTranslator non sia più usato per questi 6 metodi
- [ ] Update documentazione
- [ ] Code review
- [ ] Merge to main

---

## PROSSIMI STEP

1. **IMMEDIATO**: Implementare Phase 1 (crea EmulativeTranslator)
2. **SHORT-TERM**: Implementare Phase 2 (update CommandExecutor)
3. **MEDIUM-TERM**: Migrare altri metodi "Simulation/Workaround" a EmulativeTranslator
4. **LONG-TERM**: Eliminare completamente CommandTranslator

---

*Documento creato: 2025-11-18*
*Analisi basata su: METHOD_ANALYSIS.csv, ARCHITETTURE_REFACTORING_STATUS.md*
