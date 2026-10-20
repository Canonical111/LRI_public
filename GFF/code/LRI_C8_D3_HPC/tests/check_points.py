#!/usr/bin/env python3
"""Point checks of every precision tier (tests/point_checks.cpp) for both MP backends (PLAN.md A-RPL-5, A-KER-7),
built with the Makefile's command (common.cxx_command): the first two and the two costliest graphs of every sector and
loop of inputs/inventory.json, 4 samples each, extracted from the packs (tools/members.py).
  * L <= 7: C7(3)'s exact gates (MP <= 1e-280 scaled; binary128 sharing bitwise equal to calculate_reference<Q>;
    long-double accepted points relative <= 1e-9 and scaled <= 1e-14), hard: a breach fails the run (G3a).
  * L8 (when the inventory has it, Stage 3b): the same gates in --contract mode: a long-double or MP breach is a
    precision-contract finding, reported (status "contract_finding"; every breach recorded with its graph, sample,
    scaled and relative error under "contract_breaches") and sent to the user, never tuned away.
  * the deep-cancellation fixture (A-KER-7): point_checks --deep on tests/fixtures/deep_cancellation/L3/G0.txt.
The per-loop maxima are the measured column of docs/NUMERICS.md's accuracy contract. Nothing is written into the
package unless --output."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_common as nc  # noqa: E402
from common import compiler_identity, cxx_command  # noqa: E402

FIXTURE = nc.ROOT / 'tests/fixtures/deep_cancellation/L3/G0.txt'


def run():
    inv = nc.inventory()
    sel = []
    for sector in nc.SECTORS:
        for L, rows in inv[sector].items():
            chosen = {r['id'] for r in rows[:2] + sorted(rows, key=lambda r: -r['cost'])[:2]}
            sel += [(sector, int(L), g) for g in sorted(chosen)]
    results = []
    with tempfile.TemporaryDirectory(prefix='c8d3_points_') as temp, nc.extracted(sel) as root:
        t = Path(temp)
        lists = {}
        for s, L, g in sel:
            lists.setdefault(L >= 8, []).append(str(root / s / f'L{L}' / f'G{g}.txt'))
        for backend in ('decimal', 'gmp'):
            exe = t / backend
            cmd = cxx_command([nc.ROOT / 'tests/point_checks.cpp'], exe, defines=('C7_USE_GMP',) if backend == 'gmp' else (),
                              libs=('-lquadmath', '-lgmp') if backend == 'gmp' else ('-lquadmath',))
            subprocess.run(cmd, check=True)
            build = {**compiler_identity(cmd), 'executable_sha256': nc.digest(exe)}
            for contract, paths in sorted(lists.items()):
                f = t / f'list_{int(contract)}'
                f.write_text('\n'.join(paths) + '\n')
                cp = subprocess.run([str(exe), *(['--contract'] if contract else []), str(f)], capture_output=True, text=True)
                if cp.returncode:
                    raise AssertionError(f'{backend} point checks failed: {cp.stderr[-2000:]}')
                r = json.loads(cp.stdout)
                # contract mode: every breach is one JSON line on stderr (graph path, L, sample, scaled and relative errors)
                br = [json.loads(x) for x in cp.stderr.splitlines() if x.startswith('{"breach"')]
                for x in br:
                    x['graph_id'] = int(Path(x['graph']).stem[1:])
                    x['sector'] = Path(x['graph']).parent.parent.name
                    x['graph'] = f'{x["sector"]}/L{x["L"]}/G{x["graph_id"]}'
                if len(br) != r['long_double_tier']['breaches'] + r.get('mp_breaches', 0):
                    raise AssertionError(f'{backend}: {len(br)} breach lines for {r["long_double_tier"]["breaches"]} + {r.get("mp_breaches", 0)} counted breaches')
                r.update(build=build, loops='L8 (contract mode)' if contract else 'L3-L7 (hard gates)', graphs=len(paths), breach_records=br)
                results.append(r)
                print(cp.stdout, flush=True)
            cp = subprocess.run([str(exe), '--deep', str(FIXTURE)], capture_output=True, text=True)
            if cp.returncode:
                raise AssertionError(f'{backend} deep-cancellation fixture failed: {cp.stderr[-2000:]}')
            d = json.loads(cp.stdout)
            d['build'] = build
            results.append(d)
            print(cp.stdout, flush=True)
    findings = [r for r in results if r.get('status') == 'contract_finding']
    summary = [{'backend': r['backend'], 'graph': x['graph'], 'sample': x['sample'], 'tier': x['breach'],
                **{k: x[k] for k in ('scaled', 'relative', 'ratio', 'which', 'moderate') if k in x}}
               for r in findings for x in r.get('breach_records', [])]
    return {'status': 'passed' if not findings else 'passed_with_contract_findings', 'host': nc.host_info(),
            'graphs': len(sel), 'selection': [f'{s}/L{L}/G{g}' for s, L, g in sel], 'results': results,
            'contract_findings': len(findings), 'contract_breaches': summary}


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--output', type=Path)
    a = a.parse_args()
    x = run()
    nc.dump(a.output, x)
    print(json.dumps({k: v for k, v in x.items() if k != 'results'}, indent=2))
