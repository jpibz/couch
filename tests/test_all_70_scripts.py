#!/usr/bin/env python3
"""
READ ALL 70 SCRIPTS - Complete verification
Print every single script generated for manual reading
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from bash_tool.bash_tool_executor import BashToolExecutor

# Force emulation
executor = BashToolExecutor(working_dir='/home/user/couch', test_capabilities={'bash': False})

# All 70 commands with test inputs
commands = [
    ('pwd', 'pwd'),
    ('ps', 'ps'),
    ('chmod', 'touch /tmp/t && chmod 644 /tmp/t'),
    ('chown', 'chown user file'),
    ('df', 'df'),
    ('true', 'true'),
    ('false', 'false'),
    ('whoami', 'whoami'),
    ('hostname', 'hostname'),
    ('which', 'which python'),
    ('sleep', 'sleep 0.1'),
    ('cd', 'cd /tmp'),
    ('basename', 'basename /path/to/file.txt'),
    ('dirname', 'dirname /path/to/file.txt'),
    ('kill', 'kill -l'),
    ('mkdir', 'mkdir -p /tmp/test'),
    ('mv', 'mv /tmp/a /tmp/b'),
    ('yes', 'yes | head -n 1'),
    ('env', 'env | head -n 1'),
    ('printenv', 'printenv PATH'),
    ('export', 'export VAR=test'),
    ('touch', 'touch /tmp/file'),
    ('echo', 'echo hello world'),
    ('wc', 'echo -e "a\\nb\\nc" | wc -l'),
    ('du', 'du /tmp'),
    ('date', 'date'),
    ('head', 'echo -e "a\\nb\\nc\\nd\\ne" | head -n 3'),
    ('tail', 'echo -e "a\\nb\\nc\\nd\\ne" | tail -n 2'),
    ('rm', 'rm /tmp/file'),
    ('cat', 'echo test | cat'),
    ('cp', 'cp /tmp/a /tmp/b'),
    ('ls', 'ls -la'),
    ('tee', 'echo test | tee /tmp/file'),
    ('seq', 'seq 1 5'),
    ('file', 'file /tmp/test'),
    ('stat', 'stat /tmp/test'),
    ('readlink', 'readlink -f /tmp'),
    ('realpath', 'realpath /tmp'),
    ('test', 'test -f /tmp'),
    ('tr', 'echo hello | tr a-z A-Z'),
    ('find', 'find /tmp -name "*.txt"'),
    ('wget', 'wget --help'),
    ('curl', 'curl --help'),
    ('sed', 'echo hello | sed "s/hello/world/"'),
    ('diff', 'diff /tmp/a /tmp/b'),
    ('jq', 'echo \'{"a":"b"}\' | jq .a'),
    ('awk', 'echo "a b c" | awk \'{print $2}\''),
    ('split', 'split -l 2 /tmp/file'),
    ('sort', 'echo -e "c\\na\\nb" | sort'),
    ('uniq', 'echo -e "a\\na\\nb" | uniq'),
    ('join', 'join /tmp/a /tmp/b'),
    ('hexdump', 'hexdump -C /tmp/file'),
    ('ln', 'ln -s /tmp/a /tmp/b'),
    ('grep', 'echo -e "foo\\nbar\\nbaz" | grep ba'),
    ('gzip', 'gzip /tmp/file'),
    ('gunzip', 'gunzip /tmp/file.gz'),
    ('timeout', 'timeout 1 sleep 0.1'),
    ('tar', 'tar -cf /tmp/archive.tar /tmp/dir'),
    ('cut', 'echo "a:b:c" | cut -d: -f2'),
    ('strings', 'strings /tmp/file'),
    ('column', 'echo -e "a b\\nc d" | column -t'),
    ('paste', 'paste /tmp/a /tmp/b'),
    ('comm', 'comm /tmp/a /tmp/b'),
    ('zip', 'zip /tmp/archive.zip /tmp/file'),
    ('unzip', 'unzip -l /tmp/archive.zip'),
    ('sha256sum', 'echo test | sha256sum'),
    ('sha1sum', 'echo test | sha1sum'),
    ('md5sum', 'echo test | md5sum'),
    ('base64', 'echo hello | base64'),
    ('watch', 'watch --help'),
]

print("=" * 80)
print(f"READING ALL {len(commands)} SCRIPTS")
print("=" * 80)

for i, (name, cmd) in enumerate(commands, 1):
    print(f"\n{'='*80}")
    print(f"[{i}/70] {name}")
    print(f"INPUT: {cmd}")
    print(f"{'='*80}")

    result = executor.execute({'command': cmd, 'description': f'test {name}'})
    print(result)

print("\n" + "=" * 80)
print("COMPLETED - All 70 scripts printed above")
print("=" * 80)
