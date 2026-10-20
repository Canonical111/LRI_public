#!/usr/bin/env python3
"""Re-merge the C6(2) production from its hosted checkpoints with the production's unmodified tools, and compare.

Run from the package folder as `make -f public.mk remerge`, after `make -f public.mk fetch-data` has unpacked the hosted
run directory (392 MiB, 1,038 files) to ../../data/C6_2/hosted/run-20260928-m8192/. Steps:
 1. every hosted file against ../../data/C6_2/hosted_run-20260928-m8192.sha256;
 2. the hosted plan, configs, merged records and graph_replicates.csv byte-identical to the shipped ones (../../data/C6_2/);
 3. a copy of the hosted run in OUT/work/ without merged.json, graph_replicates.csv and C6_result.json;
 4. `tools/production.py status` (996/996 checkpoint blocks), then `tools/production.py merge`: the merge sums the
    checkpoint rows' decimal strings at 50 digits, so the 8 merged.json and 8 graph_replicates.csv must come out byte for
    byte as shipped;
 5. the unmodified `tools/assemble.py --bootstrap 4096 --output OUT/C6_result_cli.json` on the re-merged copy (it checks
    tasks.sqlite too), then public/replay.py on the copy with that output as an extra result (tolerances as in replay.py).
Exit 1 on any FAIL. About 30 s and 0.8 GB of disk (copy plus output); one core.
"""
import argparse, filecmp, hashlib, shutil, subprocess, sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
RUN = 'run-20260928-m8192'
FAILS = []


def say(ok, msg):
    print(('PASS  ' if ok else 'FAIL  ') + msg, flush=True)
    if not ok: FAILS.append(msg)


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--hosted', type=Path, default=PKG / '../../data/C6_2/hosted' / RUN)
    ap.add_argument('--sums', type=Path, default=PKG / f'../../data/C6_2/hosted_{RUN}.sha256')
    ap.add_argument('--data', type=Path, default=PKG / '../../data/C6_2' / RUN)
    ap.add_argument('--results', type=Path, default=PKG / '../../results/C6_2')
    ap.add_argument('--c7', type=Path, default=PKG / '../../results/C7_2/C7_result.json')
    ap.add_argument('--out', type=Path, default=PKG / 'public/out/remerge')
    a = ap.parse_args(); py = sys.executable
    hosted, data, out = a.hosted.resolve(), a.data.resolve(), a.out.resolve()
    if not (hosted / 'manifest.json').exists():
        print(f'remerge: {hosted}/manifest.json not found; run make -f public.mk fetch-data first', file=sys.stderr); return 2
    # 1. hosted files against the shipped list (paths relative to the parent of the run directory)
    lines = [ln.split('  ', 1) for ln in a.sums.read_text().splitlines() if ln.strip()]
    bad = [p for h, p in lines if not (hosted.parent / p).is_file() or sha(hosted.parent / p) != h]
    listed = {p for _, p in lines}
    extra = [str(f.relative_to(hosted.parent)) for f in hosted.rglob('*') if f.is_file() and str(f.relative_to(hosted.parent)) not in listed]
    say(not bad and not extra, f'hosted files match {a.sums.name}: {len(lines) - len(bad)}/{len(lines)}' + (f'; bad {bad[:3]}' if bad else '')
        + (f'; unlisted {extra[:3]}' if extra else ''))
    # 2. the shipped records are the hosted ones
    shipped = [f.relative_to(data) for f in data.rglob('*') if f.is_file()]
    diff = [str(f) for f in shipped if not filecmp.cmp(data / f, hosted / f, shallow=False)]
    say(not diff, f'{len(shipped)} shipped records byte-identical to the hosted copies' + (f'; differ {diff[:3]}' if diff else ''))
    # 3. working copy without the merge outputs
    work = out / 'work' / RUN
    if work.exists(): shutil.rmtree(work)
    shutil.copytree(hosted, work)
    for f in list(work.glob('groups/*/merged.json')) + list(work.glob('groups/*/graph_replicates.csv')) + [work / 'C6_result.json']:
        f.unlink(missing_ok=True)
    # 4. completeness and merge with the production's own tools
    st = subprocess.run([py, '-B', 'tools/production.py', 'status', str(work)], cwd=PKG, capture_output=True, text=True)
    say(st.returncode == 0 and 'complete: every checkpoint block is committed' in st.stdout,
        'production.py status: ' + ' | '.join(l for l in st.stdout.splitlines() if l.startswith('group ')))
    (out / 'tmp').mkdir(parents=True, exist_ok=True)
    mg = subprocess.run([py, '-B', 'tools/production.py', 'merge', str(work), '--scratch', str(out / 'tmp')], cwd=PKG,
                        capture_output=True, text=True)
    say(mg.returncode == 0, 'production.py merge' + ('' if mg.returncode == 0 else ': ' + mg.stderr.strip()[-300:]))
    for f in sorted(data.glob('groups/*/*')):
        if f.name in ('merged.json', 'graph_replicates.csv'):
            g = work / f.relative_to(data)
            say(g.exists() and filecmp.cmp(f, g, shallow=False), f'{f.relative_to(data)} re-merged byte for byte')
    # 5. the unmodified assembler on the re-merged copy, then the full replay on it
    cli = out / 'C6_result_cli.json'; cli.unlink(missing_ok=True)
    asm = subprocess.run([py, '-B', 'tools/assemble.py', str(work), '--bootstrap', '4096', '--output', str(cli)], cwd=PKG,
                         capture_output=True, text=True)
    say(asm.returncode == 0, 'tools/assemble.py --bootstrap 4096 on the re-merged copy: ' + (asm.stdout.strip()[:160] or asm.stderr.strip()[-300:]))
    rp = subprocess.run([py, '-B', 'public/replay.py', '--data', str(work), '--results', str(a.results.resolve()), '--c7', str(a.c7.resolve()),
                         '--extra-result', str(cli), '--out', str(out / 'replay')], cwd=PKG, capture_output=True, text=True)
    (out / 'replay.txt').write_text(rp.stdout + rp.stderr)
    say(rp.returncode == 0, 'public/replay.py on the re-merged copy (tasks.sqlite and sobol.bin checked, CLI output compared): '
        + (rp.stdout.strip().splitlines() or ['no output'])[-1])
    print(f'\nremerge: {len(FAILS)} FAIL; full replay table in {out / "replay.txt"}')
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
