#!/usr/bin/env python3
"""A-INV-2's comparison logic (gen/regress.py) without the builders: pure logic, seconds, any platform.

Checkpoint review CK-K02: the free L <= 6 relabelling exception accepted a G-file whose header weights (or rate-table
size) differed, because it compared only the masks and terms; the rate-only rule accepted a rate table of another
size; and no check compared a G-file header with its own inventory.json row. On the frozen payloads
(reference/LRI_C7_d2_progress/inputs, reference/power_mass/inputs) and edited copies of them this test checks:
  * judge(): identical files; legacy rate values (free L <= 6) accepted as rate-only, a trailing-space-only rate line
    counted as such; refused as 'other': a changed weight (wa or wb) with or without a rate change, a changed id, a
    truncated or extended rate table, a changed 2^E line, a reordering under the identity permutation or under a
    recorded automorphism, a recorded permutation that only reorders the terms, a mask value not explained by any
    permutation, a relabelling by a permutation that is not the recorded one, a rate change in power L3 or free L7,
    malformed files; a relabelling by the recorded permutation (either direction; free L4 G2) with or without legacy
    rate values accepted as 'relabelled' with its proof, and refused again once its weights, id, rate-table size or
    2^E line also change;
  * header_inventory_mismatches(): the frozen trees agree; a changed weight, mask count or id, a G-file without a row
    and a row naming a missing file are reported;
  * end to end: gen/regress.py --loops 3 with fake builders that copy the frozen L3 trees passes, and fails when the
    "built" free L3 G1.txt has only its weight wa changed (the reviewer's example: G1 has an identity permutation in
    legacy_mapping.json, and the 601b102 rule accepted it) or a rate table one entry short;
  * Stage-6 fix round 3, Z5 (S6R3-B-01): gen/gates.py check_gfile refuses a negated first mask (and parse_gfile does),
    mask tokens that are not plain decimals ('0_7', which int() reads as 7 and the native loader does not; '+7'), and a
    term coefficient outside the loader's int or written with '_'; the well-formed file passes (gfile_gate_checks);
  * Stage-6 fix round 4, W4 (S6R4-B-01): check_gfile and regress.parse_gfile refuse a no-break space (U+00A0) or a
    U+001C between two masks (str.split() split there, the loader's stream does not), a tab, CRLF line ends, a CR
    before the last line end, and a header and inventory row of M = T = 0 (load_graph needs M >= 1 and T >= 1);
    judge() no longer accepts as 'relabelled' or 'rate_only' a file with a no-break space or a rate that is no plain
    decimal (the same lenient split);
  * Stage-6 fix round 4, W5 (S6R4-B-02): judge() on bytes calls only equal bytes 'identical'; CRLF line ends, a single
    CR and a CRLF file with legacy rate values are 'other' (structure). End to end, gen/regress.py --loops 3 fails
    when the built power L3 G7.txt or free L3 G1.txt has a CRLF line end (read_text() made both identical before);
  * Stage-6 finding S6-B-02: the --loops 3 run records partial coverage; gen/regress.py refuses an empty, reversed,
    repeated or out-of-range --loops and an empty, nonpositive or repeated --threads before building anything
    (loops_arg, threads_arg); h1_problems() accepts a complete synthetic record and the real J-GEN-1 record of the
    CK-K02 fix, and refuses partial evidence: loops [3], no loop, one thread count, no serial run, a missing sector, a
    thread-identity difference, a failed build, a non-identical free L7, no header-row check (the Stage-1 record),
    a false control, listed failures, passed false, another gate name.
Usage: python3 -B gen/test_regress.py [--output FILE]"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

GEN = Path(__file__).resolve().parent
ROOT = GEN.parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, GEN / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


R = load('regress')
LEGACY = {int(r['L']): r['maps'] for r in json.loads(R.LEGACY.read_text())}


def frozen(sector: str, L: int, gid: int) -> str:
    return (R.FROZEN[sector] / f'L{L}' / f'G{gid}.txt').read_text()


def lines_of(text: str) -> list[str]:
    return text.split('\n')[:-1]


def join(lines: list[str]) -> str:
    return '\n'.join(lines) + '\n'


def set_header(text: str, field: int, value: str) -> str:
    ls = lines_of(text)
    h = ls[0].split()
    h[field] = value
    ls[0] = ' '.join(h)
    return join(ls)


def edit_rates(text: str, fn) -> str:
    """The rate line rewritten as fn(tokens) (legacy rate values), in the frozen layout (trailing space)."""
    ls = lines_of(text)
    ls[-1] = ' '.join(fn(ls[-1].split())) + ' '
    return join(ls)


def relabel(text: str, q: list[int]) -> str:
    """The G-file with edge e renamed q[e]: masks mapped and sorted, term mask indices remapped (sorted), the
    coefficient vectors and the rate table (indexed by edge subsets) permuted; header and 2^E line unchanged."""
    ls = lines_of(text)
    h = ls[0].split()
    L, T = int(h[1]), int(h[6])
    E = 2 * L

    def qm(m: int) -> int:
        return sum(1 << q[e] for e in range(E) if m >> e & 1)

    masks = [int(x) for x in ls[1].split()]
    mapped = sorted(qm(m) for m in masks)
    where = {m: i for i, m in enumerate(mapped)}
    terms = []
    for line in ls[2:2 + T]:
        t = [int(x) for x in line.split()]
        k = t[0]
        ids = sorted(where[qm(masks[i])] for i in t[1:1 + k])
        co = [0] * E
        for e, c in enumerate(t[1 + k:]):
            co[q[e]] = c
        terms.append(' '.join(map(str, [k] + ids + co)))
    rates = ls[3 + T].split()
    new_rates = [''] * len(rates)
    for s, r in enumerate(rates):
        new_rates[qm(s)] = r
    return join([ls[0], ' '.join(map(str, mapped)) + ' '] + terms + [ls[2 + T], ' '.join(new_rates) + ' '])


def inverse(p: list[int]) -> list[int]:
    out = [0] * len(p)
    for i, j in enumerate(p):
        out[j] = i
    return out


def recorded(L: int, gid: int) -> list[int]:
    return next(m['edge_permutation'] for m in LEGACY[L] if m['new'] == gid)


FAKE_BUILDER = r'''#!{python}
# A fake gen/build_{{free,power}} for gen/test_regress.py: copies the frozen L<L> tree to OUT, writes a side file equal
# for both sectors, and applies the text edits of $FAKE_REGRESS_EDITS ([[sector, L, file, old, new], ...]).
import json, os, shutil, sys
from pathlib import Path
sector = Path(sys.argv[0]).name.split('_', 1)[1]
L = int(Path(sys.argv[1]).name[len('classes'):-len('.txt')])
out, side = Path(sys.argv[2]), Path(sys.argv[3])
src = Path(json.loads({frozen_json!r})[sector]) / f'L{{L}}'
shutil.copytree(src, out)
side.write_text(f'side file L{{L}}\n')
if os.environ.get('FAKE_REGRESS_ENVLOG'):  # the OpenMP environment this builder got (outside the compared trees)
    with open(os.environ['FAKE_REGRESS_ENVLOG'], 'a') as f:
        f.write(json.dumps(dict(sector=sector, L=L, env={{k: v for k, v in os.environ.items()
                                                          if k.startswith(('OMP_', 'GOMP_', 'KMP_'))}})) + '\n')
for s, l, f, old, new in json.loads(os.environ.get('FAKE_REGRESS_EDITS', '[]')):
    if s == sector and l == L:
        p = out / f
        t = p.read_text()
        assert old in t, (f, old)
        p.write_text(t.replace(old, new, 1))
'''


def synthetic_h1_record() -> dict:
    """A complete A-INV-2 record in the layout gen/regress.py writes (loops 3..7, threads 1 and 8, both sectors, two
    G-files per loop; at free L <= 6 one of them rate-only), for h1_problems() and gen/test_handoff_inventory.py."""
    loops, threads, sectors = [3, 4, 5, 6, 7], [1, 8], ('free', 'power')
    rows = {}
    for s in sectors:
        for L in loops:
            legacy = s == 'free' and L <= 6
            rows[f'{s}_L{L}'] = dict(frozen_gfiles=2, new_gfiles=2, same_file_set=True, identical=1 if legacy else 2,
                                     rate_only=1 if legacy else 0, rate_whitespace_only=0,
                                     rate_entries_differing=3 if legacy else 0, other=[], accepted_relabelling=[],
                                     header_inventory_mismatches={'new': [], 'frozen': []}, inventory_equal=True,
                                     inventory_differences=[], inventory_bytes_identical=True)
    controls = {f'side_files_free_eq_power_L{L}': True for L in loops}
    controls['side_file_L7_eq_c8d1_L7_inventory'] = True
    return dict(schema='c8-d2-gate-1', gate='A-INV-2 regress', classes='reference/LRI_C7_d2_progress/reference',
                threads=threads, loops=loops, work='/tmp/w',
                builds=[dict(threads=th, sector=s, L=L, rc=0, seconds=0.1, stderr_tail='') for th in threads
                        for s in sectors for L in loops],
                sectors=rows, threads_identical={'1_vs_8': dict(identical=True, differences=[])}, controls=controls,
                passed=True, failures=[], free_L3_L6_rate_line_files=4, free_L3_L6_rate_whitespace_only_files=0)


def run_regress(td: Path, tag: str, edits: list, extra_env: dict | None = None) -> tuple[int, dict]:
    fb = td / f'bin_{tag}'
    fb.mkdir()
    frozen_json = json.dumps({k: str(v) for k, v in R.FROZEN.items()})
    for sector in ('free', 'power'):
        b = fb / f'build_{sector}'
        b.write_text(FAKE_BUILDER.format(python=sys.executable, frozen_json=frozen_json))
        b.chmod(0o755)
    out = td / f'regress_{tag}.json'
    env = {**os.environ, 'FAKE_REGRESS_EDITS': json.dumps(edits), 'PYTHONDONTWRITEBYTECODE': '1', **(extra_env or {})}
    r = subprocess.run([sys.executable, '-B', str(GEN / 'regress.py'), '--classes', str(ROOT / 'reference/LRI_C7_d2_progress/reference'),
                        '--threads', '1,2', '--loops', '3', '--explain', '--bin', str(fb), '--work', str(td / f'work_{tag}'),
                        '--output', str(out)], capture_output=True, text=True, env=env)
    return r.returncode, (json.loads(out.read_text()) if out.exists() else {'stdout': r.stdout[-2000:], 'stderr': r.stderr[-2000:]})


def kirchhoff_checks(check) -> None:
    """W4's class (Stage-6 fix round 4, integration; G2's note): gen/kirchhoff.py (A-INV-3(h)) read the stored kernel
    with read_text().split() and int(), so a no-break space (U+00A0) or U+001C between mask integers, a '+7' or '0_7'
    token and M = T = 0 passed its parse although the native loader refuses them. It now reads through
    regress.gfile_text and parse_gfile: on the frozen free L3 G1 the stored kernel at a rational point is the value of
    the old reader (unchanged arithmetic); each malformed copy is refused (ValueError), and check() records it as that
    kernel's failure (exact_match false, error) instead of comparing a value the loader would never compute."""
    import math
    from fractions import Fraction as Fr
    K = load('kirchhoff')
    text = frozen('free', 3, 1)
    gdir = Path(tempfile.mkdtemp(prefix='c8d2_kirchhoff_'))
    x = [Fr(3 + j, 7 + 2 * j) for j in range(6)]

    def old(t: str):  # the reader before the fix (kirchhoff.py at 2d4b27e)
        it = iter(t.split()); hdr = [next(it) for _ in range(7)]; M, T = int(hdr[-2]), int(hdr[-1])
        masks = [int(next(it)) for _ in range(M)]; mons = [math.prod(x[j] for j in range(6) if m >> j & 1) for m in masks]; v = Fr(0)
        for _ in range(T):
            k = int(next(it)); den = sum(mons[int(next(it))] for _ in range(k)); co = [int(next(it)) for _ in x]; v += sum(a * b for a, b in zip(co, x)) / den
        return v / sum(x)

    def put(t: str) -> dict:
        (gdir / 'G1.txt').write_bytes(t.encode('utf-8')); return {'file': 'G1.txt', 'id': 1}
    check('kirchhoff.stored reads the frozen free L3 G1 as before (the same Fraction)', K.stored(put(text), x, gdir) == old(text), None)
    ls = lines_of(text); masks = ls[1].split()
    bad = {'U+00A0 between masks': join([ls[0], masks[0] + '\u00a0' + ' '.join(masks[1:])] + ls[2:]),
           'U+001C between masks': join([ls[0], masks[0] + '\x1c' + ' '.join(masks[1:])] + ls[2:]),
           "'+' on a mask": join([ls[0], '+' + ls[1]] + ls[2:]),
           "'_' in a mask": join([ls[0], masks[0][:1] + '_' + masks[0][1:] + ' ' + ' '.join(masks[1:])] + ls[2:]),
           'M = T = 0': join([' '.join(ls[0].split()[:5] + ['0', '0']), '', ls[-2], ls[-1]])}
    for name, t in bad.items():
        try:
            old_ok = old(t) is not None
        except (ValueError, StopIteration, IndexError):
            old_ok = False
        try:
            K.stored(put(t), x, gdir); got = 'accepted'
        except ValueError as e:
            got = f'refused: {e}'
        check(f'kirchhoff.stored refuses a G-file the loader refuses: {name}', got.startswith('refused'), {'new': got, 'old_reader_accepted': old_ok})
    real = K.independent
    try:
        K.independent = lambda e, pt: (Fr(0), 0)
        put(bad['U+00A0 between masks'])
        r = K.check({'g': {'file': 'G1.txt', 'id': 1, 'edges': [], 'masks': 16, 'terms': 1}, 'points': [x, x], 'gdir': str(gdir), 'L': 3, 'sector': 'free'})
        check('kirchhoff.check records a malformed G-file as the kernel\'s failure', r['exact_match'] is False and all('malformed G-file' in c.get('error', '') for c in r['checks']), r)
    finally:
        K.independent = real


