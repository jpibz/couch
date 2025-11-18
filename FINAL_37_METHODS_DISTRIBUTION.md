# DISTRIBUZIONE FINALE 37 METODI PREPROCESSING/EXPANSION/CONTROL

## DECISIONE FINALE (CORRETTA)

**Data:** 2025-11-18
**Basata su:** Lettura codice effettivo + Analisi flusso di esecuzione

---

## PRINCIPIO CHIAVE

**Separazione tra PREPROCESSING e TRADUZIONE:**

- **PREPROCESSING generico** → CommandExecutor
  Opera su SINTASSI (trasformazioni testuali)
  Applicato a TUTTI i comandi indistintamente
  Esempi: espansione variabili, heredocs, brace expansion

- **TRADUZIONE specifica** → ExecuteUnixSingleCommand
  Opera su SEMANTICA (traduzione logica)
  Specifici per tipo di comando/costrutto
  Esempi: sed→PS, awk→PS, **if/for/while→PS**

---

## DISTRIBUZIONE FINALE

### 1. CommandExecutor (28 metodi) - PREPROCESSING GENERICO

**A. Heredocs e Process Substitution (5 metodi):**
1. `_process_heredocs` - Converte `<<EOF` in file temporaneo
2. `_process_substitution` - Gestisce `<(cmd)` e `>(cmd)`
3. `_process_command_substitution_recursive` - Gestisce `$(cmd)` ricorsivamente
4. `_translate_substitution_content` - Traduce contenuto substitution
5. `find_substitutions` - Trova pattern `$()` e backticks

**B. Subshell e Command Grouping (2 metodi):**
6. `_process_subshell` - Gestisce `(cmd1; cmd2)`
7. `_process_command_grouping` - Gestisce `{cmd1; cmd2}`

**C. Preprocessing Patterns (4 metodi):**
8. `_process_xargs` - Trasforma pattern xargs
9. `_process_find_exec` - Trasforma `find ... -exec`
10. `_process_escape_sequences` - Gestisce escape sequences
11. `_preprocess_test_commands` - Preprocessa `[ ]` e `[[ ]]`

**D. Variable Expansion (20 metodi):**
12. `_expand_variables` - Orchestrator principale
13. `_expand_aliases` - Espansione alias (ll, la, etc.)
14. `_expand_braces` - Orchestrator brace expansion
15. `expand_simple_var` - `$var`, `${var}`
16. `expand_default` - `${var:-default}`
17. `expand_assign` - `${var:=value}`
18. `expand_length` - `${#var}`
19. `expand_remove_prefix` - `${var#pattern}`, `${var##pattern}`
20. `expand_remove_suffix` - `${var%pattern}`, `${var%%pattern}`
21. `expand_case` - `${var^^}`, `${var,,}`, `${var~}`
22. `expand_substitution` - `$(cmd)` expansion
23. `expand_arithmetic` - `$((expr))`
24. `expand_simple_brace` - `{a,b,c}`
25. `expand_single_brace` - `{1..10}`, `{a..z}`
26. `expand_grouping` - Group expansion
27. `is_complex_substitution` - Detecta substitution complesse
28. `remove_subshell` - Rimuove sintassi subshell
29. `replace_input_substitution` - Replace `<()`
30. `replace_output_substitution` - Replace `>()`

**E. Cleanup (1 metodo):**
31. `_cleanup_temp_files` - Cleanup file temporanei (heredocs, .ps1, etc.)

**TOTALE CommandExecutor: 28 metodi**

---

### 2. ExecuteUnixSingleCommand (8 metodi) - SCRIPT TRANSLATION

**NUOVO COMPONENTE: ScriptTranslator**
Gestisce conversione bash control structures → PowerShell scripts

**A. Control Structures Detection & Conversion (4 metodi):**
1. `_has_control_structures` - Detecta if/for/while/case
2. `_convert_control_structures_to_script` - Crea file .ps1 temporaneo
3. `_bash_to_powershell` - Core conversion (if→If, for→ForEach, while→While)
4. `_convert_test_to_powershell` - Converte test conditions (`[ -f file ]` → `Test-Path`)

**B. PowerShell Strategy Decision (2 metodi):**
5. `_needs_powershell` - Detecta se serve PowerShell vs cmd.exe (basato su cmdlet nel comando TRADOTTO)
6. `_adapt_for_powershell` - Adatta comando per esecuzione PowerShell

