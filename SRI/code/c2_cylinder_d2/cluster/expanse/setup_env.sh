#!/bin/bash
# Create the pinned Python environment for this package on SDSC Expanse.
# Run on a LOGIN node (needs network). Idempotent: an existing environment with
# the exact versions is verified and left alone.
#
#   bash cluster/expanse/setup_env.sh            # default: $HOME/envs/lri_c2
#   LRI_ENV_ROOT=/path bash cluster/expanse/setup_env.sh
#
# What it builds (nothing outside LRI_ENV_ROOT is touched, no shell rc edits):
#   $LRI_ENV_ROOT/bin/uv                pinned uv binary (sha256 of the release verified)
#   $LRI_ENV_ROOT/python/               uv-managed standalone CPython $LRI_PY_VERSION
#   $LRI_ENV_ROOT/py$LRI_PY_VERSION/    venv with requirements-tested.txt (exact pins)
#   $LRI_ENV_ROOT/py$LRI_PY_VERSION/lri_env_receipt.json   versions actually installed
#
# Why home and not Lustre: the environment is ~0.5 GB in ~10^4 small files.
# Creating many small files on the 90%-full Lustre scratch runs at a few files per
# second, they would count against the shared 2M-file quota, and temp_project is
# scratch. Home (NFS, no reported per-user quota) is the place for code; the few
# concurrent jobs of this campaign import from it without trouble.
# Why not a module: Expanse modules offer python/3.8.5 (cpu/0.15.4), anaconda3/2021.05
# (Python 3.8) and the system /usr/bin/python3 3.6.8, none of which can host the
# tested numpy 2.3.5 / scipy 1.17.0 wheels. The tested packaging environment used
# CPython 3.13.5, which uv installs as a self-contained interpreter.
set -eo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PKG=$(cd "$HERE/../.." && pwd)
REQ="$PKG/requirements-tested.txt"
UV_VERSION=${UV_VERSION:-0.12.13}
LRI_PY_VERSION=${LRI_PY_VERSION:-3.13.5}
LRI_ENV_ROOT=${LRI_ENV_ROOT:-$HOME/envs/lri_c2}
LRI_ENV=${LRI_ENV:-$LRI_ENV_ROOT/py$LRI_PY_VERSION}
UV="$LRI_ENV_ROOT/bin/uv"

[[ -f "$REQ" ]] || { echo "missing $REQ" >&2; exit 66; }
case "$(uname -s)-$(uname -m)" in
    Linux-x86_64) ;;
    *) echo "setup_env.sh targets Expanse (Linux x86_64); found $(uname -s)-$(uname -m)" >&2; exit 64 ;;
esac
if [[ -n "${SLURM_JOB_ID:-}" ]]; then
    echo "note: running inside job $SLURM_JOB_ID; downloads need network access from this node" >&2
fi

# Keep uv away from user-level config, caches and interpreters.
export UV_NO_CONFIG=1 UV_PYTHON_PREFERENCE=only-managed UV_PYTHON_DOWNLOADS=manual
export UV_PYTHON_INSTALL_DIR="$LRI_ENV_ROOT/python" UV_CACHE_DIR="$LRI_ENV_ROOT/cache"
unset VIRTUAL_ENV PYTHONPATH PYTHONHOME CONDA_PREFIX

verify() {   # check exact versions and write the receipt; exit status 0 only if all match
    "$LRI_ENV/bin/python" - "$REQ" "$LRI_ENV/lri_env_receipt.json" "$UV_VERSION" <<'EOF'
import datetime, hashlib, json, platform, subprocess, sys
from importlib import metadata
req, out, uv_version = sys.argv[1:]
wanted = {}
for line in open(req):
    line = line.split('#', 1)[0].strip()
    if line:
        name, version = line.split('==')
        wanted[name.strip()] = version.strip()
found = {name: metadata.version(name) for name in wanted}
bad = {n: (wanted[n], found[n]) for n in wanted if found[n] != wanted[n]}
freeze = sorted(f"{d.metadata['Name']}=={d.version}" for d in metadata.distributions())
receipt = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
           'requirements_file_sha256': hashlib.sha256(open(req, 'rb').read()).hexdigest(),
           'required': wanted, 'installed': found, 'mismatches': bad, 'all_distributions': freeze,
           'uv_version': uv_version}
json.dump(receipt, open(out, 'w'), indent=2)
print(json.dumps({'python': platform.python_version(), 'installed': found, 'mismatches': bad}))
sys.exit(1 if bad else 0)
EOF
}

if [[ -x "$LRI_ENV/bin/python" ]] && verify; then
    echo "OK: existing environment $LRI_ENV matches requirements-tested.txt"
    echo "LRI_ENV=$LRI_ENV"
    exit 0
fi

mkdir -p "$LRI_ENV_ROOT/bin"
if ! [[ -x "$UV" ]] || [[ "$("$UV" --version | awk '{print $2}')" != "$UV_VERSION" ]]; then
    tmp=$(mktemp -d)
    url="https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-x86_64-unknown-linux-gnu.tar.gz"
    curl -fsSL -o "$tmp/uv.tar.gz" "$url"
    curl -fsSL -o "$tmp/uv.tar.gz.sha256" "$url.sha256"
    expected=$(awk '{print $1}' "$tmp/uv.tar.gz.sha256")
    actual=$(sha256sum "$tmp/uv.tar.gz" | awk '{print $1}')
    [[ "$expected" == "$actual" ]] || { echo "uv download checksum mismatch" >&2; exit 74; }
    tar -xzf "$tmp/uv.tar.gz" -C "$tmp"
    install -m 0755 "$tmp/uv-x86_64-unknown-linux-gnu/uv" "$UV"
    rm -rf "$tmp"
fi
"$UV" --version

"$UV" python install "$LRI_PY_VERSION"
"$UV" venv --python "$LRI_PY_VERSION" "$LRI_ENV"
# --link-mode=copy: the venv must not depend on the uv cache, which may be pruned.
"$UV" pip install --python "$LRI_ENV/bin/python" --link-mode=copy -r "$REQ"
"$UV" cache prune >/dev/null 2>&1 || true
verify
echo "OK: created $LRI_ENV"
echo "LRI_ENV=$LRI_ENV"
