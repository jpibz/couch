# ANALISI METODI MULTISTEP

## DEFINIZIONE MULTISTEP
Un metodo è MULTISTEP se:
1. Chiama executor (execute_cmd/execute_bash/execute_powershell/subprocess.run)
2. USA il risultato (stdout/stderr/returncode) per fare ALTRO (step successivo)

## CLASSI ANALIZZATE

---

## 1. CommandExecutor (bash_tool_executor.py)

| Line | Method | MULTISTEP |
|------|--------|-----------|
| 967 | `__init__` | FALSE |
| 1018 | `single_executor` | FALSE |
| 1054 | `execute` | FALSE |
| 1133 | `execute_bash` | FALSE |
| 1215 | `_detect_native_binaries` | FALSE |
| 1243 | `_execute_with_gitbash` | FALSE |
| 1264 | `_windows_to_gitbash_paths` | FALSE |
| 1286 | `_get_execution_map` | FALSE |
| 1347 | `_execute_find` | ? |
| 1743 | `_execute_curl` | ? |
| 1983 | `_checksum_generic` | ? |
| 2036 | `_execute_sha256sum` | FALSE |
| 2039 | `_execute_sha1sum` | FALSE |
| 2042 | `_execute_md5sum` | FALSE |
| 2051 | `_execute_ln` | ? |
| 2178 | `_parse_find_size` | FALSE |
| 2207 | `_execute_join` | ? |
| 2350 | `_execute_diff` | ? |
| 2565 | `_execute_awk` | ? |
| 2825 | `_awk_to_ps_statement` | FALSE |
| 2857 | `_awk_to_ps_condition` | FALSE |
| 2867 | `_execute_sort` | ? |
| 3060 | `_execute_uniq` | ? |
| 3224 | `_execute_grep` | ? |
| 3351 | `_execute_tar` | ? |
| 3464 | `_execute_hexdump` | ? |
| 3598 | `_execute_gzip` | ? |
| 3716 | `_execute_split` | ? |
| 3886 | `_parse_size` | FALSE |
| 3915 | `_execute_jq` | ? |
| 4026 | `_is_simple_jq_pattern` | FALSE |
| 4062 | `_jq_to_powershell` | FALSE |
| 4137 | `_execute_timeout` | ? |
| 4225 | `_parse_duration` | FALSE |
| 4252 | `_execute_sed` | ? |
| 4537 | `_execute_strings` | ? |
| 4607 | `_execute_base64` | ? |
| 4667 | `_execute_gunzip` | ? |
| 4761 | `_execute_column` | ? |
| 4858 | `_execute_unzip` | ? |
| 4948 | `_execute_watch` | ? |
| 5006 | `_execute_paste` | ? |
| 5094 | `_execute_comm` | ? |
| 5184 | `_execute_wget` | ? |
| 5231 | `_execute_head` | ? |
| 5348 | `_execute_tail` | ? |
| 5500 | `_execute_cat` | ? |
| 5692 | `_execute_wc` | ? |
| 5944 | `_execute_test` | ? |
| 6093 | `_execute_zip` | ? |

---

## 2. BashToolExecutor (bash_tool_executor.py)

