#!/usr/bin/env python3
"""The verifier's break attempts, part 2 (pure logic): CK-K02 (A-INV-2 comparator), T-03 (--only), T-05 (ast_scan),
T-02 (vendored_isolated record), O11 (a C8(3) pilot whose ledger is c8-d3-ledger-1).
  probes2.py PKGROOT OUT.json"""
import ast, importlib.util, json, os, shutil, subprocess, sys, tempfile, time, traceback
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
PY = sys.executable
R = {}


def probe(name, fn):
    t0 = time.time()
    try:
        R[name] = dict(held=True, result=fn())
    except BaseException as e:  # noqa: BLE001
        R[name] = dict(held=False, error=f'{type(e).__name__}: {e}'[:2000], traceback=traceback.format_exc()[-2500:])
    R[name]['seconds'] = round(time.time() - t0, 1)
    print(name, 'HELD' if R[name]['held'] else 'BROKEN', R[name].get('error', '')[:400], flush=True)
    OUT.write_text(json.dumps(R, indent=1, default=str) + '\n')


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


TR = load(ROOT / 'gen/test_regress.py', 'test_regress_probe')
RG = TR.R


def ck_k02():
    out = {}

    def want_other(label, sector, L, gid, new, old):
        v, info = RG.judge(sector, L, f'G{gid}.txt', new, old, TR.LEGACY)
        out[label] = v
        if v != 'other':
            raise AssertionError(f'{label}: verdict {v} {info}')

    g2 = TR.frozen('free', 4, 2)
    perm = TR.recorded(4, 2)
    rel = TR.relabel(g2, TR.inverse(perm))
    v, _ = RG.judge('free', 4, 'G2.txt', rel, g2, TR.LEGACY)
    assert v == 'relabelled', v
    ls = TR.lines_of(rel)
    # 1. one term coefficient changed in an otherwise valid relabelling
    t = ls[2].split()
    k = int(t[0])
    t[1 + k] = str(int(t[1 + k]) + 1)
    want_other('relabelled_with_one_coefficient_changed', 'free', 4, 2, TR.join([ls[0], ls[1]] + [' '.join(t)] + ls[3:]), g2)
    # 2. a term duplicated (T + 1 in the header too)
    h = ls[0].split()
    h[6] = str(int(h[6]) + 1)
    want_other('relabelled_with_a_term_duplicated', 'free', 4, 2, TR.join([' '.join(h), ls[1], ls[2]] + ls[2:]), g2)
    # 3. masks relabelled but the coefficient vectors left in the old edge order
    q = TR.inverse(perm)
    E = 8
    pm = lambda m: sum(1 << q[e] for e in range(E) if m >> e & 1)  # noqa: E731
    gl = TR.lines_of(g2)
    masks = [str(pm(int(x))) for x in gl[1].split()]
    half = TR.join([gl[0], ' '.join(masks) + ' '] + gl[2:])
    if half != g2:
        want_other('masks_relabelled_coefficients_not', 'free', 4, 2, half, g2)
    # 4. the power sector never takes the legacy rule
    p_ids = sorted(int(p.name[1:-4]) for p in (RG.FROZEN['power'] / 'L4').glob('G*.txt'))
    for gid in p_ids:
        recs = [r for r in TR.LEGACY.get(4, []) if r.get('new') == gid]
        if recs:
            pg = TR.frozen('power', 4, gid)
            want_other('power_sector_relabelled', 'power', 4, gid, TR.relabel(pg, TR.inverse([int(x) for x in recs[0]['edge_permutation']])), pg)
            break
    # 5. a file judged under another graph's name (header id != file name)
    want_other('header_id_not_the_file_name', 'free', 4, 3, rel, g2)
    # 6. a relabelling that also drops a mask nobody uses (M - 1 in the header): header differs
    h = ls[0].split()
    h[5] = str(int(h[5]) - 1)
    want_other('relabelled_header_M_changed', 'free', 4, 2, TR.join([' '.join(h)] + ls[1:]), g2)
    return out


