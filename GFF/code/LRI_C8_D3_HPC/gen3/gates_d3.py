#!/usr/bin/env python3
"""The d=3 payload gates (PLAN.md component A.3; C63d's part of H1). Standard library only.

Subcommands:
  pins     --c7d2 LRI_C7_D2_HPC/reference --c7d3-inventory FILE --write-dir gen3/pins
           (Re)derive the package pins of gate 1(a): the per-file sha256 list of C7(2)'s frozen d=2 payloads
           (gen3/pins/c7d2_frozen_d2.sha256, rows "<sha256>  <path relative to LRI_C7_D2_HPC/reference>") and
           PINS.json (that list's sha256 and counts, and the digest of the 3,512 C7(3) payload hashes taken from
           C7(3)'s inventory.json rows plus reference/inputs/free/L2/G0.txt). Run once on the Mac; the result is
           committed. With --check, compare instead of writing.
  gate1a   --d2 DIR --bin REGENERATE_RATES --work DIR --evidence DIR [--threads N] [--loops 2,3,...]
           Gate 1(a), pre-H1 (A-INV-2(a), J-GEN-D3-0): verify the frozen d=2 copy against the pins; regenerate every
           pinned d=2 payload of the selected loops with regenerate_rates (N threads, then 1 thread: determinism;
           then once more over the outputs: idempotence); every C7(3) reference payload (reference/inputs/, 3,512 at
           L2-L7) must be reproduced byte for byte, and the reference set must equal the pinned C7(3) payload set;
           each output equals its d=2 input except the magic and the rate line (check_dimension8 (i) at L <= 7);
           the rate audit (minimum rate 3 quarters free, 1 quarter power; clamped and double-lift counts). Writes
           <evidence>/gate1a.json and <evidence>/rate_audit_pre_h1.json; exit 0 only if every check passes.
           The record's a_inv_2a is true only for a full pass on Expanse x86-64 (g3common.expanse_run: machine x86_64,
           a numeric SLURM_JOB_ID, C8_SITE=expanse); any other run is labelled run_class "rehearsal".
  summary-gen-d3-0 --evidence DIR [--rehearsal]
           J-GEN-D3-0's summary jgen_d3_0.json from gate1a.json and test_gen3_sanitize.json: passed (= G1a) only when
           A-INV-2(a) holds on Expanse and A-INV-1's sanitizer part passed. Exit 0 when passed; with --rehearsal (an
           explicit off-Expanse dry run) exit 0 when every check passed, the record saying rehearsal and passed false.
  h1-copy  --source DIR --store DIR --pin SHA --evidence DIR      A.2 step 0 (J-H1-COPY, A-INV-6); a new or an existing
           copy's code is authenticated (g3common.h1_code_snapshot, S4-001) before its verify_inventory.py runs, and
           the verifier runs from that authenticated snapshot
  h1-auth  --tree DIR --pin SHA --snapshot DIR [--check] --evidence DIR [--name NAME]
           S4-001 for gen3/run_d3.sh: authenticate the H1 copy's code against the external pin and make the snapshot of
           src/gen/ that run_d3.sh runs and builds (--check: the existing snapshot is still exactly that code). Writes
           <evidence>/<name>.json; exit 1 (nothing made) when the code is not authenticated.
  source-unchanged --source DIR --before FILE --evidence DIR     A-INV-6 after J-GEN-D3
  split-audit --audit FILE --stage DIR --out DIR                 rate_audit_L7.json, rate_audit_L8.json
  gate1b, gate2, gate3, gate4, gate5, gate7, determinism         the H1 gates (Stage 1b; gen3/run_d3.sh --h1)
  report   --evidence DIR --gate1a FILE --h1-pin SHA --commit SHA --output FILE   the A.5 gate record (refuses a
           gate1a.json that is not an Expanse x86-64 full pass); written once. Its handoff_c63d field is what C63d
           writes into the HANDOFF's c63d block (DECISIONS A3, agreed 2026-10-04: pin_recorded, gates_1_7,
           gate_5_forest_certificate, nothing else).
  gate6    [--inputs DIR] --evidence DIR     Gate 6, pack identity (Stage 2b, A-INV-2(b)): every C7(3) kernel's member
           in the C8 packs (read at the C8 inventory's offset) has the sha256 of C7(3)'s inventory row (a6ce987,
           tests/fixtures/c7_inputs/inventory.json), 3,511 rows; with free/L2/G0.txt they hash to PINS.json's C7(3)
           payload digest; the L3-L6 packs equal a6ce987's; the other L7 members (the 143 + 119 s_G = 4 kernels) are at
           their MEMBERS_d3.sha256 hashes (the inputs' copy, at its manifest pin and its d=3 SHA256SUMS row); L7 totals
           2,441 + 709. Writes <evidence>/gate6.json.
  addendum --gate6 FILE --gate-record FILE --inputs-manifest FILE --commit SHA --output FILE
           Gate 6's addendum to the A.5 gate record, which `report` writes once: written next to it under
           LRI_C8_shared/assembly/H1_gates/ (refusing an existing output), only for a passed gate6.json whose inputs
           manifest is the one given and whose d=3 and H1 pins equal the gate record's. It writes nothing else; its
           handoff_c63d_update (gates_1_7["6"]: true) goes into the HANDOFF through handoff-gate6.
The A.5 report-back into the shared coordination files (Mac, where they live; each subcommand makes exactly one write,
keeps the file's mode, records the before and after sha256s, and with --dry-run only prints; a second run finds its
write done and changes nothing). S4-004: C62d's writers honour no lock of ours, so neither write is a
check-then-replace: decisions-ack makes one O_APPEND write while the file still holds the bytes it read;
handoff-gate6 makes a take-aside compare-and-swap (the HANDOFF is absent for an instant between its rename aside and
the link of the new bytes; see swap_if_unchanged). A concurrent edit is refused, never overwritten or lost:
  handoff-gate6 --handoff LRI_C8_shared/inventory/HANDOFF_inventory8_d2.json --gate-record FILE --addendum FILE
           --evidence DIR [--dry-run]
           DECISIONS A3 (agreed 2026-10-04: C63d writes pin_recorded, gates_1_7 and gate_5_forest_certificate into the
           HANDOFF's c63d block and nothing else): sets c63d.gates_1_7["6"] from "pending (Stage 2b, with the C8
           packs)" to true, the addendum's handoff_c63d_update. Only when the addendum is a passed gate 6 whose
           addendum_to sha256 is the gate record's bytes, the pins agree (HANDOFF manifest_sha256 = the record's H1
           pin = c63d.pin_recorded), the c63d block equals the record's handoff_c63d otherwise, and the file is the
           json.dumps(indent=1) text C62d's handoff_inventory.py writes (so the rewrite changes no other byte); the
           structural difference must be exactly that one value. The old bytes are kept in DIR.
  decisions-ack --decisions LRI_C8_shared/inventory/DECISIONS.md --gate-record FILE --addendum FILE --handoff FILE
           --evidence DIR [--date YYYY-MM-DD] [--dry-run]
           A.2 step 6 / A.5: appends one line carrying the d3 pin (MANIFEST_d3.json sha256) to the DECISIONS
           acknowledgment log (the last section; C63d's append-only grant), after the HANDOFF's c63d block holds gate
           6. The old bytes must be a prefix of the new.
  note     --gate-record FILE --addendum FILE --handoff FILE --decisions FILE --payload-path TEXT [--h1-copy FILE]
           --output LRI_C8_shared/assembly/NOTE_C63d_to_C62d_<date>.md [--dry-run]
           A.5's NOTE to C62d (C63d's own folder), written from those records once the HANDOFF holds gate 6 and the
           DECISIONS log holds the pin line; refuses an existing NOTE.
Nothing else in gen3/ writes under C62d's trees (g3common.refuse_c62d); the two inventory files above are the only
exceptions, by exact name.
Gate 6 (pack identity) runs in Stage 2b, where the C8 packs are built (J-IN-1).
Exit status: 0 passed; 1 a gate failed (the record says which check); 2 refused or bad input ('<path>: <reason>').
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

GEN3 = Path(__file__).resolve().parent
ROOT = GEN3.parent
sys.path.insert(0, str(GEN3))
import g3common as c  # noqa: E402

PINS = GEN3 / 'pins'
D2_LIST = PINS / 'c7d2_frozen_d2.sha256'
PINS_JSON = PINS / 'PINS.json'
D2_TREES = {'free': 'LRI_C7_d2_progress/inputs', 'power': 'power_mass/inputs'}
LOOPS = {'free': (2, 3, 4, 5, 6, 7), 'power': (3, 4, 5, 6, 7)}
# C7(3)'s payload set (F10): free L2..L7 1/5/16/76/395/2,298, power L3..L7 1/3/20/107/590 = 3,512 files.
C7D3_COUNTS = {'free': {2: 1, 3: 5, 4: 16, 5: 76, 6: 395, 7: 2298}, 'power': {3: 1, 4: 3, 5: 20, 6: 107, 7: 590}}
# C7(2)'s frozen d=2 payloads: all finite kernels, L7 with s_G = 4 included: free 2,934, power 840 = 3,774 files.
C7D2_COUNTS = {'free': {2: 1, 3: 5, 4: 16, 5: 76, 6: 395, 7: 2441}, 'power': {3: 1, 4: 3, 5: 20, 6: 107, 7: 709}}
MIN_RATE = {'free': 3, 'power': 1}   # quarters (gate 7)
ROW = re.compile(r'([0-9a-f]{64})  (\S+)')
GFILE = re.compile(r'G(0|[1-9][0-9]*)\.txt')


def stamp(msg: str) -> None:
    print(f'[{time.strftime("%Y-%m-%dT%H:%M:%S")}] {msg}', flush=True)


def read_list(p: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    data = p.read_bytes()
    if data and not data.endswith(b'\n'):
        c.die(f'{p}: no final newline')
    for k, line in enumerate(data.decode('ascii').splitlines(), 1):
        m = ROW.fullmatch(line)
        if not m or m.group(2) in out:
            c.die(f'{p}: line {k}: malformed or duplicate row {line[:100]!r}')
        out[m.group(2)] = m.group(1)
    return out


def list_text(rows: dict[str, str]) -> str:
    return ''.join(f'{h}  {p}\n' for p, h in sorted(rows.items()))


def sector_loop_id(rel: str) -> tuple[str, int, int]:
    """'LRI_C7_d2_progress/inputs/L3/G1.txt' -> ('free', 3, 1)."""
    for sector, tree in D2_TREES.items():
        if rel.startswith(tree + '/'):
            Ld, g = rel[len(tree) + 1:].split('/')
            m = GFILE.fullmatch(g)
            if not (Ld.startswith('L') and m):
                break
            return sector, int(Ld[1:]), int(m.group(1))
    c.die(f'{rel}: not a pinned d=2 payload path')


def c7d3_rows(inventory: Path, l2: Path) -> dict[str, str]:
    """The C7(3) payload set: '<sector>/L<L>/G<id>.txt' -> sha256, from C7(3)'s inventory.json rows plus the L=2
    control graph (not in the inventory)."""
    inv = json.loads(inventory.read_text())
    rows = {f'{s}/L{L}/G{r["id"]}.txt': r['sha256'] for s in ('free', 'power') for L in inv[s] for r in inv[s][L]}
    rows['free/L2/G0.txt'] = c.sha256_file(l2)
    return rows


def cmd_pins(a) -> int:
    src = Path(a.c7d2)
    rows = {}
    for sector, tree in D2_TREES.items():
        for L in LOOPS[sector]:
            for p in (src / tree / f'L{L}').glob('G*.txt'):
                if GFILE.fullmatch(p.name):
                    rows[f'{tree}/L{L}/{p.name}'] = c.sha256_file(p)
    counts = {s: {L: 0 for L in LOOPS[s]} for s in LOOPS}
    for rel in rows:
        s, L, _ = sector_loop_id(rel)
        counts[s][L] += 1
    if counts != C7D2_COUNTS:
        c.die(f'{src}: d=2 payload counts {counts} differ from the expected {C7D2_COUNTS}')
    c7 = c7d3_rows(Path(a.c7d3_inventory), ROOT / 'reference/inputs/free/L2/G0.txt')
    c7counts = {s: {L: sum(1 for k in c7 if k.startswith(f'{s}/L{L}/')) for L in C7D3_COUNTS[s]} for s in C7D3_COUNTS}
    if c7counts != C7D3_COUNTS or len(c7) != 3512:
        c.die(f'{a.c7d3_inventory}: C7(3) payload counts {c7counts} differ from {C7D3_COUNTS}')
    text = list_text(rows)
    pins = dict(schema='c8-d3-gen3-pins-1',
                c7d2_frozen_d2=dict(source='LRI_C7_D2_HPC@a55958f:reference/{LRI_C7_d2_progress,power_mass}/inputs '
                                           '(git-tracked; copied to $C8_STORE/c7d2_frozen/ in Stage 0)',
                                    list='gen3/pins/c7d2_frozen_d2.sha256', list_sha256=c.sha256_bytes(text.encode()),
                                    files=len(rows), counts={s: {str(L): n for L, n in v.items()} for s, v in counts.items()},
                                    bytes=sum((src / r).stat().st_size for r in rows)),
                c7d3_payloads=dict(source='LRI_C7_D3_HPC@a6ce987 (= c8-base): inputs/inventory.json row sha256 (3,511 '
                                          'kernels) and reference/inputs/free/L2/G0.txt; the files are reference/inputs/',
                                   digest_sha256=c.sha256_bytes(list_text(c7).encode()), files=len(c7),
                                   counts={s: {str(L): n for L, n in v.items()} for s, v in c7counts.items()},
                                   digest_rule='sha256 of the rows "<sha256>  <sector>/L<L>/G<id>.txt\\n" sorted by path'))
    if a.check:
        old = json.loads(PINS_JSON.read_text())
        same = old == pins and D2_LIST.read_text() == text
        print('pins', 'unchanged' if same else 'DIFFER')
        return 0 if same else 1
    out = c.refuse_c62d(Path(a.write_dir), 'pin directory')
    out.mkdir(parents=True, exist_ok=True)
    (out / D2_LIST.name).write_text(text)
    (out / PINS_JSON.name).write_text(json.dumps(pins, indent=1) + '\n')
    print(json.dumps(pins, indent=1))
    return 0


# ---- environment record ------------------------------------------------------------------------------------------
def cpu_model() -> str:
    try:
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.startswith('model name'):
                return line.split(':', 1)[1].strip()
    except OSError:
        pass
    try:
        return subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], capture_output=True, text=True).stdout.strip()
    except OSError:
        return platform.processor()


def environment(binary: Path) -> dict:
    build = Path(str(binary) + '.build.txt')
    return dict(host=socket.gethostname(), machine=platform.machine(), system=platform.system(), cpu=cpu_model(),
                python=sys.version.split()[0], slurm_job_id=os.environ.get('SLURM_JOB_ID'), site=os.environ.get('C8_SITE'),
                package=os.environ.get('C8_PACKAGE') or str(ROOT), binary=str(binary), binary_sha256=c.sha256_file(binary),
                build_record=build.read_text() if build.is_file() else None,
                gen3_sources={p.name: c.sha256_file(p) for p in sorted(GEN3.glob('*')) if p.suffix in ('.cpp', '.py', '.sh')})


def run_regen(binary: Path, joblist: Path, threads: int, what: str) -> tuple[list, float]:
    t0 = time.time()
    cp = subprocess.run([str(binary), str(joblist)], capture_output=True, env=dict(os.environ, OMP_NUM_THREADS=str(threads)))
    secs = time.time() - t0
    if cp.returncode != 0:
        sys.stderr.write(cp.stderr.decode(errors='replace')[-5000:])
        c.die(f'{joblist}: regenerate_rates ({what}) exited {cp.returncode}')
    return json.loads(cp.stdout), secs


# ---- gate 1(a) ---------------------------------------------------------------------------------------------------
def cmd_gate1a(a) -> int:
    t_start = time.time()
    d2 = Path(a.d2).resolve()
    binary = Path(a.bin).resolve()
    work = c.refuse_c62d(Path(a.work).resolve(), 'scratch directory')
    ev = c.refuse_c62d(Path(a.evidence).resolve(), 'evidence directory')
    loops = sorted({int(x) for x in a.loops.split(',')}) if a.loops else [2, 3, 4, 5, 6, 7]
    if not set(loops) <= {2, 3, 4, 5, 6, 7}:
        c.die(f'--loops {a.loops}: gate 1(a) covers L2-L7')
    if work.exists() and any(work.iterdir()):
        c.die(f'{work}: scratch directory exists and is not empty (use a fresh one)')
    ev.mkdir(parents=True, exist_ok=True)
    pins = json.loads(PINS_JSON.read_text())
    checks: dict[str, dict] = {}

    # 1. the pins and the frozen d=2 copy
    stamp('verifying the frozen d=2 copy against the pins')
    lt = D2_LIST.read_bytes()
    pin_d2 = read_list(D2_LIST)
    e = []
    if c.sha256_bytes(lt) != pins['c7d2_frozen_d2']['list_sha256'] or len(pin_d2) != pins['c7d2_frozen_d2']['files']:
        e.append(f'{D2_LIST}: differs from PINS.json')
    selected = {rel: h for rel, h in pin_d2.items() if sector_loop_id(rel)[1] in loops}
    for rel, h in sorted(selected.items()):
        p = d2 / rel
        if not p.is_file():
            e.append(f'{p}: missing')
        elif c.sha256_file(p) != h:
            e.append(f'{p}: sha256 differs from the pin')
    checks['frozen_d2_pin'] = dict(passed=not e, files=len(selected), errors=e[:50], error_count=len(e))
    if e:
        return finish(a, ev, checks, {}, t_start, binary, loops)

    # 2. the C7(3) reference set
    ref = ROOT / 'reference/inputs'
    refrows = {}
    for sector in ('free', 'power'):
        for L in loops:
            for p in sorted((ref / sector / f'L{L}').glob('G*.txt')):
                if GFILE.fullmatch(p.name):
                    refrows[f'{sector}/L{L}/{p.name}'] = c.sha256_file(p)
    e = []
    if loops == [2, 3, 4, 5, 6, 7]:
        if c.sha256_bytes(list_text(refrows).encode()) != pins['c7d3_payloads']['digest_sha256'] or len(refrows) != 3512:
            e.append('reference/inputs payload set differs from the pinned C7(3) payload digest (PINS.json c7d3_payloads)')
    want = {s: {L: C7D3_COUNTS[s].get(L, 0) for L in loops if L in C7D3_COUNTS[s]} for s in C7D3_COUNTS}
    got = {s: {L: sum(1 for k in refrows if k.startswith(f'{s}/L{L}/')) for L in want[s]} for s in want}
    if got != want:
        e.append(f'reference/inputs counts {got} differ from {want}')
    checks['c7d3_reference_set'] = dict(passed=not e, files=len(refrows), digest_checked=loops == [2, 3, 4, 5, 6, 7],
                                        counts={s: {str(L): n for L, n in v.items()} for s, v in got.items()}, errors=e)
    if e:
        return finish(a, ev, checks, {}, t_start, binary, loops)

    # 3. regenerate (N threads), again at 1 thread (determinism), and once more over the outputs (idempotence)
    work.mkdir(parents=True, exist_ok=True)
    pairs = []
    for rel in sorted(selected, key=lambda r: sector_loop_id(r)):
        s, L, gid = sector_loop_id(rel)
        pairs.append((d2 / rel, f'{s}/L{L}/G{gid}.txt'))
    runs = {}
    for name, threads, src in (('n', a.threads, None), ('one', 1, None), ('again', a.threads, 'n')):
        out = work / f'out_{name}'
        jl = work / f'jobs_{name}.txt'
        lines = []
        for inp, rel in pairs:
            (out / rel).parent.mkdir(parents=True, exist_ok=True)
            lines.append(f'{(work / f"out_{src}" / rel) if src else inp} {out / rel}\n')
        jl.write_text(''.join(lines))
        stamp(f'regenerate_rates {name}: {len(lines)} files, OMP_NUM_THREADS={threads}')
        recs, secs = run_regen(binary, jl, threads, name)
        runs[name] = dict(records=recs, seconds=round(secs, 2), threads=threads, out=out)
    (ev / 'rate_audit_pre_h1.json').write_text(json.dumps(
        [dict(r, file=r['file'][len(str(runs['n']['out'])) + 1:]) for r in runs['n']['records']]) + '\n')

    def strip(recs, out):
        return [dict(r, file=r['file'][len(str(out)) + 1:]) for r in recs]
    det_e, idem_e = [], []
    for inp, rel in pairs:
        b = (runs['n']['out'] / rel).read_bytes()
        if (runs['one']['out'] / rel).read_bytes() != b:
            det_e.append(rel)
        if (runs['again']['out'] / rel).read_bytes() != b:
            idem_e.append(rel)
    if strip(runs['n']['records'], runs['n']['out']) != strip(runs['one']['records'], runs['one']['out']):
        det_e.append('rate audit records differ')
    checks['determinism_threads'] = dict(passed=not det_e, threads=[a.threads, 1], files=len(pairs), errors=det_e[:50],
                                         error_count=len(det_e))
    checks['idempotence_second_pass'] = dict(passed=not idem_e, files=len(pairs), errors=idem_e[:50], error_count=len(idem_e))

    # 4. byte reproduction of every C7(3) reference payload; the extras (L7 s_G = 4) recorded
    out = runs['n']['out']
    mism, per = [], {}
    tok_rate_diff = 0
    for rel, h in sorted(refrows.items()):
        o = out / rel
        key = rel.rsplit('/', 1)[0]
        per.setdefault(key, [0, 0])
        if not o.is_file():
            mism.append(f'{rel}: not regenerated')
            per[key][1] += 1
            continue
        ob = o.read_bytes()
        if ob == (ref / rel).read_bytes() and c.sha256_bytes(ob) == h:
            per[key][0] += 1
        else:
            per[key][1] += 1
            mism.append(f'{rel}: bytes differ')
            rl_o, rl_r = c.gfile_lines(ob)[-1].split(), c.gfile_lines((ref / rel).read_bytes())[-1].split()
            tok_rate_diff += rl_o != rl_r
    extras = sorted(rel for _, rel in pairs if rel not in refrows)
    checks['byte_reproduction_c7d3'] = dict(
        passed=not mism and sum(v[0] for v in per.values()) == len(refrows), identical=sum(v[0] for v in per.values()),
        compared=len(refrows), per_sector_loop={k: dict(identical=v[0], differ=v[1]) for k, v in sorted(per.items())},
        mismatches=mism[:50], mismatch_count=len(mism), mismatching_rate_lines_as_tokens=tok_rate_diff,
        extras_not_in_c7d3=len(extras), extras_rule='L7 kernels with s_G = 4 (C7(3) dropped them at its top loop; C8 needs them)')

    # 5. structure: each output equals its d=2 input except the magic and the rate line (check_dimension8 (i), L <= 7)
    body_e = [rel for inp, rel in pairs if not c.same_body(inp.read_bytes(), (out / rel).read_bytes())]
    checks['body_equals_d2_except_magic_and_rate_line'] = dict(passed=not body_e, files=len(pairs), errors=body_e[:50],
                                                              error_count=len(body_e))

    # 6. the rate audit (gate 7 thresholds at L <= 7)
    audit = {}
    rate_e = []
    for (inp, rel), r in zip(pairs, runs['n']['records']):
        s, L = rel.split('/')[0], int(rel.split('/')[1][1:])
        k = f'{s}/L{L}'
        x = audit.setdefault(k, dict(files=0, min_rate_quarters=99, clamped_subsets=0, double_lift_kernels=0,
                                     double_lift_subsets=0, min_raw=99, raw_histogram={}))
        x['files'] += 1
        x['min_rate_quarters'] = min(x['min_rate_quarters'], r['minimum_rate_quarters'])
        x['clamped_subsets'] += r['cancelled_nonpositive_subsets']
        x['double_lift_kernels'] += r['double_lift_subsets'] > 0
        x['double_lift_subsets'] += r['double_lift_subsets']
        x['min_raw'] = min(x['min_raw'], r['min_raw'])
        for v, n in r['raw_histogram'].items():
            x['raw_histogram'][v] = x['raw_histogram'].get(v, 0) + n
        if r['minimum_rate_quarters'] < MIN_RATE[s]:
            rate_e.append(f'{rel}: minimum rate {r["minimum_rate_quarters"]} quarters < {MIN_RATE[s]}')
    checks['rate_audit_minimum_rates'] = dict(passed=not rate_e, thresholds_quarters=MIN_RATE, per_sector_loop=audit,
                                              errors=rate_e[:50], error_count=len(rate_e))
    timing = {k: dict(seconds=v['seconds'], threads=v['threads']) for k, v in runs.items()}
    if not a.keep_work:
        shutil.rmtree(work)
    return finish(a, ev, checks, timing, t_start, binary, loops)


def finish(a, ev: Path, checks: dict, timing: dict, t_start: float, binary: Path, loops: list) -> int:
    passed = all(v['passed'] for v in checks.values()) and set(checks) >= {
        'frozen_d2_pin', 'c7d3_reference_set', 'determinism_threads', 'idempotence_second_pass', 'byte_reproduction_c7d3',
        'body_equals_d2_except_magic_and_rate_line', 'rate_audit_minimum_rates'}
    full = loops == [2, 3, 4, 5, 6, 7]
    env = environment(binary)
    expanse, why = c.expanse_run(env)
    rec = dict(schema='c8-d3-gate1a-2', gate='1(a) L <= 7 byte reproduction at d=3, pre-H1 (A-INV-2(a))',
               passed=passed, scope='full (L2-L7, 3,512 C7(3) payloads)' if full else f'subset L{loops}',
               run_class='expanse' if expanse else 'rehearsal', not_expanse_because=why,
               a_inv_2a=passed and full and expanse, d2=str(Path(a.d2).resolve()), pins_json_sha256=c.sha256_file(PINS_JSON),
               checks=checks, timing=timing, seconds=round(time.time() - t_start, 1),
               utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), environment=env)
    c.write_json(ev / 'gate1a.json', rec, 'gate record')
    for k, v in checks.items():
        print(f'{k}: {"PASS" if v["passed"] else "FAIL"}' + ('' if v['passed'] else f' {v.get("errors", [])[:5]}'))
    print('gate 1(a)', 'PASSED' if passed else 'FAILED', rec['scope'], f'-> {ev / "gate1a.json"}')
    print('A-INV-2(a):', 'yes' if rec['a_inv_2a'] else
          'no (' + '; '.join((['not the full scope'] if not full else []) + (['a check failed'] if not passed else []) + why) + ')'
          + ('' if expanse else ': a rehearsal'))
    return 0 if passed else 1


def gate1a_errors(g1a: dict, where: str) -> list[str]:
    """Why a gate1a.json is not A-INV-2(a) (empty when it is): a full pass on Expanse x86-64 with 3,512 / 3,512
    C7(3) payloads byte-identical. Re-derived from the record's own fields, not only from its a_inv_2a flag."""
    e = []
    br = (g1a.get('checks') or {}).get('byte_reproduction_c7d3') or {}
    if g1a.get('passed') is not True or g1a.get('a_inv_2a') is not True:
        e.append(f'{where}: gate 1(a) is not a full pass (passed {g1a.get("passed")!r}, a_inv_2a {g1a.get("a_inv_2a")!r})')
    if not str(g1a.get('scope', '')).startswith('full'):
        e.append(f'{where}: scope {g1a.get("scope")!r} is not the full L2-L7 set')
    if not (br.get('identical') == br.get('compared') == 3512):
        e.append(f'{where}: {br.get("identical")!r} / {br.get("compared")!r} C7(3) payloads identical, not 3,512 / 3,512')
    expanse, why = c.expanse_run(g1a.get('environment') or {})
    if g1a.get('run_class') != 'expanse' or not expanse:
        e.append(f'{where}: not an Expanse x86-64 run (run_class {g1a.get("run_class")!r}'
                 + ('; ' + '; '.join(why) if why else '') + '): a rehearsal is not A-INV-2(a)')
    return e


