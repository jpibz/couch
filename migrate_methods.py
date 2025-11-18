#!/usr/bin/env python3
"""
Script per spostare metodi da BashToolExecutor a CommandExecutor e ExecuteUnixSingleCommand
"""

def read_file_lines(filepath):
    """Legge file e ritorna lista di linee"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.readlines()

def write_file_lines(filepath, lines):
    """Scrive lista di linee su file"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def extract_method(lines, start_line, end_line):
    """Estrae metodo dalle linee (1-indexed)"""
    # Convert to 0-indexed
    return lines[start_line-1:end_line]

def insert_lines_at(lines, insert_at, new_lines):
    """Inserisce nuove linee alla posizione specificata (1-indexed)"""
    # Convert to 0-indexed
    return lines[:insert_at-1] + new_lines + lines[insert_at-1:]

def remove_lines_range(lines, start_line, end_line):
    """Rimuove linee nel range specificato (1-indexed)"""
    # Convert to 0-indexed
    return lines[:start_line-1] + lines[end_line:]

# Definizione metodi da spostare verso CommandExecutor
PREPROCESSING_METHODS = [
    # (nome, start_line, end_line)
    ('_expand_braces', 6410, 6481),
    ('_process_heredocs', 6480, 6658),
    ('_process_substitution', 6659, 6762),
    ('_process_command_substitution_recursive', 6763, 6862),
    ('_expand_variables', 6962, 7204),
    ('_translate_substitution_content', 6863, 6961),
    ('_preprocess_test_commands', 7205, 7234),
    ('_expand_aliases', 7235, 7263),
    ('_process_subshell', 7264, 7291),
    ('_process_command_grouping', 7292, 7313),
    ('_process_xargs', 7314, 7340),
    ('_process_find_exec', 7341, 7367),
    ('_process_escape_sequences', 7368, 7381),
    ('_cleanup_temp_files', 7564, 7573),
]

# Definizione metodi da spostare verso ExecuteUnixSingleCommand
CONTROL_STRUCTURE_METHODS = [
    # (nome, start_line, end_line)
    ('_has_control_structures', 7382, 7386),
    ('_convert_control_structures_to_script', 7387, 7418),
    ('_bash_to_powershell', 7419, 7523),
    ('_convert_test_to_powershell', 7524, 7563),
    ('_needs_powershell', 7574, 7626),
    ('_adapt_for_powershell', 7627, 7661),
]

