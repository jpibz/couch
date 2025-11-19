#!/usr/bin/env python3
"""Migra metodi - versione 2 con ricerca dinamica"""

# Leggi file
with open('bash_tool_executor.py.backup_migration', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"File letto: {len(lines)} righe")

# STEP 1: Estrai i 14 metodi preprocessing
preprocessing_lines = []
preprocessing_lines.extend(lines[6409:7381])
preprocessing_lines.extend(lines[7563:7573])
print(f"Estratti {len(preprocessing_lines)} righe preprocessing")

# STEP 2: Estrai i 6 metodi control structure
control_lines = lines[7381:7661]
print(f"Estratti {len(control_lines)} righe control structure")

# STEP 3: Inserisci preprocessing in CommandExecutor
# Trova "class BashToolExecutor" e inserisci PRIMA
separator_ce = "\n    # ==================== PREPROCESSING METHODS (migrated) ====================\n\n"
bash_tool_line = None
for i, line in enumerate(lines):
    if line.startswith('class BashToolExecutor'):
        bash_tool_line = i
        break

if bash_tool_line is None:
    print("❌ Non trovato BashToolExecutor!")
    exit(1)

# Trova l'ultima riga non vuota prima di BashToolExecutor
insert_ce = bash_tool_line
while insert_ce > 0 and lines[insert_ce-1].strip() == '':
    insert_ce -= 1

print(f"Inserimento preprocessing alla riga {insert_ce}")

new_lines = lines[:insert_ce]
new_lines.append(separator_ce)
new_lines.extend(preprocessing_lines)
new_lines.extend(lines[insert_ce:])
lines = new_lines

# STEP 4: Inserisci control structure in ExecuteUnixSingleCommand
# Trova "class CommandExecutor" e inserisci PRIMA
separator_eu = "\n    # ==================== CONTROL STRUCTURE METHODS (migrated) ====================\n\n"
cmd_exec_line = None
for i, line in enumerate(lines):
    if line.startswith('class CommandExecutor:'):
        cmd_exec_line = i
        break

if cmd_exec_line is None:
    print("❌ Non trovato CommandExecutor!")
    exit(1)

# Trova l'ultima riga non vuota prima di CommandExecutor
insert_eu = cmd_exec_line
while insert_eu > 0 and lines[insert_eu-1].strip() == '':
    insert_eu -= 1

print(f"Inserimento control structures alla riga {insert_eu}")

new_lines = lines[:insert_eu]
new_lines.append(separator_eu)
new_lines.extend(control_lines)
new_lines.extend(lines[insert_eu:])
lines = new_lines

# STEP 5: Rimuovi metodi da BashToolExecutor
# Ora li troviamo dinamicamente cercando le righe di inizio/fine
# I metodi erano 6410-7661 nel file originale
# Ma nel nuovo file sono shiftati

# Trova la nuova posizione di BashToolExecutor
bash_tool_new = None
for i, line in enumerate(lines):
    if line.startswith('class BashToolExecutor'):
        bash_tool_new = i
        break

# Calcola offset: dovrebbe essere bash_tool_new vs bash_tool_line (6181 nel file originale)
offset = bash_tool_new - 6180  # 6181 - 1 (0-indexed)
print(f"Offset: {offset} righe")

# Rimuovi 6410-7661 con offset
remove_start = 6409 + offset
remove_end = 7661 + offset

lines = lines[:remove_start] + lines[remove_end:]

print(f"Rimossi metodi da BashToolExecutor (righe {remove_start+1}-{remove_end})")

# Scrivi file
with open('bash_tool_executor.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"✅ File scritto: {len(lines)} righe totali")
print("🎉 MIGRAZIONE COMPLETATA!")
