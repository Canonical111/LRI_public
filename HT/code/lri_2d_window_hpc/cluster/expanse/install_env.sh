#!/bin/bash
# Create (once) the immutable, read-only Expanse env envs/<env_id> from exact pins.
# Run on an Expanse login node.  usage: install_env.sh ROOT REQUIREMENTS ENVCHECK_PY
set -eo pipefail
root=$1; req=$2; check=$3
mkdir -p "$root/envs"; tmp=$root/envs/.build-$$
/usr/bin/python3.11 -m venv "$tmp"
"$tmp/bin/python" -m pip install -q --no-cache-dir --upgrade pip==24.0 >/dev/null
"$tmp/bin/python" -m pip install -q --no-cache-dir -r "$req"
id=$("$tmp/bin/python" -E -s "$check" | /usr/bin/python3 -c 'import json,sys;print(json.load(sys.stdin)["env_id"])')
if [[ -d "$root/envs/$id" ]]; then rm -rf "$tmp"; echo "env $id already present"; else mv "$tmp" "$root/envs/$id"; fi
"$root/envs/$id/bin/python" -E -s "$check" --expect "$id"
chmod -R a-w "$root/envs/$id"
echo "$id"