SANITIZE_NEED = ('A-INV-1_targeted_cases', 'A-INV-1_mutation_corpus_seed_8814',
                 'C.7_unguarded_index_selftest_aborts_at_the_dist_masks_site',
                 'A-INV-1_injected_failing_gate_in_run_d3_stops_before_publication')


def cmd_summary_gen_d3_0(a) -> int:
    """J-GEN-D3-0's summary (G1a = A-INV-1's sanitizer part and A-INV-2(a)): jgen_d3_0.json in the evidence directory."""
    ev = c.refuse_c62d(Path(a.evidence).resolve(), 'evidence directory')
    try:
        g = json.loads((ev / 'gate1a.json').read_text())
        s = json.loads((ev / 'test_gen3_sanitize.json').read_text())
    except (OSError, ValueError) as ex:
        c.die(f'{ev}: gate1a.json or test_gen3_sanitize.json: {ex}')
    names = [x.get('test') for x in s.get('tests', [])]
    missing = [n for n in SANITIZE_NEED if n not in names]
    sanitizer = s.get('status') == 'passed' and s.get('sanitize') is True and not missing
    br = (g.get('checks') or {}).get('byte_reproduction_c7d3') or {}
    g1a_e = gate1a_errors(g, 'gate1a.json')
    expanse, why = c.expanse_run(g.get('environment') or {})
    checks_passed = (g.get('passed') is True and str(g.get('scope', '')).startswith('full')
                     and br.get('identical') == br.get('compared') == 3512 and sanitizer)
    rec = dict(schema='c8-d3-jgen-d3-0-2', job='J-GEN-D3-0', run_class='expanse' if expanse else 'rehearsal',
               rehearsal=bool(a.rehearsal) or not expanse, not_expanse_because=why,
               a_inv_2a=not g1a_e, a_inv_2a_errors=g1a_e, identical=br.get('identical'), compared=br.get('compared'),
               a_inv_1_sanitizer=sanitizer, sanitizer_tests_missing=missing, sanitizer_tmpdir=s.get('tmpdir'),
               checks_passed=checks_passed, tests=names, slurm_job_id=(g.get('environment') or {}).get('slurm_job_id'),
               passed=False)
    rec['passed'] = rec['a_inv_2a'] and sanitizer
    c.write_json(ev / 'jgen_d3_0.json', rec, 'summary record')
    print(json.dumps(rec, indent=1))
    if rec['passed']:
        print('J-GEN-D3-0 PASSED: G1a (A-INV-1 sanitizer part and A-INV-2(a) on Expanse x86-64)')
        return 0
    if a.rehearsal and checks_passed:
        print('J-GEN-D3-0 REHEARSAL: every check passed; NOT G1a (' + '; '.join(why or ['--rehearsal']) + ')')
        return 0
    print('J-GEN-D3-0 FAILED: ' + '; '.join(g1a_e + ([f'sanitizer part: status {s.get("status")!r}, sanitize '
                                                     f'{s.get("sanitize")!r}, missing {missing}'] if not sanitizer else [])))
    return 1


