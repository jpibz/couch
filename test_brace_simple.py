#!/usr/bin/env python3
"""Simple test to check if brace expansion is called"""

from bash_tool_executor import BashToolExecutor

executor = BashToolExecutor(working_dir='/home/user/couch')
executor.testmode = True

# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Test simple brace expansion
result = executor.execute({'command': 'echo {1..5}', 'description': 'Test brace'})
print(f"\nResult:\n{result}")
