# CLAUDE'S REAL BASH USAGE PATTERNS

This document catalogs the ACTUAL bash commands that Claude uses in production during real work.

## PATTERN 1: CODEBASE EXPLORATION

### Find all files of a type
```bash
find . -name "*.py" -type f
find . -name "*.js" -type f ! -path "*/node_modules/*"
find . -type f -name "*.java" ! -path "*/target/*" ! -path "*/.git/*"
```

### Find files and search content
```bash
find . -name "*.py" -type f -exec grep -l "pattern" {} \;
find . -name "*.py" -exec grep -H "class.*Executor" {} \;
find . -type f -name "*.cpp" -exec grep -n "TODO" {} +
```

### Find with size/time filters
```bash
find . -type f -mtime -7  # Modified in last week
find . -type f -size +1M  # Larger than 1MB
find . -name "*.log" -mtime +30 -exec rm {} \;  # Cleanup old logs
```

## PATTERN 2: CODE ANALYSIS

### Count lines of code
```bash
wc -l *.py
find . -name "*.py" -type f -exec wc -l {} + | tail -1
find . -name "*.py" ! -path "*/venv/*" -exec wc -l {} + | sort -rn | head -20
```

### Find all class definitions
```bash
grep -r "^class " --include="*.py" .
find . -name "*.py" -exec grep -H "^class " {} \; | sort
grep -h "^class " *.py | sed 's/class \([A-Za-z_]*\).*/\1/' | sort
```

### Find all function definitions
```bash
grep -n "^def " file.py
grep -r "def.*execute" --include="*.py" .
awk '/^def / {print $2}' file.py
```

### Count occurrences of patterns
```bash
grep -c "import" file.py
grep -r "TODO" --include="*.py" . | wc -l
find . -name "*.py" -exec grep -h "^import " {} \; | sort | uniq -c | sort -rn
```

## PATTERN 3: FILE ANALYSIS

### Show specific line ranges
```bash
sed -n '100,200p' file.py
sed -n '/^class/,/^$/p' file.py
awk 'NR>=100 && NR<=200' file.py
```

### Extract and transform
```bash
grep "pattern" file.txt | sed 's/old/new/g'
cat file.py | grep -A 5 "class" | sed 's/^/  /'
awk -F: '{print $1, $3}' /etc/passwd | sort -k2 -n
```

### Complex pipelines
```bash
cat file.log | grep "ERROR" | awk '{print $1}' | sort | uniq -c | sort -rn
ls -la | grep "^-" | awk '{sum+=$5} END {print "Total bytes:", sum}'
ps aux | grep python | awk '{print $2, $11}' | sort
```

## PATTERN 4: GIT OPERATIONS

### Analyze commit history
```bash
git log --oneline | head -20
git log --oneline | awk '{print $1}' | head -10
git log --since="2 weeks ago" --pretty=format:"%h %s" | grep "fix"
```

### Compare versions
```bash
diff <(git show HEAD:file.py) <(cat file.py)
git diff HEAD~1 HEAD --stat
git log --oneline | head -5 | awk '{print $1}' | xargs -I {} git show {} --stat
```

### Find changes
```bash
git log --all --pretty=format: --name-only | sort | uniq
git diff --name-only HEAD~10 HEAD
git log --grep="pattern" --oneline
```

## PATTERN 5: DATA PROCESSING

### Sort and unique
```bash
sort file.txt | uniq
sort file.txt | uniq -c | sort -rn
cat *.log | grep "ERROR" | sort | uniq
```

### Field extraction
```bash
awk '{print $1}' file.txt
awk -F: '{print $1, $3}' /etc/passwd
cut -d: -f1,3 /etc/passwd
```

### Calculations
```bash
awk '{sum+=$1} END {print sum}' numbers.txt
awk '/pattern/ {count++} END {print count}' file.txt
awk '{if ($3 > 100) print $0}' data.csv
```

## PATTERN 6: FILE OPERATIONS