# ==== H1 (Stage 1b): intake, gates 1(b), 2, 3, 5, 7, determinism; gate 4 is kirchhoff3.py ===================
H1_EXPECT = dict(L7=dict(free=2441, power=709), L8=dict(free=16798, power=4891))   # finite kernels in H1's tars
POWER_CLASSES = {7: 1091, 8: 7231}
H1_MEMBERS_SHA256 = 'e1a77e0d193db11d106cce552ff6e8c924b0a07cbc5bf2f3e93b5de985cbdbb6'


def gate_record(ev: Path, name: str, gate: str, checks: dict, **extra) -> int:
    passed = bool(checks) and all(v.get('passed') for v in checks.values())
    rec = dict(schema='c8-d3-gate-1', gate=gate, passed=passed, checks=checks, **extra,
               utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), host=socket.gethostname(), cpu=cpu_model(),
               slurm_job_id=os.environ.get('SLURM_JOB_ID'))
    c.write_json(ev / f'{name}.json', rec, 'gate record')
    for k, v in checks.items():
        print(f'{name} {k}: {"PASS" if v.get("passed") else "FAIL"}' + ('' if v.get('passed') else f' {v.get("errors", [])[:3]}'))
    print(name, 'PASSED' if passed else 'FAILED')
    return 0 if passed else 1


def listing(root: Path) -> dict:
    """File list, sizes and mtimes of a tree (A-INV-6: C62d's source must not change), and its MANIFEST sha256."""
    rows = []
    for p in sorted(root.rglob('*')):
        st = p.lstat()
        kind = 'link' if p.is_symlink() else 'dir' if p.is_dir() else 'file' if p.is_file() else 'other'
        rows.append([p.relative_to(root).as_posix(), kind, st.st_size if kind == 'file' else 0, st.st_mtime_ns])
    man = root / 'MANIFEST.json'
    return dict(root=str(root), entries=len(rows), rows=rows,
                manifest_sha256=c.sha256_file(man) if man.is_file() else None,
                rows_sha256=c.sha256_bytes(json.dumps(rows).encode()))


def cmd_h1_copy(a) -> int:
    """A.2 step 0 (job c8d3-h1-copy, J-H1-COPY, A-INV-6): copy the HANDOFF's tree into STORE/<sha12>/ through a staging
    directory and one rename, verify the copy with H1's own verify_inventory.py --pin, and record the source's listing
    before and after, which must be equal. The source is only read. S4-001: before anything of the copy (new or
    reused) runs, its code is authenticated by this package's g3common.h1_code_snapshot against the external pin, and
    the verifier runs from that private snapshot; unauthenticated code is never run."""
    src = Path(a.source).resolve()
    store = c.refuse_c62d(Path(a.store).resolve(), 'store directory')
    ev = c.refuse_c62d(Path(a.evidence).resolve(), 'evidence directory')
    ev.mkdir(parents=True, exist_ok=True)
    if not re.fullmatch(r'[0-9a-f]{64}', a.pin):
        c.die(f'--pin {a.pin!r}: not a sha256')
    dest = store / a.pin[:12]
    checks = {}
    before = listing(src)
    (ev / 'h1_source_listing_before.json').write_text(json.dumps(before) + '\n')
    checks['source_pin'] = dict(passed=before['manifest_sha256'] == a.pin, manifest_sha256=before['manifest_sha256'])
    if not checks['source_pin']['passed']:
        return gate_record(ev, 'h1_copy', 'A.2 step 0 intake (A-INV-6)', checks, source=str(src), dest=str(dest))
    t0 = time.time()
    if dest.exists():
        checks['copy'] = dict(passed=True, note='copy exists; verified again below', seconds=0)
    else:
        tag = os.environ.get('SLURM_JOB_ID') or str(os.getpid())
        tmp = c.refuse_c62d(store / f'.{a.pin[:12]}.tmp.{tag}', 'staging directory')
        if tmp.exists():
            c.die(f'{tmp}: exists (remove a stale staging copy by hand)')
        store.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, tmp, symlinks=True, copy_function=shutil.copy2)
        if dest.exists():
            shutil.rmtree(tmp)
            c.die(f'{dest}: appeared during the copy')
        os.rename(tmp, dest)
        checks['copy'] = dict(passed=True, seconds=round(time.time() - t0, 1))
    ver = dest / 'src/gen/verify_inventory.py'
    snap = Path(tempfile.mkdtemp(prefix='c8d3_h1code_'))
    try:
        try:
            checks['h1_code_authenticated'] = c.h1_code_snapshot(dest, a.pin, snap / 'gen')
        except c.Gen3Error as ex:
            checks['h1_code_authenticated'] = dict(passed=False, error=str(ex))
        if checks['h1_code_authenticated']['passed']:
            cp = subprocess.run([sys.executable, '-B', str(snap / 'gen/verify_inventory.py'), str(dest), '--pin', a.pin, '--output',
                                 str(ev / 'verify_inventory_copy.json')], capture_output=True, text=True)
            checks['verify_inventory_copy'] = dict(passed=cp.returncode == 0, returncode=cp.returncode, stdout=cp.stdout[-2000:],
                                                  verifier=str(ver), verifier_sha256=checks['h1_code_authenticated']['verifier_sha256'],
                                                  run_from='the authenticated snapshot')
        else:
            checks['verify_inventory_copy'] = dict(passed=False, verifier=str(ver), note='not run: the H1 code was not authenticated')
    finally:
        shutil.rmtree(snap, ignore_errors=True)
    after = listing(src)
    (ev / 'h1_source_listing_after.json').write_text(json.dumps(after) + '\n')
    checks['source_unchanged'] = dict(passed=after['rows'] == before['rows'] and after['manifest_sha256'] == before['manifest_sha256'],
                                      entries=after['entries'], rows_sha256=after['rows_sha256'])
    return gate_record(ev, 'h1_copy', 'A.2 step 0 intake (A-INV-6)', checks, source=str(src), dest=str(dest), pin=a.pin)


def cmd_h1_auth(a) -> int:
    """S4-001 (gen3/run_d3.sh): the H1 copy's code authenticated and snapshotted (or, with --check, the snapshot
    re-checked) before run_d3.sh runs or builds anything of it."""
    ev = c.refuse_c62d(Path(a.evidence).resolve(), 'evidence directory')
    try:
        rec = (c.h1_snapshot_unchanged(a.snapshot, a.tree, a.pin) if a.check else c.h1_code_snapshot(a.tree, a.pin, a.snapshot))
    except c.Gen3Error as ex:
        c.die(f'h1-auth: {ex} (nothing of the H1 copy may run)', 1)
    c.write_json(ev / f'{a.name}.json', dict(schema='c8-d3-h1-code-auth-1', check=a.check, **rec,
                                             utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())), 'H1 code record')
    print(f'h1-auth: H1 code {"snapshot unchanged" if a.check else "authenticated"}: {a.snapshot}')
    return 0


def cmd_source_unchanged(a) -> int:
    """A-INV-6 after J-GEN-D3: the source's listing equals the one recorded by the intake."""
    ev = c.refuse_c62d(Path(a.evidence).resolve(), 'evidence directory')
    before = json.loads(Path(a.before).read_text())
    now = listing(Path(a.source).resolve())
    ok_ = now['rows'] == before['rows'] and now['manifest_sha256'] == before['manifest_sha256']
    return gate_record(ev, a.name, 'A-INV-6 C62d source tree unchanged', dict(
        source_unchanged=dict(passed=ok_, entries=now['entries'], rows_sha256=now['rows_sha256'],
                              recorded_rows_sha256=before.get('rows_sha256'))))


