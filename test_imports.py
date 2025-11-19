"""
Quick test to verify all imports work
"""
import sys
sys.path.insert(0, 'src')

print("Testing imports...")

try:
    from bash_tool.constants import BASH_GIT_UNSUPPORTED_COMMANDS, GITBASH_PASSTHROUGH_COMMANDS
    print("✓ constants")

    from bash_tool.tool_executor import ToolExecutor
    print("✓ tool_executor")

    from bash_tool.pipeline_analysis import PipelineAnalysis
    print("✓ pipeline_analysis")

    from bash_tool.execution_strategy import ExecutionStrategy
    print("✓ execution_strategy")

    from bash_tool.sandbox_validator import SandboxValidator
    print("✓ sandbox_validator")

    from bash_tool.path_translator import PathTranslator
    print("✓ path_translator")

    from bash_tool.command_emulator import CommandEmulator
    print("✓ command_emulator")

    from bash_tool.execution_engine import ExecutionEngine
    print("✓ execution_engine")

    from bash_tool.pipeline_strategy import PipelineStrategy
    print("✓ pipeline_strategy")

    from bash_tool.execute_unix_single_command import ExecuteUnixSingleCommand
    print("✓ execute_unix_single_command")

    from bash_tool.command_executor import CommandExecutor
    print("✓ command_executor")

    from bash_tool.bash_tool_executor import BashToolExecutor
    print("✓ bash_tool_executor")

    print("\n✅ All imports successful!")

except ImportError as e:
    print(f"\n❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
