"""The input gate through the real `production.py plan` (A-IN-4 for L <= 7, A-ASM-1(b)); a Stage-3a obligation.

Stage 2a (G2a) checks A-IN-4 and A-ASM-1(b) on prepare_inputs.plan_inputs() and verify(), because tools/production.py
`plan` is still the C7(3) planner and its prepare() refuses every request ("transitional" below). Stage 3a wires
plan_inputs into `plan` ("wired"). From then on tests/check_inputs.py and tests/check_vendored.py (b) repeat their
checks through `production.py plan` in scratch packages. These runs are G3a evidence (A-ASM-1 Mac at G3a; A-IN-4 at
L <= 7). Recorded in CHANGELOG.md (Stage 2a repair rounds 1 and 2).

The fixed input state (repair round 2). The scenarios never run on the live inputs as they are: their state moves at
Stage 2b (l7_complete true, the L8 packs pinned; on the Mac pinned but absent), and nothing orders Stage 2b after the
Stage-3a wiring. fixed_inputs() first puts the scratch package's inputs/ into one fixed state, whatever the live stage:
the live manifest with l7_complete and l8_present false and no pin, count or inventory row of a loop above 7 (an L8
pack in the scratch package is removed), the kernel total recounted and the inventory repinned when rows were dropped.
Every other pin and file stays the live one (the L <= 7 packs keep their live bytes and pins). At Stage 2a the live
inputs are already in that state and nothing is rewritten. A precondition check ("fixed-state") runs the scratch
package's own gate (tools/prepare_inputs.py gate, a non-test request) on it: the gate must pass, skip nothing and make
the plan test-only because of l7_complete. So the scenarios and their expectations hold whether Stage 2b lands before
or after the Stage-3a wiring, on Expanse with the L8 packs present and on the Mac with C8_ALLOW_NO_L8=1, which the
runner passes through when the caller sets it. If a later verify() refuses the fixed state, the precondition check
fails naming the gate's message, and fixed_inputs() is what to adapt.

Scenarios (run_plan_gate), each a NON-test plan request into a fresh campaign path, after the precondition:
  untouched       the fixed state untouched: accepted, and the campaign's manifest records test_only true
                  (l7_complete: false makes the plan test-only although no test flag was given);
  pinned-input    a one-byte change to inputs/packs/free_L7.pack (the L <= 7 analogue of free_L8.pack): refused with
                  the gate's "Checksum mismatch" naming the file;
  vendored        a one-byte change to vendor/c8_assembly/order8_assembly.py: refused, the same way;
  foreign-inputs  C8_INPUTS naming a byte-identical copy of the inputs elsewhere: refused (a non-test plan reads only
                  the package inputs/).
On every refusal: no campaign directory, nothing beside the campaign path (no plan temporary directory), nothing in
the child's TMPDIR, and no file of the scratch package created, removed or changed (the flipped file restored).

Mode: transitional iff tools/production.py does not name plan_inputs (ast) and the untouched request is refused with
prepare()'s Stage-3a message; otherwise wired (a port that removed prepare() without calling the gate is wired, and
fails). Transitional: every scenario must be refused with that message, creating nothing. Wired: the expectations
above, with the ported plan's arguments from STAGE3A; while STAGE3A is None, wired mode fails, naming the obligation.
Every check carries its scenario name ('fixed-state', a scenario, or 'obligation'). check_inputs.py runs fake wired
planners (a correct one and four wrong ones) through the same runner as its self-test, and the correct one also on
simulated post-Stage-2b inputs (fake_stage2b_inputs: Expanse with the L8 packs, the Mac without them).
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True

# Stage 3a sets this when tools/production.py plan calls prepare_inputs.plan_inputs:
#   args           the arguments after `plan <campaign>` of a NON-test plan the ported planner accepts in the scratch
#                  package (no test flag: with l7_complete false the gate must make it test-only);
#   package_paths  package paths besides tools/, vendor/, cost_models/ and inputs/ that `plan` needs there (bin/,
#                  reference/inputs/, ...), copied from the checkout (hard links where possible);
#   prepare        (Stage 3a) a function (pkg, work) -> extra arguments, run once before the scenarios: it gives the
#                  scratch package its worker and writes the files the arguments name OUTSIDE the package (see
#                  stage3a_prepare);
#   test_only_key  the key path of the test-only flag in <campaign>/manifest.json (default ['test_only']).
STAGE3A = None   # set at the end of this file (Stage 3a)
TRANSITIONAL_ARGS = ['--seed', '1', '--points', '4', '--replicates', '2', '--threads', '2', '--checkpoint-tasks', '64']
TRANSITIONAL_MARK = 'ported to them in Stage 3a'   # prepare_inputs.prepare()'s refusal
OBLIGATION = ('tools/production.py plan calls prepare_inputs.plan_inputs (Stage 3a): set tests/plan_gate.STAGE3A '
              '(the ported plan\'s non-test arguments and package paths) so that check_inputs.py and check_vendored.py '
              '(b) run A-IN-4 and A-ASM-1(b) through `plan` on the fixed input state (CHANGELOG, Stage 2a repair '
              'rounds 1 and 2; G3a evidence)')
SCENARIOS = {
    'untouched': dict(what='the untouched fixed state (l7_complete: false), a non-test plan request',
                      expect='test-only'),
    'pinned-input': dict(what='a one-byte change to inputs/packs/free_L7.pack', flip='inputs/packs/free_L7.pack',
                         expect='refuse', needles=('Checksum mismatch', 'free_L7.pack')),
    'vendored': dict(what='a one-byte change to vendor/c8_assembly/order8_assembly.py',
                     flip='vendor/c8_assembly/order8_assembly.py', expect='refuse',
                     needles=('Checksum mismatch', 'order8_assembly.py')),
    'foreign-inputs': dict(what='a non-test plan with a foreign C8_INPUTS (a byte-identical copy elsewhere)',
                           foreign=True, expect='refuse', needles=('non-test plan reads only the package inputs',)),
}


FIXED_MAX_LOOP = 7                                    # the fixed state: loops 3..7, no L8 pin
PACK_RE = re.compile(r'^packs/[A-Za-z0-9]+_L([0-9]+)\.pack$')
# what the plan's children never inherit from the caller (C8_ALLOW_NO_L8 passes through: the Mac command sets it).
# C8_SITE too: the scratch campaigns live in node-local scratch, where D.7's Lustre file guard (C8_SITE=expanse, set by
# ~/c8d3/env.sh in every Expanse job) cannot run `lfs quota` and would refuse every plan (69) in J-VAL-1.
STRIP_ENV = ('C8_INPUTS', 'PYTHONPATH', 'PYTHONPYCACHEPREFIX', 'C8_SITE')


def _above(loop: str) -> bool:
    return isinstance(loop, str) and loop.isdigit() and int(loop) > FIXED_MAX_LOOP


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fixed_inputs(pkg: Path) -> dict:
    """Put the scratch package's inputs/ into the fixed state of the scenarios (see the module text) and return what
    changed. Files are replaced, never written through (scratch files may be hard links to the package's); nothing is
    rewritten when the inputs are already in that state (Stage 2a)."""
    if pkg.resolve() == ROOT.resolve():
        raise ValueError(f'{pkg}: plan_gate rewrites the inputs of a scratch package, never the checkout\'s')
    d = pkg / 'inputs'
    mp = d / 'manifest.json'
    m = json.loads(mp.read_bytes())
    rec = dict(dropped_pins=[], dropped_counts=[], dropped_inventory_rows=0, set_false=[], removed_files=[],
               inventory_repinned=False, manifest_rewritten=False)
    pins = m.get('sha256') if isinstance(m.get('sha256'), dict) else {}
    for rel in sorted(pins):
        mm = PACK_RE.match(rel)
        if mm and _above(mm.group(1)):
            del pins[rel]
            rec['dropped_pins'].append(rel)
    counts = m.get('counts') if isinstance(m.get('counts'), dict) else {}
    for sector in sorted(counts):
        per = counts[sector]
        for loop in sorted(per) if isinstance(per, dict) else ():
            if _above(loop):
                del per[loop]
                rec['dropped_counts'].append(f'{sector}:{loop}')
    if rec['dropped_counts'] and isinstance(m.get('kernels'), int):
        m['kernels'] = sum(int(n) for per in counts.values() if isinstance(per, dict) for n in per.values())
    for key in ('l7_complete', 'l8_present'):
        if m.get(key) is not False:
            m[key] = False
            rec['set_false'].append(key)
    ip = d / 'inventory.json'
    inv = json.loads(ip.read_bytes())
    for sector, per in (inv.items() if isinstance(inv, dict) else ()):
        for loop in [x for x in per if _above(x)] if isinstance(per, dict) else ():
            rec['dropped_inventory_rows'] += len(per[loop]) if isinstance(per[loop], list) else 1
            del per[loop]
    if rec['dropped_inventory_rows']:
        data = (json.dumps(inv, indent=1, allow_nan=False) + '\n').encode()
        _replace(ip, data)
        pins['inventory.json'] = _sha(data)
        rec['inventory_repinned'] = True
    for p in sorted((d / 'packs').glob('*')) if (d / 'packs').is_dir() else ():
        mm = PACK_RE.match(f'packs/{p.name}')
        if mm and _above(mm.group(1)) and f'packs/{p.name}' not in pins:
            p.unlink()
            rec['removed_files'].append(f'packs/{p.name}')
    if rec['dropped_pins'] or rec['dropped_counts'] or rec['set_false'] or rec['inventory_repinned']:
        _replace(mp, (json.dumps(m, indent=2, allow_nan=False) + '\n').encode())
        rec['manifest_rewritten'] = True
    return rec


def child_env(env: dict, tmp: Path) -> dict:
    child = {k: v for k, v in env.items() if k not in STRIP_ENV}
    child.update(PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(tmp))
    return child


def gate(pkg: Path, work: Path, name: str, env: dict, test=False) -> dict:
    """The scratch package's own input gate (tools/prepare_inputs.py gate), as the plan's children would run it."""
    base, tmp = work / name, work / f'{name}.TMPDIR'
    base.mkdir(parents=True)
    tmp.mkdir()
    r = subprocess.run([sys.executable, '-B', str(pkg / 'tools/prepare_inputs.py'), 'gate',
                        *(['--test-only'] if test else [])], capture_output=True, text=True,
                       env=child_env(env, tmp), cwd=str(base))
    try:
        out = json.loads(r.stdout)
    except ValueError:
        out = None
    return dict(returncode=r.returncode, result=out, stderr=r.stderr[-600:])


def _fixed_state_check(pkg: Path, work: Path, env: dict, rec: dict) -> dict:
    g = gate(pkg, work, 'fixed-state', env)
    out = g['result'] or {}
    reasons = out.get('test_only_reasons') or []
    ok = (g['returncode'] == 0 and out.get('status') == 'verified' and out.get('test_only') is True
          and not out.get('skipped') and any(x.startswith('l7_complete') for x in reasons))
    return dict(scenario='fixed-state', passed=ok,
                check=('fixed input state (l7_complete and l8_present false, no pin or row above L7, whatever the live '
                       'stage): the package\'s own gate passes it, skips nothing and makes a non-test plan test-only '
                       'for l7_complete'),
                detail=dict(fixed=rec, gate_returncode=g['returncode'], test_only=out.get('test_only'),
                            reasons=reasons, skipped=out.get('skipped'), stderr=g['stderr'] if not ok else ''))


def names_plan_inputs(pkg: Path) -> bool:
    """True if tools/production.py names plan_inputs anywhere in its code (a name, an attribute or an import)."""
    tree = ast.parse((pkg / 'tools/production.py').read_text())
    for n in ast.walk(tree):
        if (isinstance(n, ast.Name) and n.id == 'plan_inputs') or \
                (isinstance(n, ast.Attribute) and n.attr == 'plan_inputs') or \
                (isinstance(n, ast.alias) and n.name == 'plan_inputs'):
            return True
    return False


def tree_state(d: Path) -> dict:
    """Every entry under d: files by (size, mtime), directories and other entries by kind only (replacing a flipped
    file changes its directory's mtime)."""
    out = {}
    for p in sorted(d.rglob('*')):
        st = p.lstat()
        out[p.relative_to(d).as_posix()] = (st.st_size, st.st_mtime_ns) if p.is_file() and not p.is_symlink() else \
            ('dir' if p.is_dir() else 'other',)
    return out


def link_or_copy(src, dst) -> None:
    """copytree's copy_function: a hard link, or a copy when the destination is on another filesystem (Expanse: a
    package work copy on Lustre, the test's scratch on node-local disk)."""
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def _replace(p: Path, data: bytes) -> None:
    """Replace a file without writing through a hard link (scratch packs are linked to the package's)."""
    p.unlink()
    p.write_bytes(data)


LARGE = 64 << 20   # files above this size (the L8 packs) are flipped by flip_large, not read into memory


def flip_large(p: Path, aside: Path):
    """Replace p by a streamed copy with its middle byte flipped; the original (often a hard link of a store blob) is
    renamed to `aside` (same filesystem), never written. Returns the function that puts the original back (same inode,
    size and mtime)."""
    size = p.stat().st_size
    at = size // 2
    os.rename(p, aside)
    try:
        with aside.open('rb') as src, p.open('xb') as dst:
            left = at
            while left:
                chunk = src.read(min(1 << 24, left))
                dst.write(chunk)
                left -= len(chunk)
            dst.write(bytes([src.read(1)[0] ^ 1]))
            shutil.copyfileobj(src, dst, 1 << 24)
    except BaseException:
        p.unlink(missing_ok=True)
        os.rename(aside, p)
        raise

    def restore() -> None:
        p.unlink()
        os.rename(aside, p)
    return restore


def _get(m, keys):
    for k in keys:
        m = m.get(k) if isinstance(m, dict) else None
    return m


def _run(pkg: Path, work: Path, name: str, args: list, env: dict, spec: dict, mark_only: bool,
         key=('test_only',)) -> dict:
    base = work / name            # the campaign's parent and the child's cwd: empty before the run
    tmp = work / f'{name}.TMPDIR'  # the child's TMPDIR: empty before the run
    base.mkdir(parents=True)
    tmp.mkdir()
    camp = base / 'campaign'
    child = child_env(env, tmp)
    if spec.get('foreign'):
        other = work / f'{name}.foreign/inputs'
        shutil.copytree(pkg / 'inputs', other, copy_function=os.link)
        child['C8_INPUTS'] = str(other)
    flip = spec.get('flip')
    before = tree_state(pkg)
    orig = restore = None
    if flip:
        p = pkg / flip
        if p.stat().st_size > LARGE:
            restore = flip_large(p, work / f'{name}.aside')
        else:
            orig = p.read_bytes()
            b = bytearray(orig)
            b[len(b) // 2 if flip.startswith('inputs/') else 100] ^= 1
            _replace(p, bytes(b))
    try:
        r = subprocess.run([sys.executable, '-B', str(pkg / 'tools/production.py'), 'plan', str(camp), *args],
                           capture_output=True, text=True, env=child, cwd=str(base))
    finally:
        if restore is not None:
            restore()
        elif flip:
            _replace(pkg / flip, orig)
    after = tree_state(pkg)
    changed = sorted(set(before) ^ set(after)) + sorted(k for k in before if k in after and k != flip
                                                         and after[k] != before[k])
    if flip and flip in after and after[flip][0] != before[flip][0]:
        changed.append(flip)
    out = r.stdout + r.stderr
    created = sorted(x.name for x in base.iterdir())
    in_tmp = sorted(x.name for x in tmp.iterdir())
    nothing = not created and not in_tmp and not changed
    rec = dict(returncode=r.returncode, created=created, tmpdir=in_tmp, package_changed=changed[:10],
               tail=out[-500:])
    if mark_only:
        rec['ok'] = r.returncode != 0 and TRANSITIONAL_MARK in out and nothing
    elif spec['expect'] == 'refuse':
        rec['ok'] = r.returncode != 0 and all(x in out for x in spec['needles']) and nothing
    else:
        m = None
        try:
            m = json.loads((camp / 'manifest.json').read_bytes())
        except (OSError, ValueError):
            pass
        flag = _get(m, key) if m is not None else None
        rec.update(test_only=flag)
        rec['ok'] = r.returncode == 0 and flag is True
    return rec


def run_plan_gate(pkg: Path, work: Path, env: dict, scenarios=tuple(SCENARIOS), stage3a='module') -> dict:
    """Put pkg's inputs/ into the fixed state, check it with pkg's own gate, then run the scenarios through pkg's
    tools/production.py plan. pkg must be a scratch package (its inputs/ may be rewritten; never the checkout) and
    work an empty scratch directory outside pkg. Returns {mode, static_wired, fixed, checks: [{scenario, check,
    passed, detail}], note}."""
    s3 = STAGE3A if stage3a == 'module' else stage3a
    work.mkdir(parents=True, exist_ok=True)
    fixed = fixed_inputs(pkg)
    checks = [_fixed_state_check(pkg, work, env, fixed)]
    static = names_plan_inputs(pkg)
    probe = None
    if not static:
        probe = _run(pkg, work, 'mode-probe', TRANSITIONAL_ARGS, env, SCENARIOS['untouched'], mark_only=True)
    mode = 'transitional' if probe is not None and probe['ok'] else 'wired'
    out = dict(mode=mode, static_wired=static, fixed=fixed, checks=checks)
    if mode == 'transitional':
        for n in scenarios:
            spec = SCENARIOS[n]
            rec = _run(pkg, work, n, TRANSITIONAL_ARGS, env, spec, mark_only=True)
            checks.append(dict(scenario=n, passed=rec['ok'], detail=rec,
                               check=f'production.py plan [transitional]: {spec["what"]}: refused with prepare()\'s '
                                     'Stage-3a message (the unported C7(3) planner refuses every request); no campaign '
                                     'directory, nothing beside it or in TMPDIR, the scratch package unchanged'))
        return dict(out, note=('production.py plan is transitional (it does not call plan_inputs): A-IN-4 and '
                               'A-ASM-1(b) were checked on the gate itself; once Stage 3a wires the gate into plan, '
                               'these checks run the real expectations through `plan` on the fixed input state '
                               '(tests/plan_gate.py, G3a evidence)'))
    if s3 is None:
        checks.append(dict(scenario='obligation', check='production.py plan [wired]: the Stage-3a obligation',
                           passed=False, detail=dict(obligation=OBLIGATION, static_wired=static, probe=probe)))
        return dict(out, note=OBLIGATION)
    for rel in s3.get('package_paths', []):
        src, dst = ROOT / rel, pkg / rel
        if dst.exists() or not src.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, copy_function=link_or_copy)
        else:
            shutil.copy2(src, dst)
    extra = s3['prepare'](pkg, work / 'stage3a_prepare') if callable(s3.get('prepare')) else []
    for n in scenarios:
        spec = SCENARIOS[n]
        rec = _run(pkg, work, n, list(s3['args']) + list(extra), env, spec, mark_only=False,
                   key=tuple(s3.get('test_only_key', ['test_only'])))
        what = ('accepted as a test-only plan (manifest test_only true)' if spec['expect'] == 'test-only' else
                f'refused naming {spec["needles"][-1]}; no campaign directory, nothing beside it or in TMPDIR, the '
                'scratch package unchanged')
        checks.append(dict(scenario=n, check=f'production.py plan [wired]: {spec["what"]}: {what}', passed=rec['ok'],
                           detail=rec))
    return dict(out, note='production.py plan calls the input gate: A-IN-4 / A-ASM-1(b) checked through `plan` on the '
                          'fixed input state (G3a)')


def run_live_flip(pkg: Path, work: Path, env: dict, flip: str) -> dict:
    """Stage 2b, A-IN-4 on Expanse: on the LIVE inputs of a scratch package (not the fixed state: its L8 packs pinned
    and present), a one-byte change to `flip` (packs/free_L8.pack; flip_large for a large file), a NON-test request
    through the wired `production.py plan` with STAGE3A's arguments: refused naming the file, creating nothing. Returns
    _run's record with 'ok'."""
    s3 = STAGE3A
    work.mkdir(parents=True, exist_ok=True)
    for rel in s3.get('package_paths', []):
        src, dst = ROOT / rel, pkg / rel
        if dst.exists() or not src.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, copy_function=link_or_copy)
        else:
            shutil.copy2(src, dst)
    extra = s3['prepare'](pkg, work / 'stage3a_prepare') if callable(s3.get('prepare')) else []
    spec = dict(what=f'a one-byte change to {flip}', flip=flip, expect='refuse',
                needles=('Checksum mismatch', Path(flip).name))
    return _run(pkg, work, 'live-flip', list(s3['args']) + list(extra), env, spec, mark_only=False,
                key=tuple(s3.get('test_only_key', ['test_only'])))


# ---- fake wired planners for the runner's self-test (check_inputs.py) ---------------------------------------------
FAKE_HEAD = '''import argparse, json, sys, tempfile
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_inputs as pi
ap = argparse.ArgumentParser()
s = ap.add_subparsers(dest='command', required=True)
q = s.add_parser('plan')
q.add_argument('directory', type=Path)
q.add_argument('--test', action='store_true')
a = ap.parse_args()
out = a.directory.resolve()
'''
FAKE_BODY = {
    'correct': 'v = pi.plan_inputs(a.test)\nout.mkdir()\nt = v["test_only"]\n',
    'ignores-test-only': 'v = pi.plan_inputs(a.test)\nout.mkdir()\nt = a.test\n',
    'directory-first': 'out.mkdir()\nv = pi.plan_inputs(a.test)\nt = v["test_only"]\n',
    'tmpdir-first': 'tempfile.mkdtemp(prefix="plan_")\nv = pi.plan_inputs(a.test)\nout.mkdir()\nt = v["test_only"]\n',
    'no-gate': 'out.mkdir()\nt = a.test\n',
}
FAKE_TAIL = '(out / "manifest.json").write_text(json.dumps({"test_only": t}))\n'
FAKE_STAGE3A = dict(args=[], package_paths=[])


def fake_planner(variant: str) -> str:
    return FAKE_HEAD + FAKE_BODY[variant] + FAKE_TAIL


def fake_stage2b_inputs(pkg: Path, with_packs: bool) -> dict:
    """Simulate the live inputs after Stage 2b in a scratch package, for the self-test: l7_complete and l8_present
    true, an L8 pack per sector pinned (with_packs: present, as on Expanse; otherwise absent, as on the Mac, which
    verify() then refuses unless C8_ALLOW_NO_L8=1 skips it). The packs are synthetic. When the checkout's live inputs
    are the Stage-2b state of the same d3 pin, their L8 rows and counts are put back (the scratch package may be in the
    runner's fixed state), so a non-test gate also passes prepare_inputs.inventory_complete (S4-003); before Stage 2b
    one synthetic row and count per sector stand in. The inventory is repinned (only the state's flags, pins, counts
    and, from S4-003, the rows' completeness matter to the runner)."""
    if pkg.resolve() == ROOT.resolve():
        raise ValueError(f'{pkg}: a scratch package only')
    d = pkg / 'inputs'
    m = json.loads((d / 'manifest.json').read_bytes())
    inv = json.loads((d / 'inventory.json').read_bytes())
    lm = json.loads((ROOT / 'inputs/manifest.json').read_bytes())
    live = json.loads((ROOT / 'inputs/inventory.json').read_bytes())
    live2b = (m.get('d3_payload_manifest_sha256') is not None and m['d3_payload_manifest_sha256'] == lm.get('d3_payload_manifest_sha256')
              and all(live[s].get('8') for s in ('free', 'power')))
    added = []
    for sector in ('free', 'power'):
        data = f'synthetic {sector} L8 pack (tests/plan_gate.py self-test)\n'.encode()
        rel = f'packs/{sector}_L8.pack'
        (d / rel).unlink(missing_ok=True)   # a live L8 pack (Expanse) is a hard link: replaced, never written through
        if with_packs:
            (d / rel).write_bytes(data)
        m['sha256'][rel] = _sha(data)
        inv[sector]['8'] = live[sector]['8'] if live2b else [dict(inv[sector]['7'][0], id=0, offset=0, length=len(data),
                                                                    sha256=_sha(data))]
        m['counts'][sector]['8'] = len(inv[sector]['8'])
        added.append(rel)
    m['kernels'] = sum(int(n) for per in m['counts'].values() for n in per.values())
    m['l7_complete'] = m['l8_present'] = True
    data = (json.dumps(inv, indent=1) + '\n').encode()
    _replace(d / 'inventory.json', data)
    m['sha256']['inventory.json'] = _sha(data)
    _replace(d / 'manifest.json', (json.dumps(m, indent=2) + '\n').encode())
    return dict(l8_pins=added, l8_packs_present=with_packs, kernels=m['kernels'], live_stage2b=live2b,
                l8_rows=sum(len(inv[s]['8']) for s in ('free', 'power')))


# ---- Stage 3a: the wired planner's request (CHANGELOG, Stage 2a repair rounds 1 and 2: the obligation) -------------
def stage3a_prepare(pkg: Path, work: Path) -> list:
    """Give the scratch package a worker and write, OUTSIDE it, what the non-test request names:
    * bin/c8d3_gmp: the checkout's build (hard links) when there is one (Expanse); otherwise (the Mac, no native build)
      tests/fake_worker.py, labelled, which implements the worker's command line, --describe and output schema;
    * a measured-schema cost model (c8-d3-cost-model-1, synthetic seconds) of exactly that executable, this host's CPU
      model and --mp-check on, keyed campaign:sector:L:graph for every inventory graph: role campaign on the measured
      basis, the request a real non-test plan makes (HD11);
    * the plan's node-local scratch (--scratch; outside a job a plan needs it and must be test-only, D.4).
    No --forbid-seeds-from (S2-002): a plan that checks its seed must also reserve it under the session lock
    (--reserve-seed), which these hermetic children (C8_SITE stripped, no C8_ROOT) cannot take; every scenario either
    stops at the input gate, before any seed rule, or is made test-only by it (`untouched`), a test-only plan that
    neither checks nor reserves a seed.
    The request carries no test flag: only the gate's l7_complete: false may make it test-only (`untouched`). The plan
    refuses any selected graph without inspect fields (PLAN B), so `untouched` passes once `make inputs-inspect` has
    filled them for L <= 7 (Stage 3a, the inspector's data commit)."""
    import platform
    work.mkdir(parents=True, exist_ok=True)
    exe = pkg / 'bin' / 'c8d3_gmp'
    if not exe.exists():
        (pkg / 'bin').mkdir(exist_ok=True)
        exe.write_text(f'#!{sys.executable}\n# plan_gate: tests/fake_worker.py standing in for the native worker (no native build here)\n'
                       + (ROOT / 'tests/fake_worker.py').read_text())
        exe.chmod(0o755)
    sha = hashlib.sha256(exe.read_bytes()).hexdigest()
    cpu = None
    try:
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.startswith('model name'):
                cpu = line.split(':', 1)[1].strip()
                break
    except OSError:
        pass
    cpu = cpu or platform.processor() or platform.machine()
    inv = json.loads((pkg / 'inputs/inventory.json').read_bytes())
    keys = {f'{c}:{s}:{L}:{r["id"]}': 1e-5 for c in 'ab' for s in ('free', 'power') for L, rows in inv.get(s, {}).items()
            for r in rows}
    model = dict(schema='c8-d3-cost-model-1', dimension=3, order=8, measured=True, backend='gmp', rates_identity='default',
                 executable_sha256=sha, cpu_model=cpu, mp_check='on', seconds_per_point=keys,
                 label='tests/plan_gate.py: synthetic seconds of a measured-schema model (the request a non-test plan makes)')
    (work / 'model.json').write_text(json.dumps(model) + '\n')
    (work / 'scratch').mkdir(exist_ok=True)
    return ['--cost-model', str(work / 'model.json'), '--scratch', str(work / 'scratch')]


STAGE3A = dict(args=['--seed', '7340032001', '--pilot', '--replicates', '2', '--threads', '2', '--checkpoint-tasks', '64',
                     '--index-hours', '0.25'],
               package_paths=['bin'], prepare=stage3a_prepare, test_only_key=['test_only'])