def stage_members(stage: Path, stems=('L7_free', 'L7_power', 'L8_free', 'L8_power')) -> list[tuple[str, str]]:
    out = []
    for stem in stems:
        d = stage / stem
        for n in sorted(p.name for p in d.iterdir() if GFILE.fullmatch(p.name)) if d.is_dir() else []:
            out.append((f'{stem}/{n}', c.sha256_file(d / n)))
    return sorted(out)


def cmd_split_audit(a) -> int:
    """regenerate_rates' records (absolute output paths) -> rate_audit_L7.json, rate_audit_L8.json, stage-relative."""
    recs = json.loads(Path(a.audit).read_text())
    stage = os.path.abspath(a.stage) + '/'          # the job list's own spelling (no symlink resolution)
    out = c.refuse_c62d(Path(a.out).resolve(), 'audit directory')
    out.mkdir(parents=True, exist_ok=True)
    by: dict[int, list] = {}
    for r in recs:
        if not r['file'].startswith(stage):
            c.die(f'{a.audit}: record file {r["file"]} is not under {stage}')
        by.setdefault(r['L'], []).append(dict(r, file=r['file'][len(stage):]))
    for L, rows in sorted(by.items()):
        (out / f'rate_audit_L{L}.json').write_text(json.dumps(sorted(rows, key=lambda r: r['file'])) + '\n')
    print({f'L{L}': len(v) for L, v in sorted(by.items())})
    return 0


def cmd_gate1b(a) -> int:
    """Gate 1(b) on H1: (a) H1's L7 d=2 G-files against C7(2)'s frozen d=2 L7 payloads, bodies byte for byte and rate
    lines as tokens (F16: the free builder's rate line may lack the trailing space); (b) the C7(3) L7 members
    (2,298 + 590) regenerated from H1 equal C7(3)'s payloads by sha256; (c) L7 totals 2,441 + 709."""
    h1, d3, d2 = Path(a.h1), Path(a.d3), Path(a.d2)
    ev = c.refuse_c62d(Path(a.evidence).resolve(), 'evidence directory')
    checks = {}
    e, n, same_bytes = [], 0, 0
    for s, tree in D2_TREES.items():
        for p in sorted((h1 / f'L7_{s}').glob('G*.txt')):
            q = d2 / tree / 'L7' / p.name
            n += 1
            if not q.is_file():
                e.append(f'{q}: missing (H1 has L7_{s}/{p.name})')
                continue
            x, y = p.read_bytes(), q.read_bytes()
            same_bytes += x == y
            try:
                lx, ly = c.gfile_lines(x), c.gfile_lines(y)
            except c.Gen3Error as ex:
                e.append(f'L7_{s}/{p.name}: {ex}')
                continue
            if lx[:-1] != ly[:-1] or lx[-1].split() != ly[-1].split():
                e.append(f'L7_{s}/{p.name}: differs from the frozen C7(2) payload (body bytes or rate-line tokens)')
    checks['a_h1_L7_d2_equals_frozen_c7d2'] = dict(passed=not e and n == 2441 + 709, files=n, byte_identical=same_bytes,
                                                   rule='bodies byte for byte, rate lines as tokens', errors=e[:50], error_count=len(e))
    e, n = [], 0
    ref = ROOT / 'reference/inputs'
    for s in ('free', 'power'):
        for p in sorted((ref / s / 'L7').glob('G*.txt')):
            n += 1
            q = d3 / f'L7_{s}' / p.name
            if not q.is_file() or c.sha256_file(q) != c.sha256_file(p):
                e.append(f'L7_{s}/{p.name}: regenerated payload differs from C7(3)\'s (or is missing)')
    checks['b_c7d3_L7_members_reproduced'] = dict(passed=not e and n == 2298 + 590, compared=n, errors=e[:50], error_count=len(e))
    cnt = {s: len([p for p in (d3 / f'L7_{s}').glob('G*.txt')]) for s in ('free', 'power')}
    cnt_h1 = {s: len([p for p in (h1 / f'L7_{s}').glob('G*.txt')]) for s in ('free', 'power')}
    checks['c_L7_totals'] = dict(passed=cnt == H1_EXPECT['L7'] and cnt_h1 == H1_EXPECT['L7'], d3=cnt, h1=cnt_h1,
                                 expected=H1_EXPECT['L7'])
    return gate_record(ev, 'gate1b', '1(b) L7 byte regression on H1 (A-INV-2(b))', checks)


def zeros_check(inventory: Path, c8d1: Path) -> dict:
    """Gate 2(c): H1's free L8 exact zeros = C8(1)'s exact_zero_L8.txt restricted to power-free classes (2,511); the
    d=1 zeros of power classes are a subset of H1's power exact zeros."""
    inv = json.loads((inventory / 'inventory_L8.json').read_text())
    t = (c8d1 / 'exact_zero_L8.txt').read_text().split()
    z1 = {int(x) for x in t[1:]}
    e = []
    if int(t[0]) != len(t) - 1 or len(z1) != len(t) - 1:
        e.append(f'exact_zero_L8.txt: header {t[0]} vs {len(t) - 1} ids ({len(z1)} distinct)')
    fz = {r['id'] for r in inv['free'] if r['status'] == 'exact-zero-kernel'}
    pz = {r['id'] for r in inv['power'] if r['status'] == 'exact-zero-kernel'}
    pw = {r['id'] for r in inv['free'] if r['power_subgraphs'] > 0}
    if fz != z1 - pw or len(fz) != 2511:
        e.append(f'free zeros {len(fz)} differ from exact_zero_L8.txt on power-free classes ({len(z1 - pw)}; expected 2,511)')
    if not (z1 & pw) <= pz:
        e.append(f'{len((z1 & pw) - pz)} d=1 power zeros are not d=2 power zeros')
    return dict(passed=not e, free_zeros=len(fz), d1_zeros=len(z1), d1_power_zeros=len(z1 & pw), d2_power_zeros=len(pz), errors=e)


def run_tool(args: list[str]) -> tuple[int, dict | None, str]:
    """Runs a gate tool (gates 2, 4, 5, 7). S4-002: its --output goes to a unique temporary sibling, so only this
    invocation's record can be read. A JSON object with a boolean "passed" written there is published (one rename onto
    --output) and returned; anything else returns no record, and a record an earlier invocation left at --output is set
    aside as <name>.superseded (neither read nor published). The callers pass a check only for exit 0 and a passed
    record."""
    args = [str(x) for x in args]
    i = args.index('--output') + 1
    out = Path(args[i])
    tmp = out.with_name(f'.{out.name}.{os.getpid()}.{secrets.token_hex(6)}.tmp')
    args[i] = str(tmp)
    try:
        cp = subprocess.run([sys.executable, '-B', *args], capture_output=True, text=True)
        try:
            rec = json.loads(tmp.read_text()) if tmp.is_file() and not tmp.is_symlink() else None
        except (OSError, ValueError):
            rec = None
        if not (isinstance(rec, dict) and isinstance(rec.get('passed'), bool)):
            rec = None
        if rec is not None:
            os.replace(tmp, out)
        elif out.exists() or out.is_symlink():
            os.replace(out, out.with_name(out.name + '.superseded'))
        return cp.returncode, rec, (cp.stdout + cp.stderr)[-3000:]
    finally:
        tmp.unlink(missing_ok=True)


def cmd_gate2(a) -> int:
    """Gate 2: (a) census and op counts (opcount.py compare against size_probe), (b) exact weights (weights_check.py),
    (c) zeros."""
    ev = c.refuse_c62d(Path(a.evidence).resolve(), 'evidence directory')
    checks = {}
    rc, rec, log = run_tool([str(GEN3 / 'opcount.py'), 'compare', '--payload', a.d3, '--sizes', a.sizes,
                             '--inventory', a.inventory, '--output', str(ev / c.GATE_SUPPORT['gate2'][0])])
    checks['a_census_and_op_counts'] = dict(passed=rc == 0 and bool(rec and rec['passed']), returncode=rc,
                                            record=c.GATE_SUPPORT['gate2'][0], log=log if rc else '')
    rc, rec, log = run_tool([str(GEN3 / 'weights_check.py'), '--classes', a.classes, '--inventory', a.inventory,
                             '--payload', a.d3, '--output', str(ev / c.GATE_SUPPORT['gate2'][1])])
    checks['b_weights'] = dict(passed=rc == 0 and bool(rec and rec['passed']), returncode=rc, record=c.GATE_SUPPORT['gate2'][1],
                               log=log if rc else '')
    checks['c_zeros'] = zeros_check(Path(a.inventory), Path(a.classes))
    return gate_record(ev, 'gate2', '2 census, op counts, weights, zeros (A-INV-3)', checks)


def cmd_gate3(a) -> int:
    """Gate 3: H1's patched check_edge_forests (built from H1's src/) on every power class at L7 and L8."""
    ev = c.refuse_c62d(Path(a.evidence).resolve(), 'evidence directory')
    checks = {}
    for L, name in zip((7, 8), c.GATE_SUPPORT['gate3']):
        out = ev / name   # H1's raw check_edge_forests output (no "passed": this gate record is its verdict)
        t0 = time.time()
        cp = subprocess.run([str(Path(a.bin) / 'check_edge_forests'), str(Path(a.classes) / f'classes{L}.txt'),
                             str(Path(a.d3) / f'L{L}_power'), str(out)], capture_output=True, text=True)
        try:
            rec = json.loads(out.read_text())
        except (OSError, ValueError):
            rec = {}
        rows = rec.get('rows', [])
        checks[f'L{L}'] = dict(passed=cp.returncode == 0 and rec.get('graphs') == POWER_CLASSES[L] and rec.get('failures') == 0
                               and all(r.get('matches_induced') for r in rows), returncode=cp.returncode,
                               graphs=rec.get('graphs'), expected_graphs=POWER_CLASSES[L], failures=rec.get('failures'),
                               seconds=round(time.time() - t0, 1), stderr=cp.stderr[-500:])
    return gate_record(ev, 'gate3', '3 edge forests on every power class (H1 check_edge_forests)', checks,
                       binary_sha256=c.sha256_file(Path(a.bin) / 'check_edge_forests'))


def cmd_gate4(a) -> int:
    ev = c.refuse_c62d(Path(a.evidence).resolve(), 'evidence directory')
    rc, rec, log = run_tool([str(GEN3 / 'kirchhoff3.py'), '--payload', a.d3, '--inventory', a.inventory,
                             '--output', str(ev / c.GATE_SUPPORT['gate4'][0])])
    n = rec.get('kernels') if rec else None
    return gate_record(ev, 'gate4', '4 Kirchhoff, exact, independent code', dict(
        kirchhoff=dict(passed=rc == 0 and bool(rec and rec['passed']) and n == 144, kernels=n, expected=144,
                       record=c.GATE_SUPPORT['gate4'][0], log=log if rc else '')))


def build_command_tokens(cmd: str) -> list[str]:
    t = cmd.split()
    if '-o' in t:
        i = t.index('-o')
        t = t[:i + 1] + t[i + 2:]
    return t


