#!/usr/bin/env python3
"""O11 residual probe: tests/test_pipeline.py part 2 with its c8-d3 pilot view keeping a c8-d3-ledger-1 ledger (the
C8(3) plan's own ledger schema, HD7) instead of the copied c8-d2 one. Expected outcome if the eta_node path followed
--schema-prefix: the d3 workflow passes; observed: the freeze of the c8-d3 pilot fails in the ledger reader."""
import json, sys
from pathlib import Path
ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / 'tests'))
import test_pipeline as TP
orig = TP.d3_view
def d3_view(X, src, dst, inp):
    out = orig(X, src, dst, inp)
    f = dst / 'submissions.jsonl'
    recs = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    for r in recs: r['schema'] = 'c8-d3-ledger-1'
    f.write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in recs))
    print(f'probe: {len(recs)} ledger record(s) of the c8-d3 view rewritten to c8-d3-ledger-1', flush=True)
    return out
TP.d3_view = d3_view
sys.argv = ['test_pipeline.py', '--only', 'part2']
try:
    rc = TP.main()
except BaseException as e:
    print(f'probe: test_pipeline part2 stopped: {type(e).__name__}: {str(e)[-1500:]}'); rc = 1
print('probe exit', rc)