| Line | Method | MULTISTEP |
|------|--------|-----------|
| 6227 | `__init__` | FALSE |
| 6341 | `_detect_git_bash` | FALSE |
| 6377 | `_detect_system_python` | FALSE |
| 6413 | `_expand_braces` | FALSE |
| 6483 | `_process_heredocs` | TRUE |
| 6663 | `_process_substitution` | TRUE |
| 6758 | `_process_command_substitution_recursive` | FALSE |
| 6858 | `_translate_substitution_content` | FALSE |
| 6957 | `_expand_variables` | FALSE |
| 7200 | `_preprocess_test_commands` | FALSE |
| 7230 | `_expand_aliases` | FALSE |
| 7259 | `_process_subshell` | FALSE |
| 7287 | `_process_command_grouping` | FALSE |
| 7309 | `_process_xargs` | FALSE |
| 7336 | `_process_find_exec` | FALSE |
| 7363 | `_process_escape_sequences` | FALSE |
| 7377 | `_has_control_structures` | FALSE |
| 7382 | `_convert_control_structures_to_script` | FALSE |
| 7414 | `_bash_to_powershell` | FALSE |
| 7519 | `_convert_test_to_powershell` | FALSE |
| 7559 | `_cleanup_temp_files` | FALSE |
| 7569 | `_needs_powershell` | FALSE |
| 7622 | `_adapt_for_powershell` | FALSE |
| 7657 | `_setup_virtual_env` | FALSE |
| 7705 | `execute` | FALSE |
| 7768 | `_setup_environment` | FALSE |
| 7789 | `_format_result` | FALSE |
| 7823 | `get_definition` | FALSE |

---

## 3. SimpleTranslator (unix_translator.py)

| Line | Method | MULTISTEP |
|------|--------|-----------|
| 352 | `__init__` | FALSE |
| 356 | `_translate_pwd` | FALSE |
| 359 | `_translate_ps` | FALSE |
| 362 | `_translate_chmod` | FALSE |
| 365 | `_translate_chown` | FALSE |
| 368 | `_translate_df` | FALSE |
| 371 | `_translate_true` | FALSE |
| 374 | `_translate_false` | FALSE |
| 381 | `_translate_whoami` | FALSE |
| 385 | `_translate_hostname` | FALSE |
| 389 | `_translate_which` | FALSE |
| 394 | `_translate_sleep` | FALSE |
| 399 | `_translate_cd` | FALSE |
| 405 | `_translate_basename` | FALSE |
| 411 | `_translate_dirname` | FALSE |
| 417 | `_translate_kill` | FALSE |
| 425 | `_translate_mkdir` | FALSE |
| 434 | `_translate_mv` | FALSE |
| 445 | `_translate_yes` | FALSE |
| 458 | `_translate_env` | FALSE |
| 473 | `_translate_printenv` | FALSE |
| 488 | `_translate_export` | FALSE |

---

## 4. PipelineTranslator (unix_translator.py)

| Line | Method | MULTISTEP |
|------|--------|-----------|
| 524 | `__init__` | FALSE |
| 528 | `_translate_touch` | FALSE |
| 554 | `_translate_echo` | FALSE |
| 591 | `_translate_wc` | FALSE |
| 638 | `_translate_du` | FALSE |
| 674 | `_translate_date` | FALSE |
| 720 | `_translate_head` | FALSE |
| 779 | `_translate_tail` | FALSE |
| 846 | `_translate_rm` | FALSE |
| 904 | `_translate_cat` | FALSE |
| 973 | `_translate_cp` | FALSE |
| 1045 | `_translate_ls` | FALSE |
| 1120 | `_translate_tee` | FALSE |
| 1143 | `_translate_seq` | FALSE |
| 1176 | `_translate_file` | FALSE |
| 1197 | `_translate_stat` | FALSE |
| 1218 | `_translate_readlink` | FALSE |
| 1244 | `_translate_realpath` | FALSE |
| 1265 | `_translate_tr` | FALSE |
| 1333 | `_translate_sha256sum` | FALSE |
| 1342 | `_translate_sha1sum` | FALSE |
| 1351 | `_translate_md5sum` | FALSE |
| 1360 | `_translate_base64` | FALSE |

---

## 5. EmulativeTranslator (unix_translator.py)

