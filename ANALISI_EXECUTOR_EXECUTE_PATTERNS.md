# Analisi Pattern executor.execute_* e result.returncode

**Data:** 2025-11-18
**File analizzati:** bash_tool_executor.py, unix_translator.py

---

## Pattern Cercati

1. `result = executor.execute_*` (qualsiasi metodo execute di ExecutionEngine)
2. `if result.returncode == 0:` seguito da `content = result.stdout`

---

## RIEPILOGO COMPLETO

### bash_tool_executor.py

**Totale occorrenze `result = executor.execute_*`: 5**
**Totale occorrenze `if result.returncode == 0:`: 5**
**Occorrenze con ENTRAMBI i pattern: 1 ✅**

### unix_translator.py

**Nessuna occorrenza** di nessuno dei due pattern.

---

## DETTAGLIO COMPLETO bash_tool_executor.py

### Occorrenze `result = executor.execute_*`

| # | Linea | Metodo Contenitore | Codice | Note |
|---|-------|-------------------|--------|------|
| 1 | 1377 | `CommandExecutor.execute()` | `result = self.executor.execute_powershell(` | PowerShell script command |
| 2 | 1387 | `CommandExecutor.execute()` | `result = self.executor.execute_powershell(` | use_powershell branch |
| 3 | 1396 | `CommandExecutor.execute()` | `result = self.executor.execute_cmd(` | CMD fallback |
| 4 | 6584 | `BashToolExecutor._process_heredocs()` | `result = self.command_executor.executor.execute_bash(` | ✅ **HA PATTERN COMPLETO** |
| 5 | 6684 | `BashToolExecutor._process_substitution()` | `result = self.command_executor.executor.execute_cmd(` | NO check returncode |

### Occorrenze `if result.returncode == 0:`

| # | Linea | Metodo Contenitore | Seguito da `content = result.stdout` | Contesto |
|---|-------|-------------------|--------------------------------------|----------|
| 1 | 1513 | `CommandExecutor._detect_native_binaries()` | NO | Native binary detection loop |
| 2 | 6603 | `BashToolExecutor._process_heredocs()` | ✅ **SI (linea 6605)** | ✅ **PATTERN COMPLETO** |
| 3 | 7413 | `BashToolExecutor._detect_git_bash()` | NO | Git Bash path validation |
| 4 | 7551 | `BashToolExecutor._detect_system_python()` | NO | Python version detection |
| 5 | 7708 | `BashToolExecutor._format_result()` | NO | Result formatting |

---

## METODO CON PATTERN COMPLETO ✅

### BashToolExecutor._process_heredocs() - Linee 6471-6650

**Pattern trovato:**

```python
# Linea 6584: Chiamata execute_bash
result = self.command_executor.executor.execute_bash(
    bash_path,
    expansion_script,
    timeout=5,
    cwd=str(self.scratch_dir),
    env=self._setup_environment(),
    errors='replace',
    encoding='utf-8'
)

# Linea 6594-6601: TESTMODE simulation
if self.TESTMODE:
    result = subprocess.CompletedProcess(
        args=result.args,
        returncode=0,
        stdout=content,  # AS IF: usa contenuto originale come "espanso"
        stderr=""
    )

# Linea 6603: Check returncode
if result.returncode == 0:
    # Linea 6605: Estrae stdout
    content = result.stdout
    self.logger.debug(f"Heredoc expanded via bash.exe (delimiter: {delimiter})")
else:
    # Expansion failed - use literal
    self.logger.warning(f"Heredoc expansion failed (exit {result.returncode}), using literal content")
```

**Contesto:** 
- Preprocessing di heredoc con espansione variabili via Git Bash
- Usa `execute_bash` per espandere variabili in heredoc
- In caso di successo (returncode 0), usa l'output espanso
- In caso di fallimento, usa contenuto letterale

**Caratteristiche:**
- ✅ Ha `result = executor.execute_bash()`
- ✅ Ha `if result.returncode == 0:`
- ✅ Ha `content = result.stdout` (linea 6605)
- ✅ Ha gestione TESTMODE
- ✅ Ha fallback in caso di errore

---

## ALTRI METODI (senza pattern completo)

### 1. CommandExecutor.execute() - Linee 1335-1413

**Occorrenze execute_*:** 3 volte (linee 1377, 1387, 1396)
**Check returncode:** NO (ritorna direttamente result)

