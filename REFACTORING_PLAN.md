# PRIMA ITERAZIONE - REFACTORING ARCHITETTURALE

## OBIETTIVO
Decomposizione pragmatica per separare responsabilità e concentrare subprocess.

---

## PUNTO 1: Spostare metodi BashToolExecutor → CommandExecutor

### Metodi da SPOSTARE (25 metodi):

**Preprocessing:**
- `_expand_braces`
- `_expand_variables` (227 righe - IL PIÙ GRANDE)
- `_process_heredocs`
- `_process_substitution`
- `_process_command_substitution_recursive`
- `_translate_substitution_content`
- `_preprocess_test_commands`
- `_expand_aliases`
- `_process_subshell`
- `_process_command_grouping`
- `_process_xargs`
- `_process_find_exec`
- `_process_escape_sequences`
- `_process_variable_assignments`

**Conversion:**
- `_has_control_structures`
- `_convert_control_structures_to_script`
- `_bash_to_powershell`
- `_convert_test_to_powershell`
- `_needs_powershell`
- `_adapt_for_powershell`

**Setup/Detection:**
- `_detect_git_bash`
- `_detect_system_python`
- `_setup_virtual_env`
- `_setup_environment`

**Cleanup:**
- `_cleanup_temp_files`

### Metodi che RIMANGONO in BashToolExecutor (3-4 metodi):

- `__init__()` - instanzia PathTranslator + CommandExecutor
- `execute()` - path translation + delegation
- `get_definition()` - tool definition
- `_format_result()` - formatting output (FORSE)

---

## PUNTO 2: Creare ExecutionEngine

```python
class ExecutionEngine:
    """
    UNICO punto di esecuzione subprocess.
    Permette test_mode, logging, metrics.
    """
    
    def __init__(self, test_mode=False):
        self.test_mode = test_mode
        self.stats = {'cmd': 0, 'powershell': 0, 'bash': 0, 'native': 0}
    
    def execute_cmd(self, command, **kwargs)
    def execute_powershell(self, command, **kwargs)
    def execute_bash(self, bash_path, command, **kwargs)
    def execute_native(self, bin_path, args, **kwargs)
```

---

## PUNTO 3: Semplificare BashToolExecutor

**PRIMA (28 metodi, subprocess ovunque):**
```python
class BashToolExecutor:
    def execute(self, params):
        # 200 righe di preprocessing
        # subprocess calls diretti
        # conversion logic
        # execution logic
        ...
```

**DOPO (3-4 metodi, ZERO subprocess):**
```python
class BashToolExecutor(ToolExecutor):
    def __init__(self, working_dir):
        self.path_translator = PathTranslator()
        self.command_executor = CommandExecutor(test_mode=self.TESTMODE)
    
    def execute(self, params):
        command = params['command']
        
        # 1. Path translation IN
        translated_paths = self.path_translator.translate_paths_in_string(
            command, direction='to_windows'
        )
        
        # 2. Delegation a CommandExecutor
        result = self.command_executor.execute_bash(translated_paths)
        
        # 3. Path translation OUT
        final_result = self.path_translator.translate_paths_in_string(
            result, direction='to_unix'
        )
        
        return self._format_result(final_result)
    
    def get_definition(self):
        # ... definizione tool
```

---

## PUNTO 4: Scomporre CommandTranslator in 3 classi

### SimpleTranslator (25 metodi - traduzioni 1:1):
- pwd, cd, mkdir, rm, mv, touch, cp
- whoami, hostname, date, sleep
- true, false, yes
- sha256sum, sha1sum, md5sum
- basename, dirname
- chmod, chown, du, df
- kill, env, printenv, export
- which

### PipelineTranslator (35 metodi - pipeline/redirect):
- ls, cat, echo
- grep, head, tail, wc
- sort, uniq, cut, tr
- diff, tee, seq
- file, stat, readlink, realpath
- hexdump, column, base64
- timeout, split
- gzip, gunzip, tar, zip, unzip
- wget, curl

### EmulativeTranslator (15 metodi - simulazioni complesse):
- find
- awk + helpers (_awk_to_ps_statement, _awk_to_ps_condition)
- sed
- test
- ln
- strings
- watch
- paste, comm, join
- jq + helpers (_is_simple_jq_pattern, _jq_to_powershell)

### CommandTranslator BASE (4 metodi - core logic):
- `__init__()` - instanzia i 3 translator
- `translate()` - dispatcher
- `_parse_command_structure()` - parsing
- `_translate_single_command()` - decide quale translator usare

---

## STRATEGIA IMPLEMENTAZIONE

1. Creo ExecutionEngine
2. Creo le 3 nuove classi translator (vuote)
3. Sposto metodi uno alla volta da CommandTranslator
4. Aggiorno CommandTranslator per usare le 3 classi
5. Sposto metodi da BashToolExecutor a CommandExecutor
6. Aggiorno CommandExecutor per usare ExecutionEngine
7. Semplifico BashToolExecutor
8. Testo che tutto funzioni

---

## TESTING

Dopo ogni modifica:
```bash
python test_output_validation.py
```

Se passa → continuo
Se fallisce → fix e riprovo

---

## COMMIT STRATEGY

Commit atomici per ogni step:
1. "Add ExecutionEngine for subprocess concentration"
2. "Create 3 translator classes (Simple/Pipeline/Emulative)"
3. "Move methods from CommandTranslator to specialized translators"
4. "Move preprocessing/conversion methods to CommandExecutor"
5. "Simplify BashToolExecutor to minimal tool interface"
6. "Update tests and verify functionality"