def gfile_gate_checks(check) -> None:
    """Z5 (S6R3-B-01, Stage-6 fix round 3): gen/gates.py check_gfile (gate A-INV-3(j)) accepts a G-file only as the
    native loader reads it and as regress.parse_gfile parses it. From the frozen free L3 G1 with a C8 rate table (s = 0
    and 2^E - 1 zero, every other entry 1, at or above each parity floor): the file passes both; negating its first mask
    (bin(-m) keeps m's popcount and the order stays ascending; the loader reads an unsigned, a huge value: 'nonhomogeneous
    mask') is refused by both; a mask token int() reads as another value than the loader ('0_7': int() 7, the loader 0
    and then a failed stream) or that is not the builders' plain decimal ('+7'), a term coefficient outside the loader's
    int and a term token with '_' are refused by check_gfile."""
    G = load('gates')
    base = lines_of(frozen('free', 3, 1))
    head = base[0].split()
    L, M, T = int(head[1]), int(head[5]), int(head[6])
    E = 2 * L
    base[-1] = ' '.join(['0'] + ['1'] * ((1 << E) - 2) + ['0'])

    def gate(ls: list[str], tag: str) -> dict:
        f = Path(tempfile.mkdtemp(prefix='c8d2_gfile_')) / f'G1_{tag}.txt'
        f.write_text(join(ls))
        try:
            return G.check_gfile((str(f), L, int(head[2]), M, T, head[3], head[4]))
        finally:
            shutil.rmtree(f.parent, ignore_errors=True)

    def parses(ls: list[str]) -> bool:
        try:
            R.parse_gfile(join(ls))
            return True
        except ValueError:
            return False

    r = gate(base, 'valid')
    check('Z5: check_gfile accepts a well-formed G-file (frozen free L3 G1, C8 rate table)', r.get('ok') is True and parses(base), r)
    masks = base[1].split()
    first = int(masks[0])
    edits = {'the first mask negated (-m)': (1, [str(-first)] + masks[1:]),
             "the first mask as int()'s '0_m' (an underscore)": (1, [f'0_{first}'] + masks[1:]),
             "the first mask as '+m'": (1, [f'+{first}'] + masks[1:])}
    for name, (row, toks) in edits.items():
        ls = list(base)
        ls[row] = ' '.join(toks)
        r = gate(ls, 'mask')
        check(f'Z5: check_gfile refuses {name}', r.get('ok') is False and 'mask line' in str(r.get('error')), r)
    ls = list(base)
    ls[1] = ' '.join([str(-first)] + masks[1:])
    check('Z5: regress.parse_gfile refuses the negated first mask too (the parser check_gfile now matches)', not parses(ls))
    t = base[2].split()
    k = int(t[0])
    for name, val in (('a term coefficient of 2^31 (outside the loader\'s int)', str(2 ** 31)),
                      ('a term coefficient written 1_0', '1_0')):
        ls = list(base)
        co = t[1 + k:]
        co[0] = val
        ls[2] = ' '.join(t[:1 + k] + co)
        r = gate(ls, 'term')
        check(f'Z5: check_gfile refuses {name}', r.get('ok') is False and 'term line' in str(r.get('error')), r)
    # ---- W4 (S6R4-B-01, Stage-6 fix round 4): bytes the loader refuses, which str.split() or read_text() hid
    def gate_bytes(data: bytes, tag: str, M_: int = M, T_: int = T) -> dict:
        f = Path(tempfile.mkdtemp(prefix='c8d2_gfile_')) / f'G1_{tag}.txt'
        f.write_bytes(data)
        try:
            return G.check_gfile((str(f), L, int(head[2]), M_, T_, head[3], head[4]))
        finally:
            shutil.rmtree(f.parent, ignore_errors=True)

    def parses_text(text: str) -> bool:
        try:
            R.parse_gfile(text)
            return True
        except ValueError:
            return False

    valid = join(base).encode()
    r = gate_bytes(valid, 'w4_valid')
    check('W4: check_gfile accepts the well-formed bytes', r.get('ok') is True, r)

    def mask_sep(sep: str) -> bytes:
        ls_ = list(base)
        ls_[1] = ls_[1].replace(' ', sep, 1)
        return join(ls_).encode('utf-8')
    w4 = {'a no-break space (U+00A0) between two masks': mask_sep('\u00a0'),
          'a U+001C (str.split() splits there, the loader does not) between two masks': mask_sep('\x1c'),
          'a tab between two masks': mask_sep('\t'),
          'CRLF line ends': valid.replace(b'\n', b'\r\n'),
          'a CR before the last line end': valid[:-1] + b'\r\n'}
    for name, data in w4.items():
        r = gate_bytes(data, 'w4')
        check(f'W4: check_gfile refuses {name}', r.get('ok') is False and 'byte 0x' in str(r.get('error')), r)
        check(f'W4: regress.parse_gfile refuses {name} (decoded without newline translation)',
              not parses_text(data.decode('utf-8')))
    zero = join([f'C7D2GRAPH1 {L} {head[2]} {head[3]} {head[4]} 0 0', '', str(1 << E), base[-1]]).encode()
    r = gate_bytes(zero, 'w4_zero', 0, 0)
    check('W4: check_gfile refuses a header and inventory row of M = T = 0 (load_graph needs M >= 1 and T >= 1)',
          r.get('ok') is False and 'outside the native loader' in str(r.get('error')), r)
    check('W4: regress.parse_gfile refuses M = T = 0 too', not parses_text(zero.decode()))
    check('W4: regress.parse_gfile accepts the well-formed file', parses_text(valid.decode()))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    results, failed = [], []

    def check(name: str, ok: bool, detail='') -> None:
        detail = detail if isinstance(detail, str) else json.dumps(detail, default=str)
        results.append(dict(check=name, passed=bool(ok), detail=detail[-1500:]))
        if not ok:
            failed.append(name)
        print(('PASS ' if ok else 'FAIL ') + name + (f': {detail[-600:]}' if detail and not ok else ''), flush=True)

    def h1(record: dict) -> list[str]:
        fn = getattr(R, 'h1_problems', None)
        if fn is None:  # before the S6-B-02 fix
            return ['no h1_problems in gen/regress.py']
        try:
            return fn(record)
        except Exception as e:  # noqa: BLE001  (must report, never raise)
            return [f'raised {type(e).__name__}: {e}']

    def verdict(name: str, sector: str, L: int, gid: int, new: str, old: str, want: str, needle: str | None = None):
        try:
            got, info = R.judge(sector, L, f'G{gid}.txt', new, old, LEGACY)
        except Exception as e:  # judge must classify, never raise
            got, info = f'raised {type(e).__name__}: {e}', {}
        ok = got == want and (needle is None or needle in json.dumps(info))
        check(name, ok, dict(verdict=got, info=info, want=want, needle=needle))
        return info

    # ---- judge(): rate-only and identical
    g1 = frozen('free', 3, 1)
    assert recorded(3, 1) == list(range(6)), 'free L3 G1 has the identity permutation in legacy_mapping.json'
    verdict('identical files', 'free', 3, 1, g1, g1, 'identical')
    one_rate = edit_rates(g1, lambda t: ['0.5'] + t[1:])
    info = verdict('free L3: legacy rate values are rate-only', 'free', 3, 1, one_rate, g1, 'rate_only')
    check('free L3: rate-only counts the differing entries', info.get('rate_entries_differing') == 1, info)
    ls = lines_of(g1)
    no_space = join(ls[:-1] + [ls[-1].rstrip(' ')])
    info = verdict('free L3: a rate line differing only in its trailing space is rate-only', 'free', 3, 1, no_space, g1, 'rate_only')
    check('free L3: ... and counted as whitespace-only', info.get('whitespace_only') is True, info)
    # ---- CK-K02: weights, ids, rate-table size, 2^E line
    verdict('CK-K02: only wa changed (identity permutation) is refused', 'free', 3, 1, set_header(g1, 3, '2'), g1, 'other', 'header weights')
    verdict('CK-K02: only wb changed is refused', 'free', 3, 1, set_header(g1, 4, '0.5'), g1, 'other', 'header weights')
    verdict('CK-K02: wa changed below binary64 resolution is refused (exact header text)', 'free', 3, 1,
            set_header(g1, 3, '1.0000000000000000001'), g1, 'other', 'header weights')
    verdict('CK-K02: wa and a rate value changed is refused', 'free', 3, 1, set_header(one_rate, 3, '2'), g1, 'other', 'header weights')
    verdict('CK-K02: a rate table one entry short is refused', 'free', 3, 1, edit_rates(g1, lambda t: t[:-1]), g1, 'other', 'rate table of 63')
    verdict('CK-K02: a rate table one entry long is refused', 'free', 3, 1, edit_rates(g1, lambda t: t + ['1']), g1, 'other', 'rate table of 65')
    ls = lines_of(g1)
    verdict('a changed 2^E line is refused', 'free', 3, 1, join(ls[:-2] + ['65', ls[-1]]), g1, 'other', 'structure')
    verdict('a changed id is refused', 'free', 3, 1, set_header(g1, 2, '7'), g1, 'other', 'header counts or ids')
    # masks reordered with the terms remapped: the same graph, but an identity permutation explains no difference
    ls = lines_of(g1)
    masks = ls[1].split()
    swapped = join([ls[0], ' '.join([masks[1], masks[0]] + masks[2:]) + ' ']
                   + [' '.join(str({0: 1, 1: 0}.get(int(x), int(x)) if 1 <= j <= int(line.split()[0]) else x)
                               for j, x in enumerate(line.split())) for line in ls[2:-2]] + ls[-2:])
    verdict('a mask reordering under the recorded identity permutation is refused', 'free', 3, 1, swapped, g1, 'other', 'mask order')
    # ---- relabelling. Most recorded permutations are automorphisms of their graph (exchanges of parallel edges, every
    # one at L3); free L4 G2's is not, so relabelling by it changes masks and terms
    g0 = frozen('free', 3, 0)
    perm0 = recorded(3, 0)
    assert perm0 != list(range(6)) and R.canonical(g0, perm0) == R.canonical(g0, None), 'free L3 G0: an automorphism'
    ls = lines_of(g0)
    masks = ls[1].split()
    swapped0 = join([ls[0], ' '.join([masks[1], masks[0]] + masks[2:]) + ' ']
                    + [' '.join(str({0: 1, 1: 0}.get(int(x), int(x)) if 1 <= j <= int(line.split()[0]) else x)
                                for j, x in enumerate(line.split())) for line in ls[2:-2]] + ls[-2:])
    verdict('a mask reordering under a recorded automorphism (free L3 G0) is refused', 'free', 3, 0, swapped0, g0, 'other', 'mask order')
    g2 = frozen('free', 4, 2)
    perm = recorded(4, 2)
    assert R.canonical(g2, perm) != R.canonical(g2, None), 'free L4 G2: not an automorphism'
    legacy_rates = lambda t: [('0.3' if x != '0.3' else '0.4') for x in t]  # noqa: E731  every value changed
    for name, q in (('the inverse of the recorded permutation', inverse(perm)), ('the recorded permutation', perm)):
        rel = edit_rates(relabel(g2, q), legacy_rates)
        verdict(f'a relabelling by {name} with legacy rates is accepted (free L4 G2)', 'free', 4, 2, rel, g2,
                'relabelled', 'edge_permutation')
    rel = edit_rates(relabel(g2, inverse(perm)), legacy_rates)
    check('the relabelled control really differs in masks and terms', {'mask values', 'term values'} <= set(R.classify(rel, g2)),
          R.classify(rel, g2))
    verdict('the relabelling with the rate values kept is accepted too', 'free', 4, 2, relabel(g2, inverse(perm)), g2, 'relabelled')
    verdict('CK-K02: relabelled with wa changed is refused', 'free', 4, 2, set_header(rel, 3, '1'), g2, 'other', 'header weights')
    verdict('CK-K02: relabelled with wb changed is refused', 'free', 4, 2, set_header(rel, 4, '0.25'), g2, 'other', 'header weights')
    verdict('CK-K02: relabelled with the id changed is refused', 'free', 4, 2, set_header(rel, 2, '5'), g2, 'other', 'header counts or ids')
    verdict('CK-K02: relabelled with a rate table one entry short is refused', 'free', 4, 2, edit_rates(rel, lambda t: t[:-1]), g2,
            'other', 'structure')
    ls = lines_of(rel)
    verdict('relabelled with a changed 2^E line is refused', 'free', 4, 2, join(ls[:-2] + ['512', ls[-1]]), g2, 'other', 'structure')
    other_perm = [1, 0] + list(range(2, 8))
    assert R.canonical(relabel(g2, other_perm), perm) != R.canonical(g2, None)
    assert R.canonical(relabel(g2, other_perm), inverse(perm)) != R.canonical(g2, None)
    verdict('a relabelling by a permutation that is not the recorded one is refused', 'free', 4, 2,
            edit_rates(relabel(g2, other_perm), legacy_rates), g2, 'other')
    g23 = frozen('free', 4, 23)
    q23 = recorded(4, 23)
    only_order = relabel(g23, inverse(q23))
    assert R.classify(only_order, g23) == ['term order'], R.classify(only_order, g23)
    verdict('a recorded permutation that only reorders the terms (free L4 G23) proves no relabelling', 'free', 4, 23,
            only_order, g23, 'other', 'term order')
    ls = lines_of(g0)
    m = ls[1].split()
    m[0] = '7'  # 0b000111: three edges, a valid mask that G0 does not have
    verdict('a mask value no permutation explains is refused', 'free', 3, 0, join([ls[0], ' '.join(m) + ' '] + ls[2:]), g0, 'other', 'mask values')
    # ---- sectors and loops outside the legacy rule
    p7 = frozen('power', 3, 7)
    verdict('power L3: a rate change is refused', 'power', 3, 7, edit_rates(p7, lambda t: ['0.5'] + t[1:]), p7, 'other', 'rate line')
    f7name = sorted((R.FROZEN['free'] / 'L7').glob('G*.txt'), key=lambda p: int(p.name[1:-4]))[0]
    f7 = f7name.read_text()
    verdict('free L7: a rate change is refused (parity rule)', 'free', 7, int(f7name.name[1:-4]), edit_rates(f7, lambda t: ['0.5'] + t[1:]),
            f7, 'other', 'rate line')
    verdict('a malformed file is classified, not raised', 'free', 3, 1, 'C7D2GRAPH1 3 1\n', g1, 'other', 'structure')
    verdict('a file without its final newline is refused', 'free', 3, 1, g1[:-1], g1, 'other', 'structure')
    # ---- W5 (S6R4-B-02, Stage-6 fix round 4): judge() on bytes; 'identical' only for equal bytes
    def bverdict(name: str, sector: str, L: int, gid: int, new: bytes, old: bytes, want: str, needle: str | None = None):
        try:
            got, info = R.judge(sector, L, f'G{gid}.txt', new, old, LEGACY)
        except Exception as e:  # judge must classify, never raise
            got, info = f'raised {type(e).__name__}: {e}', {}
        check(name, got == want and (needle is None or needle in json.dumps(info)), dict(verdict=got, info=info, want=want))
    p7b = (R.FROZEN['power'] / 'L3/G7.txt').read_bytes()
    g1b = (R.FROZEN['free'] / 'L3/G1.txt').read_bytes()
    f7b = f7name.read_bytes()
    bverdict('W5: equal bytes are identical', 'power', 3, 7, p7b, p7b, 'identical')
    bverdict('W5: power L3 G7 with CRLF line ends is not identical (structure)', 'power', 3, 7, p7b.replace(b'\n', b'\r\n'), p7b,
             'other', 'byte 0x0d')
    bverdict('W5: power L3 G7 with one CR before its last line end is not identical', 'power', 3, 7, p7b[:-1] + b'\r\n', p7b,
             'other', 'byte 0x0d')
    bverdict('W5: free L3 G1 with CRLF line ends and legacy rate values is not rate-only', 'free', 3, 1,
             one_rate.encode().replace(b'\n', b'\r\n'), g1b, 'other', 'byte 0x0d')
    bverdict('W5: free L3 G1 with legacy rate values (bytes) is still rate-only', 'free', 3, 1, one_rate.encode(), g1b, 'rate_only')
    bverdict('W5: free L7 with CRLF line ends is not identical (byte identity required)', 'free', 7, int(f7name.name[1:-4]),
             f7b.replace(b'\n', b'\r\n'), f7b, 'other', 'byte 0x0d')
    # W4's class in judge(): the lenient split accepted these as a relabelling or as legacy rates
    rel_nb = relabel(g2, inverse(perm))
    rl = lines_of(rel_nb)
    rl[1] = rl[1].replace(' ', '\u00a0', 1)
    verdict('W4: a relabelling with a no-break space in its mask line is refused (free L4 G2)', 'free', 4, 2, join(rl), g2, 'other',
            'structure')
    verdict('W4: legacy rates with a rate that is no plain decimal are refused (free L3 G1)', 'free', 3, 1,
            edit_rates(g1, lambda t: ['x'] + t[1:]), g1, 'other', 'structure')
    verdict('W4: legacy rates with a no-break space in the rate line are refused (free L3 G1)', 'free', 3, 1,
            join(lines_of(g1)[:-1] + [lines_of(g1)[-1].replace(' ', '\u00a0', 1)]), g1, 'other', 'structure')
    # ---- header_inventory_mismatches()
    bad_frozen = {f'{s} L{L}': R.header_inventory_mismatches(R.FROZEN[s], L)[:3] for s in ('free', 'power') for L in range(3, 8)}
    check('the frozen trees: every G-file header agrees with its inventory row', not any(bad_frozen.values()), bad_frozen)
    with tempfile.TemporaryDirectory(prefix='c8d2_test_regress_') as tds:
        td = Path(tds)

        def tree(tag: str) -> Path:
            t = td / tag
            shutil.copytree(R.FROZEN['free'] / 'L3', t / 'L3')
            return t

        t = tree('clean')
        check('a clean copy agrees', R.header_inventory_mismatches(t, 3) == [], R.header_inventory_mismatches(t, 3))
        for tag, field, value, needle in (('wa', 3, '2', "'wa'"), ('wb', 4, '0.5', "'wb'"), ('masks', 5, '17', "'masks'"), ('id', 2, '7', 'id')):
            t = tree(tag)
            (t / 'L3/G1.txt').write_text(set_header(g1, field, value))
            got = R.header_inventory_mismatches(t, 3)
            check(f'CK-K02: G1 header {tag} changed, its inventory row kept: reported', any(needle in x and 'G1.txt' in x for x in got), got)
        t = tree('norow')
        inv = json.loads((t / 'L3/inventory.json').read_text())
        (t / 'L3/inventory.json').write_text(json.dumps([r for r in inv if r['id'] != 1]))
        got = R.header_inventory_mismatches(t, 3)
        check('a G-file without an inventory row is reported', any('no inventory row' in x for x in got), got)
        t = tree('nofile')
        (t / 'L3/G3.txt').unlink()
        got = R.header_inventory_mismatches(t, 3)
        check('an inventory row naming a missing G-file is reported', any('L3/G3.txt, which does not exist' in x for x in got), got)
        # ---- end to end: gen/regress.py with fake builders copying the frozen L3 trees
        rc, rec = run_regress(td, 'clean', [])
        rec_clean = rec
        check('end to end: regress.py --loops 3 passes on copies of the frozen trees',
              rc == 0 and rec.get('passed') is True and rec['sectors']['free_L3']['identical'] == 5, rec.get('failures', rec))
        # ---- Stage-6 fix round 2 (Y2's defect class): an inherited OpenMP control never reaches a builder, so the
        # thread-identity comparison compares runs at the requested team sizes
        envlog = td / 'ompenv.jsonl'
        rc, rec = run_regress(td, 'ompenv', [], dict(OMP_THREAD_LIMIT='1', OMP_DYNAMIC='true', OMP_NUM_THREADS='64',
                                                     GOMP_SPINCOUNT='0', KMP_AFFINITY='none', FAKE_REGRESS_ENVLOG=str(envlog)))
        seen = [json.loads(x) for x in envlog.read_text().splitlines()] if envlog.exists() else []
        check('end to end: every builder gets OMP_NUM_THREADS and OMP_DYNAMIC=FALSE and no inherited OpenMP control',
              rc == 0 and len(seen) == 4 and all(set(x['env']) == {'OMP_NUM_THREADS', 'OMP_DYNAMIC'} and x['env']['OMP_DYNAMIC'] == 'FALSE'
                                                 for x in seen)
              and sorted(x['env']['OMP_NUM_THREADS'] for x in seen) == ['1', '1', '2', '2'], dict(rc=rc, seen=seen))
        b = R.builder_env(8, {'PATH': '/bin', 'OMP_THREAD_LIMIT': '1', 'GOMP_CPU_AFFINITY': '0', 'KMP_BLOCKTIME': '0'})
        check('builder_env (also gen/gates.py check_edge_forests): only PATH, OMP_NUM_THREADS=8 and OMP_DYNAMIC=FALSE',
              b == {'PATH': '/bin', 'OMP_NUM_THREADS': '8', 'OMP_DYNAMIC': 'FALSE'}, b)
        G = (GEN / 'gates.py').read_text()
        check('gen/gates.py runs check_edge_forests in builder_env', 'env=builder_env(a.jobs)' in G and 'from regress import builder_env' in G)
        strip = 'for v in $(compgen -e); do case "$v" in OMP_*|GOMP_*|KMP_*) unset "$v";; esac; done'
        scripts = [ROOT / 'gen/run_l8.sh', *sorted((ROOT / 'slurm/gen').glob('*.slurm'))]

        def first_run(text: str) -> int:  # the first non-comment line that starts a generator program or a pipeline step
            lines = text.splitlines()
            return next((i for i, x in enumerate(lines) if not x.lstrip().startswith('#') and
                         any(k in x for k in ('/build_', 'regress.py', 'run_l8.sh', 'gates.py', 'test_keys.py', 'make -C'))), len(lines))
        bad = [str(s.relative_to(ROOT)) for s in scripts if strip not in s.read_text().splitlines()
               or s.read_text().splitlines().index(strip) > first_run(s.read_text())]
        check('the generator job scripts and gen/run_l8.sh unset inherited OpenMP controls before any builder', not bad, bad)
        rc, rec = run_regress(td, 'wa', [['free', 3, 'G1.txt', 'C7D2GRAPH1 3 1 1 0 ', 'C7D2GRAPH1 3 1 2 0 ']])
        fails = ' | '.join(rec.get('failures', []))
        check('end to end, CK-K02: only wa changed in the built free L3 G1.txt fails A-INV-2 (G-file and header checks)',
              rc == 1 and rec.get('passed') is False and 'differ beyond the allowed rate lines' in fails
              and 'disagree with their inventory rows' in fails and not rec['sectors']['free_L3']['accepted_relabelling'], rec.get('failures', rec))
        rc, rec = run_regress(td, 'short', [['free', 3, 'G1.txt', ' 0.2125 \n', ' \n']])
        check('end to end, CK-K02: a built free L3 rate table one entry short fails A-INV-2',
              rc == 1 and rec.get('passed') is False and rec['sectors']['free_L3']['rate_only'] == 0, rec.get('failures', rec))
        # ---- W5 (Stage-6 fix round 4): CRLF line ends in a built G-file are no byte identity (read_text() hid them)
        for sector, gfile in (('power', 'G7.txt'), ('free', 'G1.txt')):
            rc, rec = run_regress(td, f'crlf_{sector}', [[sector, 3, gfile, '\n', '\r\n']])
            row = rec.get('sectors', {}).get(f'{sector}_L3', {})
            check(f'end to end, W5: a built {sector} L3 {gfile} with a CRLF line end fails A-INV-2 (not byte-identical)',
                  rc == 1 and rec.get('passed') is False and any(x.get('file') == gfile for x in row.get('other', []))
                  and row.get('identical') == row.get('frozen_gfiles', 0) - 1, dict(failures=rec.get('failures'), row=row))
        # ---- Stage-6 finding S6-B-02: the selection is validated; a subset run is never H1 evidence
        check('end to end: the --loops 3 run records partial coverage (no H1 evidence)',
              rec_clean.get('coverage', {}).get('h1') is False and any('loops' in x for x in h1(rec_clean)),
              dict(coverage=rec_clean.get('coverage'), h1=h1(rec_clean)))
        for sel, needle in ((['--loops', '7-3'], 'reversed range'), (['--loops', '3,3'], 'named twice'),
                            (['--loops', '8'], 'no frozen payload'), (['--loops', ''], 'integers'),
                            (['--threads', ''], 'integers'), (['--threads', '0,8'], 'positive'),
                            (['--threads', '8,8'], 'named twice')):
            work = td / f'work_sel_{len(results)}'
            r = subprocess.run([sys.executable, '-B', str(GEN / 'regress.py'), '--classes', str(td), '--bin', str(td),
                                '--work', str(work), *sel], capture_output=True, text=True)
            check(f'regress.py refuses {" ".join(sel)!r} before building', r.returncode == 2 and needle in r.stderr
                  and not work.exists(), dict(rc=r.returncode, stderr=r.stderr[-400:], work=work.exists()))
    for text, want in (('3-7', [3, 4, 5, 6, 7]), ('3', [3]), ('5,3', [5, 3]), ('7-7', [7])):
        try:
            got = R.loops_arg(text)
        except Exception as e:  # noqa: BLE001
            got = f'{type(e).__name__}: {e}'
        check(f'loops_arg({text!r}) = {want}', got == want, str(got))
    for text in ('7-3', '3,3', '2', '8', '2-4', '', '3-', 'x', '3,,4'):
        try:
            got = R.loops_arg(text)
        except ValueError:
            got = 'refused'
        check(f'loops_arg({text!r}) is refused (empty, reversed, repeated or out of 3..7)', got == 'refused', str(got))
    threads_arg = getattr(R, 'threads_arg', None)
    for text, want in (('1,8', [1, 8]), ('1', [1]), ('', 'refused'), ('0', 'refused'), ('1,1', 'refused'), ('-2', 'refused'),
                       ('a', 'refused')):
        try:
            got = threads_arg(text)
        except ValueError:
            got = 'refused'
        except Exception as e:  # noqa: BLE001  (missing before the S6-B-02 fix)
            got = f'{type(e).__name__}: {e}'
        check(f'threads_arg({text!r}) -> {want}', got == want, str(got))
    full = synthetic_h1_record()
    check('h1_problems: a complete synthetic record is H1 evidence', h1(full) == [], h1(full))

    def mutated(fn) -> dict:
        r = json.loads(json.dumps(full))
        fn(r)
        return r

    def drop_sector(r):
        del r['sectors']['power_L5']

    def single_thread(r):
        r['threads'], r['threads_identical'] = [1], {}
        r['builds'] = [b for b in r['builds'] if b['threads'] == 1]

    def no_serial(r):
        r['threads'], r['threads_identical'] = [2, 8], {'2_vs_8': dict(identical=True, differences=[])}
        for b in r['builds']:
            b['threads'] = 2 if b['threads'] == 1 else b['threads']

    def loops_only_3(r):
        r['loops'] = [3]
        r['builds'] = [b for b in r['builds'] if b['L'] == 3]
        r['sectors'] = {k: v for k, v in r['sectors'].items() if k.endswith('_L3')}

    def l7_rate_only(r):
        r['sectors']['free_L7'].update(identical=1, rate_only=1)

    def no_header_check(r):
        for v in r['sectors'].values():
            del v['header_inventory_mismatches']

    for name, fn, needle in (
            ('loops [3] (gen/regress.py --loops 3)', loops_only_3, 'loops [3]'),
            ('no loop at all', lambda r: r.update(loops=[], builds=[], sectors={}), 'loops []'),
            ('one thread count (--threads 1)', single_thread, 'thread identity'),
            ('no serial run (threads 2 and 8)', no_serial, 'one of them 1'),
            ('a sector missing', drop_sector, 'power_L5'),
            ('thread identity false', lambda r: r['threads_identical']['1_vs_8'].update(identical=False), 'thread identity'),
            ('a build that failed', lambda r: r['builds'][3].update(rc=1), 'builds'),
            ('free L7 not byte-identical', l7_rate_only, 'free_L7'),
            ('no header-row check (before CK-K02)', no_header_check, 'before CK-K02'),
            ('the L7 control false', lambda r: r['controls'].update(side_file_L7_eq_c8d1_L7_inventory=False), 'controls'),
            ('failures listed', lambda r: r.update(failures=['x']), 'without failures'),
            ('passed false', lambda r: r.update(passed=False), 'without failures'),
            ('another gate name', lambda r: r.update(gate='A-INV-2 comparison logic (gen/test_regress.py)'), 'not an A-INV-2')):
        got = h1(mutated(fn))
        check(f'h1_problems refuses partial evidence: {name}', any(needle in x for x in got), got)
    real = ROOT / 'benchmarks/expanse_2026-10-c8/ckpt_fix/expanse_d98e3a1/gen1.54658874.0/regress_L3_L7.json'
    if real.is_file():
        got = h1(json.loads(real.read_text()))
        check('h1_problems accepts the real J-GEN-1 record of the CK-K02 fix (Expanse 54658874)', got == [], got)
        old = ROOT / 'benchmarks/expanse_2026-10-c8/stage1/gen1.54631551.0/regress_L3_L7.json'
        got = h1(json.loads(old.read_text()))
        check('h1_problems refuses the Stage-1 record (Expanse 54631551): it predates the CK-K02 header-row check',
              bool(got) and all('before CK-K02' in x for x in got), got)
    gfile_gate_checks(check)  # Z5: A-INV-3(j)'s structural parse (gen/gates.py check_gfile) against regress.py's parser
    kirchhoff_checks(check)  # W4's class (fix round 4, integration): A-INV-3(h)'s reader
    rec = dict(schema='c8-d2-gate-1', gate='A-INV-2 comparison logic (gen/test_regress.py)', passed=not failed and bool(results),
               failed=failed, checks=results)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rec, indent=1) + '\n')
    print(f'test_regress: {len(results) - len(failed)}/{len(results)} checks passed')
    return 0 if rec['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