**Pattern:**
```python
if 'powershell' in final_cmd.lower() and '-File' in final_cmd:
    result = self.executor.execute_powershell(...)
elif use_powershell:
    result = self.executor.execute_powershell(...)
else:
    result = self.executor.execute_cmd(...)

return result, translated_cmd, method  # ← Ritorna senza check
```

**Note:** Il metodo `execute()` di CommandExecutor ritorna il result direttamente senza fare check del returncode. Il check viene fatto dal chiamante.

---

### 2. BashToolExecutor._process_substitution() - Linee 6650-6750

**Occorrenze execute_*:** 1 volta (linea 6684)
**Check returncode:** NO (scrive direttamente stdout su file)

**Pattern:**
```python
result = self.command_executor.executor.execute_cmd(
    translated,
    timeout=30,
    cwd=str(cwd),
    env=env,
    errors='replace'
)

# TESTMODE simulation
if self.TESTMODE:
    result = subprocess.CompletedProcess(...)

# Crea temp file CON OUTPUT (senza check returncode!)
temp_file = cwd / f'procsub_input_{threading.get_ident()}_{len(temp_files)}.tmp'
with open(temp_file, 'w', encoding='utf-8') as f:
    f.write(result.stdout)  # ← Scrive SEMPRE, anche se returncode != 0
```

**Note:** Questo metodo NON fa check del returncode prima di scrivere stdout. Potenziale bug se il comando fallisce.

---

### 3. CommandExecutor._detect_native_binaries() - Linee 1480-1520

**Occorrenze execute_*:** NO (usa subprocess diretto, NON executor)
**Check returncode:** SI (linea 1513)

**Pattern:**
```python
result = subprocess.run([binary, '--version'], ...)
if result.returncode == 0:
    available[cmd] = binary  # ← Non usa result.stdout
```

**Note:** Usa subprocess.run diretto (NON ExecutionEngine). Il check returncode serve solo per validare disponibilità, non estrae stdout.

---

### 4. BashToolExecutor._detect_git_bash() - Linee 7400-7450

**Occorrenze execute_*:** NO (usa subprocess diretto)
**Check returncode:** SI (linea 7413)

**Pattern:**
```python
result = subprocess.run(['where', 'bash'], ...)
if result.returncode == 0:
    bash_path = result.stdout.strip().split('\n')[0]  # ← Estrae stdout ma è un caso diverso
```

**Note:** Usa `result.stdout` ma non lo assegna a `content`. È un pattern diverso (detect path).

---

### 5. BashToolExecutor._detect_system_python() - Linee 7540-7580

**Occorrenze execute_*:** NO (usa subprocess diretto)
**Check returncode:** SI (linea 7551)

**Pattern:**
```python
result = subprocess.run([cmd, '--version'], ...)
if result.returncode == 0:
    version = result.stdout.strip()  # ← Estrae stdout ma è un caso diverso
```

**Note:** Usa `result.stdout` ma non lo assegna a `content`. È un pattern diverso (detect version).

---

### 6. BashToolExecutor._format_result() - Linee 7700-7750

**Occorrenze execute_*:** NO (riceve result come parametro)
**Check returncode:** SI (linea 7708)

**Pattern:**
```python
if result.returncode == 0:
    lines.append(f"Exit code: {result.returncode}")  # ← Formatting, non estrazione
else:
    lines.append(f"Exit code: {result.returncode}")
```

**Note:** Check returncode per formattazione output, non per estrarre stdout.

---

## CONCLUSIONE

**UNICO metodo con il pattern completo cercato:**

```
Metodo: BashToolExecutor._process_heredocs()
File: bash_tool_executor.py
Linee: 6471-6650
Pattern linea execute: 6584
Pattern linea check: 6603
Pattern linea estrazione: 6605
```

**Pattern esatto:**
```python
result = self.command_executor.executor.execute_bash(...)
if result.returncode == 0:
    content = result.stdout
```

**Altri metodi simili (ma pattern diverso):**
- `_process_substitution()`: usa execute_cmd ma NON fa check returncode
- `execute()`: usa execute_powershell/execute_cmd ma NON fa check returncode (ritorna direttamente)
- `_detect_*()`: fanno check returncode ma usano subprocess.run diretto (NON executor)
- `_format_result()`: fa check returncode ma per formattazione (NON estrazione)

**unix_translator.py:** Nessuna occorrenza di nessuno dei due pattern.
