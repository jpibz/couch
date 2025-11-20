#!/bin/bash
cd /home/user/couch/tests

# List of 68 commands
commands="awk base64 basename cat cd chmod chown column comm cp curl cut date df diff dirname du echo env export false file find grep gunzip gzip head hexdump hostname join jq kill ln ls md5sum mkdir mv paste printenv ps pwd readlink realpath rm sed seq sha1sum sha256sum sleep sort split stat strings tail tar tee test timeout touch tr true uniq unzip watch wc wget which whoami yes zip"

for cmd in $commands; do
    # Count occurrences in test files (look for command at start of string or after space/pipe/&&/||/;)
    count=$(grep -h "runner\.test\|executor\.execute" test_*.py 2>/dev/null | grep -c "\<$cmd\>")
    echo "$cmd:$count"
done | sort -t: -k2 -rn