| Line | Method | MULTISTEP |
|------|--------|-----------|
| 1435 | `__init__` | FALSE |
| 1439 | `_translate_wget` | FALSE |
| 1455 | `_translate_curl` | FALSE |
| 1694 | `_translate_sed` | FALSE |
| 1927 | `_translate_diff` | FALSE |
| 2139 | `_translate_jq` | FALSE |
| 2250 | `_translate_awk` | FALSE |
| 2422 | `_translate_split` | FALSE |
| 2592 | `_translate_sort` | FALSE |
| 2782 | `_translate_uniq` | FALSE |
| 2943 | `_translate_join` | FALSE |
| 3083 | `_translate_hexdump` | FALSE |
| 3214 | `_translate_ln` | FALSE |
| 3338 | `_translate_grep` | FALSE |
| 3476 | `_translate_gzip` | FALSE |
| 3591 | `_translate_gunzip` | FALSE |
| 3683 | `_translate_timeout` | FALSE |
| 3771 | `_translate_tar` | FALSE |
| 3881 | `_translate_cut` | FALSE |
| 3968 | `_translate_strings` | FALSE |
| 4036 | `_translate_column` | FALSE |
| 4131 | `_translate_watch` | FALSE |
| 4189 | `_translate_paste` | FALSE |
| 4277 | `_translate_comm` | FALSE |
| 4365 | `_translate_zip` | FALSE |
| 4434 | `_translate_unzip` | FALSE |
| 4522 | `_translate_find` | FALSE |
| 4575 | `_translate_test` | FALSE |
| 4650 | `_awk_to_ps_statement` | FALSE |
| 4682 | `_awk_to_ps_condition` | FALSE |
| 4689 | `_parse_cut_range` | FALSE |
| 4709 | `_parse_duration` | FALSE |

---

## 6. CommandTranslator (unix_translator.py)

