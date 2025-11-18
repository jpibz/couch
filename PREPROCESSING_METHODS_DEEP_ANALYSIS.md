# ANALISI APPROFONDITA 42 METODI PREPROCESSING/EXPANSION/CONTROL

## Obiettivo
Capire dove vanno REALMENTE i 42 metodi nell'architettura finale ESISTENTE, senza creare nuove classi.

## Due Livelli di Analisi/Esecuzione

### LIVELLO 1: PIPELINE (CommandExecutor + PipelineStrategy)
- Analizza INTERA pipeline
- Decide strategia globale (BASH_REQUIRED, HYBRID, NATIVE)
- Opera sulla pipeline completa PRIMA di suddividerla

### LIVELLO 2: COMANDO ATOMICO (ExecuteUnixSingleCommand)
- Esegue SINGOLO comando atomico
- Decide come tradurre/eseguire (Simple, Native, Bash, Emulative)
- Opera su comandi già isolati

---

## CATEGORIA 1: PREPROCESSING (14 metodi)

### Analisi Metodo per Metodo

| # | Metodo | Cosa Fa | Livello | Fase | Destinazione |
|---|--------|---------|---------|------|--------------|
| 1 | `_process_heredocs` | Processa heredocs `<<EOF` | ??? | ??? | ??? |
| 2 | `_process_substitution` | Process substitution `<()` `>()` | ??? | ??? | ??? |
| 3 | `_process_command_substitution_recursive` | Command substitution `$(cmd)` | ??? | ??? | ??? |
| 4 | `_translate_substitution_content` | Traduce contenuto substitution | ??? | ??? | ??? |
| 5 | `_process_subshell` | Processa subshell `(cmd)` | ??? | ??? | ??? |
| 6 | `_process_command_grouping` | Processa grouping `{cmd1; cmd2}` | ??? | ??? | ??? |
| 7 | `_process_xargs` | Processa xargs | ??? | ??? | ??? |
| 8 | `_process_find_exec` | Processa find -exec | ??? | ??? | ??? |
| 9 | `_process_escape_sequences` | Processa escape sequences | ??? | ??? | ??? |
| 10 | `_preprocess_test_commands` | Preprocessa test commands | ??? | ??? | ??? |
| 11 | `_cleanup_temp_files` | Cleanup temp files | ??? | ??? | ??? |
| 12 | `_needs_powershell` | Decide se serve PowerShell | ??? | ??? | ??? |
| 13 | `_adapt_for_powershell` | Adatta per PowerShell | ??? | ??? | ??? |
| 14 | `_bash_to_powershell` | Converte bash → PowerShell | ??? | ??? | ??? |

### Domande da Rispondere

**_process_heredocs**:
- Opera su pipeline completa o comando singolo?
- È preprocessing generico o parte di traduzione?
- QUANDO viene chiamato nel flusso?

**_process_command_substitution_recursive**:
- `echo $(date) | grep 2025`
- Deve eseguire $(date) PRIMA di analizzare la pipeline?
- Oppure è parte dell'esecuzione del comando echo?

**_needs_powershell**:
- Decisione strategica (PipelineStrategy)?
- O decisione tattica (ExecuteUnixSingleCommand)?

**_bash_to_powershell**:
- Traduzione generica?
- O parte di EmulativeTranslator?

---

## CATEGORIA 2: VARIABLE EXPANSION (20 metodi)

### Analisi Metodo per Metodo

