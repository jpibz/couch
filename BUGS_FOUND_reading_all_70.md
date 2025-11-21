# BUGS FOUND - Reading All 70 Scripts

Date: 2025-11-21
Method: Read COMPLETE generated scripts for all 70 commands (bash=False)

---

## CRITICAL BUGS (Syntax Errors - BROKEN)

### 1. AWK - Invalid PowerShell Syntax

**Input**: `echo "a b c" | awk '{print $2}'`

**Generated**:
```powershell
Get-Content "$2}" | ForEach-Object {
    $F = $_ -split "\s+"
    $NF = $F.Length
}
```

**PROBLEMS**:
- `"$2}"` is INVALID PowerShell! Random `}` in string
- `$2` variable doesn't exist (should be $F[1] for field 2)
- Should use `$input`, not `Get-Content`
- No output! Missing `Write-Output $F[1]`

**SEVERITY**: CRITICAL - Syntax error, won't run

---

### 2. CUT - Invalid Get-Content Usage

**Input**: `echo "a:b:c" | cut -d: -f2`

**Generated**:
```powershell
Get-Content $input | ForEach-Object {
    $F = $_ -split ":"
    ($F[1]) -join ":"
}
```

**PROBLEMS**:
- `Get-Content $input` is WRONG! $input is pipeline variable, not file path
- Will fail with "cannot find path"

**FIX**: Remove `Get-Content`, use `$input | ForEach-Object` directly

**SEVERITY**: CRITICAL - Will fail at runtime

---

### 3. GREP - Wrong Pattern Matching with stdin

**Input**: `echo -e "foo\nbar\nbaz" | grep ba`

**Generated**:
```powershell
Select-String -Pattern "ba" -Path *
```

**PROBLEMS**:
- `-Path *` tries to search files, not stdin!
- Should use `$input | Select-String -Pattern "ba"`

**SEVERITY**: CRITICAL - Wrong behavior (searches files instead of stdin)

---

## HIGH PRIORITY BUGS

### 4. TR - Only Replaces 3 Characters

**Input**: `echo hello | tr a-z A-Z`

**Generated**:
```powershell
$line = $line -replace "a", "A"
$line = $line -replace "-", "-"
$line = $line -replace "z", "Z"
```

**PROBLEMS**:
- Only replaces 'a', '-', and 'z'!
- Needs to replace ALL characters a-z → A-Z (26 characters)
- Should loop through alphabet

**SEVERITY**: HIGH - Produces wrong output

---

### 5. SLEEP - Fails to Parse Decimal Seconds

**Input**: `sleep 0.1`

**Generated**:
```
echo Error: sleep requires seconds
```

**PROBLEM**: Parser doesn't accept "0.1" as valid seconds
- Should accept decimal values
- Should use `Start-Sleep -Seconds 0.1`

**SEVERITY**: HIGH - Feature doesn't work

---

### 6. KILL - Doesn't Support -l Flag

**Input**: `kill -l`

**Generated**:
```
echo Error: kill requires PID
```

**PROBLEM**: `-l` flag (list signals) not recognized
- Should list signal names/numbers
- Common Unix feature

**SEVERITY**: MEDIUM - Missing feature

---

### 7. WGET/CURL - No --help Support

**Input**: `wget --help` / `curl --help`

**Generated**:
```
echo Error: wget requires URL
echo Error: curl requires URL
```

**PROBLEM**: `--help` flag not recognized
- Should show help text
- Common pattern

**SEVERITY**: MEDIUM - Missing feature

---

### 8. HEAD/TAIL - Echo -e Not Processed

**Input**: `echo -e "a\nb\nc\nd\ne" | head -n 3`

**Generated (echo part)**:
```powershell
Write-Host \"anbncndne\"
```

**PROBLEM**: `\n` becomes literal "n" instead of newline
- Echo translation doesn't process -e flag correctly
- Affects all head/tail tests with echo -e

**SEVERITY**: HIGH - Wrong output format

---

### 9. SORT - Uses Windows Native sort.exe

**Input**: `echo -e "c\na\nb" | sort`

**Generated**:
```
sort
```

**PROBLEM**: Calls Windows native `sort` command
- Different behavior than Unix sort
- Should use PowerShell `Sort-Object`

**SEVERITY**: MEDIUM - Inconsistent behavior

---

### 10. JQ - Extra Whitespace in Command

**Input**: `echo '{"a":"b"}' | jq .a`

**Generated**:
```powershell
$input | & jq.exe   '.a'  # Double space before '.a'
```

**PROBLEM**: Extra spaces in generated command
- Minor formatting issue
- Doesn't break functionality but looks wrong

**SEVERITY**: LOW - Cosmetic

---

## SUMMARY

**CRITICAL (Won't Run)**: 3
- awk, cut, grep

**HIGH (Wrong Output)**: 4
- tr, sleep, head/tail echo, sort

**MEDIUM (Missing Features)**: 2
- kill -l, wget/curl --help

**LOW (Cosmetic)**: 1
- jq spacing

**Total Bugs Found**: 10

---

## NEXT STEPS

Fix in order:
1. Fix CRITICAL bugs first (awk, cut, grep)
2. Fix HIGH priority (tr, sleep, echo -e, sort)
3. Fix MEDIUM (kill, wget/curl)
4. Fix LOW (jq spacing)