def cmd_gate5(a) -> int:
    """Gate 5 (a) provenance, (b) correspondence with the published tree, (c)-(e) forest_check.py; the certificate is
    true exactly when (a)-(d) pass."""
    ev = c.refuse_c62d(Path(a.evidence).resolve(), 'evidence directory')
    h1 = Path(a.inventory)
    man = json.loads((h1 / 'MANIFEST.json').read_text())
    gsrc, gbin = Path(a.h1gen) / 'src', Path(a.h1gen) / 'bin'
    checks = {}
    # (a)
    e, binaries = [], {}
    pins = man.get('gen_sources_sha256', {})
    copied = sorted(p.name for p in gsrc.iterdir() if p.is_file()) if gsrc.is_dir() else []
    if not copied:
        e.append(f'{gsrc}: no copied builder sources')
    for name in copied:
        if pins.get(f'gen/{name}') != c.sha256_file(gsrc / name):
            e.append(f'{gsrc / name}: sha256 differs from MANIFEST gen_sources_sha256 (or is not listed)')
    for k in (k for k in pins if k.startswith('gen/')):
        if k[4:] not in copied:
            e.append(f'MANIFEST source {k} was not copied')
    for L in (7, 8):
        f = Path(a.classes) / f'classes{L}.txt'
        if c.sha256_file(f) != man.get('classes_sha256', {}).get(f'classes{L}.txt'):
            e.append(f'{f}: sha256 differs from MANIFEST classes_sha256')
    for prog in ('build_free', 'build_power', 'check_edge_forests'):
        rec = man.get('builders', {}).get(prog, {})
        bt = gbin / f'{prog}.build.txt'
        cmd = next((ln[len('command: '):] for ln in bt.read_text().splitlines() if ln.startswith('command: ')), '') if bt.is_file() else ''
        if build_command_tokens(cmd) != build_command_tokens(rec.get('command', '')):
            e.append(f'{bt}: command differs from MANIFEST builders.{prog}.command apart from the -o path')
        b = gbin / prog
        h = c.sha256_file(b) if b.is_file() else None
        binaries[prog] = dict(sha256=h, manifest_sha256=rec.get('sha256'), equal=h == rec.get('sha256'), command=cmd)
    checks['a_provenance'] = dict(passed=not e, copied_sources=len(copied), binaries=binaries,
                                  note='a binary sha256 difference alone does not fail (b) is the proof', errors=e[:50])
    # (b)
    e = []
    rm = Path(a.regen) / 'regen_MEMBERS.sha256'
    if not rm.is_file() or rm.read_bytes() != (h1 / 'MEMBERS.sha256').read_bytes():
        e.append(f'{rm}: not byte-identical to the H1 copy\'s MEMBERS.sha256')
    elif c.sha256_file(rm) != H1_MEMBERS_SHA256 and not a.fixture:
        e.append(f'{rm}: sha256 {c.sha256_file(rm)} is not {H1_MEMBERS_SHA256}')
    for L in (7, 8):
        ri = Path(a.regen) / 'regen_inv' / f'inventory_L{L}.json'
        if not ri.is_file() or ri.read_bytes() != (h1 / f'inventory_L{L}.json').read_bytes():
            e.append(f'{ri}: not byte-identical to the H1 copy\'s inventory_L{L}.json')
    checks['b_correspondence'] = dict(passed=not e, members_sha256=c.sha256_file(rm) if rm.is_file() else None, errors=e)
    # (c)-(e)
    args = [str(GEN3 / 'forest_check.py'), '--side', a.side, '--c8d1', a.classes, '--inventory', a.inventory,
            '--output', str(ev / c.GATE_SUPPORT['gate5'][0])]
    if a.probe:
        args += ['--probe', a.probe]
    rc, rec, log = run_tool(args)
    fresh = rc == 0 and rec is not None   # S4-002: this invocation's record, from a run that exited 0
    rec = rec or {}
    checks['c_masks'] = dict(passed=fresh and rec.get('c_masks') is True, returncode=rc, fresh_record=rec != {},
                             record=c.GATE_SUPPORT['gate5'][0], log=log if rc else '')
    checks['d_forests'] = dict(passed=fresh and rec.get('d_forests') is True, returncode=rc)
    if a.probe:
        checks['e_size_probe'] = dict(passed=fresh and rec.get('e_probe') is True, returncode=rc, supplementary=True)
    cert = all(checks[k]['passed'] for k in ('a_provenance', 'b_correspondence', 'c_masks', 'd_forests'))
    # (a) "passes with a warning" (PLAN F, test_gen3 row): a builder binary whose sha256 differs from the MANIFEST's
    # does not fail the gate ((b) is the proof); it is listed here and printed.
    warnings = [f'a_provenance: {prog} sha256 {b["sha256"]} differs from MANIFEST builders.{prog}.sha256 '
                f'{b["manifest_sha256"]} (passes: (b) ties the outputs to the published tree)'
                for prog, b in binaries.items() if not b['equal']]
    for w in warnings:
        print('gate5 WARNING', w)
    return gate_record(ev, 'gate5', '5 forest identity on the builder masks (a)-(e)', checks,
                       gate_5_forest_certificate=cert, warnings=warnings)


def cmd_gate7(a) -> int:
    """Gate 7: the rate audit at L7 and L8 (minimum rate 3 quarters free, 1 quarter power; clamped and double-lift counts
    per kernel recorded; the double-lift power-L8 count is the pre-pilot prevalence estimate, F25) and
    check_dimension8.py (i)-(iv)."""
    ev = c.refuse_c62d(Path(a.evidence).resolve(), 'evidence directory')
    checks = {}
    for L in (7, 8):
        recs = json.loads((Path(a.audits) / f'rate_audit_L{L}.json').read_text())
        e, summ = [], {}
        for r in recs:
            s = r['file'].split('/')[0].split('_')[1]
            x = summ.setdefault(s, dict(kernels=0, min_rate_quarters=99, clamped_subsets=0, double_lift_kernels=0,
                                        double_lift_subsets=0, min_raw=99, raw_histogram={}))
            x['kernels'] += 1
            x['min_rate_quarters'] = min(x['min_rate_quarters'], r['minimum_rate_quarters'])
            x['clamped_subsets'] += r['cancelled_nonpositive_subsets']
            x['double_lift_kernels'] += r['double_lift_subsets'] > 0
            x['double_lift_subsets'] += r['double_lift_subsets']
            x['min_raw'] = min(x['min_raw'], r['min_raw'])
            for v, k in r['raw_histogram'].items():
                x['raw_histogram'][v] = x['raw_histogram'].get(v, 0) + k
            if r['minimum_rate_quarters'] < MIN_RATE[s]:
                e.append(f'{r["file"]}: minimum rate {r["minimum_rate_quarters"]} quarters < {MIN_RATE[s]}')
        want = H1_EXPECT[f'L{L}']
        if {s: v['kernels'] for s, v in summ.items()} != want:
            e.append(f'L{L}: audit holds {dict((s, v["kernels"]) for s, v in summ.items())} kernels, expected {want}')
        checks[f'rate_audit_L{L}'] = dict(passed=not e, per_sector=summ, thresholds_quarters=MIN_RATE, errors=e[:50],
                                         error_count=len(e))
    args = [str(GEN3 / 'check_dimension8.py'), '--d2', a.h1, '--d3', a.d3, '--output', str(ev / c.GATE_SUPPORT['gate7'][0])]
    for k in ('two_loop', 'two_loop_order7', 'historical', 'gamma'):
        if getattr(a, k):
            args += [f'--{k.replace("_", "-")}', getattr(a, k)]
    rc, rec, log = run_tool(args)
    checks['check_dimension8'] = dict(passed=rc == 0 and bool(rec and rec['passed']), returncode=rc,
                                      record=c.GATE_SUPPORT['gate7'][0], log=log if rc else '')
    return gate_record(ev, 'gate7', '7 rate audit and check_dimension8 (i)-(iv)', checks)


def cmd_determinism(a) -> int:
    """A.4: the regeneration at OMP_NUM_THREADS=1 and at N threads gives identical MEMBERS_d3.sha256."""
    ev = c.refuse_c62d(Path(a.evidence).resolve(), 'evidence directory')
    ma, mb = stage_members(Path(a.a)), stage_members(Path(a.b))
    ta, tb = ''.join(f'{h}  {n}\n' for n, h in ma), ''.join(f'{h}  {n}\n' for n, h in mb)
    return gate_record(ev, 'determinism', 'A.4 determinism (1 and N threads)', dict(members=dict(
        passed=bool(ma) and ta == tb, members=len(ma), sha256_a=c.sha256_bytes(ta.encode()), sha256_b=c.sha256_bytes(tb.encode()),
        threads=a.threads)))


