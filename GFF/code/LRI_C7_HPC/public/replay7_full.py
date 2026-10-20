#!/usr/bin/env python3
"""Public replay of C7(1), Tier 2 (`make -f public.mk replay-full`): rerun the production combination.

Runs the package's own tools/combine.py (verbatim; the code of commit 7320afc that produced the published
C7_final.json on 2026-09-28) on the hosted merged records of the 399 batches and the direct primitive campaign,
then compares its two outputs with ../../results/C7_1/{C7_final.json, combined_assembly.json}.

Expected layout of the hosted data (see DATA.md; built on Expanse by public/make_data_archive.py):
  <data>/c7_hpc/MANIFEST.sha256                       sha256 of every file below
  <data>/c7_hpc/batches/bNNN/{production.json, assembly.json, full_affine_assembly.json, C7_result.json}
  <data>/c7_hpc/batches/bNNN/<campaign>/{manifest.json, merged/audit.json, merged/N*.json}     (24 campaigns)
  <data>/c7_hpc/primitive/P1/{manifest.json, merged/audit.json, merged/N0.json}

Two substitutions, made here and nowhere in the shipped code:
1. campaign.verify_campaign is replaced by light_verify(): the same checks of the manifest, the merge audit, the
   merged-output SHA-256 values and the merged headers as the production verifier, but WITHOUT re-validating the
   checkpoint and task files, which are not hosted (their SHA-256 values stay listed in every merged/audit.json). In their place the audit's checkpoint list must equal, name for name, the list implied by the
   manifest's shards, checkpoint_tasks and degrees. The published C7_final.json records the SHA-256 of every merged
   stream, and this script checks every hosted stream against it, so the chain from the git records to the data is
   closed.
2. The per-batch input snapshots (batches/bNNN/inputs/, about 20 MB each) are not hosted. combine.py reads only
   inputs/L7_coord.txt (the primitive-sector guard); it is rebuilt from reference/inputs/L7_coord.txt, checked against
   the SHA-256 recorded in every L7 campaign manifest and in C7_final.json, and hard-linked into each batch (a real file
   in b001, so that the recorded relative path is reproduced).
The work tree is a hard-link copy (fallback: copy) of <data>/c7_hpc under --work, so that combine.py writes the same
relative paths as in production (../../batches/...). Nothing outside --work is written.

Comparison: byte identity of both outputs is expected with the production software (Python 3.11, NumPy of the
Expanse venv). Otherwise the JSON trees are compared: strings, integers and structure exactly, floats to 1e-12
relative (absolute 1e-12 x the largest entry of the same array for near-zero entries; for the two fields that
tools/assemble.py forms as a difference of nearly equal numbers, applied_zero_pole_control_C7 = raw_uncontrolled_C7 -
C7_full and lower_order_checks[].difference_over_sampling_se = (value - reference) / sampling_se, 1e-12 of their inputs
carried through that difference); bootstrap_se, which depends on NumPy's Generator stream, to 1e-12, else WARN within
5%. Exit 1 on any FAIL. On symmetry AMD (EPYC 8534P, NumPy 1.24.3) combined_assembly.json is byte-identical and
C7_final.json differs only in the last bits (C7_full by 1 ulp; the two difference fields by 1.6e-12 and 2.7e-12 of
themselves, 4e-16 of their inputs).

Runtime: about 5-7 min on one core, < 2 GB RAM, about 2 GB of disk under --work (Expanse job 54901438 on 2026-10-13:
409 s; symmetry 2026-10-14: 315 s). See public/slurm/archive_and_replay.sbatch for the Expanse archive build.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, shutil, sys, time
from pathlib import Path

sys.dont_write_bytecode = True
PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / 'tools'))
import campaign, assemble, combine  # noqa: E402  (the production modules, verbatim)

EXE_SHA = '33bab738a258f80561f6bb980ec6fa1f0416879b4132eff77276433eeee5518c'
P1_SEED = 3929792552365635731
LIGHT = {'campaigns': 0, 'checkpoints_listed': 0}
ROWS: list[dict] = []


def add(name, status, got='', ref='', note=''):
    ROWS.append({'check': name, 'status': status, 'got': str(got)[:120], 'ref': str(ref)[:120], 'note': note})
    print(f'{status:<6} {name}: {str(got)[:80]} {("| " + str(ref)[:80]) if ref != "" else ""} {note}', flush=True)


def light_verify(directory: Path) -> dict:
    """campaign.verify_campaign (HEAD = 7320afc) without re-reading checkpoints and task files; every other check is kept."""
    directory = Path(directory).resolve(); mp = directory / 'manifest.json'; m = json.loads(mp.read_text()); mh = campaign.digest(mp)
    ap = directory / 'merged' / 'audit.json'
    if not ap.is_file():
        raise FileNotFoundError('campaign not merged: ' + str(directory))
    audit = json.loads(ap.read_text())
    if audit.get('manifest_sha256') != mh or audit.get('complete') is not True:
        raise ValueError('audit does not match the manifest or is incomplete: ' + str(directory))
    if audit.get('work_units_per_degree') != m['total_work_units']:
        raise ValueError('audit work-unit count mismatch: ' + str(directory))
    if sum(s['work_units'] for s in m['shards']) != m['total_work_units']:
        raise ValueError('manifest shards do not add up to the planned work units: ' + str(directory))
    want = [f"checkpoints/{campaign.identity(s['id'], part, N)}.json" for s in m['shards']
            for part in range(math.ceil(s['work_units'] / m['checkpoint_tasks'])) for N in m['degrees']]
    got = [x.get('file') for x in audit.get('sources', [])]
    if got != want or not all(isinstance(x.get('sha256'), str) and len(x['sha256']) == 64 for x in audit['sources']):
        raise ValueError('audit checkpoint list differs from the one the manifest implies: ' + str(directory))
    outs = [{'file': f'merged/N{N}.json', 'sha256': campaign.digest(directory / 'merged' / f'N{N}.json')} for N in m['degrees']]
    if outs != audit.get('outputs'):
        raise ValueError('merged outputs differ from the audit: ' + str(directory))
    for N in m['degrees']:  # the merged header must describe exactly the planned streams (as in the production verifier)
        o = json.loads((directory / 'merged' / f'N{N}.json').read_text())
        if (o.get('L'), o.get('N'), o.get('replicates'), o.get('seed'), o.get('counts'), o.get('manifest_sha256'), o.get('complete'),
                len(o.get('batches', []))) != (m['L'], N, m['replicates'], m['seed'], m['counts'], mh, True, m['replicates']):
            raise ValueError(f'merged output N{N} does not match its manifest: ' + str(directory))
    LIGHT['campaigns'] += 1; LIGHT['checkpoints_listed'] += len(audit['sources'])
    return {'manifest': m, 'manifest_sha256': mh, 'audit': audit}


def link_tree(src: Path, dst: Path) -> int:
    n = 0
    for root, dirs, files in os.walk(src):
        r = Path(root); t = dst / r.relative_to(src); t.mkdir(parents=True, exist_ok=True)
        for f in files:
            try:
                os.link(r / f, t / f)
            except OSError:
                shutil.copy2(r / f, t / f)
            n += 1
    return n


def check_manifest(tree: Path) -> None:
    mf = tree / 'MANIFEST.sha256'
    if not mf.is_file():
        add('hosted MANIFEST.sha256', 'WARN', 'absent', '', 'archive file list not verified'); return
    lines = [l.split(None, 1) for l in mf.read_text().splitlines() if l.strip()]
    bad = [p.strip() for h, p in lines if not (tree / p.strip()).is_file() or campaign.digest(tree / p.strip()) != h]
    listed = {p.strip() for _, p in lines}
    extra = [str(p.relative_to(tree)) for p in tree.rglob('*') if p.is_file() and p.name != 'MANIFEST.sha256' and str(p.relative_to(tree)) not in listed]
    add('hosted MANIFEST.sha256', 'FAIL' if bad else 'PASS', f'{len(lines) - len(bad)} OK, {len(extra)} unlisted', f'{len(lines)} lines', '; '.join(bad[:5]))


def compare(new: Path, ref: Path, name: str) -> None:
    import numpy as np
    if new.read_bytes() == ref.read_bytes():
        add(f'{name}: byte-identical to the published file', 'PASS', campaign.digest(new)[:16], campaign.digest(ref)[:16]); return
    a, b = json.loads(new.read_text()), json.loads(ref.read_text()); issues = []; boot = []

    def derived(at, parent):
        """Tolerance of the two fields that tools/assemble.py computes as a difference of nearly equal numbers: 1e-12 of
        their inputs, propagated (1e-12 of the field itself would be far below the inputs' own rounding)."""
        if at == '.applied_zero_pole_control_C7':        # raw_uncontrolled_C7 - C7_full
            return 1e-12 * (abs(b['raw_uncontrolled_C7']) + abs(b['C7_full']))
        if at.endswith('.difference_over_sampling_se') and isinstance(parent, dict) and parent.get('sampling_se'):
            se = parent['sampling_se']                   # (value - reference) / sampling_se
            return 1e-12 * (abs(parent['value']) + abs(parent['reference'])) / se + 1e-12 * abs(parent['difference_over_sampling_se'])
        return 0.0

    def walk(x, y, at, scale, parent=None):
        if isinstance(x, dict) and isinstance(y, dict):
            if set(x) != set(y): issues.append((at, 'keys differ'))
            for k in set(x) & set(y): walk(x[k], y[k], f'{at}.{k}', None, y)
        elif isinstance(x, list) and isinstance(y, list):
            if len(x) != len(y): issues.append((at, 'length differs')); return
            nums = [v for v in y if isinstance(v, (int, float)) and not isinstance(v, bool)]
            s = max([abs(v) for v in nums], default=0.0)
            for p, q in zip(x, y): walk(p, q, at, s)
        elif isinstance(x, float) or isinstance(y, float):
            tol = max(1e-12 * max(abs(x), abs(y)), 1e-12 * (scale or 0.0), derived(at, parent))
            if abs(x - y) > tol:
                (boot if at.endswith('bootstrap_se') else issues).append((at, x, y))
        elif x != y:
            issues.append((at, x, y))
    walk(a, b, '', None)
    if boot and not issues:
        x, y = boot[0][1], boot[0][2]
        add(f'{name}: equal to 1e-12 except bootstrap_se', 'WARN' if abs(x - y) <= 0.05 * abs(y) else 'FAIL', x, y,
            f'NumPy {np.__version__}: Generator stream differs from production')
    else:
        add(f'{name}: equal to 1e-12 relative (not byte-identical)', 'FAIL' if issues else 'PASS', len(issues), 0,
            '; '.join(str(i)[:100] for i in issues[:5]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--data', type=Path, default=Path('../../data/C7_1'), help='folder holding c7_hpc/ (hosted archive, unpacked)')
    ap.add_argument('--results', type=Path, default=Path('../../results/C7_1'))
    ap.add_argument('--work', type=Path, default=Path('.work'))
    ap.add_argument('--jobs', type=int, default=1, help='parallel light verifications (fork start method; output identical)')
    a = ap.parse_args()
    data = (a.data / 'c7_hpc').resolve(); res = a.results.resolve(); work = a.work.resolve(); tree = work / 'c7_hpc'
    if not (data / 'batches').is_dir():
        print(f'hosted records not found under {data}; run `make -f public.mk fetch-data` first (see DATA.md)', file=sys.stderr); return 2
    t0 = time.time()
    fin = json.loads((res / 'C7_final.json').read_text()); ca = json.loads((res / 'combined_assembly.json').read_text())
    labels = [b['label'] for b in ca['batches']]
    check_manifest(data)
    # every merged stream named by the published result, by path and SHA-256
    bad = []
    for s in fin['sources']:
        for k in ('path', 'subtract'):
            if k in s:
                p = data / s[k].replace('../../', '', 1)
                if not p.is_file() or campaign.digest(p) != s[k + '_sha256']:
                    bad.append(s[k])
    add('hosted merged streams = SHA-256 recorded in C7_final.json', 'FAIL' if bad else 'PASS',
        f'{sum(("subtract" in s) + 1 for s in fin["sources"]) - len(bad)} OK', '', '; '.join(bad[:5]))
    if tree.exists():
        shutil.rmtree(tree)
    n = link_tree(data, tree); print(f'work tree: {n} files in {time.time() - t0:.0f} s: {tree}', flush=True)
    # inputs/L7_coord.txt of every batch, rebuilt from the shipped reference and checked against the manifests
    inv = work / 'inputs_shared' / 'L7_coord.txt'; inv.parent.mkdir(parents=True, exist_ok=True)
    if inv.exists():
        inv.unlink()
    shutil.copyfile(PKG / 'reference/inputs/L7_coord.txt', inv); h = campaign.digest(inv)
    rec = set(); exes = set(); dsh = set(); seen_design = set()
    for l in labels:
        b = tree / 'batches' / l; prod = json.loads((b / 'production.json').read_text())
        exes.add(prod['executable_sha256']); dsh.add(prod.get('design_sha256')); seen_design.add(json.dumps(prod.get('design'), sort_keys=True))
        for c in prod['campaigns']:
            m = json.loads((b / c / 'manifest.json').read_text())
            if m['L'] == 7:
                rec.add(m['input_sha256'].get('L7_coord.txt'))
        (b / 'inputs').mkdir(exist_ok=True); t = b / 'inputs' / 'L7_coord.txt'
        if not t.exists():
            try:
                os.link(inv, t)
            except OSError:
                shutil.copyfile(inv, t)
        if not (b / 'full_affine_assembly.json').exists():
            shutil.copyfile(PKG / 'reference/verification/full_affine_assembly.json', b / 'full_affine_assembly.json')
    add('L7_coord.txt rebuilt from reference = every L7 manifest and C7_final primitive_guard', 'PASS' if rec == {h} and h == fin['primitive_guard']['sha256'] else 'FAIL',
        h[:16], sorted(x[:16] for x in rec if x))
    add('one executable for all batches (production.json)', 'PASS' if exes == {EXE_SHA} else 'FAIL', sorted(x[:16] for x in exes), EXE_SHA[:16])
    dsha = campaign.digest(res / 'design_v1.json')
    add('one frozen design for all batches = results/C7_1/design_v1.json', 'PASS' if dsh == {dsha} and
        seen_design == {json.dumps(json.loads((res / 'design_v1.json').read_text()), sort_keys=True)} else 'FAIL', sorted(x[:16] for x in dsh if x), dsha[:16])
    pm = json.loads((tree / 'primitive/P1/manifest.json').read_text())
    add('primitive campaign P1: seed, L7 primitive selection, 64 replicates, 2^23 points per active class',
        'PASS' if (pm['seed'], pm['L'], pm.get('selection'), pm['replicates'], sorted(set(c for c in pm['counts'] if c))) == (P1_SEED, 7, 'primitive', 64, [2 ** 23])
        and sum(1 for c in pm['counts'] if c) == 44 else 'FAIL', (pm['seed'], pm.get('selection'), pm['replicates'], sum(1 for c in pm['counts'] if c)))
    # substitution 1, in every module that imported the verifier by name
    for mod in (campaign, assemble, combine):
        if hasattr(mod, 'verify_campaign'):
            mod.verify_campaign = light_verify
    if a.jobs > 1:
        import multiprocessing
        multiprocessing.set_start_method('fork', force=True)  # children inherit the substitution
    out_rel = Path('replay/final')  # two levels below c7_hpc, as in production (paths ../../batches/...)
    os.chdir(tree)
    if out_rel.exists():
        shutil.rmtree(out_rel)
    sys.argv = ['combine.py', *[f'batches/{l}' for l in labels], '--primitive', 'primitive/P1', '--output', str(out_rel), '--jobs', str(a.jobs)]
    t1 = time.time()
    try:
        combine.main(); ok = (out_rel / 'C7_final.json').is_file()
    except (OSError, ValueError, ArithmeticError) as e:
        print('combine failed:', e, file=sys.stderr); ok = False
    add('tools/combine.py on the hosted records', 'PASS' if ok else 'FAIL', f'{time.time() - t1:.0f} s',
        '', f'{LIGHT["campaigns"]} light campaign verifications, {LIGHT["checkpoints_listed"]} checkpoints listed in audits (not re-read)')
    if ok:
        compare(out_rel / 'combined_assembly.json', res / 'combined_assembly.json', 'combined_assembly.json')
        compare(out_rel / 'C7_final.json', res / 'C7_final.json', 'C7_final.json')
        new = json.loads((out_rel / 'C7_final.json').read_text())
        for k, q in (('C7_full', -322549.88881298894), ('sampling_se', 10.087912951713953), ('bootstrap_se', 10.111393886841418)):
            add(f'{k} (Tier 2 recomputation)', 'PASS' if abs(new[k] - q) <= (0.05 if k == 'bootstrap_se' else 1e-12) * abs(q) else 'FAIL', new[k], q)
        add('half splits (recomputed from the replicate streams)', 'PASS' if all(abs(x[7] - y[7]) <= 1e-12 * abs(y[7]) for x, y in zip(new['half_splits'], fin['half_splits'])) else 'FAIL',
            [round(x[7], 2) for x in new['half_splits']], [round(y[7], 2) for y in fin['half_splits']])
        per = {x['label']: x for x in new['batches']['per_batch']}; diffs = []; present = 0
        for l in labels:  # each batch's own C7_result.json (production.py merge, commit 3213ce0) against combine's re-assembly
            p = tree / 'batches' / l / 'C7_result.json'
            if p.is_file():
                present += 1; r = json.loads(p.read_text())
                if abs(r['C7_full'] - per[l]['C7_full']) > 1e-12 * abs(r['C7_full']) or abs(r['sampling_se'] - per[l]['sampling_se']) > 1e-12 * r['sampling_se']:
                    diffs.append(l)
        add('per-batch results = each batch C7_result.json', ('FAIL' if diffs else 'PASS') if present else 'SKIP',
            f'{present - len(diffs)} of {present} present equal', len(labels), ' '.join(diffs[:10]))
    (work / 'replay7_full.json').write_text(json.dumps({'rows': ROWS, 'seconds': round(time.time() - t0, 1), **LIGHT}, indent=1) + '\n')
    nf = sum(r['status'] == 'FAIL' for r in ROWS)
    print(f'C7(1) Tier 2 replay: {len(ROWS)} checks, {nf} FAIL, {time.time() - t0:.0f} s; report {work / "replay7_full.json"}')
    return 1 if nf else 0


if __name__ == '__main__':
    sys.exit(main())
