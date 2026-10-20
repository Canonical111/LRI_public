#!/usr/bin/env python3
"""The C8(3) inputs (PLAN component B; G2a: A-IN-1, A-IN-2, A-IN-4 for L <= 7; G2b: A-IN-3..5; F row check_inputs.py).

The checks follow the live state: the Stage-2a state (no d3 pin in inputs/manifest.json; the list below) or, from
Stage 2b on (the manifest carries the d3 pin), the Stage-2b state described after the list.

 * Regeneration: tools/prepare_inputs.py build --out <scratch> reproduces every file of inputs/ byte for byte; the
   generated set equals the tracked set under inputs/ (`git ls-files`, or a walk of an export; the L8 packs of Stage 2b
   are not generated here), no stale file lies in inputs/, and the working tree equals HEAD there.
 * verify() accepts the package inputs (no L8 pack is pinned before Stage 2b, so nothing is skipped).
 * Manifest (A-IN-4 for L <= 7): schema c8-d3-hpc-inputs-1, dimension 3, order 8, epsilon 2s-3; the 15 pinned files
   (2 low-loop, 2 order-7, the inventory, 10 packs); counts; l7_complete and l8_present false; inspect_complete true
   exactly when inspect/inspect.json (make inputs-inspect, Stage 3a) is present and covers every row; the
   H1 and d3 pins null; the vendored pins equal to tools/VENDORED.json and the HANDOFF; the L3-L7 packs and the order-7
   files at the sha256 of LRI_C7_D3_HPC@a6ce987 (tests/fixtures/c7_inputs/manifest.json); the recorded prepare_low8
   comparison.
 * A-IN-1: inputs/two_loop.json and inputs/gamma_d3_8.txt byte-equal to the vendored inputs_d3/ files at the HANDOFF
   sha256s (6c31bf7f..., f868fbe2...); the build ran prepare_low8.py --d 3 in compare mode (exit 0); 7 gamma rows of
   9 tokens with labels 6..0; rows L = 2..7 repeat tokens 2..8 of inputs/order7/gamma_d3_7.txt; the L = 8 norm is
   -2 Gamma(3/2)^8 / Gamma(3/4)^16 to 60 digits.
 * A-IN-2: B2 lengths 7 (order 8), 6 (order 7) and 5 (the historical reference/reference/d3_C6_two_loop.json), the
   order-8 prefix string-equal to order 7; unless --no-dimension8, gen3/check_dimension8.py (ii)-(iv) on the package's
   inputs with the comparison counts 6, 5, 5, 7, 7 and 42. Its negative tests are in gen3/test_gen3.py.
 * Inventory (B; gate 6 for L <= 7): the row fields of PLAN B in order, ascending ids, contiguous members whose bytes
   hash to the row sha256 and whose headers give id, wa, wb, M, T; cost = max(1, M T); s_G = 12 wb / wa an integer
   (never 4 at L7, which C7(3) excluded); the inspect fields equal to inspect/inspect.json's row (member sha256 and
   values) when that file exists, else null; the rows equal a6ce987's on id, primitive, offset,
   length, sha256, cost, monomials and terms; the member list with free/L2/G0.txt hashes to gen3/pins/PINS.json's
   C7(3) payload digest. double_lift: prepare_inputs.raw_valuations equals gen3/g3common.d3_rates (the pure-Python
   port of regenerate_rates.cpp) on every L3-L5 kernel, every 25th L6 kernel and, per sector, the two smallest L7
   kernels and the two smallest with a double lift (power only); the totals reproduce the Stage-1a / RECON:1346
   observation (power L7: 106 double-lift subsets in 42 kernels; free: none).
 * A-IN-4 (L <= 7), the plan's input gate prepare_inputs.plan_inputs() in scratch packages (`plan` calls it first; its
   wiring into tools/production.py is Stage 3a): a one-byte change to 8 of the 15 pinned inputs (all three file kinds) or to
   4 vendored files, or a missing
   pack, is refused naming the file; a non-test plan with a foreign C8_INPUTS is refused and a test plan records it;
   l7_complete: false makes every plan test-only; a C7(3) and a dimension-2 manifest are refused; a missing pinned L8
   pack is refused unless C8_ALLOW_NO_L8=1 (SKIPPED, test-only); nothing is created or changed by the gate.
 * A-IN-4 through the real `production.py plan` (tests/plan_gate.py, Stage 2a repair rounds 1 and 2), in the
   scratch package on the runner's fixed input state (l7_complete and l8_present false, no L8 pin; the live state at
   Stage 2a, so nothing is rewritten now), which the package's own gate must first pass as a test-only plan: a
   one-byte change to packs/free_L7.pack and to a vendored file, and a non-test plan with a foreign C8_INPUTS.
   Transitional (Stage 2a, production.py does not call plan_inputs): each is refused by the unported C7(3) planner's
   prepare() before anything is created. Wired (from Stage 3a): each is refused naming the file or C8_INPUTS, with no
   campaign directory, nothing beside it or in TMPDIR and the package unchanged, and the untouched non-test request
   comes out test-only; plan_gate.STAGE3A must then be set (else the check fails, naming the obligation). These wired
   runs are G3a evidence, valid before and after Stage 2b. A self-test runs fake wired planners (one correct, four
   wrong) through the same runner and requires each wrong one to fail, and runs the correct one on simulated
   post-Stage-2b inputs (Expanse with the L8 packs, the Mac without them under C8_ALLOW_NO_L8=1), which must pass.
Stage 2b (G2b: A-IN-3, A-IN-4, A-IN-5; gate 6), in addition to the above where it still applies:
 * the L8 packs must be present (Expanse, after make link-l8) or C8_ALLOW_NO_L8=1 (the Mac); the regeneration is the
   Stage-2b `make inputs` (L8 rows re-derived from the packs when present, carried forward when not) and the generated
   set adds selection.json, h1/{MANIFEST.json,SHA256SUMS} and d3/{MANIFEST_d3.json,SHA256SUMS,MEMBERS_d3.sha256,
   rate_audit_L7.json,rate_audit_L8.json};
 * manifest: 25 pinned files (the 12 packs among them, the L8 packs at their pins when present); counts L3-L6 as C7(3),
   L7 2,441 / 709, L8 16,064 / 4,336 (24,173 kernels); l7_complete and l8_present true; the H1 pin is the HANDOFF's
   (46341a3c...); the d3 pin equals the A.5 gate record's (C8_GATE_RECORD, else ../LRI_C8_shared/assembly/H1_gates/
   beside the package; noted when neither exists); the Stage-2b chain (prepare_inputs.Stage2b) with H1's counts and
   primitives (44 at L7, 248 at L8);
 * inventory: loops 3..8; the L <= 7 row checks; L3-L6 rows equal a6ce987's; the C7(3) L7 rows equal a6ce987's apart
   from the offset, and their members, in id order, are a6ce987's L7 pack (gate 6); the 143 + 119 new L7 rows have
   s_G = 4; every L7/L8 row at its MEMBERS_d3.sha256 hash and with the rate audit's double_lift; L8 ids, primitive
   flags (248) and s_G != 4 from selection.json; with the L8 packs present every L8 member is read (contiguous, at its
   sha256, header = row) and the numpy double_lift equals the audit's (C++) on the 2 smallest L8 kernels per sector;
   inspect_complete and every row's inspect fields equal to inspect/inspect.json;
 * A-IN-4: the untouched gate is not test-only with the L8 packs present (test-only with C8_ALLOW_NO_L8=1 without
   them); one-byte changes to selection.json and the d3/h1 copies are refused; with the L8 packs present, a one-byte
   change to packs/free_L8.pack is refused by the gate and by `production.py plan` (non-test), which creates nothing;
 * inputs_mini (A-IN-3): tests/fixtures/inputs_mini/ holds exactly its four files; its L3-L7 rows are the package's,
   its L8 rows the 8 smallest per sector (by bytes, then id) with the package's fields apart from the offset, at their
   MEMBERS_d3.sha256 hashes; materialized (prepare_inputs.materialize_mini) it passes verify() and the gate only as a
   test plan; with the L8 packs present `prepare_inputs.py mini` regenerates it byte for byte.
 * Stage-6 fix round 2 (Stage 2b state): a count-preserving duplicate graph id in the inventory (L3 and L7; counts, packs
   and pins kept, only the inventory hash refreshed) is refused by inventory_complete (R2-S1-03); a "synthetic"
   manifest makes a non-test plan test-only or is refused on any site but the fakes, and the environment's test seam
   (C8_TEST_SYNTHETIC_INPUTS=1) is honoured only under C8_SITE=fake off the real sites (R2-S1-02); `mini` (its
   default destination symlinked to the package inputs, an --out whose packs/ links into them, a temporary path
   linked into them) and `mini-materialize` (a destination whose packs/ links into them) refuse before writing
   anything, every byte of the package inputs unchanged (R2-S1-05).
Usage: python3 -B tests/check_inputs.py [--output FILE] [--no-dimension8] [--keep]
Exit 0 when every check passes.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'gen3'))
import prepare_inputs as pi  # noqa: E402
sys.path.append(str(ROOT / 'tests'))
import plan_gate  # noqa: E402

INPUTS = ROOT / 'inputs'
LOW_SHA = {'two_loop.json': '6c31bf7fcea49e1c16b52c82ca117502932a0f6a890e5d58b4846b3cb91fbffc',
           'gamma_d3_8.txt': 'f868fbe27855ea0474e633e221629d5c5c1011b7dd07c2d6a4df6853b4b7293d'}   # PLAN F11, A-IN-1
HISTORICAL = ROOT / 'reference/reference/d3_C6_two_loop.json'
HISTORICAL_SHA = 'f60e2064305772dc02768a4d316af214f8b4ecf67b64f6c952c7d3ca9fa5291b'
C7_MANIFEST = ROOT / 'tests/fixtures/c7_inputs/manifest.json'
C7_INVENTORY = ROOT / 'tests/fixtures/c7_inputs/inventory.json'
EXPECTED_FILES = {*pi.LOW_LOOP, *(f'order7/{n}' for n in pi.ORDER7), 'inventory.json', 'manifest.json',
                  *pi.C7D3_PACK_SHA256}
EXPECTED_2B = EXPECTED_FILES | set(pi.STAGE2B_FILES)
GATE_RECORD = ROOT.parent / 'LRI_C8_shared/assembly/H1_gates' / f'inventory8_d2_{pi.H1_MANIFEST_SHA256[:12]}_C63d_gates.json'
GATE_DRIVER = r'''
import json, sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import prepare_inputs as pi
try:
    r = pi.prepare() if sys.argv[2] == 'prepare' else pi.plan_inputs(sys.argv[2] == 'test')
except pi.InputsError as e:
    print(json.dumps({'refused': str(e)}))
    sys.exit(3)
r.pop('manifest', None)
print(json.dumps(r))
'''


def sha256(p: Path) -> str:
    return pi.digest(p)


def child_env(**extra) -> dict:
    env = {k: v for k, v in os.environ.items()
           if k not in ('PYTHONPYCACHEPREFIX', 'PYTHONPATH', 'C8_INPUTS', 'C8_ALLOW_NO_L8', pi.SYNTHETIC_SEAM)}
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env.update(extra)
    return env


def git(*args) -> subprocess.CompletedProcess:
    return subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True, text=True)


def replace(p: Path, data: bytes) -> None:
    """Replace a file without writing through a hard link (the scratch packs are linked to the package's)."""
    p.unlink()
    p.write_bytes(data)


def tree_state(d: Path) -> dict:
    """Every entry under d: files by (size, mtime), directories by kind only, as plan_gate.tree_state. A directory's
    st_size means nothing portable: BeeGFS reports 0 for a new directory and its entry count later (symmetry J-E0-sym
    570317: inputs 0 -> 9, tools 0 -> 41, nothing added or removed)."""
    return {p.relative_to(d).as_posix(): ('dir', None) if p.is_dir() else (p.stat().st_size, p.stat().st_mtime_ns)
            for p in sorted(d.rglob('*'))}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--output', type=Path)
    ap.add_argument('--no-dimension8', action='store_true', help='skip gen3/check_dimension8.py (A-IN-2 (ii)-(iv))')
    ap.add_argument('--keep', action='store_true', help='keep the scratch directory')
    a = ap.parse_args()
    results, failed, notes = [], [], []
    t0 = time.time()

    def check(name: str, ok: bool, detail='') -> None:
        detail = detail if isinstance(detail, str) else json.dumps(detail, default=str)
        results.append(dict(check=name, passed=bool(ok), detail=detail[-2000:]))
        if not ok:
            failed.append(name)
        print(('PASS ' if ok else 'FAIL ') + name + (f': {detail[-800:]}' if detail and not ok else ''), flush=True)

    live = json.loads((INPUTS / 'manifest.json').read_bytes())
    post = live.get('d3_payload_manifest_sha256') is not None   # the Stage-2b state
    expected = EXPECTED_2B if post else EXPECTED_FILES
    loops = pi.LOOPS_2B if post else pi.LOOPS
    l8_here = post and all((INPUTS / r).is_file() for r in pi.L8_PACKS)
    td = None
    if l8_here:   # the scratch packages hard-link the L8 packs (9.4 GB): keep them on the package's filesystem
        try:
            td = Path(tempfile.mkdtemp(prefix='.c8d3_check_inputs_', dir=ROOT.parent))
        except OSError:
            td = None
    td = td or Path(tempfile.mkdtemp(prefix='c8d3_check_inputs_'))
    l8_skip = post and not l8_here
    notes.append(f'state: {"Stage 2b" if post else "Stage 2a"}' + (f'; the L8 packs {"present" if l8_here else "absent"}'
                                                                     if post else ''))
    try:
        if post:
            check('Stage 2b: the L8 packs are present (make link-l8 STORE=$C8_STORE) or C8_ALLOW_NO_L8=1 (the Mac)',
                  l8_here or os.environ.get('C8_ALLOW_NO_L8') == '1',
                  'inputs/packs/{free,power}_L8.pack are missing and C8_ALLOW_NO_L8 is not 1')
        # ---- regeneration ----------------------------------------------------------------------------------------
        regen = td / 'regen/inputs'
        cp = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/prepare_inputs.py'), 'build', '--out', str(regen)],
                            capture_output=True, text=True, env=child_env())
        check('make inputs (prepare_inputs.py build) runs into a scratch directory', cp.returncode == 0,
              (cp.stdout + cp.stderr)[-1500:])
        gen = {p.relative_to(regen).as_posix() for p in regen.rglob('*') if p.is_file()} if regen.is_dir() else set()
        if (ROOT / '.git').exists():
            tracked = {x[len('inputs/'):] for x in git('ls-files', '-z', 'inputs').stdout.split('\0') if x}
            source = 'git ls-files inputs'
        else:
            tracked = {p.relative_to(INPUTS).as_posix() for p in INPUTS.rglob('*') if p.is_file()
                       and p.name != '.DS_Store' and p.relative_to(INPUTS).as_posix() not in pi.L8_PACKS}
            source = 'a walk of inputs/ (no .git)'
        check(f'the generated set equals the tracked inputs ({len(expected) - 1} pinned files and the manifest; the L8 packs '
              'are not generated here)', gen == tracked == expected,
              dict(source=source, only_generated=sorted(gen - tracked), only_tracked=sorted(tracked - gen),
                   unexpected=sorted(gen ^ expected)))
        if post:
            how = cp.stderr
            check('the Stage-2b regeneration ran in 2b-carry mode, the L8 rows ' + ('re-derived from the packs' if l8_here
                  else 'carried forward (checked)'), '(2b-carry)' in how and how.count('(rederived_from)' if l8_here
                                                                                   else '(carried)') == 2, how[-600:])
        diff = sorted(rel for rel in gen & tracked if sha256(regen / rel) != sha256(INPUTS / rel))
        check('every regenerated file is byte-identical to the package\'s', not diff and bool(gen), diff)
        present = {p.relative_to(INPUTS).as_posix() for p in INPUTS.rglob('*')
                   if p.is_file() and p.name != '.DS_Store'}
        stale = sorted(present - tracked - set(pi.L8_PACKS))
        check('no stale file in inputs/ (the C7(3) gamma_d3_7.txt and primitive_reference.json are gone)', not stale,
              stale)
        if (ROOT / '.git').exists():
            d = git('status', '--porcelain', '--', 'inputs')
            dirty = [ln for ln in d.stdout.splitlines() if not any(ln.endswith(x) for x in pi.L8_PACKS)]
            check('the checked inputs are the committed ones (git status of inputs/ is clean)',
                  d.returncode == 0 and not dirty, dirty[:20])
        else:
            notes.append('no .git: the committed-state check of inputs/ is not applicable in an export')
        # ---- verify ----------------------------------------------------------------------------------------------
        cp = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/prepare_inputs.py'), 'verify'], capture_output=True,
                            text=True, env=child_env(**({'C8_ALLOW_NO_L8': '1'} if l8_skip else {})))
        try:
            vr = json.loads(cp.stdout)
        except ValueError:
            vr = {}
        if not post:
            check('prepare_inputs.py verify accepts the package inputs (nothing skipped; test-only reasons l7_complete and '
                  'l8_present)', cp.returncode == 0 and vr.get('skipped') == [] and len(vr.get('test_only_reasons', [])) == 2
                  and vr.get('manifest_sha256') == sha256(INPUTS / 'manifest.json'), (cp.stdout + cp.stderr)[-800:])
        elif l8_here:
            check('prepare_inputs.py verify accepts the Stage-2b inputs with the L8 packs (nothing skipped, no test-only '
                  'reason)', cp.returncode == 0 and vr.get('skipped') == [] and vr.get('test_only_reasons') == []
                  and vr.get('manifest_sha256') == sha256(INPUTS / 'manifest.json'), (cp.stdout + cp.stderr)[-800:])
        else:
            check('prepare_inputs.py verify accepts the Stage-2b inputs without the L8 packs only under C8_ALLOW_NO_L8=1 '
                  '(both skipped, the skip the only test-only reason)', cp.returncode == 0
                  and vr.get('skipped') == list(pi.L8_PACKS) and len(vr.get('test_only_reasons', [])) == 1
                  and 'C8_ALLOW_NO_L8' in vr['test_only_reasons'][0], (cp.stdout + cp.stderr)[-800:])
        # ---- manifest (A-IN-4 for L <= 7) ------------------------------------------------------------------------
        m = json.loads((INPUTS / 'manifest.json').read_bytes())
        c7m = json.loads(C7_MANIFEST.read_bytes())
        v = json.loads((ROOT / 'tools/VENDORED.json').read_bytes())
        handoff = json.loads((ROOT / pi.VENDOR / 'HANDOFF_assembly.json').read_bytes())
        check('manifest: schema c8-d3-hpc-inputs-1, dimension 3, order 8, epsilon 2s-3',
              (m.get('schema'), m.get('dimension'), m.get('order'), m.get('epsilon')) == (pi.SCHEMA, 3, 8, '2s-3'))
        pinned = m.get('sha256', {})
        want_pins = (expected - {'manifest.json'}) | (set(pi.L8_PACKS) if post else set())
        check(f'manifest: pins exactly the {len(want_pins)} input files (2 low-loop, 2 order-7, the inventory, '
              + ('10 packs L3-L7)' if not post else '12 packs L3-L8, selection.json, h1/ and d3/)') + ', each at its sha256'
              + (' (the absent L8 packs not hashed)' if l8_skip else ''), set(pinned) == want_pins
              and all(pinned[r] == sha256(INPUTS / r) for r in pinned if r in expected or l8_here),
              sorted(set(pinned) ^ want_pins))
        packs_c7 = {r: h for r, h in c7m['sha256'].items() if r.startswith('packs/')}
        if not post:
            check('manifest: the L3-L7 packs at the sha256 of LRI_C7_D3_HPC@a6ce987 (gate 6; L7 = C7(3)\'s before Stage 2b)',
                  {r: pinned.get(r) for r in packs_c7} == packs_c7 == pi.C7D3_PACK_SHA256 and len(packs_c7) == 10)
        else:
            l36 = {r: h for r, h in packs_c7.items() if not r.endswith('_L7.pack')}
            check('manifest: the L3-L6 packs at the sha256 of LRI_C7_D3_HPC@a6ce987; the L7 packs (complete) differ',
                  {r: pinned.get(r) for r in l36} == l36 and len(l36) == 8
                  and all(pinned[r] != packs_c7[r] for r in packs_c7 if r.endswith('_L7.pack')))
        check('manifest: the order-7 files at a6ce987\'s sha256 (3dddb802..., d5008ca0...)',
              pinned.get('order7/two_loop.json') == c7m['sha256']['two_loop.json'] == pi.ORDER7['two_loop.json']
              and pinned.get('order7/gamma_d3_7.txt') == c7m['sha256']['gamma_d3_7.txt'] == pi.ORDER7['gamma_d3_7.txt'])
        want_counts = {s: {str(L): n for L, n in c.items()} for s, c in pi.C7D3_COUNTS.items()}
        if not post:
            check('manifest: counts free 5/16/76/395/2,298 and power 1/3/20/107/590 (3,511 kernels)',
                  m.get('counts') == want_counts and m.get('kernels') == 3511 and c7m['counts'] == want_counts)
        else:
            want2b = {s: {**{L: n for L, n in want_counts[s].items() if L != '7'},
                          **{str(L): n for L, n in pi.STAGE2B_COUNTS[s].items()}} for s in pi.SECTORS}
            check('A-IN-3: counts L3-L6 as C7(3), L7 2,441 / 709, L8 16,064 / 4,336 (24,173 kernels)',
                  m.get('counts') == want2b and m.get('kernels') == 24173, m.get('counts'))
        inspected = (ROOT / pi.INSPECT_DATA).exists()
        irows = {}
        if inspected:
            idata = json.loads((ROOT / pi.INSPECT_DATA).read_bytes())
            irows = {(s_, int(L_), r_[0]): r_ for s_, lp in idata['rows'].items() for L_, rs in lp.items() for r_ in rs}
        sb = None
        if not post:
            check('manifest: l7_complete and l8_present false; inspect_complete true exactly when inspect/inspect.json is '
                  'present (make inputs-inspect); the H1 and d3 pins null (Stage 2b)',
                  m.get('l7_complete') is False and m.get('l8_present') is False and m.get('inspect_complete') is inspected
                  and m.get('inventory8_d2_manifest_sha256') is None and m.get('d3_payload_manifest_sha256') is None)
        else:
            covered = inspected and len(irows) == 24173
            check('A-IN-3 / A-IN-4: l7_complete and l8_present true; inspect_complete true exactly when inspect/inspect.json '
                  'covers all 24,173 kernels; the H1 pin is the HANDOFF\'s (46341a3c...)',
                  m.get('l7_complete') is True and m.get('l8_present') is True and m.get('inspect_complete') is covered
                  and m.get('inventory8_d2_manifest_sha256') == pi.H1_MANIFEST_SHA256,
                  dict(inspect_rows=len(irows), inspect_complete=m.get('inspect_complete')))
            gr_path = Path(os.environ['C8_GATE_RECORD']) if os.environ.get('C8_GATE_RECORD') else GATE_RECORD
            if gr_path.is_file():
                gr = json.loads(gr_path.read_bytes())
                check('A-INV-5 / B: the manifest\'s d3 pin (a copy) equals the A.5 gate record\'s manifest_d3_sha256, and its '
                      'H1 pin the record\'s', gr.get('manifest_d3_sha256') == m.get('d3_payload_manifest_sha256')
                      and gr.get('h1_manifest_sha256') == m.get('inventory8_d2_manifest_sha256'),
                      dict(record=str(gr_path), record_pin=gr.get('manifest_d3_sha256'), manifest_pin=m.get('d3_payload_manifest_sha256')))
            else:
                notes.append(f'the A.5 gate record is not reachable here ({gr_path}; set C8_GATE_RECORD): the d3 pin was '
                             'not compared with it in this run')
            try:
                sb = pi.Stage2b(pi.stage2b_files_in(INPUTS), m.get('d3_payload_manifest_sha256'),
                                m.get('inventory8_d2_manifest_sha256'), 'inputs')
                err = None
            except pi.InputsError as e:
                sb, err = None, str(e)
            check('A-IN-3 / A.2 step 6: the Stage-2b chain (MANIFEST_d3 -> SHA256SUMS -> MEMBERS_d3.sha256 and the rate '
                  'audits; H1 MANIFEST -> SHA256SUMS -> selection.json) ends at the two pins; selection.json has H1\'s '
                  'counts and primitives (44 at L7, 248 at L8)', sb is not None
                  and sb.manifest_d3.get('counts') == {'L7_free': 2441, 'L7_power': 709, 'L8_free': 16798, 'L8_power': 4891},
                  err or (sb.manifest_d3.get('counts') if sb else None))
        va = m.get('vendored_assembly') or {}
        check('manifest: the vendored HANDOFF and file pins equal tools/VENDORED.json and the HANDOFF (A-ASM-1(b))',
              m.get('vendored_assembly_handoff_sha256') == va.get('handoff_sha256') == v['handoff']['sha256']
              == pi.HANDOFF_SHA256 and va.get('files') == {f['vendored_path']: f['sha256'] for f in v['files']}
              == {f'{pi.VENDOR}/{f["path"]}': f['sha256'] for f in handoff['files']} and len(va['files']) == 13)
        check('manifest: reference_manifest_sha256 is reference/DELIVERY_MANIFEST.json\'s',
              m.get('reference_manifest_sha256') == sha256(ROOT / 'reference/DELIVERY_MANIFEST.json'))
        low8 = (m.get('sources') or {}).get('prepare_low8_compare') or {}
        check('A-IN-1: make inputs ran the vendored prepare_low8.py --d 3 in compare mode with the fixture LRI_ROOT: '
              'exit 0, three files identical', low8.get('exit_status') == 0 and low8.get('LRI_ROOT') == pi.FIXTURES
              and low8.get('files') == {'two_loop.json': 'identical', 'gamma_d3_8.txt': 'identical',
                                        'checks.json': 'identical'}, low8)
        # ---- A-IN-1 ----------------------------------------------------------------------------------------------
        for name, want in LOW_SHA.items():
            b = (INPUTS / name).read_bytes()
            check(f'A-IN-1: inputs/{name} is byte-equal to {pi.VENDOR}/inputs_d3/{name} at the HANDOFF sha256 '
                  f'{want[:8]}...', b == (ROOT / pi.VENDOR / 'inputs_d3' / name).read_bytes()
                  and hashlib.sha256(b).hexdigest() == want
                  and {f['path']: f['sha256'] for f in handoff['files']}[f'inputs_d3/{name}'] == want)
        g8 = [ln.split() for ln in (INPUTS / 'gamma_d3_8.txt').read_text().splitlines()]
        g7 = [ln.split() for ln in (INPUTS / 'order7/gamma_d3_7.txt').read_text().splitlines()]
        check('A-IN-1: gamma_d3_8.txt has 7 rows of 9 tokens with labels 6..0',
              len(g8) == 7 and all(len(r) == 9 for r in g8) and [r[0] for r in g8] == [str(k) for k in range(6, -1, -1)],
              [len(r) for r in g8])
        rep = len(g7) == 6 and all(len(r) == 8 for r in g7) and [r[0] for r in g7] == [str(k) for k in range(5, -1, -1)]
        rep = rep and all(r8[1:8] == r7[1:8] for r8, r7 in zip(g8[:6], g7, strict=True))
        check('A-IN-1: rows L = 2..7 repeat tokens 2..8 (norm, l_0..l_5) of inputs/order7/gamma_d3_7.txt', rep)
        import mpmath as mp
        with mp.workdps(80):
            exact = -2 * mp.gamma(mp.mpf(3) / 2) ** 8 / mp.gamma(mp.mpf(3) / 4) ** 16
            tok = g8[6][1]
            rel = abs(mp.mpf(tok) - exact) / abs(exact)
            ok = tok == mp.nstr(exact, 60) and rel < mp.mpf('1e-59') and g8[6][0] == '0'
            check('A-IN-1: the L = 8 norm equals -2 Gamma(3/2)^8 / Gamma(3/4)^16 to 60 digits', ok,
                  dict(token=tok, exact=mp.nstr(exact, 65), relative=mp.nstr(rel, 3)))
        # ---- A-IN-2 ----------------------------------------------------------------------------------------------
        o8 = json.loads((INPUTS / 'two_loop.json').read_text())
        o7 = json.loads((INPUTS / 'order7/two_loop.json').read_text())
        hist = json.loads(HISTORICAL.read_text())
        errs = []
        if (o8.get('dimension'), o8.get('order'), len(o8.get('B2', []))) != (3, 8, 7):
            errs.append('inputs/two_loop.json: not dimension 3, order 8 with exactly 7 B2 strings')
        if (o7.get('dimension'), o7.get('order'), len(o7.get('B2', []))) != (3, 7, 6):
            errs.append('inputs/order7/two_loop.json: not dimension 3, order 7 with exactly 6 B2 strings')
        if len(hist.get('B2_decimal', [])) != 5 or sha256(HISTORICAL) != HISTORICAL_SHA:
            errs.append(f'{HISTORICAL.relative_to(ROOT)}: not the historical file (sha256 f60e2064...) with 5 strings')
        if not errs and any(x != y for x, y in zip(o8['B2'][:6], o7['B2'][:6], strict=True)):
            errs.append('the order-8 prefix differs from the order-7 strings')
        check('A-IN-2: B2 lengths 7 / 6 / 5 (order 8, order 7, historical), order-8 [:6] string-equal to order 7',
              not errs, errs)
        if a.no_dimension8:
            notes.append('--no-dimension8: gen3/check_dimension8.py (A-IN-2 (ii)-(iv)) not run here')
        else:
            out = td / 'check_dimension8.json'
            cp = subprocess.run([sys.executable, '-B', str(ROOT / 'gen3/check_dimension8.py'), '--output', str(out)],
                                capture_output=True, text=True, env=child_env())
            rec = json.loads(out.read_text()) if out.exists() else {}
            ck = rec.get('checks', {})
            ok = (cp.returncode == 0 and rec.get('passed') is True
                  and ck.get('ii_two_loop', {}).get('counts') == dict(order8_vs_order7_strings=6, order7_vs_historical=5,
                                                                       order8_vs_historical=5, contour=7, taylor=7)
                  and ck.get('iii_gamma_rows', {}).get('comparisons') == 42 and ck.get('iv_power_three_loop_b3', {}).get('passed')
                  and ck['ii_two_loop']['files'] == dict(order8=str(INPUTS / 'two_loop.json'),
                                                         order7=str(INPUTS / 'order7/two_loop.json'),
                                                         historical=str(HISTORICAL)))
            check('A-IN-2: gen3/check_dimension8.py on the package inputs: (ii) counts 6, 5, 5, 7, 7 within 1e-46 / 1e-50, '
                  '(iii) 42 gamma comparisons within 1e-46, (iv) -16 pi / 15', ok,
                  dict(worst=ck.get('ii_two_loop', {}).get('worst'), gamma_worst=ck.get('iii_gamma_rows', {}).get('worst'),
                       iv=ck.get('iv_power_three_loop_b3', {}).get('difference'), tail=(cp.stdout + cp.stderr)[-400:]))
        # ---- inventory -------------------------------------------------------------------------------------------
        inv = json.loads((INPUTS / 'inventory.json').read_bytes())
        c7inv = json.loads(C7_INVENTORY.read_bytes())
        covered_all = all(irows.get((s_, L_, r_['id'])) is not None for s_ in pi.SECTORS for L_ in loops
                          for r_ in inv.get(s_, {}).get(str(L_), []))
        check(f'inventory: keys inspect_complete, free, power; loops {loops[0]}..{loops[-1]}; inspect_complete = the '
              'manifest\'s', list(inv) == ['inspect_complete', 'free', 'power'] and inv['inspect_complete'] is m.get('inspect_complete')
              and all(list(inv[s]) == [str(L) for L in loops] for s in pi.SECTORS)
              and (inv['inspect_complete'] is (inspected and covered_all) if post else inv['inspect_complete'] is inspected))
        bad_rows, regress, members = [], [], {}
        shist = {}
        c7ids = {(s, int(L)): {r['id'] for r in c7inv[s][L]} for s in pi.SECTORS for L in c7inv[s]}
        for s in pi.SECTORS:
            for L in loops:
                rows = inv[s][str(L)]
                read = L <= 7 or l8_here
                pf = (INPUTS / f'packs/{s}_L{L}.pack').open('rb') if read else None
                off = 0
                c7cat = hashlib.sha256()
                for r in rows:
                    where = f'{s} L{L} G{r.get("id")}'
                    if tuple(r) != pi.ROW_FIELDS:
                        bad_rows.append(f'{where}: fields {list(r)}')
                        continue
                    errs = []
                    if r['offset'] != off:
                        errs.append(f'offset {r["offset"]} != {off}')
                    if read:
                        pf.seek(r['offset'])
                        data = pf.read(r['length'])
                        h = data.split(b'\n', 1)[0].split()
                        if hashlib.sha256(data).hexdigest() != r['sha256']:
                            errs.append('member sha256')
                        if [x.decode() for x in h] != ['C7D3GRAPH1', str(L), str(r['id']), r['wa'], r['wb'],
                                                       str(r['monomials']), str(r['terms'])]:
                            errs.append(f'header {h}')
                        if L == 7 and r['id'] in c7ids[(s, 7)]:
                            c7cat.update(data)
                    fa, fb = Fraction(r['wa']), Fraction(r['wb'])
                    if r['cost'] != max(1, r['monomials'] * r['terms']):
                        errs.append('cost')
                    if 12 * fb != r['s_G'] * fa and abs(12 * fb / fa - r['s_G']) > Fraction(1, 10 ** 12):
                        errs.append('s_G')
                    ir = irows.get((s, L, r['id']))
                    if ir is not None:
                        if ir[1] != r['sha256'] or [r[k] for k in pi.INSPECT_FIELDS] != ir[2:]:
                            errs.append('inspect fields differ from inspect/inspect.json')
                    elif any(r[k] is not None for k in pi.INSPECT_FIELDS):
                        errs.append('inspect field not null')
                    elif not post and inspected:
                        errs.append('row missing from inspect/inspect.json')
                    if not (isinstance(r['double_lift'], int) and r['double_lift'] >= 0):
                        errs.append('double_lift')
                    if post and L >= 7:
                        key = (s, L, r['id'])
                        if sb is None or sb.members.get(key) != r['sha256'] or sb.double_lift.get(key) != r['double_lift']:
                            errs.append('not at its MEMBERS_d3.sha256 hash or the rate audit\'s double_lift')
                    if errs:
                        bad_rows.append(f'{where}: {errs}')
                    off += r['length']
                    members[f'{s}/L{L}/G{r["id"]}.txt'] = r['sha256']
                    shist.setdefault(f'{s}:{L}', {}).setdefault(str(r['s_G']), 0)
                    shist[f'{s}:{L}'][str(r['s_G'])] += 1
                if read:
                    size = pf.seek(0, 2)
                    pf.close()
                    if off != size:
                        bad_rows.append(f'{s} L{L}: members cover {off} of {size} bytes')
                if post and L == 7 and c7cat.hexdigest() != pi.C7D3_PACK_SHA256[f'packs/{s}_L7.pack']:
                    bad_rows.append(f'{s} L7: the C7(3) members in id order are not a6ce987\'s L7 pack (gate 6)')
                ids = [r['id'] for r in rows]
                if ids != sorted(set(ids)):
                    bad_rows.append(f'{s} L{L}: ids not strictly ascending')
                keys = ('id', 'primitive', 'offset', 'length', 'sha256', 'cost', 'monomials', 'terms')
                if L <= 6 or (L == 7 and not post):
                    if [tuple(r[k] for k in keys) for r in rows] != [tuple(r[k] for k in keys) for r in c7inv[s][str(L)]]:
                        regress.append(f'{s} L{L}')
                elif L == 7:
                    k7 = keys[:2] + keys[3:]   # all but the offset
                    got = {r['id']: tuple(r[k] for k in k7) for r in rows}
                    if any(got.get(r['id']) != tuple(r[k] for k in k7) for r in c7inv[s]['7']):
                        regress.append(f'{s} L7 (the C7(3) rows apart from the offset)')
        check('inventory: every row has the PLAN B fields in order; members contiguous, at their sha256, headers equal '
              'to the row (id, wa, wb, M, T); cost = max(1, M T); s_G = 12 wb / wa; inspect fields from inspect/inspect.json '
              '(else null)' + ('; every L7/L8 row at its MEMBERS_d3.sha256 hash and the rate audit\'s double_lift; the '
                               'C7(3) L7 members in id order are a6ce987\'s L7 pack' if post else '')
              + ('' if not post or l8_here else ' (the L8 members themselves only on Expanse: the packs are absent here)'),
              not bad_rows, bad_rows[:20])
        check('inventory: rows equal LRI_C7_D3_HPC@a6ce987\'s on id, primitive, offset, length, sha256, cost, monomials, '
              'terms' + (' (L3-L6; the C7(3) L7 rows apart from the offset)' if post else ''), not regress, regress)
        pins = json.loads((ROOT / 'gen3/pins/PINS.json').read_text())['c7d3_payloads']
        rows6 = {k: h for k, h in members.items()
                 if int(k.split('/')[1][1:]) <= 6 or int(k.split('/')[2][1:-4]) in c7ids[(k.split('/')[0], 7)]}
        rows6 = {k: h for k, h in rows6.items() if int(k.split('/')[1][1:]) <= 7}
        rows6['free/L2/G0.txt'] = sha256(ROOT / 'reference/inputs/free/L2/G0.txt')
        dig = hashlib.sha256(''.join(f'{h}  {p}\n' for p, h in sorted(rows6.items())).encode()).hexdigest()
        check('gate 6 (L <= 7): the C7(3) members, with free/L2/G0.txt, hash to gen3/pins/PINS.json\'s C7(3) payload digest',
              dig == pins['digest_sha256'] and len(rows6) == pins['files'] == 3512, dict(digest=dig, pin=pins['digest_sha256']))
        prim = {f'{s}:{L}': sum(r['primitive'] for r in inv[s][str(L)]) for s in pi.SECTORS for L in loops}
        check('inventory: primitives 1 / 1 / 3 / 10 / 44 (free L3..L7)' + (', 248 at L8 (selection.json\'s)' if post else '')
              + ', none in the power sector',
              [prim[f'free:{L}'] for L in pi.LOOPS] == [1, 1, 3, 10, 44] and not any(prim[f'power:{L}'] for L in loops)
              and (not post or (prim['free:8'] == 248 and sb is not None
                                and {r['id'] for r in inv['free']['8'] if r['primitive']} == sb.primitive[8]
                                and {r['id'] for r in inv['free']['7'] if r['primitive']} == sb.primitive[7])), prim)
        if not post:
            check('inventory: no s_G = 4 kernel at L7 (C7(3) integrated only s_G != 4 there)',
                  all(r['s_G'] != 4 for s in pi.SECTORS for r in inv[s]['7']), shist)
        else:
            new7 = {s: [r for r in inv[s]['7'] if r['id'] not in c7ids[(s, 7)]] for s in pi.SECTORS}
            ok = (all(r['s_G'] != 4 for s in pi.SECTORS for r in inv[s]['7'] if r['id'] in c7ids[(s, 7)])
                  and {s: len(v) for s, v in new7.items()} == {'free': 143, 'power': 119}
                  and all(r['s_G'] == 4 for v in new7.values() for r in v)
                  and all(r['s_G'] != 4 for s in pi.SECTORS for r in inv[s]['8'])
                  and sb is not None and all([r['id'] for r in inv[s][str(L)]] == sb.ids[(s, L)] for s in pi.SECTORS for L in (7, 8)))
            check('A-IN-3: L7 = C7(3)\'s kernels (s_G != 4) and the 143 + 119 new s_G = 4 kernels; L8 s_G != 4; the L7 and '
                  'L8 ids are selection.json\'s', ok, shist)
        # double_lift: the numpy valuation against the line-by-line pure-Python port (and, at L8, the C++ rate audit)
        import g3common as g3
        sample, mism = [], []
        for s in pi.SECTORS:
            for L in loops:
                rows = inv[s][str(L)]
                if L <= 5:
                    pick = rows
                elif L == 6:
                    pick = rows[::25]
                elif L == 7:
                    c7rows = [r for r in rows if r['id'] in c7ids[(s, 7)]]
                    small = sorted(c7rows, key=lambda r: (r['terms'] * r['monomials'], r['id']))
                    pick = small[:2] + sorted([r for r in c7rows if r['double_lift']], key=lambda r: (r['terms'], r['id']))[:2]
                    if post:
                        pick += sorted([r for r in rows if r['id'] not in c7ids[(s, 7)]],
                                       key=lambda r: (r['terms'] * r['monomials'], r['id']))[:2]
                else:
                    pick = sorted(rows, key=lambda r: (r['length'], r['id']))[:2] if l8_here else []
                with (INPUTS / f'packs/{s}_L{L}.pack').open('rb') if pick else contextlib.nullcontext() as pf:
                    for r in pick:
                        pf.seek(r['offset'])
                        data = pf.read(r['length'])
                        g = g3.parse_gfile(data, f'{s}/L{L}/G{r["id"]}.txt')
                        ALL = (1 << g.E) - 1
                        raw_np = pi.raw_valuations(g.L, g.masks, g.terms)
                        if L == 8:   # E = 16: the pure-Python port is too slow; the C++ audit is the independent count
                            if r['double_lift'] != int((raw_np <= -5).sum()):
                                mism.append(f'{s} L{L} G{r["id"]}')
                        else:
                            _, raw_py = g3.d3_rates(g)
                            if list(map(int, raw_np)) != raw_py[1:ALL] or r['double_lift'] != sum(x <= -5 for x in raw_py[1:ALL]):
                                mism.append(f'{s} L{L} G{r["id"]}')
                        sample.append(f'{s}:{L}:{r["id"]}')
        check('double_lift: prepare_inputs.raw_valuations equals gen3/g3common.d3_rates (all L3-L5, every 25th L6, the two '
              'smallest C7(3) L7 kernels per sector and two power-L7 double-lift kernels'
              + (', the two smallest new L7 kernels per sector' if post else '') + ') and the rows\' counts follow from it'
              + ('; at L8 the numpy count equals the row (= the C++ rate audit) on the 2 smallest kernels per sector'
                 if l8_here else ''),
              not mism and len(sample) >= (140 if not post else 144 + (4 if l8_here else 0)),
              dict(mismatches=mism, compared=len(sample)))
        tot = {f'{s}:{L}': [sum(r['double_lift'] for r in inv[s][str(L)] if L < 7 or r['id'] in c7ids[(s, 7)]),
                            sum(1 for r in inv[s][str(L)] if r['double_lift'] and (L < 7 or r['id'] in c7ids[(s, 7)]))]
               for s in pi.SECTORS for L in pi.LOOPS}
        check('double_lift: the C7(3) kernels: power L7 106 subsets in 42 kernels (Stage 1a, RECON:1346); none in the '
              'free sector', tot['power:7'] == [106, 42] and all(tot[f'free:{L}'] == [0, 0] for L in pi.LOOPS), tot)
        if post:
            notes.append('double_lift totals (all kernels): ' + json.dumps({f'{s}:{L}': [sum(r['double_lift'] for r in inv[s][str(L)]),
                         sum(1 for r in inv[s][str(L)] if r['double_lift'])] for s in pi.SECTORS for L in (7, 8)}))
        # ---- inputs_mini (Stage 2b, A-IN-3) ------------------------------------------------------------------------
        if post:
            mini = ROOT / pi.MINI
            mfiles = sorted(q.relative_to(mini).as_posix() for q in mini.rglob('*') if q.is_file()
                            and q.name != '.DS_Store') if mini.is_dir() else []
            errs = []
            if mfiles != sorted(pi.MINI_OWN):
                errs.append(f'files {mfiles} are not {sorted(pi.MINI_OWN)}')
            else:
                mm = json.loads((mini / 'manifest.json').read_bytes())
                minv_b = (mini / 'inventory.json').read_bytes()
                minv = json.loads(minv_b)
                pkgf = sorted(r for r in m['sha256'] if r not in pi.MINI_OWN)
                if mm.get('test_inputs') != pi.MINI_LABEL or mm.get('package_files') != pkgf \
                        or any(mm['sha256'].get(r) != m['sha256'][r] for r in pkgf):
                    errs.append('the manifest\'s label, package_files or their pins differ from the package\'s')
                if mm['sha256'].get('inventory.json') != hashlib.sha256(minv_b).hexdigest():
                    errs.append('inventory.json is not at its pin')
                for s in pi.SECTORS:
                    if any(minv[s].get(str(L)) != inv[s][str(L)] for L in pi.LOOPS):
                        errs.append(f'{s}: the L3-L7 rows differ from the package\'s')
                    want = sorted(sorted(inv[s]['8'], key=lambda r: (r['length'], r['id']))[:pi.MINI_PER_SECTOR],
                                  key=lambda r: r['id'])
                    got = minv[s].get('8', [])
                    if [{k: v for k, v in r.items() if k != 'offset'} for r in got] != \
                            [{k: v for k, v in r.items() if k != 'offset'} for r in want] or len(got) != 8:
                        errs.append(f'{s}: the L8 rows are not the package\'s 8 smallest (by bytes, then id)')
                    pack = (mini / f'packs/{s}_L8.pack').read_bytes()
                    if mm['sha256'].get(f'packs/{s}_L8.pack') != hashlib.sha256(pack).hexdigest():
                        errs.append(f'packs/{s}_L8.pack is not at its pin')
                    off = 0
                    for r in got:
                        b = pack[r['offset']:r['offset'] + r['length']]
                        if r['offset'] != off or hashlib.sha256(b).hexdigest() != r['sha256'] or sb is None \
                                or sb.members.get((s, 8, r['id'])) != r['sha256']:
                            errs.append(f'{s} L8 G{r["id"]}: not contiguous or not at its inventory / MEMBERS_d3 hash')
                        off += r['length']
                    if off != len(pack):
                        errs.append(f'packs/{s}_L8.pack: rows cover {off} of {len(pack)} bytes')
            check('A-IN-3: tests/fixtures/inputs_mini/ (its four files; the package\'s L3-L7 rows and pins; the 8 smallest '
                  'L8 kernels per sector with the package\'s fields, contiguous, at their inventory and MEMBERS_d3.sha256 '
                  'hashes)', not errs, errs[:20])
            if not errs:
                z = td / 'mini/inputs'
                try:
                    pi.materialize_mini(z)
                    zerr = None
                except (ValueError, OSError) as e:
                    zerr = str(e)
                cps = [subprocess.run([sys.executable, '-B', str(ROOT / 'tools/prepare_inputs.py'), 'gate', *t],
                                      capture_output=True, text=True, env=child_env(C8_INPUTS=str(z)))
                       for t in (['--test-only'], [])]
                try:
                    g0 = json.loads(cps[0].stdout)
                except ValueError:
                    g0 = {}
                check('A-IN-3: inputs_mini verifies: materialized (its files copied, the package files hard-linked) it passes '
                      'the gate as a test plan (test-only, nothing skipped), and a non-test plan on it is refused',
                      zerr is None and cps[0].returncode == 0 and g0.get('test_only') is True and g0.get('skipped') == []
                      and cps[1].returncode == 1 and 'non-test plan reads only the package inputs' in cps[1].stderr,
                      dict(error=zerr, test=(cps[0].stdout + cps[0].stderr)[-400:], nontest=cps[1].stderr[-300:]))
                if l8_here:
                    regen_mini = td / 'mini_regen'
                    cp = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/prepare_inputs.py'), 'mini', '--out',
                                         str(regen_mini)], capture_output=True, text=True, env=child_env())
                    same = cp.returncode == 0 and all((regen_mini / r).read_bytes() == (mini / r).read_bytes() for r in pi.MINI_OWN)
                    check('A-IN-3: prepare_inputs.py mini regenerates tests/fixtures/inputs_mini/ byte for byte from the L8 packs',
                          same, (cp.stdout + cp.stderr)[-600:])
        # ---- A-IN-4 (L <= 7): the plan's input gate in scratch packages ------------------------------------------
        pkg = td / 'pkg'
        (pkg / 'tools').mkdir(parents=True)
        for f in list((ROOT / 'tools').glob('*.py')) + [ROOT / 'tools/VENDORED.json']:
            shutil.copy2(f, pkg / 'tools' / f.name)
        shutil.copytree(ROOT / 'vendor', pkg / 'vendor', ignore=shutil.ignore_patterns('__pycache__', '.DS_Store'))
        shutil.copytree(ROOT / 'cost_models', pkg / 'cost_models')
        (pkg / 'inputs/packs').mkdir(parents=True)
        (pkg / 'inputs/order7').mkdir()
        for rel in sorted(expected | (set(pi.L8_PACKS) if l8_here else set())):
            src, dst = INPUTS / rel, pkg / 'inputs' / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(src, dst) if rel.startswith('packs/') else shutil.copy2(src, dst)
            except OSError:
                shutil.copy2(src, dst)
        gate_py = td / 'gate.py'
        gate_py.write_text(GATE_DRIVER)

        def gate(mode: str, **env):
            r = subprocess.run([sys.executable, '-B', str(gate_py), str(pkg / 'tools'), mode], capture_output=True,
                               text=True, env=child_env(**env))
            try:
                out = json.loads(r.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError):
                out = {'error': (r.stdout + r.stderr)[-600:]}
            return r.returncode, out, r.stderr

        before = tree_state(pkg)
        genv = {'C8_ALLOW_NO_L8': '1'} if l8_skip else {}
        rc, out, _ = gate('nontest', **genv)
        if not post:
            check('A-IN-4: the untouched scratch package passes the gate; l7_complete false and l8_present false make even a '
                  'non-test plan test-only', rc == 0 and out.get('test_only') is True and len(out.get('test_only_reasons', [])) == 2
                  and any('l7_complete' in x for x in out['test_only_reasons']), out)
        elif l8_here:
            check('A-IN-4: the untouched Stage-2b inputs with the L8 packs pass the gate as a non-test plan (no test-only '
                  'reason)', rc == 0 and out.get('test_only') is False and out.get('test_only_reasons') == [], out)
        else:
            check('A-IN-4: the untouched Stage-2b inputs without the L8 packs pass the gate only under C8_ALLOW_NO_L8=1, and '
                  'then test-only', rc == 0 and out.get('test_only') is True and out.get('skipped') == list(pi.L8_PACKS), out)
            rc0, out0, _ = gate('nontest')
            check('A-IN-4: without the L8 packs and without C8_ALLOW_NO_L8 the gate refuses, naming free_L8.pack',
                  rc0 == 3 and 'free_L8.pack' in out0.get('refused', '') and 'missing' in out0['refused'], out0)
        rc, out, _ = gate('test', **genv)
        check('A-IN-4: a test plan passes the gate', rc == 0 and out.get('test_only') is True, out)
        flips = ['packs/free_L7.pack', 'packs/power_L3.pack', 'packs/free_L5.pack', 'inventory.json', 'two_loop.json',
                 'gamma_d3_8.txt', 'order7/two_loop.json', 'order7/gamma_d3_7.txt']
        if post:
            flips += ['selection.json', 'd3/MEMBERS_d3.sha256', 'd3/rate_audit_L8.json', 'h1/SHA256SUMS']
        res = {}
        for rel in flips:
            p = pkg / 'inputs' / rel
            orig = p.read_bytes()
            b = bytearray(orig)
            b[len(b) // 2] ^= 1
            replace(p, bytes(b))
            rc, out, _ = gate('nontest', **genv)
            rc2, out2, _ = gate('test', **genv)
            replace(p, orig)
            res[rel] = rc == 3 and rc2 == 3 and rel in out.get('refused', '') and 'Checksum mismatch' in out['refused']
        check(f'A-IN-4: a one-byte change to {len(flips)} of the {len(expected) - 1} pinned small inputs and packs '
              '(packs/free_L7.pack, the L8 analogue, among them) makes the gate refuse, test plan or not, naming the file',
              all(res.values()), res)
        if post and l8_here:
            # A-IN-4 on Expanse: a real one-byte change to packs/free_L8.pack (a flipped copy replaces the hard link; the
            # store blob is untouched), refused by the gate and by `production.py plan` (non-test) creating nothing
            p8 = pkg / 'inputs/packs/free_L8.pack'
            restore = plan_gate.flip_large(p8, td / 'free_L8.aside')
            try:
                rc, out, _ = gate('nontest')
            finally:
                restore()
            ok8 = rc == 3 and 'free_L8.pack' in out.get('refused', '') and 'Checksum mismatch' in out['refused']
            check('A-IN-4: a one-byte change to packs/free_L8.pack makes the gate refuse, naming it', ok8, out)
        p = pkg / 'inputs/packs/power_L6.pack'
        orig = p.read_bytes()
        p.unlink()
        rc, out, _ = gate('test', **genv)
        p.write_bytes(orig)
        check('A-IN-4: a missing pack is refused', rc == 3 and 'power_L6.pack' in out.get('refused', '')
              and 'missing' in out['refused'], out)
        res = {}
        for rel in ('vendor/c8_assembly/order8_assembly.py', 'vendor/c8_assembly/inputs_d3/two_loop.json',
                    'vendor/c8_assembly/HANDOFF_assembly.json', 'vendor/c8_assembly/POWER_PROTOCOL.md'):
            p = pkg / rel
            orig = p.read_bytes()
            b = bytearray(orig)
            b[100] ^= 1
            replace(p, bytes(b))
            rc, out, _ = gate('test', **genv)
            replace(p, orig)
            res[rel] = rc == 3 and Path(rel).name in out.get('refused', '')
        check('A-IN-4 / A-ASM-1(b): a one-byte change to a vendored file (or the HANDOFF copy) makes the gate refuse, '
              'naming it', all(res.values()), res)
        after = tree_state(pkg)
        resized = sorted((k, before[k][0], after[k][0]) for k in set(before) & set(after) if after[k][0] != before[k][0])
        check('A-IN-4: the gate creates and changes nothing (the scratch package is as before, the restored files apart)',
              set(after) == set(before) and not resized,
              {'added_or_removed': sorted(set(after) ^ set(before))[:10], 'resized (path, size before, size after)': resized[:10]})
        if post and l8_here:
            # through `production.py plan` (non-test, the wired gate) on the live inputs: run_live_flip first gives the
            # scratch package bin/ and the plan's measured-schema model (so after the snapshot above)
            rec8 = plan_gate.run_live_flip(pkg, td / 'plan_l8_flip', child_env(), 'inputs/packs/free_L8.pack')
            check('A-IN-4: a one-byte change to packs/free_L8.pack makes `production.py plan` (non-test) refuse before '
                  'creating anything (no campaign directory, nothing beside it or in TMPDIR, the package unchanged)',
                  rec8['ok'], rec8)
        # C8_INPUTS
        other = td / 'other/inputs'
        shutil.copytree(pkg / 'inputs', other, copy_function=os.link)
        rc, out, _ = gate('nontest', C8_INPUTS=str(other), **genv)
        check('A-IN-4: a non-test plan with a foreign C8_INPUTS is refused', rc == 3
              and 'non-test plan reads only the package inputs' in out.get('refused', ''), out)
        rc, out, _ = gate('test', C8_INPUTS=str(other), **genv)
        check('A-IN-4: a test plan with a foreign C8_INPUTS passes, the foreign directory recorded as a test-only reason',
              rc == 0 and out.get('inputs') == str(other.resolve())
              and any('C8_INPUTS' in x for x in out.get('test_only_reasons', [])), out)
        rel_spelling = os.path.relpath(pkg / 'inputs', Path.cwd())
        rc, out, _ = gate('nontest', C8_INPUTS=rel_spelling, **genv)
        check('A-IN-4: C8_INPUTS naming the package inputs/ (another spelling) is not foreign',
              rc == 0 and not any('C8_INPUTS' in x for x in out.get('test_only_reasons', [])), out)
        c7dir = td / 'c7/inputs'
        c7dir.mkdir(parents=True)
        shutil.copy2(C7_MANIFEST, c7dir / 'manifest.json')
        rc, out, _ = gate('test', C8_INPUTS=str(c7dir), **genv)
        check('A-IN-4 / HD7: a C7(3) inputs manifest is refused naming LRI_C7_D3_HPC@a6ce987', rc == 3
              and 'LRI_C7_D3_HPC@a6ce987' in out.get('refused', ''), out)
        d2dir = td / 'd2/inputs'
        d2dir.mkdir(parents=True)
        m2 = dict(m, schema='c8-d2-hpc-inputs-1', dimension=2)
        (d2dir / 'manifest.json').write_text(json.dumps(m2, indent=2) + '\n')
        rc, out, _ = gate('test', C8_INPUTS=str(d2dir), **genv)
        check('A-IN-4 / HD7: a dimension-2 inputs manifest is refused', rc == 3 and 'dimension 2' in out.get('refused', ''),
              out)
        # ---- S4-003: test inputs never pass as the production inputs -------------------------------------------------
        if post:
            try:
                comp, cerr = pi.inventory_complete(INPUTS, m), None
            except (ValueError, OSError) as e:
                comp, cerr = None, str(e)
            check('S4-003: prepare_inputs.inventory_complete (what a non-test plan now needs) accepts the package inputs: '
                  'L7 and L8 exactly selection.json\'s kernels at their MEMBERS_d3.sha256 hashes, C7(3)\'s L3-L6, the '
                  'manifest\'s counts', cerr is None, cerr or comp)
            # R2-S1-03: a count-preserving duplicate (free L3 G6 replaced by a second G3 row; power L7's last row by its
            # first): counts, packs and their pins kept, only the manifest's inventory hash refreshed
            dup = {}
            for name, (s_, L_, fn) in {'free L3 G6 -> G3': ('free', '3', lambda rows: [next(q for q in rows if q['id'] == 3)
                                                                                          if r['id'] == 6 else r for r in rows]),
                                       'power L7 last -> first': ('power', '7', lambda rows: rows[:-1] + rows[:1])}.items():
                dd = td / 'dup' / name.split()[0] / 'inputs'
                for rel in (*pi.STAGE2B_FILES, 'manifest.json'):
                    (dd / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(INPUTS / rel, dd / rel)
                inv = json.loads((INPUTS / 'inventory.json').read_bytes())
                inv[s_][L_] = fn(inv[s_][L_])
                text = pi.inventory_text(inv).encode()
                (dd / 'inventory.json').write_bytes(text)
                md = json.loads(json.dumps(m))
                md['sha256']['inventory.json'] = hashlib.sha256(text).hexdigest()
                same = [len(inv[x][y]) for x in pi.SECTORS for y in inv[x]] == [md['counts'][x][y] for x in pi.SECTORS for y in inv[x]] \
                    and {k: v for k, v in md['sha256'].items() if k != 'inventory.json'} == {k: v for k, v in m['sha256'].items() if k != 'inventory.json'}
                try:
                    dup[name] = dict(counts_and_packs_kept=same, accepted=pi.inventory_complete(dd, md))
                except (ValueError, OSError) as e:
                    dup[name] = dict(counts_and_packs_kept=same, refused=str(e)[-300:])
            check('R2-S1-03: a duplicated graph id with the counts, the packs and their pins kept and only the inventory '
                  'hash refreshed (free L3: G6 replaced by a second G3 row, the finding\'s case; power L7) is refused by '
                  'inventory_complete, naming the repeated id',
                  all(v['counts_and_packs_kept'] and 'graph ids repeated' in v.get('refused', '') for v in dup.values())
                  and 'free L3: graph ids repeated [3]' in dup['free L3 G6 -> G3'].get('refused', ''), dup)
            # inputs_mini installed AS a scratch package's own inputs/ (where `mini --out inputs` used to put it)
            mp2 = td / 'mini_pkg'
            (mp2 / 'tools').mkdir(parents=True)
            for f in list((ROOT / 'tools').glob('*.py')) + [ROOT / 'tools/VENDORED.json']:
                shutil.copy2(f, mp2 / 'tools' / f.name)
            shutil.copytree(ROOT / 'vendor', mp2 / 'vendor', copy_function=os.link,
                            ignore=shutil.ignore_patterns('__pycache__', '.DS_Store'))
            pi.materialize_mini(mp2 / 'inputs')

            def gate2(mode: str, **env):
                r = subprocess.run([sys.executable, '-B', str(gate_py), str(mp2 / 'tools'), mode], capture_output=True,
                                   text=True, env=child_env(**env))
                try:
                    return r.returncode, json.loads(r.stdout.strip().splitlines()[-1])
                except (ValueError, IndexError):
                    return r.returncode, {'error': (r.stdout + r.stderr)[-600:]}
            rc, out = gate2('nontest')
            check('S4-003: inputs_mini installed as a package\'s own inputs/: its test_inputs marker makes a non-test plan '
                  'test-only', rc == 0 and out.get('test_only') is True
                  and any(x.startswith('test_inputs') for x in out.get('test_only_reasons', [])), out)
            man = mp2 / 'inputs/manifest.json'
            mm = json.loads(man.read_bytes())
            mm.pop('test_inputs', None)
            replace(man, (json.dumps(mm, indent=2) + '\n').encode())
            rc, out = gate2('nontest')
            rc2, out2 = gate2('test')
            check('S4-003: the same without the marker: a non-test plan is refused, its inventory incomplete against '
                  'selection.json (8 L8 kernels per sector); a test plan still passes',
                  rc == 3 and 'incomplete against H1\'s selection.json' in out.get('refused', '')
                  and 'free L8: 8 kernels' in out['refused'] and rc2 == 0 and out2.get('test_only') is True,
                  dict(nontest=out, test=out2))
            # R2-S1-02: no manifest content lifts the completeness check. A "synthetic" manifest (pinned or not) makes a
            # non-test plan test-only (or is refused) wherever no seam is honoured; a tree without pins and without the
            # label is refused. The environment's seam (C8_TEST_SYNTHETIC_INPUTS=1) is honoured only under C8_SITE=fake off
            # the real sites, and then only for tests/c8pkg.py's label with neither pin.
            seam = {pi.SYNTHETIC_SEAM: '1'}
            nopins = dict(inventory8_d2_manifest_sha256=None, d3_payload_manifest_sha256=None)
            var = {}
            for name, edit, env in (
                    ('synthetic label, pins kept', dict(synthetic=pi.SYNTHETIC_INPUTS_LABEL), dict(C8_SITE='')),
                    ('no label, no pins', nopins, dict(C8_SITE='')),
                    ('no label, no pins, seam under fake', nopins, dict(C8_SITE='fake', **seam)),
                    ('synthetic label, no pins', dict(synthetic=pi.SYNTHETIC_INPUTS_LABEL, **nopins), dict(C8_SITE='')),
                    ('synthetic label, no pins, C8_SITE=fake without the seam', dict(synthetic=pi.SYNTHETIC_INPUTS_LABEL, **nopins),
                     dict(C8_SITE='fake')),
                    ('synthetic label, no pins, C8_SITE=symmetry', dict(synthetic=pi.SYNTHETIC_INPUTS_LABEL, **nopins),
                     dict(C8_SITE='symmetry')),
                    ('synthetic label, no pins, seam under symmetry', dict(synthetic=pi.SYNTHETIC_INPUTS_LABEL, **nopins),
                     dict(C8_SITE='symmetry', **seam)),
                    ('synthetic label, no pins, seam without C8_SITE', dict(synthetic=pi.SYNTHETIC_INPUTS_LABEL, **nopins),
                     dict(C8_SITE='', **seam)),
                    ('synthetic label, no pins, seam under fake on an Expanse host',
                     dict(synthetic=pi.SYNTHETIC_INPUTS_LABEL, **nopins), dict(C8_SITE='fake', SLURM_CLUSTER_NAME='expanse', **seam)),
                    ('synthetic label, pins kept, seam under fake', dict(synthetic=pi.SYNTHETIC_INPUTS_LABEL), dict(C8_SITE='fake', **seam)),
                    ('another synthetic value, no pins, seam under fake', dict(synthetic=True, **nopins), dict(C8_SITE='fake', **seam)),
                    ('synthetic label, no pins, seam under fake', dict(synthetic=pi.SYNTHETIC_INPUTS_LABEL, **nopins),
                     dict(C8_SITE='fake', **seam))):
                x = json.loads(json.dumps(mm))
                x.update(edit)
                replace(man, (json.dumps(x, indent=2) + '\n').encode())
                var[name] = gate2('nontest', **env)
            replace(man, (json.dumps(mm, indent=2) + '\n').encode())

            def held(rc_out) -> bool:   # refused, or test-only with the synthetic reason; never a non-test plan
                rc, out = rc_out
                return rc == 3 or (rc == 0 and out.get('test_only') is True
                                   and any(r.startswith('synthetic') for r in out.get('test_only_reasons', [])))
            nonfake = [k for k in var if ('synthetic' in k or 'another' in k) and k != 'synthetic label, no pins, seam under fake']
            r2, o2 = var['no label, no pins']
            r2s, o2s = var['no label, no pins, seam under fake']
            rf, of = var['synthetic label, no pins, seam under fake']
            # on a real site (val1 on symmetry or Expanse) the seam is never honoured (C8_SITE=fake is refused there): the property
            # that holds is that no variant gives a non-test plan; the Mac's expectations below need a host off the real sites
            import ledger
            real_host = sorted(ledger.host_sites({k: v for k, v in os.environ.items() if k != 'SLURM_CLUSTER_NAME'}))
            if real_host:
                check(f'R2-S1-02 on a real site ({",".join(real_host)}): no synthetic or unpinned manifest variant, seam or not, gives a '
                      'non-test plan (each is refused or test-only); the seam-honoured case is the Mac\'s',
                      all(rc == 3 or (rc == 0 and o.get('test_only') is True) for rc, o in var.values()),
                      {k: (rc, {kk: vv for kk, vv in o.items() if kk in ('test_only', 'refused')}) for k, (rc, o) in var.items()})
            else:
             check('R2-S1-02: a synthetic manifest never makes a non-test plan without the seam honoured: the label (pinned or '
                   'not), another synthetic value, and the seam under symmetry, without C8_SITE or on an Expanse host are each '
                   'refused or test-only (the seam set off the fakes refused, on a real host with ledger.py\'s text, which val1 '
                   'records as SITE_REFUSED); a tree without pins and without the label is '
                   'refused, seam or not; only the seam under C8_SITE=fake off the real sites, on the label with neither pin, '
                   'skips the completeness check (recorded)',
                   all(held(var[k]) for k in nonfake)
                   and all(var[k][0] == 3 and pi.SYNTHETIC_SEAM in var[k][1].get('refused', '') for k in
                           ('synthetic label, no pins, seam under symmetry', 'synthetic label, no pins, seam without C8_SITE',
                            'synthetic label, no pins, seam under fake on an Expanse host'))
                   and "this host is expanse but C8_SITE is 'fake'" in var['synthetic label, no pins, seam under fake on an Expanse host'][1]['refused']
                   and r2 == 3 and 'needs the Stage-2b inputs of H1' in o2.get('refused', '')
                   and r2s == 3 and 'needs the Stage-2b inputs of H1' in o2s.get('refused', '')
                   and rf == 0 and of.get('test_only') is False and 'skipped' in (of.get('inventory_complete') or {}),
                   {k: (rc, {kk: vv for kk, vv in o.items() if kk in ('test_only', 'test_only_reasons', 'refused', 'inventory_complete')})
                    for k, (rc, o) in var.items()})
            st = tree_state(mp2)
            lnk = td / 'mini_pkg_inputs_link'
            lnk.symlink_to(mp2 / 'inputs')
            res = {}
            for args in (['mini', '--out', mp2 / 'inputs'], ['mini', '--out', mp2 / 'inputs/sub'], ['mini', '--out', mp2],
                         ['mini', '--out', lnk], ['mini-materialize', '--to', mp2 / 'inputs'],
                         ['mini-materialize', '--to', lnk / 'x']):
                cp = subprocess.run([sys.executable, '-B', str(mp2 / 'tools/prepare_inputs.py'), *map(str, args)],
                                    capture_output=True, text=True, env=child_env())
                res[' '.join(map(str, args)).replace(str(td), '<td>')] = (cp.returncode, 'overlaps the package inputs'
                                                                            in cp.stderr)
            after2 = tree_state(mp2)
            check('S4-003: prepare_inputs.py mini --out and mini-materialize --to refuse a destination equal to, inside, '
                  'containing or symlinked to the package inputs/ before reading or writing anything',
                  all(v == (1, True) for v in res.values()) and after2 == st,
                  dict(results=res, changed=sorted(k for k in set(st) | set(after2) if st.get(k) != after2.get(k))[:10]))
            # R2-S1-05: links below or at the default destination. mp2's inputs are first made to differ from what `mini`
            # writes (no test_inputs marker; one byte appended to its free_L8.pack, re-pinned), so a writer that follows a
            # link into them changes their bytes: the default destination tests/fixtures/inputs_mini symlinked to the
            # package inputs (A), an --out whose packs/ links to inputs/packs (B), an --out holding the old temporary
            # path .manifest.json.tmp as a link to inputs/manifest.json (C); mini-materialize into a destination whose
            # packs/ links to inputs/d3 (D) or whose manifest.json links to inputs/inventory.json (E). Each must exit 1
            # before writing anything, A, B, D and E naming the overlap; every byte of mp2's inputs/ is unchanged.
            p8 = mp2 / 'inputs/packs/free_L8.pack'
            replace(p8, p8.read_bytes() + b'\n')
            mm['sha256']['packs/free_L8.pack'] = sha256(p8)
            replace(man, (json.dumps(mm, indent=2) + '\n').encode())

            def content(d: Path) -> dict:
                return {q.relative_to(d).as_posix(): (q.is_symlink(), hashlib.sha256(q.read_bytes()).hexdigest() if q.is_file() else None)
                        for q in sorted(d.rglob('*'))}
            prod0, fix = content(mp2 / 'inputs'), mp2 / 'tests/fixtures/inputs_mini'
            fix.parent.mkdir(parents=True)
            fix.symlink_to(mp2 / 'inputs')
            outs = {k: td / f'r2s105_{k}' for k in 'BCDE'}
            for k in 'BCD':
                outs[k].mkdir()
            (outs['B'] / 'packs').symlink_to(mp2 / 'inputs/packs')
            (outs['C'] / '.manifest.json.tmp').symlink_to(mp2 / 'inputs/manifest.json')
            (outs['D'] / 'packs').symlink_to(mp2 / 'inputs/d3')
            outs['E'].mkdir()
            (outs['E'] / 'manifest.json').symlink_to(mp2 / 'inputs/inventory.json')
            res5 = {}
            for k, args in (('A', ['mini']), ('B', ['mini', '--out', outs['B']]), ('C', ['mini', '--out', outs['C']]),
                            ('D', ['mini-materialize', '--to', outs['D']]), ('E', ['mini-materialize', '--to', outs['E']])):
                if k == 'D':   # mini-materialize reads the real fixture (A's link replaced by a copy)
                    fix.unlink()
                    shutil.copytree(ROOT / pi.MINI, fix)
                cp = subprocess.run([sys.executable, '-B', str(mp2 / 'tools/prepare_inputs.py'), *map(str, args)],
                                    capture_output=True, text=True, env=child_env())
                res5[k] = (cp.returncode, 'overlaps the package inputs' in cp.stderr, cp.stderr.strip()[-200:])
            prod1 = content(mp2 / 'inputs')
            written = {k: sorted(q.name for q in outs[k].rglob('*') if not q.is_symlink()) for k in 'BCDE'}
            check('R2-S1-05: `prepare_inputs.py mini` with its default destination symlinked to the package inputs, with an '
                  '--out whose packs/ links into them or holding a temporary path linked into them, and `mini-materialize` '
                  'into a destination whose packs/ or manifest.json links into them, each refuse before writing anything; '
                  'every byte of the package inputs is unchanged',
                  all(v[0] == 1 for v in res5.values()) and all(res5[k][1] for k in 'ABDE') and prod1 == prod0
                  and not any(written.values()),
                  dict(results=res5, written=written, changed=sorted(k for k in set(prod0) | set(prod1) if prod0.get(k) != prod1.get(k))[:10]))
            # the publishing path itself: mini on a fresh --out (here the mini of the materialized mini) writes
            # tests/fixtures/inputs_mini's four files byte for byte, nothing else, and a second run changes nothing
            fresh = td / 'r2s105_fresh'
            cps = [subprocess.run([sys.executable, '-B', str(mp2 / 'tools/prepare_inputs.py'), 'mini', '--out', str(fresh)],
                                  capture_output=True, text=True, env=child_env()) for _ in range(2)]
            try:
                ch = [json.loads(c.stdout)['changed'] for c in cps]
            except (ValueError, KeyError):
                ch = None
            check('R2-S1-05: mini on a fresh --out publishes exactly the four inputs_mini files (equal to the committed '
                  'fixture) through its private staging directory, which it removes; a second run changes nothing',
                  ch == [['inventory.json', *pi.L8_PACKS, 'manifest.json'], []]
                  and sorted(q.relative_to(fresh).as_posix() for q in fresh.rglob('*') if q.is_file()) == sorted(pi.MINI_OWN)
                  and all((fresh / r).read_bytes() == (ROOT / pi.MINI / r).read_bytes() for r in pi.MINI_OWN)
                  and sorted(q.name for q in fresh.iterdir()) == ['inventory.json', 'manifest.json', 'packs'],
                  dict(changed=ch, err=[c.stderr[-300:] for c in cps]))
        # the L8 skip rule on a synthetic manifest (Stage 2b pins the real L8 packs)
        l8dir = td / 'l8/inputs'
        shutil.copytree(pkg / 'inputs', l8dir, copy_function=os.link,
                        ignore=shutil.ignore_patterns('free_L8.pack', 'power_L8.pack'))
        m8 = json.loads((l8dir / 'manifest.json').read_bytes())
        m8['sha256'].update({r: hashlib.sha256(r.encode()).hexdigest() for r in pi.L8_PACKS})
        m8['l8_present'] = True
        (l8dir / 'manifest.json').unlink()
        (l8dir / 'manifest.json').write_text(json.dumps(m8, indent=2) + '\n')
        rc, out, _ = gate('test', C8_INPUTS=str(l8dir))
        ok1 = rc == 3 and 'free_L8.pack' in out.get('refused', '') and 'missing' in out['refused']
        rc, out, err = gate('test', C8_INPUTS=str(l8dir), C8_ALLOW_NO_L8='1')
        ok2 = rc == 0 and out.get('skipped') == list(pi.L8_PACKS) and err.count('SKIPPED') == 2 \
            and any('C8_ALLOW_NO_L8' in x for x in out.get('test_only_reasons', []))
        (l8dir / 'packs/free_L8.pack').write_bytes(b'not the pinned pack\n')
        rc, out, _ = gate('test', C8_INPUTS=str(l8dir), C8_ALLOW_NO_L8='1')
        ok3 = rc == 3 and 'free_L8.pack' in out.get('refused', '') and 'Checksum mismatch' in out['refused']
        check('verify: a missing pinned L8 pack is refused, skipped (SKIPPED, test-only) only with C8_ALLOW_NO_L8=1, and a '
              'present but different one is refused even then (synthetic manifest)', ok1 and ok2 and ok3,
              dict(refused_without=ok1, skipped_with=ok2, wrong_present=ok3))
        rc, out, _ = gate('prepare')
        check('transitional: prepare_inputs.prepare() (the unported C7(3) planner\'s call) refuses the C8(3) inputs',
              rc == 3 and 'Stage 3a' in out.get('refused', ''), out)
        # ---- A-IN-4 through the real `production.py plan` (tests/plan_gate.py; Stage 2a repair rounds 1 and 2) ---
        # On the runner's fixed input state (l7_complete and l8_present false, no L8 pin; the live state at Stage 2a,
        # so nothing is rewritten now), checked first with the package's own gate. Transitional (Stage 2a): the
        # unported C7(3) planner refuses every request before creating anything. Wired (Stage 3a on): the one-byte
        # flips, the foreign C8_INPUTS and l7_complete: false -> test-only, through `plan`, creating nothing on a
        # refusal (G3a evidence); STAGE3A unset then fails. C8_ALLOW_NO_L8 is passed through as the caller set it.
        allow = {'C8_ALLOW_NO_L8': os.environ['C8_ALLOW_NO_L8']} if os.environ.get('C8_ALLOW_NO_L8') else {}
        pg = plan_gate.run_plan_gate(pkg, td / 'plan_gate', child_env(**allow))
        for c in pg['checks']:
            check('A-IN-4 ' + c['check'], c['passed'], c['detail'])
        fx = pg['fixed']
        notes.append(f'plan gate through production.py plan: mode {pg["mode"]}; fixed input state: '
                     f'{"rewritten " + json.dumps(fx) if fx["manifest_rewritten"] else "the live inputs unchanged"}; '
                     f'{pg["note"]}')
        # the runner's self-test: fake wired planners in a copy of the scratch package (hard links; flips replace)
        fk = td / 'fake_pkg'
        shutil.copytree(pkg, fk, copy_function=os.link)
        expect = {'correct': set(), 'ignores-test-only': {'untouched'},
                  'directory-first': {'pinned-input', 'vendored', 'foreign-inputs'},
                  'tmpdir-first': {'pinned-input', 'vendored', 'foreign-inputs'},
                  'no-gate': {'untouched', 'pinned-input', 'vendored', 'foreign-inputs'}}
        got = {}

        def fake(where: Path, variant: str) -> None:
            (where / 'tools/production.py').unlink()
            (where / 'tools/production.py').write_text(plan_gate.fake_planner(variant))

        def failed_of(r: dict) -> list:
            return sorted(c['scenario'] for c in r['checks'] if not c['passed'])
        for variant in expect:
            fake(fk, variant)
            r = plan_gate.run_plan_gate(fk, td / f'fake_{variant}', child_env(), stage3a=plan_gate.FAKE_STAGE3A)
            got[variant] = dict(mode=r['mode'], static=r['static_wired'], failed=failed_of(r),
                                scenarios=[c['scenario'] for c in r['checks']])
        r = plan_gate.run_plan_gate(fk, td / 'fake_unset', child_env(), stage3a=None)
        unset_ok = r['mode'] == 'wired' and failed_of(r) == ['obligation'] \
            and [c['scenario'] for c in r['checks']] == ['fixed-state', 'obligation'] \
            and 'Stage-3a obligation' in r['checks'][-1]['check']
        check('plan_gate self-test (fake wired planners): a correct one passes; one ignoring the gate\'s test_only, one '
              'creating the campaign directory or a TMPDIR entry before the gate, and one never calling the gate (wired '
              'by behaviour) each fail; a wired planner with plan_gate.STAGE3A unset fails, naming the obligation',
              all(got[v]['mode'] == 'wired' and set(got[v]['failed']) == expect[v]
                  and got[v]['scenarios'] == ['fixed-state', *plan_gate.SCENARIOS] for v in expect)
              and got['no-gate']['static'] is False and unset_ok, dict(variants=got, unset_obligation=unset_ok))
        # the runner on simulated post-Stage-2b live inputs (repair round 2): Stage 2b may land before or after the
        # Stage-3a wiring, so a correct wired planner must pass on Expanse (L8 present, not test-only) and on the Mac
        # (L8 pinned but absent, C8_ALLOW_NO_L8=1 as the Mac command sets it). The simulated states are first shown to
        # be what Stage 2b gives, by the real gate: on Expanse a non-test plan is no longer test-only; on the Mac the
        # missing L8 packs are refused without C8_ALLOW_NO_L8 and skipped (test-only) with it.
        sims = {}
        for site, present in (('expanse', True), ('mac', False)):
            sp = td / f'sim2b_{site}'
            shutil.copytree(fk, sp, copy_function=os.link)
            fake(sp, 'correct')
            made = plan_gate.fake_stage2b_inputs(sp, present)
            gw = td / f'sim2b_{site}_gate'
            g0 = plan_gate.gate(sp, gw, 'plain', child_env())
            g1 = plan_gate.gate(sp, gw, 'allow', child_env(C8_ALLOW_NO_L8='1'))
            r0, r1 = g0['result'] or {}, g1['result'] or {}
            if present:
                real = g0['returncode'] == 0 and r0.get('test_only') is False and not r0.get('skipped')
            else:
                real = (g0['returncode'] != 0 and 'free_L8.pack' in g0['stderr'] and 'missing' in g0['stderr']
                        and g1['returncode'] == 0 and r1.get('test_only') is True
                        and r1.get('skipped') == list(pi.L8_PACKS))
            env = child_env() if present else child_env(C8_ALLOW_NO_L8='1')
            r = plan_gate.run_plan_gate(sp, td / f'sim2b_{site}_run', env, stage3a=plan_gate.FAKE_STAGE3A)
            fx = r['fixed']
            fixed_ok = (fx['dropped_pins'] == list(pi.L8_PACKS) and fx['set_false'] == ['l7_complete', 'l8_present']
                        and fx['dropped_counts'] == ['free:8', 'power:8'] and fx['dropped_inventory_rows'] == made['l8_rows']
                        and fx['inventory_repinned'] and fx['removed_files'] == (list(pi.L8_PACKS) if present else []))
            sims[site] = dict(simulated=made, real_stage2b_state=real, mode=r['mode'], failed=failed_of(r), fixed=fx,
                              fixed_ok=fixed_ok, gate_plain=dict(rc=g0['returncode'], test_only=r0.get('test_only'),
                                                                 stderr=g0['stderr'][-200:]),
                              gate_allow=dict(rc=g1['returncode'], test_only=r1.get('test_only'),
                                              skipped=r1.get('skipped')))
        check('plan_gate on simulated post-Stage-2b inputs (l7_complete true, L8 pinned): the runner puts them into '
              'its fixed state (L8 pins, counts, rows and packs dropped, l7_complete and l8_present false) and a '
              'correct wired planner passes every scenario, on Expanse (L8 present) and on the Mac (L8 absent, '
              'C8_ALLOW_NO_L8=1 passed through)',
              all(v['real_stage2b_state'] and v['fixed_ok'] and v['mode'] == 'wired' and not v['failed']
                  for v in sims.values()), sims)
    finally:
        if a.keep:
            notes.append(f'scratch kept: {td}')
        else:
            shutil.rmtree(td, ignore_errors=True)
    import numpy as np
    commit = git('rev-parse', 'HEAD').stdout.strip() if (ROOT / '.git').exists() else None
    rec = dict(schema='c8-d3-gate-1', gate='check_inputs: regeneration, A-IN-1, A-IN-2, A-IN-4 (L <= 7)',
               passed=bool(results) and not failed, failed=failed, checks=results, notes=notes,
               seconds=round(time.time() - t0, 1), commit=commit, root=str(ROOT), host=platform.node(),
               machine=platform.machine(), python=sys.version.split()[0], numpy=np.__version__,
               C8_ALLOW_NO_L8=os.environ.get('C8_ALLOW_NO_L8'))
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rec, indent=1) + '\n')
    for n in notes:
        print('NOTE', n)
    print(f'check_inputs: {len(results) - len(failed)}/{len(results)} checks passed ({rec["seconds"]} s)')
    return 0 if rec['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
