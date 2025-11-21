# BUG REPORT - Found by Reading Generated Scripts

## Testing Method
Forced emulation (bash=False) and READ complete PowerShell/CMD scripts generated.

## BUGS FOUND

### 1. AWK - Syntax Error in PowerShell Script

**Command**: `echo "a b c" | awk '{print $2}'`

**Generated Script**:
```powershell
Get-Content "$2}" | ForEach-Object {
    $F = $_ -split "\s+"
    $NF = $F.Length
}
```

**PROBLEM**: `"$2}"` is invalid PowerShell syntax!
- `$2` is not defined (should be $F[1] for field 2)
- Extra `}` in string
- Should use `$input` for stdin, not Get-Content

**CORRECT SCRIPT SHOULD BE**:
```powershell
$input | ForEach-Object {
    $F = $_ -split "\s+"
    Write-Output $F[1]  # Print field 2
}
```

**File**: src/bash_tool/command_emulator.py
**Method**: `_translate_awk`

---

### 2. CUT - Invalid Use of Get-Content with $input

**Command**: `echo "a:b:c" | cut -d: -f2`

**Generated Script**:
```powershell
Get-Content $input | ForEach-Object {
    $F = $_ -split ":"
    ($F[1]) -join ":"
}
```

**PROBLEM**: `Get-Content $input` is WRONG!
- `$input` is already a pipeline variable
- Get-Content expects file path, not pipeline data
- Creates error: Get-Content cannot find path

**CORRECT SCRIPT SHOULD BE**:
```powershell
$input | ForEach-Object {
    $F = $_ -split ":"
    $F[1]  # Return field 2
}
```

**File**: src/bash_tool/command_emulator.py
**Method**: `_translate_cut`

---

### 3. SORT - Using Native Windows sort.exe

**Command**: `echo -e "c\na\nb" | sort`

**Generated Script**:
```
sort
```

**PROBLEM**: Just calls native `sort` command
- Windows sort.exe has different behavior than Unix sort
- No PowerShell emulation script
- May fail or produce unexpected results

**SHOULD USE**: PowerShell Sort-Object for consistent Unix-like behavior

**File**: src/bash_tool/command_emulator.py
**Method**: `_translate_sort`

---

## Impact

- **awk**: Will fail with syntax error
- **cut**: Will fail with "cannot find path" error
- **sort**: May work but with different behavior than Unix

## Severity

- **HIGH**: awk and cut are BROKEN (syntax errors)
- **MEDIUM**: sort works but inconsistent behavior

## Next Steps

1. Fix awk to use `$input | ForEach-Object` and correct field access
2. Fix cut to remove `Get-Content` and use `$input` directly
3. Consider using `Sort-Object` for sort instead of native command

---

**Found by**: Reading complete generated scripts (not just checking markers!)
**Date**: 2025-11-21
**Test**: test_script_verification.py with bash=False
