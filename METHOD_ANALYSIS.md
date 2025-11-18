# METODI DELLE 3 CLASSI PRINCIPALI

**TOTALE METODI:** 125

- **PathTranslator**: 15 metodi
- **CommandTranslator**: 81 metodi
- **BashToolExecutor**: 29 metodi

---

| # | Metodo | Classe | Visibilità | Righe | 
|---|--------|--------|------------|-------|
| 1 | `__init__` | PathTranslator | public | ? |
| 2 | `get_workspace_root` | PathTranslator | public | ? |
| 3 | `get_tool_scratch_directory` | PathTranslator | public | ? |
| 4 | `get_claude_home_unix` | PathTranslator | public | ? |
| 5 | `get_claude_home_windows` | PathTranslator | public | ? |
| 6 | `get_uploads_directory_unix` | PathTranslator | public | ? |
| 7 | `get_uploads_directory_windows` | PathTranslator | public | ? |
| 8 | `get_outputs_directory_unix` | PathTranslator | public | ? |
| 9 | `get_outputs_directory_windows` | PathTranslator | public | ? |
| 10 | `to_windows` | PathTranslator | public | ? |
| 11 | `to_unix` | PathTranslator | public | ? |
| 12 | `ensure_directories_exist` | PathTranslator | public | ? |
| 13 | `translate_paths_in_string` | PathTranslator | public | ? |
| 14 | `_translate_unix_paths_to_windows` | PathTranslator | private | ? |
| 15 | `_translate_windows_paths_to_unix` | PathTranslator | private | ? |
| 16 | `__init__` | CommandTranslator | public | ? |
| 17 | `translate` | CommandTranslator | public | ? |
| 18 | `_parse_command_structure` | CommandTranslator | private | ? |
| 19 | `_translate_single_command` | CommandTranslator | private | ? |
| 20 | `_translate_ls` | CommandTranslator | private | ? |
| 21 | `_translate_cat` | CommandTranslator | private | ? |
| 22 | `_translate_echo` | CommandTranslator | private | ? |
| 23 | `_translate_pwd` | CommandTranslator | private | ? |
| 24 | `_translate_cd` | CommandTranslator | private | ? |
| 25 | `_translate_mkdir` | CommandTranslator | private | ? |
| 26 | `_translate_rm` | CommandTranslator | private | ? |
| 27 | `_translate_cp` | CommandTranslator | private | ? |
| 28 | `_translate_mv` | CommandTranslator | private | ? |
| 29 | `_translate_touch` | CommandTranslator | private | ? |
| 30 | `_translate_ln` | CommandTranslator | private | ? |
| 31 | `_translate_grep` | CommandTranslator | private | ? |
| 32 | `_translate_find` | CommandTranslator | private | ? |
| 33 | `_translate_which` | CommandTranslator | private | ? |
| 34 | `_translate_head` | CommandTranslator | private | ? |
| 35 | `_translate_tail` | CommandTranslator | private | ? |
| 36 | `_translate_wc` | CommandTranslator | private | ? |
| 37 | `_translate_sort` | CommandTranslator | private | ? |
| 38 | `_translate_uniq` | CommandTranslator | private | ? |
| 39 | `_translate_ps` | CommandTranslator | private | ? |
| 40 | `_translate_kill` | CommandTranslator | private | ? |
| 41 | `_translate_env` | CommandTranslator | private | ? |
| 42 | `_translate_printenv` | CommandTranslator | private | ? |
| 43 | `_translate_export` | CommandTranslator | private | ? |
| 44 | `_translate_wget` | CommandTranslator | private | ? |
| 45 | `_translate_curl` | CommandTranslator | private | ? |
| 46 | `_translate_chmod` | CommandTranslator | private | ? |
| 47 | `_translate_chown` | CommandTranslator | private | ? |
| 48 | `_translate_du` | CommandTranslator | private | ? |
| 49 | `_translate_df` | CommandTranslator | private | ? |
| 50 | `_translate_date` | CommandTranslator | private | ? |
| 51 | `_translate_sleep` | CommandTranslator | private | ? |
| 52 | `_translate_basename` | CommandTranslator | private | ? |
| 53 | `_translate_dirname` | CommandTranslator | private | ? |
| 54 | `_translate_tar` | CommandTranslator | private | ? |
| 55 | `_translate_zip` | CommandTranslator | private | ? |
| 56 | `_translate_unzip` | CommandTranslator | private | ? |
| 57 | `_translate_sed` | CommandTranslator | private | ? |
| 58 | `_translate_awk` | CommandTranslator | private | ? |
| 59 | `_awk_to_ps_statement` | CommandTranslator | private | ? |
| 60 | `_awk_to_ps_condition` | CommandTranslator | private | ? |
| 61 | `_translate_cut` | CommandTranslator | private | ? |
| 62 | `_parse_cut_range` | CommandTranslator | private | ? |
| 63 | `_translate_true` | CommandTranslator | private | ? |
| 64 | `_translate_false` | CommandTranslator | private | ? |
| 65 | `_translate_test` | CommandTranslator | private | ? |
| 66 | `_translate_tr` | CommandTranslator | private | ? |
| 67 | `_translate_diff` | CommandTranslator | private | ? |
| 68 | `_translate_tee` | CommandTranslator | private | ? |
| 69 | `_translate_seq` | CommandTranslator | private | ? |
| 70 | `_translate_yes` | CommandTranslator | private | ? |
| 71 | `_translate_whoami` | CommandTranslator | private | ? |
| 72 | `_translate_hostname` | CommandTranslator | private | ? |
| 73 | `_translate_file` | CommandTranslator | private | ? |
| 74 | `_translate_stat` | CommandTranslator | private | ? |
| 75 | `_translate_readlink` | CommandTranslator | private | ? |
| 76 | `_translate_realpath` | CommandTranslator | private | ? |
| 77 | `_translate_sha256sum` | CommandTranslator | private | ? |
| 78 | `_translate_sha1sum` | CommandTranslator | private | ? |
| 79 | `_translate_md5sum` | CommandTranslator | private | ? |
| 80 | `_translate_hexdump` | CommandTranslator | private | ? |
| 81 | `_translate_strings` | CommandTranslator | private | ? |
| 82 | `_translate_column` | CommandTranslator | private | ? |
| 83 | `_translate_watch` | CommandTranslator | private | ? |
| 84 | `_translate_paste` | CommandTranslator | private | ? |
| 85 | `_translate_comm` | CommandTranslator | private | ? |
| 86 | `_translate_join` | CommandTranslator | private | ? |
| 87 | `_translate_base64` | CommandTranslator | private | ? |
| 88 | `_translate_timeout` | CommandTranslator | private | ? |
| 89 | `_parse_duration` | CommandTranslator | private | ? |
| 90 | `_translate_split` | CommandTranslator | private | ? |
| 91 | `_parse_size` | CommandTranslator | private | ? |
| 92 | `_translate_gzip` | CommandTranslator | private | ? |
| 93 | `_translate_gunzip` | CommandTranslator | private | ? |
| 94 | `_translate_jq` | CommandTranslator | private | ? |
| 95 | `_is_simple_jq_pattern` | CommandTranslator | private | ? |
| 96 | `_jq_to_powershell` | CommandTranslator | private | ? |
| 97 | `__init__` | BashToolExecutor | public | ? |
| 98 | `_detect_git_bash` | BashToolExecutor | private | ? |
| 99 | `_detect_system_python` | BashToolExecutor | private | ? |
| 100 | `_expand_braces` | BashToolExecutor | private | ? |
| 101 | `_process_heredocs` | BashToolExecutor | private | ? |
| 102 | `_process_substitution` | BashToolExecutor | private | ? |
| 103 | `_process_command_substitution_recursive` | BashToolExecutor | private | ? |
| 104 | `_translate_substitution_content` | BashToolExecutor | private | ? |
| 105 | `_expand_variables` | BashToolExecutor | private | ? |
| 106 | `_preprocess_test_commands` | BashToolExecutor | private | ? |
| 107 | `_expand_aliases` | BashToolExecutor | private | ? |
| 108 | `_process_subshell` | BashToolExecutor | private | ? |
| 109 | `_process_command_grouping` | BashToolExecutor | private | ? |
| 110 | `_process_xargs` | BashToolExecutor | private | ? |
| 111 | `_process_find_exec` | BashToolExecutor | private | ? |
| 112 | `_process_escape_sequences` | BashToolExecutor | private | ? |
| 113 | `_has_control_structures` | BashToolExecutor | private | ? |
| 114 | `_convert_control_structures_to_script` | BashToolExecutor | private | ? |
| 115 | `_bash_to_powershell` | BashToolExecutor | private | ? |
| 116 | `_convert_test_to_powershell` | BashToolExecutor | private | ? |
| 117 | `_cleanup_temp_files` | BashToolExecutor | private | ? |
| 118 | `_needs_powershell` | BashToolExecutor | private | ? |
| 119 | `_adapt_for_powershell` | BashToolExecutor | private | ? |
| 120 | `_setup_virtual_env` | BashToolExecutor | private | ? |
| 121 | `_process_variable_assignments` | BashToolExecutor | private | ? |
| 122 | `execute` | BashToolExecutor | public | ? |
| 123 | `_setup_environment` | BashToolExecutor | private | ? |
| 124 | `_format_result` | BashToolExecutor | private | ? |
| 125 | `get_definition` | BashToolExecutor | public | ? |

---

## STATISTICHE

**PathTranslator:**
- Public: 13
- Private: 2

**CommandTranslator:**
- Public: 2
- Private: 79

**BashToolExecutor:**
- Public: 3
- Private: 26

