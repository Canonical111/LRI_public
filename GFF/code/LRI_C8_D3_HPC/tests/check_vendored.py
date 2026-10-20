#!/usr/bin/env python3
"""A-ASM-1: the vendored order-8 assembly against its HANDOFF, its pins and the read rule (PLAN E.1, component F).

--standalone, A-ASM-1(a) (G-H2 on the Mac; with --no-review-record also on a cluster export, J-E2/J-VAL-1):
  * vendor/c8_assembly/HANDOFF_assembly.json is the HANDOFF byte copy at the pinned sha256 f5ff6a35... (PLAN HD4), the
    sha256 tools/VENDORED.json records; VENDORED.json records C62d's accepting review of this HANDOFF, no required
    change, and the step-0 verdict-gate decision with its scope ("this HANDOFF version only");
  * vendor/c8_assembly/ holds exactly the 13 files the HANDOFF lists plus the HANDOFF copy (none missing, none extra,
    no other directory entry such as __pycache__), each a regular file at the sha256, md5 and size the HANDOFF
    records, and VENDORED.json lists the same files with the same pins;
  * VENDORED.json carries the consumer-side wording of the H2 record (PLAN F12): loop7_gate an order-8 gate; jacobians
    float or complex means only; power_null_rows compared on numeric fields; the run rules;
  * the fixtures (C62d's R16): vendor/c8_assembly_fixtures/ holds exactly VENDORED.json's list, every file a regular
    file at its sha256 and size; each source pin is re-verified where it is reachable (a reference/ copy at its
    reference/SHA256SUMS_c8 entry always; a git object of this repository when .git exists; a git object of
    LRI_C7_D2_HPC or LRI_C8_D2_HPC when that repository is next to this package), otherwise a NOTE says so;
  * no symlink is tracked anywhere in the package (`git ls-files -s` mode 120000, or a walk of an export);
  * the review record LRI_C8_shared/inventory/reviews/order8_assembly_<sha12>.json, when reachable (give
    --no-review-record on a cluster export), names this HANDOFF, accepts it with the same verdict gate, requires no
    change of C63d and has a status for every checklist step 0-10;
  * the interface: the vendored order8_assembly.py, imported here without writing bytecode, exports every name the
    package uses with the signature VENDORED.json records (read there from the source with ast) and the recorded
    constants (FLAG_PULL, ORDER3_ROUNDING, ...);
  * the exact-check classification tests/fixtures/exact_check_keys.json covers every leaf of the vendored
    exact_check_results.json exactly once and pins that file's sha256 (tests/exact_keys.py);
  * the read rule (E.1): a static scan of every tracked code file outside tests/ and vendor/ finds the vendored tree
    or its module names only in files on READ_RULE (the importers, hashers, executors and the writer the plan names),
    and an open/import/subprocess spy in a scratch package (Stage 2a, G2a) shows that
      - prepare_inputs.verify() (which `plan` calls) opens vendored files only through the hash helper common.digest,
        starts no process and imports nothing from vendor/;
      - prepare_inputs.build() (`make inputs`) opens vendored files only through common.digest and
        common.verified_bytes, the latter only for the HANDOFF copy and inputs_d3/{two_loop.json,gamma_d3_8.txt}
        (copied after the hash check, HD4), imports nothing from vendor/ and starts exactly one process: the vendored
        prepare_low8.py --d 3 in compare mode (no --write) under python -B;
    a negative control (a scratch tool importing the vendored module) must be caught by the same spy. Since Stage 3a
    the same spy runs `production.py plan` (vendored files opened only through common.digest, via the input gate) and
    `run --index` (nothing under vendor/ opened, no vendored process or module; A-ORC-13) in a tests/c8pkg.py scratch
    package with synthetic complete inputs and the fake worker.
Default (no --standalone), A-ASM-1(a) and (b) (G2a, after `make inputs` wrote the pins):
  * inputs/manifest.json carries vendored_assembly_handoff_sha256 and every vendored file's sha256, equal to
    VENDORED.json and the HANDOFF (a manifest without them fails this mode, never skips it);
  * prepare_inputs.verify() (which `plan` calls) passes, and refuses after a one-byte change to a vendored file in a
    scratch export;
  * the same flip through the real `production.py plan` in that export (tests/plan_gate.py, Stage 2a repair rounds 1
    and 2), on the runner's fixed input state (l7_complete and l8_present false, no L8 pin, whatever the live stage;
    the export's own gate must first pass it as a test-only plan; C8_ALLOW_NO_L8=1 is passed through): while plan is
    transitional (the unported C7(3) planner, which does not call plan_inputs) it is refused with prepare()'s Stage-3a
    message before anything is created; once Stage 3a wires plan_inputs into plan (G3a evidence, before or after Stage
    2b) it must be refused naming the vendored file, with no campaign directory, nothing beside it or in TMPDIR and the
    export unchanged, and the untouched non-test request must come out test-only (l7_complete: false); with
    plan_gate.STAGE3A unset the wired check fails, naming the obligation.
Usage: python3 -B tests/check_vendored.py [--standalone] [--no-review-record] [--output FILE]
Exit status 0 when every check passes."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'vendor/c8_assembly'
FIXTURES = ROOT / 'vendor/c8_assembly_fixtures'
VENDORED = ROOT / 'tools/VENDORED.json'
HANDOFF_SHA256 = 'f5ff6a353371abdc22a296d106e83af03885dfa672a25662fa59f468b9948437'  # PLAN F11, HD4
GATE_DECISIONS = {'accepted_documentation_only_minor_fixes', 'all_verifier_verdicts_pass'}
REQUIRED_NAMES = {'coefficients', 'jacobians', 'campaign_moments', 'sector_assembly', 'power_null_rows',
                  'top_slot_gate', 'loop7_gate', 'affinity_gate', 'ms8_rows', 'ms8_value'}
# PLAN E.1 "One read rule": the only code files outside tests/ and vendor/ that may name the vendored tree or its
# modules, with their role. Hashers open vendored files only through common.digest; importers import the vendored
# order8_assembly; `make inputs` executes prepare_low8.py --d 3 in compare mode; the writer is tools/vendor_assembly.py.
READ_RULE = {
    'tools/vendor_assembly.py': 'writer: copies and hashes the HANDOFF files, measures the read set by running the '
                                "HANDOFF's own tests on a temporary copy, reads signatures with ast (no import)",
    'tools/prepare_inputs.py': 'hash (verify(), hence plan); make inputs: copies inputs_d3/ after the hash check and '
                               'executes prepare_low8.py --d 3 in compare mode (HD4)',
    'tools/production.py': 'hash (verify_base: merge, assemble)',
    'tools/verify_delivery.py': 'hash',
    'tools/write_delivery.py': 'hash (the delivery manifest)',
    'tools/assemble.py': 'import', 'tools/combine.py': 'import', 'tools/verify_result.py': 'import',
    'tools/report.py': 'import', 'tools/pilot_report.py': 'import', 'tools/design_fallback.py': 'import',
    'Makefile': 'executes prepare_low8.py --d 3 in compare mode (make inputs, HD4)',
}
SCAN_DIRS = ('tools', 'slurm', 'src', 'gen3', 'c7_legacy', 'bin')
SCAN_FILES = ('Makefile',)
MENTION = re.compile(rb'vendor/c8_assembly|c8_assembly_fixtures|order8_assembly|exact_check|prepare_low8')
F12_WORDING = {'loop7_gate': 'order-8 gate', 'jacobians': 'float or complex means only',
               'power_null_rows': 'numeric fields (delta, se, pull, flag)'}

SPY = r'''
import importlib, json, os, sys
tools, vendor, out, entry = sys.argv[1:5]
kwargs = json.loads(sys.argv[5]) if len(sys.argv) > 5 else {}
sys.path.insert(0, tools)
events = []
procs = []
def _frames():
    f = sys._getframe(2)
    while f is not None:
        yield f
        f = f.f_back
def hook(ev, args):
    if ev == 'subprocess.Popen':
        procs.append([os.fsdecode(x) for x in (args[1] if isinstance(args[1], (list, tuple)) else [args[1]])])
        return
    if ev != 'open' or not args or isinstance(args[0], int):
        return
    p = os.path.realpath(os.fsdecode(args[0]))
    if p == vendor or p.startswith(vendor + os.sep):
        events.append(dict(path=p, mode=str(args[1]) if len(args) > 1 else '',
                           stack=[(f.f_code.co_filename, f.f_code.co_name) for f in _frames()]))
sys.addaudithook(hook)
err = None
try:
    mod, _, fn = entry.partition(':')
    m = importlib.import_module(mod)
    if fn:
        getattr(m, fn)(**kwargs)
except Exception as e:
    err = f'{type(e).__name__}: {e}'
mods = sorted(n for n, m in list(sys.modules.items())
              if getattr(m, '__file__', None) and os.path.realpath(m.__file__).startswith(vendor + os.sep))
json.dump(dict(events=events, procs=procs, vendored_modules=mods, error=err), open(out, 'w'))
'''
SPY_CONTROL = '''"""Negative control of tests/check_vendored.py: a tool that imports the vendored module, opens a vendored file
without the hash helpers and starts a process (never committed)."""
import subprocess, sys
from pathlib import Path
sys.dont_write_bytecode = True
_V = Path(__file__).resolve().parents[1] / 'vendor/c8_assembly'
sys.path.insert(0, str(_V))
import order8_assembly  # noqa: E402,F401
with open(_V / 'inputs_d3/two_loop.json', 'rb') as f:
    f.read()
subprocess.run([sys.executable, '-B', '-c', 'pass'], check=True)
'''


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def md5_file(p: Path) -> str:
    h = hashlib.md5()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def entries(d: Path) -> tuple[dict[str, Path], list[str]]:
    """Files (regular or symlink) under d by relative path, and every other non-directory or unexpected entry."""
    files, odd = {}, []
    for p in sorted(d.rglob('*')):
        rel = p.relative_to(d).as_posix()
        if p.is_symlink():
            files[rel] = p
            odd.append(f'symlink {rel}')
        elif p.is_file():
            files[rel] = p
        elif not p.is_dir():
            odd.append(f'special {rel}')
        elif p.name in ('__pycache__', '.pytest_cache'):
            odd.append(f'directory {rel}')
    return files, odd


def signature_record(fn) -> list:
    return [dict(name=p.name, kind=p.kind.name, default=None if p.default is inspect.Parameter.empty else repr(p.default))
            for p in inspect.signature(fn).parameters.values()]


def tracked_files() -> list[str] | None:
    if not (ROOT / '.git').exists():
        return None
    out = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '-z'], capture_output=True, check=True).stdout
    return [x for x in out.decode().split('\0') if x]


def git_blob_sha256(repo: Path, commit: str, path: str) -> str | None:
    r = subprocess.run(['git', '-C', str(repo), 'show', f'{commit}:{path}'], capture_output=True)
    return hashlib.sha256(r.stdout).hexdigest() if r.returncode == 0 else None


def run_spy(td: Path, tools: Path, vendor: str, entry: str, tag: str, kwargs: dict | None = None) -> dict:
    spy = td / 'spy.py'
    spy.write_text(SPY)
    out = td / f'{tag}.json'
    # C8_SITE is not inherited: the scratch campaigns are node-local, where D.7's Lustre file guard (C8_SITE=expanse in an
    # Expanse job) cannot run `lfs quota` (J-VAL-1)
    env = {k: v for k, v in os.environ.items()
           if k not in ('PYTHONPYCACHEPREFIX', 'PYTHONPATH', 'C8_INPUTS', 'C8_ALLOW_NO_L8', 'C8_SITE')}
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    r = subprocess.run([sys.executable, '-B', str(spy), str(tools), vendor, str(out), entry, json.dumps(kwargs or {})],
                       capture_output=True, text=True, env=env, cwd=td)
    if not out.exists():
        return dict(events=[], procs=[], vendored_modules=['?'], error=(r.stdout + r.stderr)[-500:])
    return json.loads(out.read_text())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--standalone', action='store_true', help='A-ASM-1(a) only (before G2a)')
    ap.add_argument('--no-review-record', action='store_true', help='the review record is not reachable (cluster)')
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    sys.dont_write_bytecode = True
    results, failed, notes = [], [], []

    def check(name: str, ok: bool, detail='') -> None:
        detail = detail if isinstance(detail, str) else json.dumps(detail, default=str)
        results.append(dict(check=name, passed=bool(ok), detail=detail[-1500:]))
        if not ok:
            failed.append(name)
        print(('PASS ' if ok else 'FAIL ') + name + (f': {detail[-600:]}' if detail and not ok else ''), flush=True)

    v = json.loads(VENDORED.read_bytes())
    hcopy = VENDOR / 'HANDOFF_assembly.json'
    hbytes = hcopy.read_bytes()
    handoff = json.loads(hbytes)
    hsha = hashlib.sha256(hbytes).hexdigest()
    # the HANDOFF copy and its acceptance
    check('the HANDOFF copy is a regular file at the pinned sha256, which VENDORED.json records',
          not hcopy.is_symlink() and hsha == HANDOFF_SHA256 == v['handoff']['sha256']
          and v['handoff']['path'] == 'vendor/c8_assembly/HANDOFF_assembly.json',
          dict(copy=hsha, pinned=HANDOFF_SHA256, vendored=v['handoff']['sha256']))
    rv = v['review']
    check('VENDORED.json records an accepting review of this HANDOFF, no required change, and the step-0 '
          'verdict-gate decision with its scope (this HANDOFF version only)',
          rv['overall_verdict'] in ('ACCEPT', 'ACCEPT_WITH_MINOR') and rv['verdict_gate'] in GATE_DECISIONS
          and rv['record'].endswith(f'order8_assembly_{hsha[:12]}.json') and rv.get('required_changes_for_C63d') == []
          and 'this HANDOFF version only' in rv.get('verdict_gate_scope', '')
          and 'does not extend to any later HANDOFF revision' in (rv.get('verdict_gate_decision') or ''), rv)
    # the complete deliverable set
    listed = {f['path']: f for f in handoff['files']}
    have, odd = entries(VENDOR)
    extra = sorted(set(have) - set(listed) - {'HANDOFF_assembly.json'})
    missing = sorted(set(listed) - set(have))
    check('vendor/c8_assembly holds exactly the 13 HANDOFF files plus the HANDOFF copy, and nothing else',
          len(listed) == 13 and not extra and not missing and not odd, dict(extra=extra, missing=missing, odd=odd))
    bad = [n for n, f in listed.items() if n in have and (have[n].is_symlink() or sha256_file(have[n]) != f['sha256']
                                                            or md5_file(have[n]) != f['md5']
                                                            or have[n].stat().st_size != f['bytes'])]
    check('every vendored file is a regular file at the sha256, md5 and size the HANDOFF records', not bad, bad)
    vf = {f['path']: f for f in v['files']}
    check('VENDORED.json lists the 13 HANDOFF files with the HANDOFF pins and their vendored paths',
          set(vf) == set(listed) and all((vf[n]['sha256'], vf[n]['md5'], vf[n]['bytes'], vf[n]['vendored_path']) ==
                                         (listed[n]['sha256'], listed[n]['md5'], listed[n]['bytes'],
                                          f'vendor/c8_assembly/{n}') for n in listed),
          sorted(set(vf) ^ set(listed)))
    pp = v.get('power_protocol', {})
    check('VENDORED.json pins POWER_PROTOCOL.md at the HANDOFF sha256',
          pp.get('sha256') == listed['POWER_PROTOCOL.md']['sha256'], pp)
    notes_ = v['interface'].get('notes', {})
    missing_wording = [k for k, phrase in F12_WORDING.items() if phrase not in notes_.get(k, '')]
    check('VENDORED.json carries the consumer-side wording of the H2 record (PLAN F12) and the run rules',
          not missing_wording and len(v.get('run_rules', [])) >= 5, dict(missing=missing_wording))
    # fixtures
    fx = {f['path']: f for f in v['fixtures']['files']}
    have, odd = entries(FIXTURES)
    check('vendor/c8_assembly_fixtures holds exactly the VENDORED.json fixtures, regular files only',
          set(have) == set(fx) and not odd and v['fixtures']['count'] == len(fx)
          and v['fixtures']['bytes'] == sum(f['bytes'] for f in fx.values()),
          dict(extra=sorted(set(have) - set(fx)), missing=sorted(set(fx) - set(have)), odd=odd))
    badfx, pins = [], dict(verified=0, not_reachable=0)
    sums = {}
    for line in (ROOT / 'reference/SHA256SUMS_c8').read_text().splitlines():
        m = re.match(r'^([0-9a-f]{64})  (\S+)  <=  (\S+)$', line)
        if m:
            sums[m.group(2)] = (m.group(1), m.group(3))
    for n, f in fx.items():
        p = have.get(n)
        if p is None or p.is_symlink() or not p.is_file() or sha256_file(p) != f['sha256'] or p.stat().st_size != f['bytes']:
            badfx.append(n)
            continue
        pin = f['source_pin']
        if pin['kind'] == 'reference_checksum':
            entry = sums.get(pin['source'])
            if entry is None or entry[0] != f['sha256'] or sha256_file(ROOT / pin['source']) != f['sha256']:
                badfx.append(f'{n} (reference pin)')
            else:
                pins['verified'] += 1
        elif pin['kind'] == 'git':
            repo = ROOT if pin['repository'] == '.' else ROOT.parent / pin['repository']
            if (repo / '.git').exists():
                if git_blob_sha256(repo, pin['commit'], pin['path']) != f['sha256']:
                    badfx.append(f'{n} (git pin {pin["repository"]}@{pin["commit"][:12]})')
                else:
                    pins['verified'] += 1
            else:
                pins['not_reachable'] += 1
        else:
            badfx.append(f'{n} (unknown pin kind {pin["kind"]})')
    if pins['not_reachable']:
        notes.append(f'{pins["not_reachable"]} fixture git pins not re-read here (repository not reachable); every '
                     'fixture was still checked against its recorded sha256')
    check('every fixture is a regular file at its recorded sha256; every reachable source pin re-verified', not badfx,
          dict(bad=badfx, pins=pins))
    tracked = tracked_files()
    if tracked is not None:
        ls = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '-s'], capture_output=True, text=True, check=True).stdout
        links = [ln.split('\t', 1)[1] for ln in ls.splitlines() if ln.startswith('120000 ')]
    else:
        links = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_symlink()]
    check('no symlink is tracked anywhere in the package', not links, links[:20])
    # the review record
    if a.no_review_record:
        notes.append(f'review record not checked here (--no-review-record): {rv["record"]}')
    else:
        rpath = ROOT.parent / rv['record']
        try:
            rbytes = rpath.read_bytes()
            rr = json.loads(rbytes)
        except (OSError, ValueError) as e:
            rbytes, rr = b'', {'error': str(e)}
        steps = rr.get('checklist', {})
        want = [s for s in steps if s.startswith('step_')]
        nums = sorted(int(s.split('_')[1]) for s in want)
        check('the review record exists, accepts this HANDOFF with the same verdict gate, requires no change of C63d '
              'and has a status for every checklist step 0-10',
              rr.get('handoff', {}).get('sha256') == hsha and rr.get('overall_verdict') == rv['overall_verdict']
              and steps.get('step_0_handoff', {}).get('verdict_gate') == rv['verdict_gate']
              and rr.get('required_changes_for_C63d') == [] and nums == list(range(11))
              and all('status' in steps[s] for s in want),
              dict(record=str(rpath), steps=nums, statuses={s: steps[s].get('status') for s in want}))
        now = hashlib.sha256(rbytes).hexdigest()
        if rbytes and now != rv.get('record_sha256_at_vendoring'):
            notes.append(f'the review record changed since vendoring (sha256 {now[:12]} vs '
                         f'{rv.get("record_sha256_at_vendoring", "")[:12]}); verdict and gate re-checked above')
    # the interface
    spec = importlib.util.spec_from_file_location('c8d3_vendored_order8_assembly_check', VENDOR / 'order8_assembly.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sigs = v['interface']['signatures']
    badsig = [n for n, s in sigs.items() if not callable(getattr(mod, n, None)) or signature_record(getattr(mod, n)) != s]
    consts = v['interface'].get('constants', {})
    badconst = [c for c, val in consts.items() if repr(getattr(mod, c, None)) != val]
    check('the vendored order8_assembly exports every used name with the recorded signature, and the recorded '
          'constants', not badsig and not badconst and set(sigs) >= REQUIRED_NAMES
          and {'FLAG_PULL', 'ORDER3_ROUNDING'} <= set(consts), dict(signatures=badsig, constants=badconst))
    # the exact-check classification
    sys.path.insert(0, str(ROOT / 'tests'))
    import exact_keys as ek  # noqa: E402
    classes = json.loads(ek.KEYS.read_bytes())
    res_bytes = (VENDOR / 'exact_check_results.json').read_bytes()
    cerr = ek.check_classes(classes, json.loads(res_bytes))
    check('tests/fixtures/exact_check_keys.json classifies every leaf of the vendored exact_check_results.json exactly '
          'once and pins it', not cerr and classes['source']['sha256'] == hashlib.sha256(res_bytes).hexdigest()
          == listed['exact_check_results.json']['sha256'] and classes['source']['handoff_sha256'] == hsha,
          dict(errors=cerr, counts=classes.get('counts')))
    # the read rule: static scan
    if tracked is not None:
        code = [t for t in tracked if t.split('/')[0] in SCAN_DIRS or t in SCAN_FILES]
    else:
        code = [p.relative_to(ROOT).as_posix() for d in SCAN_DIRS if (ROOT / d).is_dir()
                for p in (ROOT / d).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
        code += [f for f in SCAN_FILES if (ROOT / f).is_file()]
    mentions = sorted(t for t in code if t != 'tools/VENDORED.json' and (ROOT / t).is_file()
                      and MENTION.search((ROOT / t).read_bytes()))
    unlisted = [t for t in mentions if t not in READ_RULE]
    check('read rule (static): only files on the allowlist name the vendored tree or its modules', not unlisted,
          dict(unlisted=unlisted, listed_mentions={t: READ_RULE[t] for t in mentions if t in READ_RULE}))
    notes.append('read rule: files naming the vendored tree: '
                 + (', '.join(f'{t} ({READ_RULE[t].split(":")[0]})' for t in mentions if t in READ_RULE) or 'none'))
    # the read rule: open/import/subprocess spies on prepare_inputs (Stage 2a), with a negative control
    with tempfile.TemporaryDirectory(prefix='c8d3_vendor_rule_') as td:
        td = Path(td)
        pkg = td / 'pkg'
        shutil.copytree(ROOT / 'tools', pkg / 'tools', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(ROOT / 'vendor', pkg / 'vendor', ignore=shutil.ignore_patterns('__pycache__'))

        def link_tree(src: Path, dst: Path) -> None:   # hard links (packs, reference payloads), else copies
            def cp(a_, b_):
                try:
                    os.link(a_, b_)
                except OSError:
                    shutil.copy2(a_, b_)
            shutil.copytree(src, dst, copy_function=cp, ignore=shutil.ignore_patterns('__pycache__', '.DS_Store'))
        link_tree(ROOT / 'inputs', pkg / 'inputs')
        if (ROOT / 'inspect').is_dir():   # the inspect data (make inputs-inspect, Stage 3a): make inputs merges it into the inventory
            link_tree(ROOT / 'inspect', pkg / 'inspect')
        link_tree(ROOT / 'reference/inputs', pkg / 'reference/inputs')
        shutil.copy2(ROOT / 'reference/DELIVERY_MANIFEST.json', pkg / 'reference/DELIVERY_MANIFEST.json')
        vend = os.path.realpath(pkg / 'vendor')
        vfiles = {os.path.realpath(pkg / f['vendored_path']) for f in v['files']} | {os.path.realpath(pkg / v['handoff']['path'])}

        def helpers(e) -> set:
            return {fn for file, fn in e['stack'] if file.endswith('common.py') and fn in ('digest', 'verified_bytes')}
        # verify(): what `plan` calls (C8_ALLOW_NO_L8=1 lets a Mac export without the Stage-2b L8 packs pass)
        rec = run_spy(td, pkg / 'tools', vend, 'prepare_inputs:verify', 'verify',
                      dict(inputs=str(pkg / 'inputs'), env={'C8_ALLOW_NO_L8': '1'}))
        opened = {e['path'] for e in rec['events']}
        ok = (rec.get('error') is None and all(helpers(e) == {'digest'} and e['mode'] in ('rb', 'r') for e in rec['events'])
              and opened == vfiles and not rec['procs'] and not rec['vendored_modules'])
        check('read rule (spy): prepare_inputs.verify() hashes the 13 vendored files and the HANDOFF copy only through '
              'common.digest, starts no process and imports nothing from vendor/', ok,
              dict(error=rec.get('error'), opened=len(opened), missing=sorted(vfiles - opened)[:5],
                   other=sorted(opened - vfiles)[:5], procs=rec['procs'], vendored_modules=rec['vendored_modules']))
        # build(): `make inputs` (HD4: inputs_d3/ copied after the hash check; prepare_low8.py --d 3 compare as a process)
        built = td / 'built'
        rec = run_spy(td, pkg / 'tools', vend, 'prepare_inputs:build', 'build', dict(out=str(built)))
        copied = {os.path.realpath(pkg / x) for x in ('vendor/c8_assembly/HANDOFF_assembly.json',
                                                     'vendor/c8_assembly/inputs_d3/two_loop.json',
                                                     'vendor/c8_assembly/inputs_d3/gamma_d3_8.txt')}
        bad_open = [e['path'] for e in rec['events'] if not helpers(e) or e['mode'] not in ('rb', 'r')
                    or ('verified_bytes' in helpers(e) and e['path'] not in copied)]
        procs = rec['procs']
        low8 = os.path.realpath(pkg / 'vendor/c8_assembly/prepare_low8.py')
        proc_ok = (len(procs) == 1 and procs[0][1:2] == ['-B'] and os.path.realpath(procs[0][2]) == low8
                   and procs[0][3:] == ['--d', '3'])
        same = (built / 'manifest.json').is_file() and \
            sha256_file(built / 'manifest.json') == sha256_file(ROOT / 'inputs/manifest.json')
        check('read rule (spy): prepare_inputs.build() (make inputs) opens vendored files only through common.digest and '
              'common.verified_bytes (the latter for the HANDOFF copy and inputs_d3/{two_loop.json,gamma_d3_8.txt}), '
              'imports nothing from vendor/ and starts one process, prepare_low8.py --d 3 in compare mode under -B; its '
              'manifest equals the package\'s', rec.get('error') is None and not bad_open and proc_ok
              and not rec['vendored_modules'] and same,
              dict(error=rec.get('error'), bad_open=bad_open[:5], procs=procs, vendored_modules=rec['vendored_modules'],
                   manifest_equal=same, opened=len(rec['events'])))
        notes.append(f'prepare_inputs.build() opened {len(rec["events"])} vendored files and ran {procs[:1]}')
        (pkg / 'tools/_c8d3_spy_control.py').write_text(SPY_CONTROL)
        ctl = run_spy(td, pkg / 'tools', vend, '_c8d3_spy_control', 'control')
        check('read rule (spy negative control): a scratch tool importing the vendored module, opening a vendored file '
              'without the hash helpers and starting a process is caught on all three counts',
              ctl.get('error') is None and 'order8_assembly' in ctl['vendored_modules']
              and any(e['path'].endswith('order8_assembly.py') for e in ctl['events'])
              and any(e['path'].endswith('inputs_d3/two_loop.json') and not helpers(e) for e in ctl['events'])
              and len(ctl['procs']) == 1,
              dict(error=ctl.get('error'), vendored_modules=ctl['vendored_modules'], opened=len(ctl['events']),
                   procs=ctl['procs']))
    # the read rule for `production.py plan` and `run --index` (Stage 3a, G3a; PLAN E.1, A-ORC-13): in a scratch package
    # of tests/c8pkg.py (synthetic complete inputs with inspect fields, the vendored tree hard-linked, the fake worker)
    sys.path.insert(0, str(ROOT / 'tests'))
    import c8pkg  # noqa: E402
    with tempfile.TemporaryDirectory(prefix='c8d3_vendor_rule_pr_') as td:
        td = Path(td)
        pkg = c8pkg.make(td)
        scr = td / 'scratch'
        scr.mkdir()
        run_dir = td / 'campaign'
        vend = os.path.realpath(pkg / 'vendor')
        vfiles = {os.path.realpath(pkg / f['vendored_path']) for f in v['files']} | {os.path.realpath(pkg / v['handoff']['path'])}
        argv = ['plan', str(run_dir), '--seed', '7700113', '--pilot', '--test-only', '--points', '512', '--replicates', '2',
                '--plan-role', 'validation', '--bootstrap-chunk', '512', '--shards', '1', '--threads', '1', '--scratch', str(scr)]
        rec = run_spy(td, pkg / 'tools', vend, 'production:main', 'plan', dict(argv=argv))
        opened = {e['path'] for e in rec['events']}
        hashed = all({fn for file, fn in e['stack'] if file.endswith('common.py') and fn == 'digest'} == {'digest'}
                     and e['mode'] in ('rb', 'r') for e in rec['events'])
        vproc = [x for x in rec['procs'] if any(os.path.realpath(a_).startswith(vend + os.sep) for a_ in x if os.path.isabs(a_))]
        planned = (run_dir / 'manifest.json').is_file()
        check('read rule (spy): `production.py plan` opens vendored files only through common.digest (the input gate '
              'prepare_inputs.plan_inputs -> verify(): the 13 files and the HANDOFF copy), starts no process under vendor/ '
              'and imports nothing from vendor/', rec.get('error') is None and planned and hashed and opened == vfiles
              and not vproc and not rec['vendored_modules'],
              dict(error=rec.get('error'), planned=planned, opened=len(opened), other=sorted(opened - vfiles)[:5],
                   missing=sorted(vfiles - opened)[:5], vendored_procs=vproc[:2], vendored_modules=rec['vendored_modules']))
        if planned:
            rec = run_spy(td, pkg / 'tools', vend, 'production:main', 'run',
                          dict(argv=['run', str(run_dir), '--index', '0', '--threads', '1', '--scratch', str(scr)]))
            vproc = [x for x in rec['procs'] if any(os.path.realpath(a_).startswith(vend + os.sep) for a_ in x if os.path.isabs(a_))]
            ran = any(run_dir.glob('groups/*/checkpoints/*.json'))
            check('read rule (spy): `production.py run --index` opens nothing under vendor/, starts no vendored process and '
                  'imports nothing from vendor/ (A-ORC-13), and commits its blocks', rec.get('error') is None and ran
                  and not rec['events'] and not vproc and not rec['vendored_modules'],
                  dict(error=rec.get('error'), committed=ran, opened=[e['path'] for e in rec['events']][:5],
                       vendored_procs=vproc[:2], vendored_modules=rec['vendored_modules']))
    notes.append('still to come at G3a (A-ASM-1 Mac; A-IN-4 at L <= 7; CHANGELOG, Stage 2a repair rounds 1 and 2): '
                 'once production.py plan calls prepare_inputs.plan_inputs, (b) and tests/check_inputs.py repeat their '
                 'checks through `production.py plan` in scratch packages on plan_gate\'s fixed input state '
                 '(l7_complete false, no L8 pin, whatever the live stage, so before or after Stage 2b): the one-byte '
                 'flips of a pinned L <= 7 input and of a vendored file, a foreign C8_INPUTS on a non-test plan, '
                 'l7_complete false giving a test-only plan, asserting that no campaign directory or plan temporary '
                 'directory is created; tests/plan_gate.py runs them, and fails until plan_gate.STAGE3A is set')
    # (b) the input manifest
    if not a.standalone:
        m = json.loads((ROOT / 'inputs/manifest.json').read_bytes())
        pins = m.get('vendored_assembly') or {}
        ok = (m.get('vendored_assembly_handoff_sha256') == hsha and pins.get('handoff_sha256') == hsha
              and pins.get('files') == {f['vendored_path']: f['sha256'] for f in v['files']}
              and pins.get('files') == {f'vendor/c8_assembly/{n}': f['sha256'] for n, f in listed.items()})
        check('A-ASM-1(b): inputs/manifest.json records the HANDOFF sha256 and every vendored pin, equal to '
              'VENDORED.json and the HANDOFF', ok, dict(handoff=m.get('vendored_assembly_handoff_sha256'),
                                                        files=len(pins.get('files') or {}), schema=m.get('schema')))
        sys.path.insert(0, str(ROOT / 'tools'))
        import prepare_inputs as pi  # noqa: E402
        has_verify = callable(getattr(pi, 'verify', None))
        check('A-ASM-1(b): prepare_inputs.verify() exists (Stage 2a)', has_verify)
        if ok and has_verify:
            with tempfile.TemporaryDirectory(prefix='c8d3_vendor_flip_') as td:
                exp = Path(td) / 'pkg'
                exp.mkdir()
                if (ROOT / '.git').exists():
                    arch = subprocess.run(['git', '-C', str(ROOT), 'archive', '--format=tar', 'HEAD'],
                                          capture_output=True, check=True).stdout
                    subprocess.run(['tar', '-x', '-C', str(exp)], input=arch, check=True)
                else:
                    shutil.copytree(ROOT, exp, dirs_exist_ok=True, symlinks=False,
                                    ignore=shutil.ignore_patterns('free_L8.pack', 'power_L8.pack', '__pycache__'))
                code = ('import sys; sys.path.insert(0, sys.argv[1]); import prepare_inputs as pi\n'
                        'try:\n    pi.verify()\nexcept Exception as e:\n    print("REFUSED", e); sys.exit(3)\n'
                        'print("ACCEPTED")\n')
                env = {k: val for k, val in os.environ.items() if k not in ('C8_INPUTS', 'C8_SITE')}
                env.update(PYTHONDONTWRITEBYTECODE='1', C8_ALLOW_NO_L8='1')
                r0 = subprocess.run([sys.executable, '-B', '-c', code, str(exp / 'tools')], capture_output=True,
                                    text=True, env=env)
                target = exp / 'vendor/c8_assembly/order8_assembly.py'
                orig = target.read_bytes()
                b = bytearray(orig)
                b[100] ^= 1
                target.write_bytes(bytes(b))
                r = subprocess.run([sys.executable, '-B', '-c', code, str(exp / 'tools')], capture_output=True,
                                   text=True, env=env)
                target.write_bytes(orig)
                check('A-ASM-1(b): a one-byte change to a vendored file makes prepare_inputs.verify() refuse (the '
                      'untouched scratch export verifies)', r0.returncode == 0 and r.returncode == 3
                      and 'order8_assembly.py' in r.stdout, (r0.stdout + r0.stderr + r.stdout + r.stderr)[-700:])
                # (b) through the real `production.py plan` (tests/plan_gate.py; Stage 2a repair rounds 1 and 2), in
                # the export on the runner's fixed input state (l7_complete false, no L8 pin; the export's own gate
                # passes it first). Transitional at Stage 2a: the unported C7(3) planner refuses every request
                # before creating anything. Wired (Stage 3a on, G3a evidence): the vendored flip is refused naming
                # the file, creating no campaign directory, nothing beside it or in TMPDIR, and the untouched non-test
                # request comes out test-only; plan_gate.STAGE3A unset fails.
                sys.path.append(str(ROOT / 'tests'))
                import plan_gate  # noqa: E402
                pg = plan_gate.run_plan_gate(exp, Path(td) / 'plan_gate', env, scenarios=('untouched', 'vendored'))
                for c in pg['checks']:
                    check('A-ASM-1(b) ' + c['check'], c['passed'], c['detail'])
                fx = pg['fixed']
                notes.append(f'A-ASM-1(b) through production.py plan: mode {pg["mode"]}; fixed input state: '
                             f'{"rewritten " + json.dumps(fx) if fx["manifest_rewritten"] else "the inputs unchanged"}'
                             f'; {pg["note"]}')
    rec = dict(schema='c8-d3-gate-1', gate='A-ASM-1(a)' if a.standalone else 'A-ASM-1(a)+(b)', handoff_sha256=hsha,
               passed=bool(results) and not failed, failed=failed, checks=results, notes=[n for n in notes if n],
               python=sys.version.split()[0], host=os.uname().nodename, root=str(ROOT),
               commit=(subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True)
                       .stdout.strip() if (ROOT / '.git').exists() else None))
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rec, indent=1) + '\n')
    for n in rec['notes']:
        print('NOTE', n)
    print(f'check_vendored{" --standalone" if a.standalone else ""}: {len(results) - len(failed)}/{len(results)} '
          f'checks passed')
    return 0 if rec['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