def main():
    print("🔄 Inizio migrazione metodi...")

    # Backup del file originale
    import shutil
    shutil.copy('/home/user/couch/bash_tool_executor.py',
                '/home/user/couch/bash_tool_executor.py.backup_migration')
    print("✅ Backup creato: bash_tool_executor.py.backup_migration")

    # Leggi file
    lines = read_file_lines('/home/user/couch/bash_tool_executor.py')
    print(f"📄 File letto: {len(lines)} righe")

    # FASE 1: Estrai tutti i metodi
    print("\n📦 FASE 1: Estrazione metodi...")

    preprocessing_methods_code = []
    for name, start, end in sorted(PREPROCESSING_METHODS, key=lambda x: x[1]):
        method_lines = extract_method(lines, start, end)
        preprocessing_methods_code.extend(method_lines)
        print(f"  ✅ Estratto {name}: {len(method_lines)} righe")

    control_methods_code = []
    for name, start, end in sorted(CONTROL_STRUCTURE_METHODS, key=lambda x: x[1]):
        method_lines = extract_method(lines, start, end)
        control_methods_code.extend(method_lines)
        print(f"  ✅ Estratto {name}: {len(method_lines)} righe")

    # FASE 2: Trova punti di inserimento
    print("\n🔍 FASE 2: Ricerca punti di inserimento...")

    # Trova fine di CommandExecutor.__init__
    command_executor_start = None
    for i, line in enumerate(lines):
        if 'class CommandExecutor:' in line:
            command_executor_start = i + 1
            print(f"  ✅ CommandExecutor trovato alla linea {i+1}")
            break

    # Trova un buon punto di inserimento in CommandExecutor (cerca il primo metodo def dopo __init__)
    command_executor_insert = None
    if command_executor_start:
        for i in range(command_executor_start, min(command_executor_start + 200, len(lines))):
            if lines[i].strip().startswith('def ') and '__init__' not in lines[i]:
                command_executor_insert = i
                print(f"  ✅ Punto di inserimento CommandExecutor: linea {i+1}")
                break

    # Trova ExecuteUnixSingleCommand
    exec_unix_start = None
    for i, line in enumerate(lines):
        if 'class ExecuteUnixSingleCommand:' in line:
            exec_unix_start = i + 1
            print(f"  ✅ ExecuteUnixSingleCommand trovato alla linea {i+1}")
            break

    # Trova punto inserimento in ExecuteUnixSingleCommand (dopo __init__)
    exec_unix_insert = None
    if exec_unix_start:
        for i in range(exec_unix_start, min(exec_unix_start + 200, len(lines))):
            if lines[i].strip().startswith('def ') and '__init__' not in lines[i]:
                exec_unix_insert = i
                print(f"  ✅ Punto di inserimento ExecuteUnixSingleCommand: linea {i+1}")
                break

    if not command_executor_insert or not exec_unix_insert:
        print("❌ ERRORE: Non trovati punti di inserimento!")
        return 1

    # FASE 3: Inserisci metodi nelle destinazioni
    print("\n📝 FASE 3: Inserimento metodi...")

    # Aggiungi commento separatore
    separator_ce = ["\n", "    # ==================== PREPROCESSING METHODS ====================\n", "\n"]
    separator_eu = ["\n", "    # ==================== CONTROL STRUCTURE METHODS ====================\n", "\n"]

    # Inserisci in ExecuteUnixSingleCommand per primo (linea più bassa)
    lines = insert_lines_at(lines, exec_unix_insert, separator_eu + control_methods_code)
    print(f"  ✅ Inseriti {len(control_methods_code)} righe in ExecuteUnixSingleCommand")

    # Aggiusta offset per inserimento precedente
    offset = len(separator_eu + control_methods_code)

    # Inserisci in CommandExecutor
    lines = insert_lines_at(lines, command_executor_insert + offset, separator_ce + preprocessing_methods_code)
    print(f"  ✅ Inseriti {len(preprocessing_methods_code)} righe in CommandExecutor")

    # FASE 4: Rimuovi metodi da BashToolExecutor
    print("\n🗑️  FASE 4: Rimozione metodi da BashToolExecutor...")

    # Calcola nuovo offset dopo inserimenti
    total_offset = len(separator_ce + preprocessing_methods_code) + len(separator_eu + control_methods_code)

    # Ordina per rimuovere dall'alto verso il basso (così gli offset non cambiano)
    all_methods = sorted(PREPROCESSING_METHODS + CONTROL_STRUCTURE_METHODS,
                        key=lambda x: x[1], reverse=True)

    removed_lines = 0
    for name, start, end in all_methods:
        # Aggiusta con offset
        adjusted_start = start + total_offset
        adjusted_end = end + total_offset

        before_len = len(lines)
        lines = remove_lines_range(lines, adjusted_start, adjusted_end)
        after_len = len(lines)

        lines_removed = before_len - after_len
        removed_lines += lines_removed
        print(f"  ✅ Rimosso {name}: {lines_removed} righe")

    print(f"\n📊 Totale righe rimosse da BashToolExecutor: {removed_lines}")

    # FASE 5: Scrivi file modificato
    print("\n💾 FASE 5: Scrittura file...")
    write_file_lines('/home/user/couch/bash_tool_executor.py', lines)
    print(f"✅ File scritto: {len(lines)} righe totali")

    # FASE 6: Verifica sintassi
    print("\n🔍 FASE 6: Verifica sintassi Python...")
    import subprocess
    result = subprocess.run(['python', '-m', 'py_compile', '/home/user/couch/bash_tool_executor.py'],
                          capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ Sintassi Python: OK")
    else:
        print(f"❌ Errore sintassi:\n{result.stderr}")
        # Salva versione con errore per debug
        shutil.copy('/home/user/couch/bash_tool_executor.py',
                   '/home/user/couch/bash_tool_executor.py.failed')
        print("💾 Salvato file con errore: bash_tool_executor.py.failed")
        # Ripristina backup
        shutil.copy('/home/user/couch/bash_tool_executor.py.backup_migration',
                   '/home/user/couch/bash_tool_executor.py')
        print("⚠️  Ripristinato backup")
        return 1

    print("\n🎉 MIGRAZIONE COMPLETATA CON SUCCESSO!")
    return 0

if __name__ == '__main__':
    exit(main())
