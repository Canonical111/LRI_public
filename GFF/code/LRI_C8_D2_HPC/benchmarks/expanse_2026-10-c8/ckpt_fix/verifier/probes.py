#!/usr/bin/env python3
"""The independent verifier's own break attempts on the checkpoint-review fixes (pure logic, fake worker; Mac).

  probes.py PKGROOT OUT.json
PKGROOT is the checkout at the commit under test. Uses tests/unit_orchestration.py's harness (isolated package copy).
Each probe tries a case the fixers' tests do not cover; "held" means the fix resisted it."""
import copy, hashlib, io, json, math, os, re, shutil, subprocess, sys, tempfile, time, traceback
from pathlib import Path
from unittest import mock

ROOT = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(ROOT / 'tests'))
import unit_orchestration as U  # noqa: E402

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


with tempfile.TemporaryDirectory(prefix='c8d2_probe_') as td:
    td = Path(td)
    pkg = U.make_package(td)
    c7cal = (ROOT / 'reference/c7d2_hpc_a55958f/tools/calibration.json').read_bytes()
    if (pkg / 'tools/calibration.json').read_bytes() != c7cal:
        U.replace_bytes(pkg / 'tools/calibration.json', c7cal)
    M = U.load_modules(pkg)
    E = U.Env(pkg, M, td)
    os.environ['C8_INPUTS'] = str(E.fixture)
    prod = M.prod

    # ------------------------------------------------------------------ O01
    def interrupted_campaign(name, seed, kill_final=True):
        """6 shards, fan-in 2: level-1 runs (3) and level-2 runs (2) complete in merge_work, killed before the final pass."""
        d = td / f'{name}_src'
        E.small(d, '--shards', 6, '--test-graphs', 3, points=16, seed=seed)
        E.run_all(d)
        ref = td / f'{name}_ref'
        shutil.copytree(d, ref)
        U.cli(prod, 'merge', ref, '--serial')

        class Killed(BaseException):
            pass
        real_final = prod._final_pass

        def kill(*a, **k):
            raise Killed()
        base = td / f'{name}_cut'
        shutil.copytree(d, base)
        with mock.patch.object(prod, '_final_pass', side_effect=kill):
            try:
                U.cli(prod, 'merge', base, '--fan-in', 2, '--jobs', 1)
                raise AssertionError('not interrupted')
            except Killed:
                pass
        return d, ref, base

    def same_as_ref(c, ref, d):
        for g in U.manifest(d)['groups']:
            for t in ('merged.json', 'graph_replicates.csv', 'graph_tails.csv', 'graph_costs.csv'):
                if (c / 'groups' / g['name'] / t).read_bytes() != (ref / 'groups' / g['name'] / t).read_bytes():
                    return False
        return True

    def o01():
        d, ref, base = interrupted_campaign('o01', U.SEED + 501)
        runs = sorted((base / 'merge_work').glob('*.run'))
        grp = runs[0].name.split('.')[0]
        mine = sorted(r for r in runs if r.name.startswith(grp + '.'))
        lv1 = [r for r in mine if '.p1.' in r.name]
        lv2 = [r for r in mine if '.p2.' in r.name]
        assert len(lv1) >= 2 and lv2, [r.name for r in mine]
        out = {'group': grp, 'level1': len(lv1), 'level2': len(lv2)}

        def body(p):
            ls = p.read_text().splitlines(keepends=True)
            assert ls[-1] == '#end\n'
            return ls[:-1]

        def write(p, lines):
            p.write_text(''.join(lines) + '#end\n')

        def case(label, edit):
            c = td / f'o01_{label}'
            shutil.copytree(base, c)
            touched = edit(c / 'merge_work')
            r = U.cli(prod, 'merge', c, '--fan-in', 2, '--jobs', 1)
            nreb = sum(1 for t in touched if t in r.stderr)
            ok = same_as_ref(c, ref, d) and nreb == len(touched) and 'fails verification' in r.stderr
            out[label] = dict(rebuilt_reported=nreb, touched=len(touched), equal_to_serial=same_as_ref(c, ref, d))
            if not ok:
                raise AssertionError(f'{label}: {out[label]} stderr {r.stderr[-500:]}')

        # (a) the value fields of two rows exchanged ACROSS two level-1 runs: keys, order and row counts all kept
        def swap_across(w):
            a, b = w / lv1[0].name, w / lv1[1].name
            la, lb = body(a), body(b)
            fa, fb = la[0].split('\t'), lb[0].split('\t')
            fa[3:], fb[3:] = fb[3:], fa[3:]
            assert fa[3:] != fb[3:]
            la[0], lb[0] = '\t'.join(fa), '\t'.join(fb)
            write(a, la)
            write(b, lb)
            return [a.name, b.name]
        case('swap_values_across_runs', swap_across)

        # (b) the same digit edit in a level-1 run AND in the level-2 run built from it (a consistent forgery)
        def consistent(w):
            a = w / lv1[0].name
            la = body(a)
            line = la[0]
            i = max(j for j, ch in enumerate(line) if ch.isdigit())
            new = line[:i] + str((int(line[i]) + 1) % 10) + line[i + 1:]
            la[0] = new
            write(a, la)
            hit = []
            for p in lv2:
                q = w / p.name
                lq = body(q)
                if line in lq:
                    lq[lq.index(line)] = new
                    write(q, lq)
                    hit.append(q.name)
            assert hit, 'the edited row is in no level-2 run'
            return [a.name] + hit
        case('consistent_edit_level1_and_level2', consistent)

        # (c) a level-2 run replaced by another level-2 run's bytes (complete, sorted, wrong rows)
        def replaced(w):
            if len(lv2) < 2:
                q = w / lv2[0].name
                write(q, body(q)[:-1])
                return [q.name]
            (w / lv2[0].name).write_bytes((w / lv2[1].name).read_bytes())
            return [lv2[0].name]
        case('level2_run_replaced_by_sibling', replaced)

        # (d) CRLF line ends in a run (same text, other bytes)
        def crlf(w):
            q = w / lv1[0].name
            q.write_bytes(q.read_bytes().replace(b'\n', b'\r\n', 1))
            return [q.name]
        case('crlf_in_one_line', crlf)
        return out
    probe('O01_cached_run_forgeries', o01)

    # ------------------------------------------------------------------ O02: phase 1 memory, the verifier's own measurement
    def o02():
        import tracemalloc
        res = {}
        for pts in (64, 512):
            d = td / f'o02_{pts}'
            E.plan(d, '--pilot', '--points', pts, '--replicates', 2, '--test-graphs', 3, '--bootstrap-chunk', 1, '--shards', 1,
                   '--checkpoint-tasks', 64, seed=U.SEED + 600 + pts)
            m = U.manifest(d)
            j = max(m['jobs'], key=lambda j: j['tasks'])
            E.run(d, j['id'])
            mh = hashlib.sha256((d / 'manifest.json').read_bytes()).hexdigest()
            prod._merge_init(str(d), mh)
            out = td / f'o02_{pts}.run'
            tracemalloc.start()
            s = prod._phase1(j['id'], str(out), 16, prod.merge_key())
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            res[pts] = dict(tasks=j['tasks'], blocks=s['blocks'], rows=s['rows'], traced_peak=peak)
        lo, hi = res[64], res[512]
        growth = hi['traced_peak'] - lo['traced_peak']
        per_row = growth / max(1, hi['rows'] - lo['rows'])
        res['growth_bytes'] = growth
        res['growth_bytes_per_extra_row'] = per_row
        if hi['rows'] < 6 * lo['rows'] or per_row > 50:
            raise AssertionError(f'phase-1 memory grows with the shard: {res}')
        return res
    probe('O02_phase1_traced_memory_flat_in_rows', o02)

    # ------------------------------------------------------------------ O05/O04: effective options edge cases
    def o05():
        ss = M.ss
        scr = td / 'eff.sh'
        out = {}
        cases = {
            'exclusive_mode_value': ('#!/bin/bash\n#SBATCH --exclusive=user\n\necho\n', [], lambda e: e.get('exclusive') == 'user'),
            'directive_after_blank_and_comment': ('#!/bin/bash\n\n# note\n#SBATCH --exclusive\nset -e\n', [], lambda e: e.get('exclusive') is True),
            'directive_after_command_ignored': ('#!/bin/bash\nset -e\n#SBATCH --exclusive\n', [], lambda e: 'exclusive' not in e),
            'short_partition_glued': ('#!/bin/bash\n#SBATCH -pdirq\n', ['-p', 'cliq'], lambda e: e.get('partition') == 'cliq'),
        }
        for k, (text, cli, want) in cases.items():
            scr.write_text(text)
            eff = ss.effective_options([*cli, str(scr)], {})
            out[k] = eff
            if not want(eff):
                raise AssertionError(f'{k}: {eff}')
        # an option the reader does not know refuses (no option escapes the checks)
        scr.write_text('#!/bin/bash\n#SBATCH --gpus=1\n')
        try:
            ss.effective_options([str(scr)], {})
            raise AssertionError('an unknown directive was accepted')
        except ss.Refuse as r:
            out['unknown_directive'] = dict(code=r.code)
            assert r.code == 64
        # the real scripts: no exclusive directive anywhere in slurm/ that a lane or merge submits
        for s in ('lane_worker.sh', 'merge.sh', 'run_array.sh'):
            eff = ss.effective_options([str(pkg / 'slurm' / s)], {})
            out[s] = eff
            if eff.get('exclusive'):
                raise AssertionError(f'{s} carries --exclusive')
        return out
    probe('O05_effective_options_edge_cases', o05)

    # ------------------------------------------------------------------ O06: more incomplete-accounting shapes
    def o06():
        acc = M.acc
        recs, bad = acc.parse_sacct('1|1|10|8|cn1|COMPLETED|defq\n\n1|1|10|8|cn1|COMPLETED\n2|2|-5|8|cn1|FAILED|defq\n3|3|10|x|cn1|FAILED|defq\n')
        out = dict(parsed=len(recs), malformed=len(bad))
        assert len(recs) == 1 and len(bad) == 3, (recs, bad)
        # array spec with a throttle and ranges; a pending range record covering a sub-range; an element seen only in
        # the checkpoints' need map but not in the ledger's spec
        assert acc.array_elements('0-3,7%2') == [0, 1, 2, 3, 7] and acc.array_elements('x') is None
        run = td / 'o06'
        run.mkdir()
        (run / 'submissions.jsonl').write_text(json.dumps({'schema': 'c8-d2-ledger-1', 'jobid': '900', 'role': 'array', 'array': '0-3'}) + '\n'
                                               + json.dumps({'schema': 'c8-d2-ledger-1', 'jobid': '901', 'role': 'lane'}) + '\n'
                                               + json.dumps({'schema': 'c8-d2-ledger-1', 'jobid': '901', 'role': 'lane', 'type': 'attempt', 'restart_count': '2'}) + '\n')
        known = M.ledger.jobs(run)
        r1, _ = acc.parse_sacct('910|900_0|5|8|n|COMPLETED|q\n900|900_[1-3]|0|0|None|PENDING|q\n901|901|5|8|n|COMPLETED|q\n901|901|5|8|n|NODE_FAIL|q\n')
        why = acc.coverage(run, known, r1, {})
        out['ledger_attempt_restart2_with_two_records'] = why
        assert any('job 901: 2 sacct record(s), 3 attempt(s)' in w for w in why), why
        r2, _ = acc.parse_sacct('910|900_0|5|8|n|COMPLETED|q\n900|900_[1-3]|0|0|None|PENDING|q\n' + '901|901|5|8|n|COMPLETED|q\n' * 3)
        assert acc.coverage(run, known, r2, {}) == [], acc.coverage(run, known, r2, {})
        why = acc.coverage(run, known, r2, {('900', 5): 1})
        out['checkpoint_element_outside_spec'] = why
        assert any('element 5' in w for w in why), why
        why = acc.coverage(run, known, r2, {('900', 2): 2})
        out['requeued_array_element'] = why
        assert any('array job 900 element 2' in w for w in why), why
        return out
    probe('O06_accounting_coverage_edge_cases', o06)

    # ------------------------------------------------------------------ O09: a model of another campaign, and a corrupt file
    def o09():
        mcm = M.mcm
        f = td / 'cm.json'
        doc = {'schema': 'c8-d2-cost-model-1', 'keys': 1, 'derived_utc': 'x', 'note': 'a', 'seconds_per_point': {'a:free:3:1': 1e-6}}
        assert mcm.publish_model(f, doc) == 'written'
        out = {'reuse_same_but_note': mcm.publish_model(f, {**doc, 'note': 'b', 'derived_utc': 'y'}, reuse=True)}
        for label, other in (('value', {**doc, 'seconds_per_point': {'a:free:3:1': 2e-6}}), ('extra_key', {**doc, 'extra': 1})):
            try:
                mcm.publish_model(f, other, reuse=True)
                raise AssertionError(f'{label}: accepted')
            except ValueError as e:
                out[label] = str(e)[:120]
        try:
            mcm.publish_model(f, doc, reuse=False)
            raise AssertionError('no-clobber broken')
        except (FileExistsError, ValueError, OSError) as e:
            out['no_reuse_refuses'] = type(e).__name__
        f.write_text('{not json')
        try:
            mcm.publish_model(f, doc, reuse=True)
            raise AssertionError('corrupt model accepted')
        except ValueError as e:
            out['corrupt'] = str(e)[:80]
        return out
    probe('O09_reuse_identical_edge_cases', o09)

    # ------------------------------------------------------------------ O10: what the identity can and cannot catch
    def o10():
        sys.path.insert(0, str(pkg / 'tests'))
        import verify_result as vr
        import assemble as asm
        import numpy as np
        from assembly_checks import synthetic_ar
        import combine
        b1 = dict(label='x', design_sha256='d' * 64, inputs_manifest_sha256='i' * 64, numerics='exact', rates_identity='default', seeds=list(range(24)),
                  ar=synthetic_ar(np.random.default_rng(7), R=6))
        b2 = dict(b1, label='y', seeds=list(range(100, 124)), ar=synthetic_ar(np.random.default_rng(8), R=6))
        fin = json.loads(json.dumps(combine.combine_batches([b1, b2], planned=2, bootstrap=0)))
        out = {'untouched': vr.verify(fin)}
        assert out['untouched'] == []
        t = copy.deepcopy(fin)
        t['batches']['per_batch'][0]['sampling_se'] *= 2
        out['per_batch_se_changed'] = vr.verify(t)[:2]
        assert out['per_batch_se_changed'], 'a per-batch SE change was accepted'
        t = copy.deepcopy(fin)
        t['batches']['planned'] = 3
        out['planned_changed'] = vr.verify(t)[:2]
        assert out['planned_changed'], 'planned 3 with final true accepted'
        t = copy.deepcopy(fin)
        t['batches']['per_batch'].append(copy.deepcopy(t['batches']['per_batch'][0]))
        out['duplicated_batch'] = vr.verify(t)[:2]
        assert out['duplicated_batch']
        # a coordinated edit of power_free_se and the cross covariance that keeps the identity: documented as not
        # detectable (no statistics stored to recompute power_free_se); recorded, not a failure of the fix
        n = fin['order']
        t = copy.deepcopy(fin)
        d = 0.01 * t['power_free_se'] ** 2
        t['power_free_se'] = math.sqrt(t['power_free_se'] ** 2 + 2 * d)
        t['power_free_correction_covariance'] -= d
        out['coordinated_pfse_and_cross_keep_identity'] = 'accepted (documented limit)' if not vr.verify(t) else vr.verify(t)[:2]
        return out
    probe('O10_combination_and_identity_edges', o10)

probe_names = list(R)
R['all_held'] = all(v['held'] for k, v in R.items() if isinstance(v, dict) and 'held' in v)
OUT.write_text(json.dumps(R, indent=1, default=str) + '\n')
print('ALL HELD' if R['all_held'] else 'SOME BROKEN')