| Line | Method | MULTISTEP |
|------|--------|-----------|
| 4751 | `__init__` | FALSE |
| 4847 | `preprocess_command` | ? |
| 4897 | `execute_command` | FALSE |
| 4937 | `translate` | FALSE |
| 5037 | `_parse_command_structure` | FALSE |
| 5146 | `_translate_single_command` | FALSE |
| 5204 | `_translate_ls` | FALSE |
| 5279 | `_translate_cat` | FALSE |
| 5348 | `_translate_echo` | FALSE |
| 5385 | `_translate_pwd` | FALSE |
| 5388 | `_translate_cd` | FALSE |
| 5394 | `_translate_mkdir` | FALSE |
| 5403 | `_translate_rm` | FALSE |
| 5461 | `_translate_cp` | FALSE |
| 5533 | `_translate_mv` | FALSE |
| 5544 | `_translate_touch` | FALSE |
| 5570 | `_translate_ln` | FALSE |
| 5694 | `_translate_grep` | FALSE |
| 5832 | `_translate_find` | FALSE |
| 5885 | `_translate_which` | FALSE |
| 5890 | `_translate_head` | FALSE |
| 5949 | `_translate_tail` | FALSE |
| 6016 | `_translate_wc` | FALSE |
| 6063 | `_translate_sort` | FALSE |
| 6253 | `_translate_uniq` | FALSE |
| 6414 | `_translate_ps` | FALSE |
| 6417 | `_translate_kill` | FALSE |
| 6425 | `_translate_env` | FALSE |
| 6440 | `_translate_printenv` | FALSE |
| 6455 | `_translate_export` | FALSE |
| 6474 | `_translate_wget` | FALSE |
| 6490 | `_translate_curl` | FALSE |
| 6729 | `_translate_chmod` | FALSE |
| 6732 | `_translate_chown` | FALSE |
| 6735 | `_translate_du` | FALSE |
| 6771 | `_translate_df` | FALSE |
| 6774 | `_translate_date` | FALSE |
| 6820 | `_translate_sleep` | FALSE |
| 6825 | `_translate_basename` | FALSE |
| 6831 | `_translate_dirname` | FALSE |
| 6837 | `_translate_tar` | FALSE |
| 6947 | `_translate_zip` | FALSE |
| 7016 | `_translate_unzip` | FALSE |
| 7104 | `_translate_sed` | FALSE |
| 7337 | `_translate_awk` | FALSE |
| 7509 | `_awk_to_ps_statement` | FALSE |
| 7541 | `_awk_to_ps_condition` | FALSE |
| 7548 | `_translate_cut` | FALSE |
| 7635 | `_parse_cut_range` | FALSE |
| 7655 | `_translate_true` | FALSE |
| 7658 | `_translate_false` | FALSE |
| 7665 | `_translate_test` | FALSE |
| 7740 | `_translate_tr` | FALSE |
| 7808 | `_translate_diff` | FALSE |
| 8020 | `_translate_tee` | FALSE |
| 8043 | `_translate_seq` | FALSE |
| 8076 | `_translate_yes` | FALSE |
| 8089 | `_translate_whoami` | FALSE |
| 8093 | `_translate_hostname` | FALSE |
| 8097 | `_translate_file` | FALSE |
| 8118 | `_translate_stat` | FALSE |
| 8139 | `_translate_readlink` | FALSE |
| 8165 | `_translate_realpath` | FALSE |
| 8186 | `_translate_sha256sum` | FALSE |
| 8195 | `_translate_sha1sum` | FALSE |
| 8204 | `_translate_md5sum` | FALSE |
| 8213 | `_translate_hexdump` | FALSE |
| 8344 | `_translate_strings` | FALSE |
| 8412 | `_translate_column` | FALSE |
| 8507 | `_translate_watch` | FALSE |
| 8565 | `_translate_paste` | FALSE |
| 8653 | `_translate_comm` | FALSE |
| 8741 | `_translate_join` | FALSE |
| 8881 | `_translate_base64` | FALSE |
| 8939 | `_translate_timeout` | FALSE |
| 9027 | `_parse_duration` | FALSE |
| 9051 | `_translate_split` | FALSE |
| 9221 | `_parse_size` | FALSE |
| 9247 | `_translate_gzip` | FALSE |
| 9362 | `_translate_gunzip` | FALSE |
| 9454 | `_translate_jq` | FALSE |
| 9565 | `_is_simple_jq_pattern` | FALSE |
| 9601 | `_jq_to_powershell` | FALSE |
| 9667 | `_expand_braces` | FALSE |
| 9737 | `_process_heredocs` | TRUE |
| 9907 | `_process_substitution` | TRUE |
| 10002 | `_process_command_substitution_recursive` | FALSE |
| 10102 | `_translate_substitution_content` | FALSE |
| 10201 | `_expand_variables` | FALSE |
| 10444 | `_preprocess_test_commands` | FALSE |
| 10474 | `_expand_aliases` | FALSE |
| 10503 | `_process_subshell` | FALSE |
| 10531 | `_process_command_grouping` | FALSE |
| 10553 | `_process_xargs` | FALSE |
| 10580 | `_process_find_exec` | FALSE |
| 10607 | `_process_escape_sequences` | FALSE |
| 10621 | `_has_control_structures` | FALSE |
| 10626 | `_convert_control_structures_to_script` | FALSE |
| 10658 | `_bash_to_powershell` | FALSE |
| 10763 | `_convert_test_to_powershell` | FALSE |
| 10803 | `_cleanup_temp_files` | FALSE |
| 10813 | `_needs_powershell` | FALSE |
| 10866 | `_adapt_for_powershell` | FALSE |
| 10902 | `_get_default_environment` | FALSE |

---

## SUMMARY

**Metodi con flag "?" - DA ANALIZZARE:**
- CommandExecutor: 42 metodi _execute_*
- CommandTranslator: 1 metodo (preprocess_command)

**Metodi CONFERMATI MULTISTEP:**
- BashToolExecutor._process_heredocs (line 6483)
- BashToolExecutor._process_substitution (line 6663)
- CommandTranslator._process_heredocs (line 9737)
- CommandTranslator._process_substitution (line 9907)

**TOTALE METODI: ~270**
