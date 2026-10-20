#!/bin/bash
# Step 5 of the a42cfb7 validation (R3 on symmetry): re-verify, on the symmetry LOGIN node (as F6 was checked in
# stage5/fix/fxf6.login/), every stored result file of the C8(2) campaigns on BeeGFS with the new tools/verify_result.py
# of the export pkg/a42cfb718e69 (pull_bound / pull_problems, R3). Light work (a fraction of a second per file, no
# native program). For contrast, the fix-round-2 tool (pkg/e914701b042b, the tool R3 changed; a57e07f added only
# evidence) runs on the same files. Every C8_*.json result and *reassembled*.json under <SCRATCH>/c8-d2 and
# <SCRATCH>/c8d2/evidence is found by name, so none is missed; outputs go to
# <SCRATCH>/c8d2/evidence/<sha12>/rsverify.login/ (refused if it exists); the files of this export's own evidence tree are excluded.
# Usage (on the login node): bash rsverify_login.sh <SCRATCH>/c8d2/pkg/a42cfb718e69
set -uo pipefail
source "$HOME/c8d2/env.sh"
PKG=${1:?export}; OLD=<SCRATCH>/c8d2/pkg/e914701b042b
E=<SCRATCH>/c8d2/evidence/$(basename "$PKG")/rsverify.login
mkdir -p "$(dirname "$E")"; mkdir "$E" || { echo "$E exists; refusing" >&2; exit 64; }
mkdir "$E/new" "$E/before"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
{ hostname; grep -m1 'model name' /proc/cpuinfo; grep -m1 -o -w avx512f /proc/cpuinfo || echo 'no avx512f'; date -Is
  python3 --version; python3 -c 'import numpy; print("numpy", numpy.__version__); numpy.show_runtime()' 2>&1
  sha256sum "$HOME/c8d2/env.sh" "$PKG/tools/verify_result.py" "$OLD/tools/verify_result.py"; } > "$E/node.txt" 2>&1
cat "$E/node.txt" | head -4
find <SCRATCH>/c8-d2 <SCRATCH>/c8d2/evidence -type f \( -name 'C8_*.json' -o -name '*reassembled*.json' \) \
  -not -path "$(dirname "$E")/*" 2>/dev/null | sort > "$E/files.txt"
echo "files: $(wc -l < "$E/files.txt")"
i=0
while read -r f; do
  i=$((i+1)); k=$(printf '%02d' $i)
  t0=$(date +%s.%N)
  ( cd "$PKG" && python3 -B tools/verify_result.py "$f" --output "$E/new/$k.json" ) > "$E/new/$k.txt" 2>&1; c=$?
  t1=$(date +%s.%N)
  ( cd "$OLD" && python3 -B tools/verify_result.py "$f" --output "$E/before/$k.json" ) > "$E/before/$k.txt" 2>&1; cb=$?
  printf '%s new=%s before=%s %.2fs %s\n' "$k" "$c" "$cb" "$(awk -v a="$t0" -v b="$t1" 'BEGIN{print b-a}')" "$f" | tee -a "$E/exits.txt"
done < "$E/files.txt"
python3 - "$E" "$PKG" <<'PY'
import hashlib, json, sys
from pathlib import Path
E, PKG = Path(sys.argv[1]), Path(sys.argv[2])
rows = []
for n, line in enumerate((E / 'files.txt').read_text().splitlines(), 1):
    k = f'{n:02d}'; f = Path(line)
    def rec(d):
        p = E / d / f'{k}.json'
        if not p.exists(): return {'record': None, 'stdout_tail': (E / d / f'{k}.txt').read_text()[-600:]}
        r = json.loads(p.read_text()); return {'verified': r['verified'], 'problem_count': r['problem_count'], 'problems_first': r['problems'][:5]}
    rows.append({'n': k, 'file': str(f), 'sha256': hashlib.sha256(f.read_bytes()).hexdigest(), 'bytes': f.stat().st_size,
                 'new_a42cfb7': rec('new'), 'before_e914701': rec('before')})
s = {'schema': 'c8-d2-verify-stored-1', 'tool': str(PKG / 'tools/verify_result.py'),
     'tool_sha256': hashlib.sha256((PKG / 'tools/verify_result.py').read_bytes()).hexdigest(),
     'node': (E / 'node.txt').read_text().splitlines()[:3], 'files': len(rows),
     'verified_new': sum(r['new_a42cfb7'].get('verified') is True for r in rows),
     'verified_before': sum(r['before_e914701'].get('verified') is True for r in rows), 'rows': rows}
s['all_verified_new'] = s['verified_new'] == len(rows) and len(rows) > 0
(E / 'summary.json').write_text(json.dumps(s, indent=1) + '\n')
print(f"new tool: {s['verified_new']}/{len(rows)} verified; fix-round-2 tool: {s['verified_before']}/{len(rows)}")
for r in rows:
    if not r['new_a42cfb7'].get('verified') or not r['before_e914701'].get('verified'):
        print(r['n'], r['file'], 'new', r['new_a42cfb7'].get('verified'), r['new_a42cfb7'].get('problems_first', [])[:2],
              'before', r['before_e914701'].get('verified'), r['before_e914701'].get('problems_first', [])[:2])
sys.exit(0 if s['all_verified_new'] else 1)
PY