| # | Metodo | Pattern | Livello | Fase | Destinazione |
|---|--------|---------|---------|------|--------------|
| 1 | `_expand_variables` | Main expansion orchestrator | ??? | ??? | ??? |
| 2 | `_expand_aliases` | Alias expansion | ??? | ??? | ??? |
| 3 | `_expand_braces` | Brace expansion orchestrator | ??? | ??? | ??? |
| 4 | `expand_simple_var` | `$var` `${var}` | ??? | ??? | ??? |
| 5 | `expand_default` | `${var:-default}` | ??? | ??? | ??? |
| 6 | `expand_assign` | `${var:=value}` | ??? | ??? | ??? |
| 7 | `expand_length` | `${#var}` | ??? | ??? | ??? |
| 8 | `expand_remove_prefix` | `${var#pattern}` | ??? | ??? | ??? |
| 9 | `expand_remove_suffix` | `${var%pattern}` | ??? | ??? | ??? |
| 10 | `expand_case` | `${var^^}` `${var,,}` | ??? | ??? | ??? |
| 11 | `expand_substitution` | `$(cmd)` expansion | ??? | ??? | ??? |
| 12 | `expand_arithmetic` | `$((expr))` | ??? | ??? | ??? |
| 13 | `expand_simple_brace` | `{a,b,c}` | ??? | ??? | ??? |
| 14 | `expand_single_brace` | `{1..10}` | ??? | ??? | ??? |
| 15 | `expand_grouping` | Group expansion | ??? | ??? | ??? |
| 16 | `find_substitutions` | Find `$()` and `` `cmd` `` | ??? | ??? | ??? |
| 17 | `is_complex_substitution` | Detect complex subst | ??? | ??? | ??? |
| 18 | `remove_subshell` | Remove subshell syntax | ??? | ??? | ??? |
| 19 | `replace_input_substitution` | Replace `<()` | ??? | ??? | ??? |
| 20 | `replace_output_substitution` | Replace `>()` | ??? | ??? | ??? |

### Domande da Rispondere

**_expand_variables**:
- `find . -name "*.${ext}" | grep pattern`
- Espandere ${ext} PRIMA di analizzare pipeline?
- O durante esecuzione del comando find?

**expand_arithmetic**:
- `echo $((1+2))`
- Calcolare PRIMA di analizzare?
- O parte della traduzione del comando echo?

**Brace expansion** (`{a,b,c}`, `{1..10}`):
- `echo {1..10}` → deve diventare `echo 1 2 3 4 5 6 7 8 9 10`
- Espandere PRIMA di analizzare?
- O durante traduzione?

---

## CATEGORIA 3: CONTROL STRUCTURES (8 metodi)

### Analisi Metodo per Metodo

| # | Metodo | Cosa Fa | Livello | Fase | Destinazione |
|---|--------|---------|---------|------|--------------|
| 1 | `_has_control_structures` | Detecta if/for/while | ??? | ??? | ??? |
| 2 | `_convert_control_structures_to_script` | Converte a script | ??? | ??? | ??? |
| 3 | `_convert_test_to_powershell` | `[ test ]` → PowerShell | ??? | ??? | ??? |
| 4 | `convert_if` | `if; then; fi` → PowerShell | ??? | ??? | ??? |
| 5 | `convert_for` | `for; do; done` → PowerShell | ??? | ??? | ??? |
| 6 | `convert_while` | `while; do; done` → PowerShell | ??? | ??? | ??? |
| 7 | `convert_test` | `[ -f file ]` → PowerShell | ??? | ??? | ??? |
| 8 | `convert_double_test` | `[[ expr ]]` → PowerShell | ??? | ??? | ??? |

### Domande da Rispondere

**_has_control_structures**:
- Decisione strategica (PipelineStrategy)?
- Se ho `if [ -f file ]; then cat file | grep pattern; fi`
- PipelineStrategy deve sapere che c'è control structure?

**convert_if/for/while**:
- Conversione generica?
- O parte di EmulativeTranslator?
- O parte di PipelineStrategy quando detecta control structures?

---

## PROSSIMO PASSO

Per OGNI metodo devo rispondere:

1. **QUANDO viene chiamato?**
   - Prima dell'analisi pipeline?
   - Durante l'analisi pipeline?
   - Durante l'esecuzione del comando?

2. **SU COSA opera?**
   - Comando RAW (prima di tutto)?
   - Pipeline completa (dopo parsing)?
   - Comando atomico isolato?

3. **QUAL È il suo scopo?**
   - Preprocessing generico?
   - Analisi/decisione strategica?
   - Traduzione/esecuzione?

4. **Quindi DOVE va?**
   - CommandExecutor (preprocessing generico)?
   - PipelineStrategy (analisi/decisione pipeline)?
   - ExecuteUnixSingleCommand (traduzione comando atomico)?
   - Translators (Simple/Emulative/Pipeline)?

**NESSUNA nuova classe. Solo distribuzione tra classi ESISTENTI.**
