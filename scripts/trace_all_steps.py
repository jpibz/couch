#!/usr/bin/env python3
"""
Trace ALL preprocessing steps to find where ${TESTUPPER,,} gets corrupted
"""

from bash_tool_executor_REFACTORED import BashToolExecutor
import os

os.environ['TESTUPPER'] = 'HELLO'

executor = BashToolExecutor(working_dir='/home/user/couch')

# Monkey-patch ALL preprocessing functions
original_expand_aliases = BashToolExecutor._expand_aliases
original_process_subshell = BashToolExecutor._process_subshell
original_process_grouping = BashToolExecutor._process_command_grouping
original_preprocess_test = BashToolExecutor._preprocess_test_commands
original_expand_braces = BashToolExecutor._expand_braces
original_process_heredocs = BashToolExecutor._process_heredocs
original_process_substitution = BashToolExecutor._process_substitution
original_expand_variables = BashToolExecutor._expand_variables

def traced_expand_aliases(self, cmd):
    result = original_expand_aliases(self, cmd)
    if result != cmd:
        print(f"[_expand_aliases] CHANGED: {repr(cmd)} → {repr(result)}")
    return result

def traced_process_subshell(self, cmd):
    result = original_process_subshell(self, cmd)
    if result != cmd:
        print(f"[_process_subshell] CHANGED: {repr(cmd)} → {repr(result)}")
    return result

def traced_process_grouping(self, cmd):
    result = original_process_grouping(self, cmd)
    if result != cmd:
        print(f"[_process_command_grouping] CHANGED: {repr(cmd)} → {repr(result)}")
    return result

def traced_preprocess_test(self, cmd):
    result = original_preprocess_test(self, cmd)
    if result != cmd:
        print(f"[_preprocess_test_commands] CHANGED: {repr(cmd)} → {repr(result)}")
    return result

def traced_expand_braces(self, cmd):
    result = original_expand_braces(self, cmd)
    if result != cmd:
        print(f"[_expand_braces] CHANGED: {repr(cmd)} → {repr(result)}")
    return result

def traced_process_heredocs(self, cmd):
    result, files = original_process_heredocs(self, cmd)
    if result != cmd:
        print(f"[_process_heredocs] CHANGED: {repr(cmd)} → {repr(result)}")
    return result, files

def traced_process_substitution(self, cmd):
    result, files = original_process_substitution(self, cmd)
    if result != cmd:
        print(f"[_process_substitution] CHANGED: {repr(cmd)} → {repr(result)}")
    return result, files

def traced_expand_variables(self, cmd):
    print(f"[_expand_variables] INPUT: {repr(cmd)}")
    result = original_expand_variables(self, cmd)
    print(f"[_expand_variables] OUTPUT: {repr(result)}")
    return result

# Apply patches
BashToolExecutor._expand_aliases = traced_expand_aliases
BashToolExecutor._process_subshell = traced_process_subshell
BashToolExecutor._process_command_grouping = traced_process_grouping
BashToolExecutor._preprocess_test_commands = traced_preprocess_test
BashToolExecutor._expand_braces = traced_expand_braces
BashToolExecutor._process_heredocs = traced_process_heredocs
BashToolExecutor._process_substitution = traced_process_substitution
BashToolExecutor._expand_variables = traced_expand_variables

print("=" * 80)
print("TRACING: echo ${TESTUPPER,,}")
print("=" * 80)
print()

result = executor.execute({
    'command': 'echo ${TESTUPPER,,}',
    'description': 'test lowercase'
})

print()
print("=" * 80)
print("FINAL RESULT:")
print(result[:200])
