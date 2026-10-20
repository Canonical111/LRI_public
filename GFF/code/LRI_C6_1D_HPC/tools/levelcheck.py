"""Check that a merged level was produced by the approved code and data (PLAN.md rev 6, 4.6 production).

Usage: python levelcheck.py LEVEL.json IDENTITIES_JSON_STRING MANIFEST.json
Exit 0 iff: tools/levelio.validate_level accepts the file (canonical name matches header, exact sector coverage,
widths, finite values, totals consistent); header source_sha256 equals identities.source; exe_sha256
equals identities.c6sum (double) or identities.c6sum_ld (long double); graphs_sha256 equals identities.graphs6/7
for L = 5/6; weights_sha256 equals the manifest hash for (L, N) and precision.
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from levelio import validate_level, LevelError  # noqa: E402

try:
    rec = validate_level(sys.argv[1]); ids = json.loads(sys.argv[2]); man = json.loads(Path(sys.argv[3]).read_text())
    h = rec['header']; L = int(h['L']); N = int(h['N'])
    dbl = h['kind'] == 'double8'
    want = {'source_sha256': ids['source'], 'exe_sha256': ids['c6sum' if dbl else 'c6sum_ld'],
            'graphs_sha256': ids['graphs6' if L == 5 else 'graphs7'],
            'weights_sha256': man[f'L{L}_N{N}']['bin_sha256' if dbl else 'dd_sha256']}
    bad = {k: (h.get(k), v) for k, v in want.items() if h.get(k) != v}
    if bad:
        print(f'{sys.argv[1]}: mismatch {bad}', file=sys.stderr); sys.exit(1)
except LevelError as e:
    print(f'LEVEL INVALID: {e}', file=sys.stderr); sys.exit(1)
except (OSError, ValueError, KeyError) as e:
    print(f'{sys.argv[1]}: unreadable or malformed ({e})', file=sys.stderr); sys.exit(1)