def only_selections():
    out = {}
    for script, args in (('tests/unit_orchestration.py', ['--only', 'roles,,nope']), ('tests/unit_orchestration.py', ['--only', ' ']),
                         ('tests/test_pipeline.py', ['--only', 'part1,PART2']), ('tests/test_pipeline.py', ['--only=']),
                         ('tests/validate.py', ['--only', 'none'])):
        t0 = time.time()
        p = subprocess.run([PY, '-B', str(ROOT / script), *args], capture_output=True, text=True, timeout=300, cwd=ROOT,
                           env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        out[f'{script} {" ".join(args)}'] = dict(exit=p.returncode, seconds=round(time.time() - t0, 1), stderr=p.stderr.strip()[-160:])
        if p.returncode != 2 or time.time() - t0 > 60:
            raise AssertionError(out)
    return out


def ast_scan():
    sc = load(ROOT / 'tests/ast_scan.py', 'ast_scan_probe')
    cases = {
        # (source, expected number of findings)
        'del_in_nested_try_finally': ('def f():\n    x=1\n    try:\n        try:pass\n        finally:del x\n    finally:pass\n    return x\n', 1),
        'del_in_with_body': ('def f(p):\n    x=1\n    with open(p):\n        del x\n    return x\n', 1),
        'while_else_after_del_break': ('def f(n):\n    x=1\n    while n:\n        del x\n        break\n    else:\n        x=2\n    return x\n', 1),
        'reassigned_in_finally_after_handler_del': ('def f():\n    x=1\n    try:\n        g()\n    except OSError as x:\n        pass\n    finally:\n        x=3\n    return x\n', 0),
        'except_as_unbinds': ('def f():\n    x=1\n    try:\n        g()\n    except OSError as x:\n        pass\n    return x\n', 1),
        'loop_rebinds_before_use': ('def f(s):\n    for i in s:\n        x=i\n        del x\n    return 0\n', 0),
        'nested_function_not_flagged': ('def f():\n    x=1\n    def g():return x\n    del x\n    return g\n', 0),
    }
    out = {}
    bad = []
    for name, (src, want) in cases.items():
        t = ast.parse(src)
        got = len(sc.unreachable(t, name) + sc.unbound(t, name))
        out[name] = dict(findings=got, expected=want)
        if got != want:
            bad.append(name)
    if bad:
        raise AssertionError(f'ast_scan disagrees on {bad}: {out}')
    return out


def vendored_record():
    """T-02: an interrupt by KeyboardInterrupt-like signal mid-run still writes passed=false."""
    out = {}
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        src = (ROOT / 'tests/vendored_isolated.py').read_text()
        d = td / 'x'
        (d / 'tests').mkdir(parents=True)
        (d / 'tests/vendored_isolated.py').write_text(src)
        (d / 'vendor/c8_assembly').mkdir(parents=True)
        (d / 'vendor/c8_assembly/HANDOFF_assembly.json').write_text('{not json')
        rec = td / 'rec.json'
        p = subprocess.run([PY, '-B', str(d / 'tests/vendored_isolated.py'), '--in-place', '--output', str(rec)], capture_output=True, text=True, timeout=120)
        r = json.loads(rec.read_text())
        out['malformed_handoff_json'] = dict(exit=p.returncode, passed=r['passed'], completed=r['completed'], error=(r['error'] or '')[:120])
        if p.returncode == 0 or r['passed'] is not False or r['completed'] is not False:
            raise AssertionError(out)
    return out


def o11_d3_ledger():
    """A C8(3) pilot keeps its own ledger, schema c8-d3-ledger-1 (C8(3) PLAN HD7). design.py's eta_node goes through
    tools/accounting.py and tools/ledger.py, whose ledger reader accepts only c8-d2-ledger-1 records. Shown directly on
    ledger.read and on accounting.account's ledger step (no Slurm needed to reach it)."""
    sys.path[:0] = [str(ROOT / 'tools')]
    import ledger as L
    out = {}
    with tempfile.TemporaryDirectory() as td:
        run = Path(td)
        (run / 'submissions.jsonl').write_text(json.dumps({'schema': 'c8-d3-ledger-1', 'jobid': '123', 'role': 'lane'}) + '\n')
        try:
            L.read(run)
            out['ledger_read_c8_d3'] = 'accepted'
        except ValueError as e:
            out['ledger_read_c8_d3'] = f'refused: {e}'[:200]
    acc_src = (ROOT / 'tools/accounting.py').read_text()
    out['accounting_reads_ledger_via'] = 'ledger.jobs(run)' if 'ledger.jobs(run)' in acc_src else 'other'
    out['accounting_schema_param'] = 'schemas_of' in acc_src
    return out


probe('CK-K02_comparator_edge_cases', ck_k02)
probe('T-03_only_selection_edge_cases', only_selections)
probe('T-05_ast_scan_extra_cases', ast_scan)
probe('T-02_malformed_handoff_json_record', vendored_record)
probe('O11_c8_d3_ledger_schema_reach', o11_d3_ledger)
R['all_held'] = all(v['held'] for v in R.values() if isinstance(v, dict) and 'held' in v)
OUT.write_text(json.dumps(R, indent=1, default=str) + '\n')
print('ALL HELD' if R['all_held'] else 'SOME BROKEN')