def cmd_report(a) -> int:
    """A.5: the gate record for LRI_C8_shared/assembly/H1_gates/inventory8_d2_<H1 sha12>_C63d_gates.json, assembled from
    the J-GEN-D3 evidence (gates/*.json, verify_d3.json, MANIFEST_d3.sha256) and J-GEN-D3-0's gate1a.json. Written only
    when every gate passed; the HANDOFF's c63d block (pin_recorded, gates_1_7, gate_5_forest_certificate) is its
    `handoff_c63d` field, which C63d writes into the HANDOFF (DECISIONS A3, agreed 2026-10-04). Gate 6 (pack
    identity) is reported later, with the C8 packs (Stage 2b): `addendum`, then `handoff-gate6`."""
    ev, out = Path(a.evidence), c.refuse_c62d(Path(a.output), 'gate record')
    if not re.fullmatch(r'[0-9a-f]{64}', a.h1_pin):
        c.die(f'--h1-pin {a.h1_pin!r}: not a sha256')
    if out.exists():
        c.die(f'{out}: exists (a gate record is written once)')
    recs, errors = {}, []
    for name in c.H1_GATES:
        p = ev / 'gates' / f'{name}.json'
        try:
            recs[name] = json.loads(p.read_text())
        except (OSError, ValueError) as ex:
            errors.append(f'{p}: {ex}')
            continue
        if recs[name].get('passed') is not True:
            errors.append(f'{p}: gate did not pass')
    try:
        g1a = json.loads(Path(a.gate1a).read_text())
        errors += gate1a_errors(g1a if isinstance(g1a, dict) else {}, str(a.gate1a))
    except (OSError, ValueError) as ex:
        errors.append(f'{a.gate1a}: {ex}')
        g1a = {}
    try:
        ver = json.loads((ev / 'verify_d3.json').read_text())
        pin = (ev / 'MANIFEST_d3.sha256').read_text().strip()
        if not ver.get('passed') or ver.get('pin') != pin or not re.fullmatch(r'[0-9a-f]{64}', pin):
            errors.append(f'{ev}/verify_d3.json: the published tree did not verify against {pin!r}')
    except (OSError, ValueError) as ex:
        errors.append(f'{ev}: verify_d3.json or MANIFEST_d3.sha256: {ex}')
        pin = None
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        print('report: NOT written (a gate is missing or failed)', file=sys.stderr)
        return 1
    cert = bool(recs['gate5'].get('gate_5_forest_certificate'))
    gates = {'1a': True, '1b': True, '2': True, '3': True, '4': True, '5': True, '6': 'pending (Stage 2b, with the C8 packs)',
             '7': True, 'determinism': True}
    rec = dict(schema='c8-d3-h1-gates-1', h1='inventory8_d2', h1_manifest_sha256=a.h1_pin, manifest_d3_sha256=pin,
               package='LRI_C8_D3_HPC', commit=a.commit, gates=gates, gate_5_forest_certificate=cert,
               jobs=sorted({r.get('slurm_job_id') for r in recs.values() if r.get('slurm_job_id')}),
               hosts=sorted({r.get('host') for r in recs.values() if r.get('host')}),
               cpus=sorted({r.get('cpu') for r in recs.values() if r.get('cpu')}),
               gate1a=dict(identical=g1a['checks']['byte_reproduction_c7d3']['identical'], job=g1a['environment'].get('slurm_job_id'),
                           host=g1a['environment'].get('host'), machine=g1a['environment'].get('machine'),
                           run_class=g1a.get('run_class')),
               details={k: {kk: vv.get('passed') for kk, vv in v.get('checks', {}).items()} for k, v in recs.items()},
               handoff_c63d=dict(pin_recorded=a.h1_pin, gates_1_7={k: v for k, v in gates.items() if k != 'determinism'},
                                 gate_5_forest_certificate=cert, manifest_d3_sha256=pin),
               utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    c.write_json(out, rec, 'gate record')
    print(json.dumps(rec['handoff_c63d']))
    return 0


def cmd_gate6(a) -> int:
    """Gate 6, pack identity (A.3 6, A-INV-2(b); Stage 2b): see the module text."""
    inputs = Path(a.inputs).resolve() if a.inputs else ROOT / 'inputs'
    ev = c.refuse_c62d(Path(a.evidence).resolve(), 'evidence directory')
    man_b = (inputs / 'manifest.json').read_bytes()
    man = json.loads(man_b)
    inv_b = (inputs / 'inventory.json').read_bytes()
    if c.sha256_bytes(inv_b) != man['sha256'].get('inventory.json'):
        c.die(f'{inputs}/inventory.json: sha256 differs from {inputs}/manifest.json')
    inv = json.loads(inv_b)
    c7 = json.loads((ROOT / 'tests/fixtures/c7_inputs/inventory.json').read_text())
    c7man = json.loads((ROOT / 'tests/fixtures/c7_inputs/manifest.json').read_text())
    pins = json.loads(PINS_JSON.read_text())['c7d3_payloads']
    checks = {}
    # (a) every C7(3) row: the C8 member at the C8 offset has C7(3)'s sha256
    e, n, rows = [], 0, {}
    packs = {}
    for s in ('free', 'power'):
        for L, c7rows in c7[s].items():
            c8 = {r['id']: r for r in inv.get(s, {}).get(L, [])}
            p = inputs / f'packs/{s}_L{L}.pack'
            with p.open('rb') as f:
                for r in c7rows:
                    q = c8.get(r['id'])
                    if q is None:
                        e.append(f'{s} L{L} G{r["id"]}: not in the C8 inventory')
                        continue
                    f.seek(q['offset'])
                    h = c.sha256_bytes(f.read(q['length']))
                    n += 1
                    if not (h == q['sha256'] == r['sha256']):
                        e.append(f'{s} L{L} G{r["id"]}: C8 member {h[:12]} (row {q["sha256"][:12]}) is not C7(3)\'s row '
                                 f'{r["sha256"][:12]}')
                    rows[f'{s}/L{L}/G{r["id"]}.txt'] = h
    checks['a_c7d3_rows'] = dict(passed=not e and n == 3511, members=n, errors=e[:50], error_count=len(e))
    # (b) the digest of the 3,512 C7(3) payloads (the rows and the L = 2 control graph)
    rows['free/L2/G0.txt'] = c.sha256_file(ROOT / 'reference/inputs/free/L2/G0.txt')
    dig = c.sha256_bytes(list_text(rows).encode())
    checks['b_c7d3_payload_digest'] = dict(passed=dig == pins['digest_sha256'] and len(rows) == pins['files'],
                                           digest=dig, pin=pins['digest_sha256'], files=len(rows))
    # (c) the L3-L6 packs are a6ce987's bytes
    e = []
    for s in ('free', 'power'):
        for L in (3, 4, 5, 6):
            rel = f'packs/{s}_L{L}.pack'
            got = c.sha256_file(inputs / rel)
            packs[rel] = got
            if not (got == man['sha256'].get(rel) == c7man['sha256'].get(rel)):
                e.append(f'{rel}: {got[:12]} is not a6ce987\'s {c7man["sha256"].get(rel, "")[:12]}')
    checks['c_l3_l6_packs_a6ce987'] = dict(passed=not e, errors=e)
    # (d) the new L7 members at their MEMBERS_d3.sha256 hashes (the inputs' copy, tied to the d3 pin)
    e, n_new, sg = [], {'free': 0, 'power': 0}, {}
    mem_b = (inputs / 'd3/MEMBERS_d3.sha256').read_bytes() if (inputs / 'd3/MEMBERS_d3.sha256').is_file() else b''
    d3man_b = (inputs / 'd3/MANIFEST_d3.json').read_bytes() if (inputs / 'd3/MANIFEST_d3.json').is_file() else b''
    sums_b = (inputs / 'd3/SHA256SUMS').read_bytes() if (inputs / 'd3/SHA256SUMS').is_file() else b''
    chain = (bool(mem_b) and c.sha256_bytes(mem_b) == man['sha256'].get('d3/MEMBERS_d3.sha256')
             and c.sha256_bytes(d3man_b) == man.get('d3_payload_manifest_sha256') and sums_b
             and c.sha256_bytes(sums_b) == json.loads(d3man_b).get('sha256sums_sha256')
             and f'{c.sha256_bytes(mem_b)}  MEMBERS_d3.sha256' in sums_b.decode().splitlines())
    if not chain:
        e.append('inputs/d3/MEMBERS_d3.sha256 is not tied to the d3 pin (manifest pin, MANIFEST_d3.json, SHA256SUMS)')
    members = {}
    for line in mem_b.decode().splitlines():
        m = ROW.fullmatch(line)
        if m:
            members[m.group(2)] = m.group(1)
    for s in ('free', 'power'):
        c7ids = {r['id'] for r in c7[s]['7']}
        p = inputs / f'packs/{s}_L7.pack'
        with p.open('rb') as f:
            for q in inv.get(s, {}).get('7', []):
                f.seek(q['offset'])
                h = c.sha256_bytes(f.read(q['length']))
                if h != members.get(f'L7_{s}/G{q["id"]}.txt'):
                    e.append(f'{s} L7 G{q["id"]}: member {h[:12]} is not at its MEMBERS_d3.sha256 hash')
                if q['id'] not in c7ids:
                    n_new[s] += 1
                    sg[q['s_G']] = sg.get(q['s_G'], 0) + 1
        packs[f'packs/{s}_L7.pack'] = c.sha256_file(p)
    checks['d_l7_members_d3'] = dict(passed=not e and n_new == {'free': 143, 'power': 119} and set(sg) == {4},
                                     new_members=n_new, new_s_G=sg, chain=bool(chain), errors=e[:50], error_count=len(e))
    cnt = {s: len(inv.get(s, {}).get('7', [])) for s in ('free', 'power')}
    checks['e_l7_totals'] = dict(passed=cnt == H1_EXPECT['L7'] and man.get('l7_complete') is True, l7=cnt,
                                 expected=H1_EXPECT['L7'], l7_complete=man.get('l7_complete'))
    return gate_record(ev, 'gate6', '6 pack identity (A.3 6, A-INV-2(b); Stage 2b)', checks,
                       inputs=str(inputs), inputs_manifest_sha256=c.sha256_bytes(man_b),
                       d3_payload_manifest_sha256=man.get('d3_payload_manifest_sha256'),
                       inventory8_d2_manifest_sha256=man.get('inventory8_d2_manifest_sha256'), packs=packs,
                       l8_packs={r: man['sha256'].get(r) for r in ('packs/free_L8.pack', 'packs/power_L8.pack')})


def cmd_addendum(a) -> int:
    """Gate 6's addendum to the A.5 gate record (written once by `report`): see the module text."""
    out = c.refuse_c62d(Path(a.output).resolve(), 'gate-6 addendum')
    if out.exists():
        c.die(f'{out}: exists (an addendum is written once)')
    g6 = json.loads(Path(a.gate6).read_text())
    gr_b = Path(a.gate_record).read_bytes()
    gr = json.loads(gr_b)
    man_b = Path(a.inputs_manifest).read_bytes()
    man = json.loads(man_b)
    errors = []
    if g6.get('gate') != '6 pack identity (A.3 6, A-INV-2(b); Stage 2b)' or g6.get('passed') is not True:
        errors.append(f'{a.gate6}: not a passed gate-6 record')
    if g6.get('inputs_manifest_sha256') != c.sha256_bytes(man_b):
        errors.append(f'{a.gate6}: made on inputs manifest {g6.get("inputs_manifest_sha256")}, not {a.inputs_manifest}')
    if gr.get('schema') != 'c8-d3-h1-gates-1':
        errors.append(f'{a.gate_record}: not the A.5 gate record')
    if (gr.get('manifest_d3_sha256'), gr.get('h1_manifest_sha256')) != (man.get('d3_payload_manifest_sha256'),
                                                                        man.get('inventory8_d2_manifest_sha256')):
        errors.append(f'{a.gate_record}: its d=3 / H1 pins {gr.get("manifest_d3_sha256")} / {gr.get("h1_manifest_sha256")} '
                      f'differ from the inputs manifest\'s copies')
    if not re.fullmatch(r'[0-9a-f]{7,40}', a.commit):
        errors.append(f'--commit {a.commit!r}: not a commit')
    if errors:
        for x in errors:
            print(x, file=sys.stderr)
        print('addendum: NOT written', file=sys.stderr)
        return 1
    rec = dict(schema='c8-d3-h1-gates-addendum-1', h1='inventory8_d2', h1_manifest_sha256=gr['h1_manifest_sha256'],
               manifest_d3_sha256=gr['manifest_d3_sha256'], package='LRI_C8_D3_HPC', commit=a.commit,
               addendum_to=dict(file=Path(a.gate_record).name, sha256=c.sha256_bytes(gr_b),
                                note='the A.5 gate record is written once (gates_d3.py report); its gate "6" said '
                                     '"pending (Stage 2b, with the C8 packs)"; this addendum records it'),
               gates={'6': True}, gate6={k: v.get('passed') for k, v in g6['checks'].items()},
               gate6_summary=dict(c7d3_members=g6['checks']['a_c7d3_rows']['members'],
                                  c7d3_payload_digest=g6['checks']['b_c7d3_payload_digest']['digest'],
                                  new_l7_members=g6['checks']['d_l7_members_d3']['new_members'],
                                  l7_totals=g6['checks']['e_l7_totals']['l7']),
               jobs=[j for j in [g6.get('slurm_job_id')] if j], hosts=[g6.get('host')], cpus=[g6.get('cpu')],
               inputs_manifest_sha256=c.sha256_bytes(man_b), packs=g6.get('packs'), l8_packs=g6.get('l8_packs'),
               handoff_c63d_update=dict(gates_1_7={'6': True}),
               utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    c.write_json(out, rec, 'gate-6 addendum')
    print(json.dumps(dict(written=str(out), gates=rec['gates'], jobs=rec['jobs'])))
    return 0


# ---- the A.5 report-back into the shared coordination files (DECISIONS A3; A.2 step 6) -----------------------------
PENDING6 = 'pending (Stage 2b, with the C8 packs)'
HANDOFF_NAME, DECISIONS_NAME = 'HANDOFF_inventory8_d2.json', 'DECISIONS.md'
ACK_HEADER = '## Acknowledgment log (append-only; C63d may append here)'
NOTE_NAME = re.compile(r'NOTE_C63d_to_C62d_(\d{4}-\d{2}-\d{2})[a-z]?\.md')
GATE_KEYS = ('1a', '1b', '2', '3', '4', '5', '6', '7')


def shared_file(path, folder: str, name: str | None = None, exists: bool = True) -> Path:
    """`path` as <...>/LRI_C8_shared/<folder>/<name> (also after resolving symlinks), a regular file when `exists`.
    The report-back subcommands write only there: the two inventory files by exact name, the NOTE in assembly/."""
    p = Path(os.path.abspath(os.fspath(path)))
    for q in (p, p.parent.resolve() / p.name):
        if (q.parent.name, q.parent.parent.name) != (folder, 'LRI_C8_shared') or (name and q.name != name):
            c.die(f'{path}: not LRI_C8_shared/{folder}/{name or "<file>"}')
    if exists and (p.is_symlink() or not p.is_file()):
        c.die(f'{path}: not a regular file')
    return p


def json_leaves_differing(a, b, at=()) -> list:
    """The paths at which two parsed JSON values differ (key order and value types included)."""
    if isinstance(a, dict) and isinstance(b, dict):
        if list(a) != list(b):
            return [at + ('<keys>',)]
        return [d for k in a for d in json_leaves_differing(a[k], b[k], at + (k,))]
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [at + ('<length>',)]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in json_leaves_differing(x, y, at + (i,))]
    return [] if type(a) is type(b) and a == b else [at]


# S4-004: the two report-back writes go into files C62d owns, whose writers honour no lock of ours. Neither is a
# check-then-replace any more (an owner's edit between the check and a rename would be lost):
#  - decisions-ack appends: the duplicate check, then ONE O_APPEND write of the new line, only if the file still holds
#    exactly the bytes read (checked through the open descriptor); afterwards the file must read old + line;
#  - handoff-gate6 swaps with a take-aside compare-and-swap: rename(p, aside) (aside a unique sibling), compare the
#    aside's bytes with the bytes read, link(new, p) (fails if p was recreated meanwhile), unlink(aside). Between the
#    rename and the link, p is absent for an instant: a reader then gets "no such file" and must retry; no writer's
#    bytes are lost. On any mismatch or failure the aside is restored if p is absent (a newer p is never overwritten;
#    the aside is then kept and named) and the tool refuses (exit 1).
def append_exact(p: Path, old: bytes, suffix: bytes) -> None:
    """Append `suffix` to `p` with one O_APPEND write, only while `p` holds exactly `old`; then `p` must read old +
    suffix. Refuses (exit 1) before writing if `p` changed; after the write, a different content (a concurrent writer)
    is reported, never repaired."""
    fd = os.open(p, os.O_RDWR | os.O_APPEND | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_CLOEXEC', 0))
    try:
        held = b''
        while len(held) <= len(old):
            chunk = os.pread(fd, len(old) + 1 - len(held), len(held))
            if not chunk:
                break
            held += chunk
        if held != old:
            c.die(f'{p}: changed while this tool ran (nothing written)', 1)
        n = os.write(fd, suffix)
        os.fsync(fd)
    finally:
        os.close(fd)
    if n != len(suffix):
        c.die(f'{p}: short append ({n} of {len(suffix)} bytes): check the file by hand', 1)
    if p.read_bytes() != old + suffix:
        c.die(f'{p}: after the one append it is not the old bytes plus the new line (a concurrent writer): the line was '
              f'appended once; nothing else was written; check the file by hand', 1)


def swap_if_unchanged(p: Path, old: bytes, new: bytes) -> None:
    """Replace `p`'s bytes `old` by `new` with the take-aside compare-and-swap described above; the mode is kept; the
    result is read back. Refuses (exit 1) without losing any writer's bytes."""
    mode = p.stat().st_mode & 0o7777
    tag = f'{os.getpid()}.{secrets.token_hex(6)}'
    tmp, aside = p.with_name(f'.{p.name}.c63d.{tag}.tmp'), p.with_name(f'.{p.name}.c63d.{tag}.aside')
    try:
        with open(tmp, 'xb') as f:
            f.write(new)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, mode)

        def refuse(why: str) -> None:
            try:
                os.link(aside, p)          # restore only while p is absent; never over a newer p
                os.unlink(aside)
                kept = ''
            except FileExistsError:
                kept = f'; {p} was recreated meanwhile and is left as it is; the bytes taken aside are kept in {aside}'
            except OSError as ex:
                kept = f'; the bytes taken aside could not be put back ({ex}) and are kept in {aside}'
            c.die(f'{p}: {why} (nothing written{kept})', 1)
        try:
            os.rename(p, aside)            # p is absent from here ...
        except OSError as ex:
            c.die(f'{p}: cannot take it aside ({ex}; nothing written)', 1)
        try:
            took = aside.read_bytes()
        except OSError as ex:
            refuse(f'cannot read the bytes taken aside ({ex})')
        if took != old:
            refuse('changed while this tool ran')
        try:
            os.link(tmp, p)                # ... to here; fails if p was recreated meanwhile
        except OSError as ex:
            refuse(f'cannot put the new bytes in place ({ex})')
        os.unlink(aside)
    finally:
        tmp.unlink(missing_ok=True)
    if p.read_bytes() != new:
        c.die(f'{p}: reads back different bytes right after the swap (a concurrent writer?)', 1)


def report_back_records(gate_record: str, addendum: str) -> tuple[dict, bytes, dict, bytes, list[str]]:
    """The A.5 gate record and the gate-6 addendum, with the checks every report-back subcommand needs."""
    gr_b, ad_b = Path(gate_record).read_bytes(), Path(addendum).read_bytes()
    gr, ad = json.loads(gr_b), json.loads(ad_b)
    e = []
    hc = gr.get('handoff_c63d') or {}
    if gr.get('schema') != 'c8-d3-h1-gates-1' or not isinstance(gr.get('gates'), dict):
        e.append(f'{gate_record}: not the A.5 gate record')
    elif ({k: v for k, v in gr['gates'].items() if k != '6'} != {k: True for k in gr['gates'] if k != '6'}
          or gr['gates'].get('6') != PENDING6 or gr.get('gate_5_forest_certificate') is not True
          or set(gr['gates']) != set(GATE_KEYS) | {'determinism'}):
        e.append(f'{gate_record}: gates {gr["gates"]} are not "every gate passed, 6 pending"')
    if hc.get('gates_1_7') != {k: gr.get('gates', {}).get(k) for k in GATE_KEYS} or hc.get('pin_recorded') != gr.get(
            'h1_manifest_sha256') or hc.get('gate_5_forest_certificate') != gr.get('gate_5_forest_certificate'):
        e.append(f'{gate_record}: handoff_c63d does not restate the record')
    for k in ('h1_manifest_sha256', 'manifest_d3_sha256'):
        if not re.fullmatch(r'[0-9a-f]{64}', str(gr.get(k))) or ad.get(k) != gr.get(k):
            e.append(f'{addendum}: {k} {ad.get(k)} is not the gate record\'s {gr.get(k)}')
    to = ad.get('addendum_to') or {}
    if ad.get('schema') != 'c8-d3-h1-gates-addendum-1' or ad.get('gates') != {'6': True} or not ad.get('gate6') \
            or not all(v is True for v in ad['gate6'].values()):
        e.append(f'{addendum}: not a passed gate-6 addendum')
    if to.get('sha256') != c.sha256_bytes(gr_b) or to.get('file') != Path(gate_record).name:
        e.append(f'{addendum}: addendum_to ({to.get("file")}, {str(to.get("sha256"))[:12]}) is not {gate_record}')
    if ad.get('handoff_c63d_update') != {'gates_1_7': {'6': True}}:
        e.append(f'{addendum}: handoff_c63d_update is not {{"gates_1_7": {{"6": true}}}}')
    return gr, gr_b, ad, ad_b, e


def handoff_state(h: dict, gr: dict) -> str:
    """'pending' (the c63d block as the gate record wrote it), 'done' (the same with gate 6 true) or why neither."""
    blk = h.get('c63d') if isinstance(h.get('c63d'), dict) else {}
    if h.get('manifest_sha256') != gr['h1_manifest_sha256']:
        return f'manifest_sha256 {h.get("manifest_sha256")} is not the gate record\'s H1 pin'
    if blk.get('pin_recorded') != gr['h1_manifest_sha256'] or blk.get('gate_5_forest_certificate') != gr[
            'gate_5_forest_certificate']:
        return 'its c63d block\'s pin_recorded or gate_5_forest_certificate differs from the gate record'
    g = blk.get('gates_1_7')
    want = gr['handoff_c63d']['gates_1_7']
    if g == want:
        return 'pending'
    if g == dict(want, **{'6': True}) and list(g) == list(want):
        return 'done'
    return f'its c63d.gates_1_7 {g} is neither the gate record\'s nor that with "6": true'


def finish_report_back(a, what: str, rec: dict) -> int:
    print(json.dumps(rec, indent=1))
    if a.dry_run:
        print(f'{what}: dry run, nothing written', file=sys.stderr)
    return 0


def report_back_evidence(a, name: str) -> Path:
    ev = c.refuse_c62d(Path(a.evidence).resolve(), 'evidence directory')
    if (ev / name).exists():
        c.die(f'{ev / name}: exists (one report-back record per evidence directory)')
    return ev


def cmd_handoff_gate6(a) -> int:
    """DECISIONS A3: gate 6 into the HANDOFF's c63d block (see the module text)."""
    p = shared_file(a.handoff, 'inventory', HANDOFF_NAME)
    ev = None if a.dry_run else report_back_evidence(a, 'handoff_gate6.json')
    gr, gr_b, ad, ad_b, errors = report_back_records(a.gate_record, a.addendum)
    old = p.read_bytes()
    h = json.loads(old)
    if (json.dumps(h, indent=1) + '\n').encode() != old:
        errors.append(f'{p}: not the json.dumps(indent=1) text of handoff_inventory.py (a rewrite would change other bytes)')
    state = handoff_state(h, gr) if not errors else 'not checked'
    if state not in ('pending', 'done'):
        errors.append(f'{p}: {state}')
    if errors:
        for x in errors:
            print(x, file=sys.stderr)
        print('handoff-gate6: NOT written', file=sys.stderr)
        return 1
    rec = dict(schema='c8-d3-handoff-gate6-1', handoff=str(p), decision='DECISIONS A3 (agreed 2026-10-04)',
               gate_record=dict(file=Path(a.gate_record).name, sha256=c.sha256_bytes(gr_b)),
               addendum=dict(file=Path(a.addendum).name, sha256=c.sha256_bytes(ad_b)),
               sha256_before=c.sha256_bytes(old), utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    if state == 'done':
        rec.update(changed=[], sha256_after=rec['sha256_before'], note='gate 6 was already recorded; nothing written')
        return finish_report_back(a, 'handoff-gate6', rec)
    new_h = json.loads(old)
    new_h['c63d']['gates_1_7']['6'] = True
    new = (json.dumps(new_h, indent=1) + '\n').encode()
    diff = json_leaves_differing(h, json.loads(new))
    if diff != [('c63d', 'gates_1_7', '6')]:
        c.die(f'{p}: the rewrite would change {diff}, not exactly c63d.gates_1_7["6"]', 1)
    rec.update(changed=['c63d.gates_1_7["6"]: "pending (Stage 2b, with the C8 packs)" -> true'],
               sha256_after=c.sha256_bytes(new), before_copy='HANDOFF_inventory8_d2.before.json')
    if a.dry_run:
        return finish_report_back(a, 'handoff-gate6', rec)
    ev.mkdir(parents=True, exist_ok=True)
    (ev / rec['before_copy']).write_bytes(old)
    swap_if_unchanged(p, old, new)
    c.write_json(ev / 'handoff_gate6.json', rec, 'report-back record')
    return finish_report_back(a, 'handoff-gate6', rec)


def ack_log(text: str, path) -> list[str]:
    """Why `text` is not a DECISIONS.md whose last section is the acknowledgment log ending in a table row."""
    lines = text.split('\n')
    heads = [i for i, s in enumerate(lines) if s == ACK_HEADER]
    if len(heads) != 1:
        return [f'{path}: {len(heads)} lines {ACK_HEADER!r} (need exactly one)']
    if any(s.startswith('#') for s in lines[heads[0] + 1:]):
        return [f'{path}: a heading follows the acknowledgment log (it must be the last section)']
    if not text.endswith('\n') or not lines[-2].startswith('| ') or not lines[-2].endswith(' |'):
        return [f'{path}: does not end with a table row and a newline']
    return []


def ack_line(a, gr: dict, gr_b: bytes, ad: dict, ad_b: bytes) -> str:
    return (f'| {a.date} | H1 gates 1–7 (A.5) and the d=3 payload pin | C63d\'s gates 1–7 on H1 (MANIFEST sha256 '
            f'`{gr["h1_manifest_sha256"]}`) all passed and gate 5\'s forest certificate holds. The d=3 payload '
            f'`d3_payload/{gr["h1_manifest_sha256"][:12]}` built from it is pinned by MANIFEST_d3.json sha256 '
            f'`{gr["manifest_d3_sha256"]}` (A.2 step 6: `make inputs-l8 D3PIN=` and `gen3/verify_d3.py --pin` take '
            f'this value). Records: `assembly/H1_gates/{Path(a.gate_record).name}` (sha256 `{c.sha256_bytes(gr_b)[:12]}…`; '
            f'J-GEN-D3-0 {gr.get("gate1a", {}).get("job")}, J-GEN-D3 {", ".join(gr.get("jobs", []))}) and gate 6 in '
            f'`assembly/H1_gates/{Path(a.addendum).name}` (sha256 `{c.sha256_bytes(ad_b)[:12]}…`; J-IN-1 '
            f'{", ".join(ad.get("jobs", []))}); the HANDOFF\'s `c63d` block holds gates 1–7 (A3). | C63d |')


def cmd_decisions_ack(a) -> int:
    """A.2 step 6 / A.5: the DECISIONS log line carrying the d3 pin (see the module text)."""
    p = shared_file(a.decisions, 'inventory', DECISIONS_NAME)
    hp = shared_file(a.handoff, 'inventory', HANDOFF_NAME)
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', a.date):
        c.die(f'--date {a.date!r}: not YYYY-MM-DD')
    ev = None if a.dry_run else report_back_evidence(a, 'decisions_ack.json')
    gr, gr_b, ad, ad_b, errors = report_back_records(a.gate_record, a.addendum)
    old = p.read_bytes()
    text = old.decode('utf-8')
    errors += ack_log(text, p)
    if not errors and handoff_state(json.loads(hp.read_bytes()), gr) != 'done':
        errors.append(f'{hp}: its c63d block does not hold gate 6 yet (run handoff-gate6 first)')
    if errors:
        for x in errors:
            print(x, file=sys.stderr)
        print('decisions-ack: NOT written', file=sys.stderr)
        return 1
    log = text.split(ACK_HEADER, 1)[1]
    rec = dict(schema='c8-d3-decisions-ack-1', decisions=str(p), sha256_before=c.sha256_bytes(old),
               manifest_d3_sha256=gr['manifest_d3_sha256'], utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    have = [s for s in log.split('\n') if gr['manifest_d3_sha256'] in s and s.rstrip().endswith('| C63d |')]
    if have:
        rec.update(line=have[0], sha256_after=rec['sha256_before'], note='the pin line is already logged; nothing written')
        return finish_report_back(a, 'decisions-ack', rec)
    line = ack_line(a, gr, gr_b, ad, ad_b)
    new = old + (line + '\n').encode('utf-8')
    if not new.startswith(old) or new.count(b'\n') != old.count(b'\n') + 1:
        c.die(f'{p}: the append would not be one line', 1)
    rec.update(line=line, sha256_after=c.sha256_bytes(new))
    if a.dry_run:
        return finish_report_back(a, 'decisions-ack', rec)
    ev.mkdir(parents=True, exist_ok=True)
    append_exact(p, old, new[len(old):])
    c.write_json(ev / 'decisions_ack.json', rec, 'report-back record')
    return finish_report_back(a, 'decisions-ack', rec)


def note_text(a, gr, gr_b, ad, ad_b, date: str, h1c: dict | None) -> str:
    """The NOTE's text: one line per item (Markdown wraps them), every value taken from the records."""
    h1, d3 = gr['h1_manifest_sha256'], gr['manifest_d3_sha256']
    g1a, g6 = gr.get('gate1a', {}), ad.get('gate6_summary', {})
    new7, tot7 = g6.get('new_l7_members', {}), g6.get('l7_totals', {})
    jobs = lambda xs: ', '.join(str(x) for x in xs if x)  # noqa: E731
    n = lambda x: f'{x:,}' if isinstance(x, int) else str(x)  # noqa: E731
    copy = (f'   - J-H1-COPY {h1c["slurm_job_id"]} ({h1c.get("host")}) copied the tree into C63d\'s store and verified the '
            f'copy with the tree\'s own verify_inventory.py (all four steps PASS). The source listing was unchanged '
            f'afterwards (A-INV-6).\n') if h1c else ''
    return (
        f'C63d -> C62d ({date}): H1 report-back (PLAN A.5, DECISIONS A3). C63d\'s gates 1-7 on inventory8_d2 all '
        f'passed, and the d=3 payload built from it is published and pinned. Nothing is requested from you.\n\n'
        f'1. H1 pin: MANIFEST.json sha256 {h1} (the HANDOFF\'s manifest_sha256).\n{copy}'
        f'2. Gates 1-7: the A.5 gate record LRI_C8_shared/assembly/H1_gates/{Path(a.gate_record).name} (sha256 '
        f'{c.sha256_bytes(gr_b)}, package LRI_C8_D3_HPC commit {gr.get("commit")}).\n'
        f'   - Gate 1a: J-GEN-D3-0 {g1a.get("job")} ({g1a.get("host")}, {g1a.get("machine")}). It reproduced '
        f'{n(g1a.get("identical"))} C7(3) payloads byte for byte from C7(2)\'s frozen d=2 payloads.\n'
        f'   - Gates 1b, 2, 3, 4, 5, 7 and the determinism check: J-GEN-D3 {jobs(gr.get("jobs", []))} '
        f'({jobs(gr.get("hosts", []))}, {jobs(gr.get("cpus", []))}).\n'
        f'   - Gate 5\'s forest certificate is true: (a)-(d) passed on the regenerated builder masks, so the '
        f'certificate covers the forest identity and no bare-series identity is needed at L8.\n'
        f'3. Gate 6 (pack identity, Stage 2b): true. The gate record is written once, so gate 6 is in the addendum '
        f'LRI_C8_shared/assembly/H1_gates/{Path(a.addendum).name} (sha256 {c.sha256_bytes(ad_b)}, commit '
        f'{ad.get("commit")}, J-IN-1 {jobs(ad.get("jobs", []))}).\n'
        f'   - The {n(g6.get("c7d3_members"))} C7(3) members of the C8 packs carry C7(3)\'s row sha256s (payload '
        f'digest {g6.get("c7d3_payload_digest")}).\n'
        f'   - L7 totals {n(tot7.get("free"))} + {n(tot7.get("power"))}, of which {n(new7.get("free"))} + '
        f'{n(new7.get("power"))} are the new s_G = 4 kernels.\n'
        f'4. HANDOFF_inventory8_d2.json: under A3, C63d\'s c63d block now reads gates_1_7 "6": true. pin_recorded and '
        f'gate_5_forest_certificate are unchanged, and nothing else in the file changed (gen3/gates_d3.py '
        f'handoff-gate6 checks that the structural difference is exactly that one value).\n'
        f'5. The d=3 payload: {a.payload_path}, pinned by MANIFEST_d3.json sha256 {d3}.\n'
        f'   - Verify a copy with `python3 -B gen3/verify_d3.py <tree> --pin {d3}` (LRI_C8_D3_HPC).\n'
        f'   - The pin is in the gate record and in the DECISIONS acknowledgment log (line of {a.ack_date}).\n'
        f'6. No defect was found, so the r2 procedure is not triggered.\n')


def cmd_note(a) -> int:
    """A.5's NOTE to C62d (see the module text)."""
    out = shared_file(a.output, 'assembly', exists=False)
    c.refuse_c62d(out, 'NOTE')
    m = NOTE_NAME.fullmatch(out.name)
    if not m:
        c.die(f'{a.output}: not NOTE_C63d_to_C62d_<YYYY-MM-DD>[a-z].md')
    if out.exists() or out.is_symlink():
        c.die(f'{out}: exists (a NOTE is written once)')
    hp = shared_file(a.handoff, 'inventory', HANDOFF_NAME)
    dp = shared_file(a.decisions, 'inventory', DECISIONS_NAME)
    gr, gr_b, ad, ad_b, errors = report_back_records(a.gate_record, a.addendum)
    h1c = None
    if a.h1_copy:
        h1c = json.loads(Path(a.h1_copy).read_text())
        ck = h1c.get('checks') or {}
        if h1c.get('passed') is not True or h1c.get('pin') != gr.get('h1_manifest_sha256') or not h1c.get('slurm_job_id') \
                or not all((ck.get(k) or {}).get('passed') is True for k in ('verify_inventory_copy', 'source_unchanged')):
            errors.append(f'{a.h1_copy}: not a passed J-H1-COPY record of the gate record\'s H1 pin')
    lines = []
    if not errors:
        if handoff_state(json.loads(hp.read_bytes()), gr) != 'done':
            errors.append(f'{hp}: its c63d block does not hold gate 6 yet (run handoff-gate6 first)')
        text = dp.read_text()
        errors += ack_log(text, dp)
        lines = [s for s in text.split(ACK_HEADER, 1)[-1].split('\n')
                 if gr['manifest_d3_sha256'] in s and s.rstrip().endswith('| C63d |')]
        if not lines:
            errors.append(f'{dp}: no acknowledgment-log line carries the d3 pin (run decisions-ack first)')
    if errors:
        for x in errors:
            print(x, file=sys.stderr)
        print('note: NOT written', file=sys.stderr)
        return 1
    a.ack_date = lines[0].split('|')[1].strip()
    text = note_text(a, gr, gr_b, ad, ad_b, m.group(1), h1c)
    if a.dry_run:
        print(text)
        print('note: dry run, nothing written', file=sys.stderr)
        return 0
    tmp = out.with_name(f'.{out.name}.{os.getpid()}.tmp')
    tmp.write_text(text)
    try:
        os.link(tmp, out)   # refuses an existing NOTE even if one appeared meanwhile
    except FileExistsError:
        c.die(f'{out}: exists (a NOTE is written once)')
    finally:
        tmp.unlink()
    print(json.dumps(dict(written=str(out), sha256=c.sha256_file(out))))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('pins')
    p.add_argument('--c7d2', required=True, help='LRI_C7_D2_HPC/reference')
    p.add_argument('--c7d3-inventory', required=True, help="C7(3)'s inputs/inventory.json (c8-base)")
    p.add_argument('--write-dir', default=str(PINS))
    p.add_argument('--check', action='store_true')
    g = sub.add_parser('gate1a')
    g.add_argument('--d2', required=True, help='the frozen d=2 copy (holds LRI_C7_d2_progress/ and power_mass/)')
    g.add_argument('--bin', required=True, help='regenerate_rates')
    g.add_argument('--work', required=True)
    g.add_argument('--evidence', required=True)
    g.add_argument('--threads', type=int, default=int(os.environ.get('SLURM_CPUS_PER_TASK') or os.cpu_count() or 1))
    g.add_argument('--loops', help='comma-separated subset of 2..7 (a Mac-side subset check; the gate needs all)')
    g.add_argument('--keep-work', action='store_true')
    sg = sub.add_parser('summary-gen-d3-0')
    sg.add_argument('--evidence', required=True, help="J-GEN-D3-0's evidence directory (gate1a.json, test_gen3_sanitize.json)")
    sg.add_argument('--rehearsal', action='store_true', help='an explicit off-Expanse dry run: exit 0 when every check passed')
    h = sub.add_parser('h1-copy')
    h.add_argument('--source', required=True)
    h.add_argument('--store', required=True, help='$C8_STORE/h1')
    h.add_argument('--pin', required=True, help="H1's MANIFEST sha256")
    h.add_argument('--evidence', required=True)
    ha = sub.add_parser('h1-auth')
    ha.add_argument('--tree', required=True, help='the H1 copy')
    ha.add_argument('--pin', required=True, help="H1's MANIFEST sha256 (the external pin)")
    ha.add_argument('--snapshot', required=True, help='the src/gen snapshot to make (or, with --check, to re-check)')
    ha.add_argument('--check', action='store_true')
    ha.add_argument('--evidence', required=True)
    ha.add_argument('--name', default='h1_code_auth')
    u = sub.add_parser('source-unchanged')
    u.add_argument('--source', required=True)
    u.add_argument('--before', required=True, help='h1_source_listing_before.json of the intake')
    u.add_argument('--evidence', required=True)
    u.add_argument('--name', default='h1_source_after')
    sa = sub.add_parser('split-audit')
    sa.add_argument('--audit', required=True)
    sa.add_argument('--stage', required=True)
    sa.add_argument('--out', required=True)
    b = sub.add_parser('gate1b')
    b.add_argument('--h1', required=True, help='H1 d=2 G-files extracted: L7_free/, L7_power/')
    b.add_argument('--d3', required=True, help='the d=3 stage')
    b.add_argument('--d2', required=True, help='the frozen C7(2) d=2 copy')
    b.add_argument('--evidence', required=True)
    g2 = sub.add_parser('gate2')
    for k in ('--d3', '--inventory', '--sizes', '--classes', '--evidence'):
        g2.add_argument(k, required=True)
    g3 = sub.add_parser('gate3')
    for k in ('--bin', '--d3', '--classes', '--evidence'):
        g3.add_argument(k, required=True)
    g4 = sub.add_parser('gate4')
    for k in ('--d3', '--inventory', '--evidence'):
        g4.add_argument(k, required=True)
    g5 = sub.add_parser('gate5')
    for k in ('--inventory', '--h1gen', '--regen', '--side', '--classes', '--evidence'):
        g5.add_argument(k, required=True)
    g5.add_argument('--probe')
    g5.add_argument('--fixture', action='store_true', help=argparse.SUPPRESS)   # test fixtures: no fixed MEMBERS sha256
    g7 = sub.add_parser('gate7')
    for k in ('--audits', '--h1', '--d3', '--evidence'):
        g7.add_argument(k, required=True)
    for k in ('--two-loop', '--two-loop-order7', '--historical', '--gamma'):
        g7.add_argument(k)
    dt = sub.add_parser('determinism')
    for k in ('--a', '--b', '--evidence'):
        dt.add_argument(k, required=True)
    dt.add_argument('--threads', default='1 and N')
    rp = sub.add_parser('report')
    rp.add_argument('--evidence', required=True, help="J-GEN-D3's evidence directory")
    rp.add_argument('--gate1a', required=True, help="J-GEN-D3-0's gate1a.json")
    rp.add_argument('--h1-pin', required=True)
    rp.add_argument('--commit', required=True)
    rp.add_argument('--output', required=True, help='LRI_C8_shared/assembly/H1_gates/inventory8_d2_<sha12>_C63d_gates.json')
    g6 = sub.add_parser('gate6')
    g6.add_argument('--inputs', help='the package inputs/ (default)')
    g6.add_argument('--evidence', required=True)
    ad = sub.add_parser('addendum')
    for k in ('--gate6', '--gate-record', '--inputs-manifest', '--commit'):
        ad.add_argument(k, required=True)
    ad.add_argument('--output', required=True,
                    help='LRI_C8_shared/assembly/H1_gates/inventory8_d2_<sha12>_C63d_gates_addendum_gate6.json')
    hg = sub.add_parser('handoff-gate6')
    hg.add_argument('--handoff', required=True, help='LRI_C8_shared/inventory/HANDOFF_inventory8_d2.json')
    da = sub.add_parser('decisions-ack')
    da.add_argument('--decisions', required=True, help='LRI_C8_shared/inventory/DECISIONS.md')
    da.add_argument('--handoff', required=True, help='LRI_C8_shared/inventory/HANDOFF_inventory8_d2.json (read only)')
    da.add_argument('--date', default=time.strftime('%Y-%m-%d'))
    nt = sub.add_parser('note')
    nt.add_argument('--handoff', required=True, help='LRI_C8_shared/inventory/HANDOFF_inventory8_d2.json (read only)')
    nt.add_argument('--decisions', required=True, help='LRI_C8_shared/inventory/DECISIONS.md (read only)')
    nt.add_argument('--payload-path', required=True, help='where the published d=3 payload lives (text for the NOTE)')
    nt.add_argument('--h1-copy', help="J-H1-COPY's h1_copy.json")
    nt.add_argument('--output', required=True, help='LRI_C8_shared/assembly/NOTE_C63d_to_C62d_<date>.md')
    for p in (hg, da, nt):
        p.add_argument('--gate-record', required=True, help='the A.5 gate record')
        p.add_argument('--addendum', required=True, help="the gate-6 addendum")
        p.add_argument('--dry-run', action='store_true', help='print what would be written; write nothing')
    for p in (hg, da):
        p.add_argument('--evidence', required=True, help='a directory for the record (and, for the HANDOFF, its old bytes)')
    a = ap.parse_args(argv)
    try:
        return {'pins': cmd_pins, 'gate1a': cmd_gate1a, 'summary-gen-d3-0': cmd_summary_gen_d3_0, 'h1-copy': cmd_h1_copy, 'h1-auth': cmd_h1_auth,
                'source-unchanged': cmd_source_unchanged,
                'split-audit': cmd_split_audit, 'gate1b': cmd_gate1b, 'gate2': cmd_gate2, 'gate3': cmd_gate3,
                'gate4': cmd_gate4, 'gate5': cmd_gate5, 'gate7': cmd_gate7, 'determinism': cmd_determinism,
                'report': cmd_report, 'gate6': cmd_gate6, 'addendum': cmd_addendum,
                'handoff-gate6': cmd_handoff_gate6, 'decisions-ack': cmd_decisions_ack, 'note': cmd_note}[a.cmd](a)
    except c.Gen3Error as e:
        c.die(str(e))


if __name__ == '__main__':
    sys.exit(main())
