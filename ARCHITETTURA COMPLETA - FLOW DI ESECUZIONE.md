┌─────────────────────────────────────────────────────────────┐
│ INPUT: Bash command string (Windows paths!)                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: BashCommandPreprocessor.preprocess_always()         │
│ [CATEGORIA 1 - SAFE, ALWAYS]                                │
│ - Aliases (ll → ls -la)                                      │
│ - Tilde (~/dir → C:\Users\...\dir)                          │
│ - Arithmetic ($((5+3)) → 8)                                  │
│ - Variables ($VAR, ${VAR}, ${VAR:-default}, etc)            │
│ - Braces ({1..3}, {a,b}{1,2} → cartesian product)          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: BashPipelineParser.parse_bash_command()             │
│ String → Tokens → AST                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: BashPipelinePreprocessor.preprocess()               │
│ [PIPELINE LEVEL]                                             │
│ - Command substitution $(cmd)                                │
│ - Process substitution <(cmd), >(cmd)                        │
│ - Heredocs <<EOF                                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Re-parse → Fresh AST                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: PipelineAnalyzer.analyze() → STRATEGIA!             │
│ [BLACKLIST APPROACH - "CAZZIMMA NAPOLETANA"]                │
│ - Check command availability (builtin/native/.exe)          │
│ - bash_full: ALL commands available → PASSTHROUGH!          │
│ - manual: SOME commands need emulation                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    ┌───────┴───────┐
                    ↓               ↓
        ┌─────────────────┐  ┌─────────────────┐
        │ bash_full        │  │ manual          │
        │ execute_bash()   │  │ walk_ast()      │
        │ ZERO OVERHEAD!   │  │ Recursive exec  │
        └─────────────────┘  └─────────────────┘
                                      ↓
                          ┌───────────────────────┐
                          │ SimpleCommand         │
                          │ _analyze_single_      │
                          │ strategy()            │
                          └───────────────────────┘
                                      ↓
                    ┌─────────┬───────┴────────┐
                    ↓         ↓                ↓
            ┌──────────┐ ┌────────┐ ┌──────────────────┐
            │ BASH     │ │ NATIVE │ │ EMULATED         │
            │ Direct   │ │ Direct │ │ + CATEGORIA 2!   │
            │ bash.exe │ │ .exe   │ │ (test translation)│
            └──────────┘ └────────┘ └──────────────────┘