**Note:**
- I metodi `convert_if`, `convert_for`, `convert_while`, `convert_test`, `convert_double_test` sono **CLOSURE functions** dentro `_bash_to_powershell`, NON metodi standalone
- Questi 5 non vengono contati nei 37 metodi totali

**TOTALE ExecuteUnixSingleCommand: 8 metodi**
*Di cui 1 metodo (`_adapt_for_powershell`) potrebbe essere spostato in EmulativeTranslator*

---

### 3. EmulativeTranslator (1 metodo) - EMULATION ADAPTATION

1. `_adapt_for_powershell` - Adatta comando per emulazione PowerShell

*Alternativa: Questo metodo potrebbe restare in ExecuteUnixSingleCommand se è decisione tattica generale, non specifica dell'emulation*

**TOTALE EmulativeTranslator: 0-1 metodo** (dipende da scelta implementativa)

---

## VERIFICA TOTALE

- CommandExecutor: 28 metodi
- ExecuteUnixSingleCommand: 8 metodi
- EmulativeTranslator: 1 metodo

**TOTALE: 37 metodi** ✓

(42 metodi originali - 5 closure functions = 37 metodi veri)

---

## MOTIVAZIONE CHIAVE

**Perché bash→PowerShell va in ExecuteUnixSingleCommand, NON in CommandExecutor?**

1. **`_bash_to_powershell` è TRADUZIONE, non preprocessing:**
   - Preprocessing: `$var` → valore (testuale)
   - Traduzione: `if...; then...; fi` → `If (...) { ... }` (semantica)

2. **Parallelo con altri Translators:**
   - SimpleTranslator: `pwd` → `Get-Location`
   - EmulativeTranslator: `sed` → PowerShell emulation
   - PipelineTranslator: `|` → pipeline operators
   - **ScriptTranslator**: `if/for/while` → PowerShell script

3. **ExecuteUnixSingleCommand gestisce strategie di ESECUZIONE:**
   - SIMPLE: Traduzione 1:1
   - NATIVE: Binary nativo (.exe)
   - BASH: Passthrough a bash.exe
   - EMULATIVE: Emulazione PowerShell
   - **SCRIPT**: Conversione a PowerShell script

4. **CommandExecutor deve essere "thin orchestrator":**
   - 28 metodi di preprocessing generico: OK
   - +8 metodi di script translation: TROPPO, deve delegare

---

## FLUSSO DI ESECUZIONE FINALE

```
1. Input: "if [ -f file ]; then cat file | grep pattern; fi"

2. CommandExecutor (LEVEL 1 - MACRO):
   - Preprocessing generico (variabili, heredocs, etc.)
   - Passa a PipelineStrategy

3. PipelineStrategy (LEVEL 1 - MACRO):
   - Analizza comando preprocessato
   - Detecta: "Control structure detected"
   - Decide strategia: SCRIPT_CONVERSION (oppure BASH_REQUIRED)
   - Passa a ExecuteUnixSingleCommand con strategia

4. ExecuteUnixSingleCommand (LEVEL 2 - MICRO):
   - Riceve strategia SCRIPT_CONVERSION
   - ScriptTranslator._has_control_structures() → True
   - ScriptTranslator._convert_control_structures_to_script()
     - Chiama _bash_to_powershell()
     - Crea /tmp/script.ps1
   - Esegue: powershell -File /tmp/script.ps1
```

---

## NOTE IMPLEMENTATIVE

**"Single" in ExecuteUnixSingleCommand:**
- NON significa "singolo comando atomico"
- Significa "singola unità di esecuzione" che può essere:
  - Comando atomico: `ls -la`
  - Script completo: `if...; then...; fi`

**ScriptTranslator:**
- Nuovo componente di ExecuteUnixSingleCommand
- Parallelo a SimpleTranslator, EmulativeTranslator, PipelineTranslator
- Gestisce SOLO control structures (if/for/while/case)
- Contiene il cluster bash→PowerShell (6-8 metodi)

**PipelineStrategy aggiornato:**
- Deve detectare control structures
- Deve decidere: SCRIPT_CONVERSION vs BASH_REQUIRED
- Non implementa la conversione (delega a ExecuteUnixSingleCommand)

---

## CONCLUSIONE

**DECISIONE FINALE:**

❌ **SBAGLIATA (precedente):**
Tutto il cluster bash→PowerShell (8 metodi) → CommandExecutor

✅ **CORRETTA:**
Cluster bash→PowerShell (6-8 metodi) → **ExecuteUnixSingleCommand/ScriptTranslator**

**MOTIVO:**
È TRADUZIONE semantica specifica, non preprocessing sintattico generico.