### Batch rename/move
```bash
find . -name "*.txt" -exec mv {} {}.bak \;
for f in *.jpg; do mv "$f" "${f%.jpg}.jpeg"; done
find . -name "*.tmp" -delete
```

### Archive operations
```bash
tar -czf backup.tar.gz dir/
tar -xzf archive.tar.gz
find . -name "*.log" -mtime +7 -exec tar -czf old_logs.tar.gz {} +
```

### File comparison
```bash
diff file1.txt file2.txt
diff -u old.txt new.txt
comm -12 <(sort file1.txt) <(sort file2.txt)
```

## PATTERN 7: TEXT PROCESSING

### Sed transformations
```bash
sed 's/old/new/g' file.txt
sed -i 's/pattern/replacement/g' *.txt
sed -n '/START/,/END/p' file.txt
sed -e 's/a/b/' -e 's/c/d/' file.txt
```

### Complex grep
```bash
grep -r "pattern" --include="*.py" .
grep -E "regex|pattern" file.txt
grep -v "exclude" file.txt | grep "include"
grep -C 5 "pattern" file.txt  # 5 lines context
```

### Awk programming
```bash
awk '/pattern/ {print $0}' file.txt
awk 'BEGIN {sum=0} {sum+=$1} END {print sum}' numbers.txt
awk -F, '{if (NR>1) print $2}' data.csv
```

## PATTERN 8: COMMAND SUBSTITUTION

### Nested substitution
```bash
echo "Files: $(find . -type f | wc -l)"
grep "pattern" $(find . -name "*.py")
cat $(find . -name "README.md" | head -1)
```

### In pipelines
```bash
cat $(ls *.txt | head -3) | wc -l
diff <(ls) <(git ls-files)
wc -l $(find . -name "*.py" -type f) | tail -1
```

## PATTERN 9: COMPLEX WORKFLOWS

### Code refactoring analysis
```bash
# Find all imports
find . -name "*.py" -exec grep -h "^import \|^from " {} \; | sort | uniq -c | sort -rn

# Find duplicate code
find . -name "*.py" -exec md5sum {} \; | sort | uniq -w32 -D

# Analyze function complexity
grep -r "^def " --include="*.py" . | wc -l

# Find long files
find . -name "*.py" -exec wc -l {} + | sort -rn | head -20
```

### Dependency analysis
```bash
# Find all imports
grep -rh "^import \|^from " --include="*.py" . | sed 's/import //' | sed 's/from //' | awk '{print $1}' | sort | uniq

# Count import frequency
find . -name "*.py" -exec grep -oh "import \w\+" {} \; | sort | uniq -c | sort -rn
```

### Test coverage analysis
```bash
# Find test files
find . -name "test_*.py" -o -name "*_test.py"

# Count test functions
find . -name "test_*.py" -exec grep -c "^def test_" {} + | awk -F: '{sum+=$2} END {print sum}'

# Find untested modules
comm -23 <(find . -name "*.py" ! -name "test_*" | sort) <(find . -name "test_*.py" | sed 's/test_//' | sort)
```

## PATTERN 10: DEBUGGING & ANALYSIS

### Log analysis
```bash
# Find errors
grep -i "error\|exception" logfile.log | wc -l

# Timeline of errors
grep "ERROR" logfile.log | awk '{print $1, $2}' | sort | uniq -c

# Top error messages
grep "ERROR" *.log | sed 's/.*ERROR: //' | sort | uniq -c | sort -rn | head -10
```

### Performance analysis
```bash
# Find large files
find . -type f -size +10M -exec ls -lh {} \;

# Disk usage by directory
du -sh */ | sort -rh | head -10

# File count by type
find . -type f | sed 's/.*\.//' | sort | uniq -c | sort -rn
```

## CRITICAL INSIGHT

**Every single one of these patterns:**
1. Is used regularly by Claude during actual work
2. Involves multiple commands/features
3. Has complex parsing requirements
4. Will fail if ANY part of the emulation is wrong
5. Is MISSION CRITICAL for Claude's ability to work

**If these don't work → Claude is paralyzed on Windows.**

This is not theoretical. This is the ACTUAL usage pattern.
