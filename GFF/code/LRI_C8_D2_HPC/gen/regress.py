#!/usr/bin/env python3
"""A-INV-2: regression of the ported d=2 builders against the frozen C7(2) payloads at L3..L7 (x86-64 only).

Regenerates every loop with bin/gen/build_free and bin/gen/build_power at each requested thread count, then checks
  * power L3..L7: every G-file byte-identical to reference/power_mass/inputs/L*/, the same file set;
  * free L7: all 2,441 finite G-files byte-identical, rate lines included (parity rule);
  * free L3..L6: header, mask, term and 2^E lines byte-identical; only the rate lines may differ (the frozen files
    keep legacy C6 rate tables, relabelled through verification/legacy_mapping.json), and their count is reported,
    with the files whose rate tokens agree and only the line's trailing space differs counted apart (the free
    builder writes the rate line as the frozen parity-rule free L7 files have it, tokens joined by single spaces
    with no trailing space; the frozen free L<=6 and power files keep the C7(2) builders' trailing space);
  * the builder inventory.json objects equal the frozen ones field by field (forests included; numbers compared
    as exact numerals, never through binary64);
  * the outputs are identical at every thread count (L7 included);
  * control for gate A-INV-3(b): the subgraph side file of both builders at L7 equals C8(1)'s L7_inventory.txt
    byte for byte, and the two builders' side files are identical at every loop.
  * every G-file header agrees with its own inventory.json row (L, id, mask and term counts exactly, wa and wb at the
    inventory's binary64 precision, the file name), every G-file has a row and every row's file exists, in the new
    tree and in the frozen one (checkpoint review CK-K02: the inventory comparison alone never read the G-files).
Every G-file must also be well formed (parse_gfile): M masks in [0, 2^E) of L edges each, 2^E = 2^(2L) on its line
and as the rate-table size, every term line 1 + k + E integers with 1 <= k <= M and mask indices below M.
Stage-6 fix round 4: 'identical' means equal BYTES (W5): the G-files are read as bytes, never as text with newline
translation (read_text() turned CRLF and CR into LF, so a file with other line ends counted as byte-identical). Any
other comparison decodes the bytes without translation (gfile_text). A G-file is read as the builders write it and the
native loader reads it (W4's class): printable ASCII, spaces and LF only; header counts and every integer plain ASCII
decimals within the loader's bounds (2 <= L <= 8, 1 <= M <= 16384, 1 <= T <= 10000, int coefficients); weights and
rates plain decimals. gen/gates.py's A-INV-3(j) reader uses the same helpers.
--explain classifies every other difference (header weights, header counts or ids, mask order or values, term order
or values, 2^E line, rate line, structure); for free L <= 6 such a difference is compared again after the
vertex/edge relabelling of legacy_mapping.json. Only a difference proven to be that relabelling is accepted
(legacy_relabel_equal): the header (magic, L, id, wa, wb, M, T), the 2^E line and the rate-table size byte-identical,
only mask, term and rate-value parts differing, the masks (as a multiset) and the terms (multiset of mask multiset and
coefficient vector) different as they stand (an order difference alone is no relabelling) and equal after the graph's
recorded edge permutation, in either direction; rate values stay free, as for the rate-only rule (legacy tables). The
per-file verdict is judge(), exercised without the builders by gen/test_regress.py.

Usage: python3 -B gen/regress.py --classes reference/LRI_C7_d2_progress/reference --threads 1,8 --explain
           [--bin bin/gen] [--work DIR] [--loops 3-7] [--output FILE]
--loops is LO-HI or a comma list of loops in 3..7, --threads a comma list of distinct positive counts; an empty,
reversed, repeated or out-of-range selection is refused before anything is built (Stage-6 finding S6-B-02). A subset
run passes when what it ran passes, but the record's `coverage` says so, and only a record that h1_problems() finds
complete (every loop 3..7, both sectors, thread identity against 1 thread) is H1 evidence (gen/handoff_inventory.py).
Exit status 0 when A-INV-2 passes."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN = {'free': ROOT / 'reference/LRI_C7_d2_progress/inputs', 'power': ROOT / 'reference/power_mass/inputs'}
LEGACY = ROOT / 'reference/LRI_C7_d2_progress/verification/legacy_mapping.json'
C8D1 = ROOT / 'reference/c8d1_inputs8'


OMP_CONTROL_PREFIXES = ('OMP_', 'GOMP_', 'KMP_')


def builder_env(threads: int, base=None) -> dict:
    """The environment of a generator program (build_free, build_power, check_edge_forests) at `threads` OpenMP threads
    (Stage-6 fix round 2, Y2's defect class): the inherited one without any OpenMP runtime control (OMP_*, GOMP_*,
    KMP_*: an inherited OMP_THREAD_LIMIT=1 or OMP_DYNAMIC=true would run the 8-thread build serially, and A-INV-2's
    thread-identity comparison would compare two serial runs), then OMP_NUM_THREADS=threads and OMP_DYNAMIC=FALSE."""
    e = {k: v for k, v in (os.environ if base is None else base).items() if not k.startswith(OMP_CONTROL_PREFIXES)}
    e.update(OMP_NUM_THREADS=str(threads), OMP_DYNAMIC='FALSE')
    return e


# ---- the G-file as the builders write it and the native loader reads it (W4, W5; Stage-6 fix round 4) -------------
# src/kernel.hpp load_graph's header limits (LMAX, MAXMASKS, MAXTERMS) and its integer types: a mask is an unsigned, a
# term entry an int. Z5's token rules (fix round 3) are here so gen/gates.py and this file read one format.
LMAX, MAXMASKS, MAXTERMS = 8, 16384, 10000
MASK_TOKEN = re.compile(r'[0-9]+')
TERM_TOKEN = re.compile(r'-?[0-9]+')
INT_RANGE = (-2 ** 31, 2 ** 31)
WEIGHT_TOKEN = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?')  # the header's wa and wb (long double)
RATE_DECIMAL = re.compile(r'(?:0|[1-9][0-9]*)(?:\.[0-9]+)?')  # a rate-table entry, as every builder writes it
_GFILE_BYTES = bytes([0x0a, *range(0x20, 0x7f)])  # LF, space and printable ASCII
_GFILE_TEXT_BAD = re.compile(r'[^\n -~]')


def gfile_text(data: bytes) -> str:
    """W4/W5: the bytes of a G-file as text, WITHOUT newline translation: every byte LF, space or printable ASCII (the
    builders write nothing else). Refused (ValueError naming the byte and its offset): CR (read_text() turned CRLF and
    CR into LF, hiding them from a byte-identity check), tab and every other control byte, and every non-ASCII byte
    (Python's str.split() splits on U+00A0, U+2000.., and on U+001C..U+001F, where the loader's stream extraction does
    not, so a token check after split() passed files the loader refuses)."""
    data = bytes(data)
    rest = data.translate(None, _GFILE_BYTES)
    if rest:
        i = data.index(rest[:1])
        raise ValueError(f'byte 0x{data[i]:02x} at offset {i}: a G-file holds LF, spaces and printable ASCII only')
    return data.decode('ascii')


def parse_gfile(text: str) -> dict:
    """Split a G-file into its parts; raises ValueError if the structure is wrong: the header, the masks (M integers in
    [0, 2^E), each of L edges), every term line (1 + k + E integers, 1 <= k <= M, mask indices below M), the 2^E line
    equal to 2^(2L) and a rate table of exactly 2^E entries (the kernel's load_graph contract).
    W4's class (Stage-6 fix round 4): read as the native loader reads it, not more leniently. Only LF, spaces and
    printable ASCII; the header 'C7D2GRAPH1 L id wa wb M T' with L, id, M and T plain ASCII decimals within the
    loader's bounds (2 <= L <= 8, 1 <= M <= 16384, 1 <= T <= 10000) and the weights plain decimals; every mask a plain
    decimal (int() also takes '+7', '0_7', '-7' and non-ASCII digits); every term entry a plain decimal within the
    loader's int; every rate entry a plain decimal."""
    if _GFILE_TEXT_BAD.search(text):
        c = _GFILE_TEXT_BAD.search(text).group()
        raise ValueError(f'character {c!r}: a G-file holds LF, spaces and printable ASCII only')
    lines = text.split('\n')
    if lines[-1] != '':
        raise ValueError('no final newline')
    lines = lines[:-1]
    if not lines:
        raise ValueError('empty file')
    head = lines[0].split()
    if (len(head) != 7 or head[0] != 'C7D2GRAPH1' or not all(MASK_TOKEN.fullmatch(head[i]) for i in (1, 2, 5, 6))
            or not all(WEIGHT_TOKEN.fullmatch(head[i]) for i in (3, 4))):
        raise ValueError('bad header')
    L, M, T = int(head[1]), int(head[5]), int(head[6])
    if not (2 <= L <= LMAX and 1 <= M <= MAXMASKS and 1 <= T <= MAXTERMS):
        raise ValueError(f'bad header (L={L}, M={M}, T={T} outside the native loader\'s bounds)')
    E = 2 * L
    if len(lines) != 4 + T:
        raise ValueError(f'{len(lines)} lines for T={T}')
    masks = lines[1].split()
    if len(masks) != M:
        raise ValueError('mask count')
    if not all(MASK_TOKEN.fullmatch(x) for x in masks):
        raise ValueError('masks: a token is not a plain decimal')
    if any(not 0 <= m < 1 << E or bin(m).count('1') != L for m in map(int, masks)):
        raise ValueError('masks: mask outside [0, 2^E) or not of L edges')
    for line in lines[2:2 + T]:
        toks = line.split()
        if not all(TERM_TOKEN.fullmatch(x) for x in toks):
            raise ValueError('term line not integer')
        t = [int(x) for x in toks]
        if (not t or not 1 <= t[0] <= M or len(t) != 1 + t[0] + E or any(not 0 <= i < M for i in t[1:1 + t[0]])
                or any(not INT_RANGE[0] <= c < INT_RANGE[1] for c in t)):
            raise ValueError('term line shape')
    if lines[2 + T] != str(1 << E):
        raise ValueError(f'2^E line {lines[2 + T]!r} for E={E}')
    rates = lines[3 + T].split()
    if len(rates) != 1 << E:
        raise ValueError(f'rate table of {len(rates)} entries for 2^E={1 << E}')
    if not all(RATE_DECIMAL.fullmatch(x) for x in rates):
        raise ValueError('rate table: an entry is not a plain decimal')
    return dict(lines=lines, head=head, L=L, E=E, M=M, T=T, terms=lines[2:2 + T], pow2=lines[2 + T], rate=lines[3 + T])


def classify(new: str, old: str) -> list[str]:
    """--explain: which parts of two G-files differ."""
    try:
        a, b = parse_gfile(new), parse_gfile(old)
    except ValueError as e:
        return [f'structure ({e})']
    out = []
    if a['head'] != b['head']:
        if a['head'][3:5] != b['head'][3:5]:
            out.append('header weights')
        if a['head'][:3] + a['head'][5:] != b['head'][:3] + b['head'][5:]:
            out.append('header counts or ids')
    if a['lines'][1] != b['lines'][1]:
        out.append('mask order' if sorted(a['lines'][1].split()) == sorted(b['lines'][1].split()) else 'mask values')
    if a['terms'] != b['terms']:
        out.append('term order' if Counter(a['terms']) == Counter(b['terms']) else 'term values')
    if a['pow2'] != b['pow2']:
        out.append('2^E line')
    if a['rate'] != b['rate']:
        out.append('rate line')
    if not out and new != old:
        out.append('layout (whitespace)')
    return out


def canonical(text: str, perm: list[int] | None) -> tuple:
    """Order-independent form of masks and terms after relabelling edge e -> perm[e]: the masks as a multiset, the
    terms as a multiset of (multiset of their masks, coefficient vector)."""
    g = parse_gfile(text)
    E = g['E']
    p = perm if perm is not None else list(range(E))

    def pm(m: int) -> int:
        return sum(1 << p[e] for e in range(E) if m >> e & 1)

    masks = [int(x) for x in g['lines'][1].split()]
    terms = []
    for line in g['terms']:
        t = [int(x) for x in line.split()]
        k = t[0]
        basis = tuple(sorted(pm(masks[i]) for i in t[1:1 + k]))
        co = [0] * E
        for e, c in enumerate(t[1 + k:]):
            co[p[e]] = c
        terms.append((basis, tuple(co)))
    return tuple(sorted(pm(m) for m in masks)), Counter(terms)


# The parts of a G-file that an edge relabelling can change: the masks and the terms (their order and values), and
# the rate values (free L <= 6 keep legacy rate tables either way). The header, the 2^E line and the rate-table size
# are invariant under a relabelling.
RELABEL_PARTS = frozenset({'mask order', 'mask values', 'term order', 'term values', 'rate line'})


def legacy_relabel_equal(new: str, old: str, gid: int, L: int, legacy: dict) -> str | None:
    """A proof description when new and old differ only by graph gid's recorded relabelling, else None (CK-K02).

    Required: both files well formed; the header (magic, L, id, wa, wb, M, T), the 2^E line and the rate-table size
    byte-identical; every differing part in RELABEL_PARTS and at least one of them a mask or term part; the masks and
    terms NOT equal as they stand (canonical(new, None) != canonical(old, None): a difference of order alone is no
    relabelling, which also leaves out the identity permutation and the many recorded permutations that are
    automorphisms, e.g. exchanges of parallel edges); and equal after gid's recorded edge permutation at L or its
    inverse (canonical()). Rate values are not compared (legacy tables, as for the rate-only rule)."""
    try:
        a, b = parse_gfile(new), parse_gfile(old)
    except ValueError:
        return None
    if a['head'] != b['head'] or a['pow2'] != b['pow2'] or len(a['rate'].split()) != len(b['rate'].split()):
        return None
    if a['L'] != L or int(a['head'][2]) != gid:
        return None
    parts = classify(new, old)
    if not parts or not set(parts) <= RELABEL_PARTS or set(parts) <= {'rate line'}:
        return None
    ref = canonical(old, None)
    if canonical(new, None) == ref:
        return None
    for rec in legacy.get(L, []):
        if rec.get('new') != gid:
            continue
        perm = [int(x) for x in rec['edge_permutation']]
        if sorted(perm) != list(range(a['E'])):
            continue
        inv = [0] * len(perm)
        for i, j in enumerate(perm):
            inv[j] = i
        for name, p in (('edge_permutation', perm), ('inverse edge_permutation', inv)):
            if canonical(new, p) == ref:
                return f'equal after {name} of legacy map old={rec.get("old")}'
    return None


def judge(sector: str, L: int, name: str, new, old, legacy: dict) -> tuple[str, dict]:
    """A-INV-2's verdict on one G-file against its frozen counterpart: 'identical'; 'rate_only' (free L <= 6, only
    rate values differ, the rate-table size equal); 'relabelled' (free L <= 6, legacy_relabel_equal's proof); else
    'other' with the differing parts. Pure: the builders are not needed (gen/test_regress.py).
    W5 (S6R4-B-02, Stage-6 fix round 4): new and old are the files' BYTES (main reads them so), and 'identical' means
    equal bytes; anything else is compared as text decoded without newline translation (gfile_text), so other line
    ends, a CR or a non-ASCII byte are an 'other' (structure) difference, never 'identical'. Text arguments (the pure
    tests) are compared as given."""
    if isinstance(new, (bytes, bytearray)) or isinstance(old, (bytes, bytearray)):
        nb = bytes(new) if isinstance(new, (bytes, bytearray)) else new.encode()
        ob = bytes(old) if isinstance(old, (bytes, bytearray)) else old.encode()
        if nb == ob:
            return 'identical', {}
        try:
            new, old = gfile_text(nb), gfile_text(ob)
        except ValueError as e:
            return 'other', dict(parts=[f'structure ({e})'])
    if new == old:
        return 'identical', {}
    parts = classify(new, old)
    legacy_rate_ok = sector == 'free' and L <= 6
    if parts == ['rate line'] and legacy_rate_ok:
        ra, rb = parse_gfile(new)['rate'].split(), parse_gfile(old)['rate'].split()
        nd = sum(1 for x, y in zip(ra, rb) if x != y)  # equal sizes: parse_gfile requires 2^E entries in both
        return 'rate_only', dict(rate_entries_differing=nd, whitespace_only=nd == 0)
    if legacy_rate_ok:
        proof = legacy_relabel_equal(new, old, int(name[1:-4]), L, legacy)
        if proof:
            return 'relabelled', dict(parts=parts, proof=proof)
    return 'other', dict(parts=parts)


def header_inventory_mismatches(tree: Path, L: int) -> list[str]:
    """Every G-file header of tree/L<L> against its row in tree/L<L>/inventory.json (CK-K02): L, id, mask and term
    counts exactly, wa and wb at the inventory's binary64 precision (the header holds the long-double numeral, which
    float() rounds correctly), the row's file name; a malformed header, a G-file without a row, a duplicated id and a
    row naming a missing file are mismatches too."""
    d = tree / f'L{L}'
    out = []
    try:
        rows = json.loads((d / 'inventory.json').read_text())
    except (OSError, ValueError) as e:
        return [f'L{L}: inventory.json unreadable ({e})']
    by_id = {}
    for r in rows:
        if r.get('id') in by_id:
            out.append(f'L{L}: inventory.json lists id {r.get("id")} twice')
        by_id[r.get('id')] = r
    names = sorted((p.name for p in d.glob('G*.txt')), key=lambda s: int(s[1:-4]))
    for name in names:
        try:
            # W4/W5's class: the bytes as the loader reads them (no newline translation, ASCII only, plain decimals)
            head = gfile_text((d / name).read_bytes()).split('\n', 1)[0].split()
            if (len(head) != 7 or head[0] != 'C7D2GRAPH1' or not all(MASK_TOKEN.fullmatch(head[i]) for i in (1, 2, 5, 6))
                    or not all(WEIGHT_TOKEN.fullmatch(head[i]) for i in (3, 4))):
                raise ValueError('bad header')
            h = dict(L=int(head[1]), id=int(head[2]), wa=float(head[3]), wb=float(head[4]), masks=int(head[5]),
                     terms=int(head[6]))
        except (OSError, ValueError) as e:
            out.append(f'L{L}/{name}: unreadable header ({e})')
            continue
        r = by_id.get(h['id'])
        if r is None:
            out.append(f'L{L}/{name}: no inventory row for id {h["id"]}')
            continue
        bad = [k for k in ('L', 'masks', 'terms') if r.get(k) != h[k] or isinstance(r.get(k), bool)]
        bad += [k for k in ('wa', 'wb') if isinstance(r.get(k), bool) or not isinstance(r.get(k), (int, float))
                or float(r[k]) != h[k]]
        if h['L'] != L:
            bad.append('L (directory)')
        if h['id'] != int(name[1:-4]):
            bad.append('id (file name)')
        if r.get('file') != f'L{L}/{name}':
            bad.append('file')
        if bad:
            out.append(f'L{L}/{name}: header and inventory row differ in {bad} (header {head[1:]}, row '
                       f'{ {k: r.get(k) for k in ("L", "id", "wa", "wb", "masks", "terms", "file")} })')
    listed = {r.get('file') for r in rows if r.get('file')}
    for f in sorted(listed - {f'L{L}/{n}' for n in names}):
        out.append(f'L{L}: inventory.json names {f}, which does not exist')
    return out


def exact_json(path: Path):
    return json.loads(path.read_text(), parse_float=lambda s: ('num', s), parse_int=lambda s: ('num', s))


def num_equal(x, y) -> bool:
    return isinstance(x, tuple) and isinstance(y, tuple) and Decimal(x[1]) == Decimal(y[1])


def compare_inventories(new: Path, old: Path) -> list[str]:
    a, b = exact_json(new), exact_json(old)
    diffs = []
    if len(a) != len(b):
        return [f'{len(a)} objects vs {len(b)} frozen']
    for i, (x, y) in enumerate(zip(a, b)):
        if set(x) != set(y):
            diffs.append(f'object {i}: fields {sorted(set(x) ^ set(y))}')
            continue
        for k in y:
            if x[k] != y[k]:
                kind = 'numerically equal, textually different' if num_equal(x[k], y[k]) else 'different'
                diffs.append(f'object {i} ({y.get("id")}) field {k}: {x[k]!r} vs {y[k]!r} ({kind})')
    return diffs


def same_tree(a: Path, b: Path) -> list[str]:
    fa = {p.relative_to(a).as_posix() for p in a.rglob('*') if p.is_file()}
    fb = {p.relative_to(b).as_posix() for p in b.rglob('*') if p.is_file()}
    out = [f'only in one tree: {sorted(fa ^ fb)[:5]}'] if fa != fb else []
    out += [f'differs: {n}' for n in sorted(fa & fb) if (a / n).read_bytes() != (b / n).read_bytes()]
    return out


# The loops with frozen C7(2) payloads, and the coverage the H1 handoff requires (gen/handoff_inventory.py): every
# loop L3..L7, both sectors, and at least two thread counts, one of them 1 (thread identity against the serial run).
REGRESS_LOOPS = (3, 4, 5, 6, 7)
SECTORS = ('free', 'power')


def _ints(s: str, what: str) -> list[int]:
    try:
        out = [int(x) for x in s.split(',')]
    except ValueError:
        raise ValueError(f'{what} {s!r}: not a comma-separated list of integers') from None
    return out


def loops_arg(s: str) -> list[int]:
    """--loops: 'LO-HI' (LO <= HI) or a comma list, each loop in 3..7 (the frozen payloads), none repeated; ValueError
    for an empty, reversed, repeated or out-of-range selection (Stage-6 finding S6-B-02)."""
    s = s.strip()
    if '-' in s:
        lo, sep, hi = s.partition('-')
        try:
            lo_i, hi_i = int(lo), int(hi)
        except ValueError:
            raise ValueError(f'--loops {s!r}: a range is LO-HI with integers') from None
        if lo_i > hi_i:
            raise ValueError(f'--loops {s!r}: a reversed range selects no loop')
        loops = list(range(lo_i, hi_i + 1))
    else:
        loops = _ints(s, '--loops')
    bad = [L for L in loops if L not in REGRESS_LOOPS]
    if bad:
        raise ValueError(f'--loops {s!r}: loops {bad} have no frozen payload (the regression covers L3..L7)')
    if len(set(loops)) != len(loops):
        raise ValueError(f'--loops {s!r}: a loop is named twice')
    return loops


def threads_arg(s: str) -> list[int]:
    """--threads: a comma list of distinct positive thread counts; ValueError otherwise."""
    threads = _ints(s.strip(), '--threads')
    if any(t < 1 for t in threads):
        raise ValueError(f'--threads {s!r}: thread counts are positive')
    if len(set(threads)) != len(threads):
        raise ValueError(f'--threads {s!r}: a thread count is named twice')
    return threads


def coverage(loops: list[int], threads: list[int]) -> dict:
    """What a run covers, against the H1 requirement (every loop L3..L7, both sectors, thread identity vs 1 thread)."""
    full_loops = sorted(loops) == list(REGRESS_LOOPS)
    identity = len(threads) >= 2 and 1 in threads
    return dict(loops_L3_L7=full_loops, sectors=list(SECTORS), thread_identity=identity, h1=full_loops and identity)


def h1_problems(rec: dict) -> list[str]:
    """Why an A-INV-2 record (gen/regress.py --output) is not the full evidence the H1 handoff needs; [] when it is.

    Recomputed from the record's own content, never from a flag: schema and gate name, a pass with no failure; the
    loops exactly 3..7 and at least two distinct positive thread counts including 1; one successful build per
    (thread count, sector, loop); thread identity of every other count against the last one; for every sector and
    loop the same G-file set, no unexplained difference, the inventory equal and every G-file header equal to its
    inventory row in the new and the frozen tree, and every file accounted for (identical, rate-only or relabelled,
    the last two only at free L <= 6); the side-file controls at every loop and the L7 control against C8(1)."""
    out: list[str] = []
    if not isinstance(rec, dict):
        return ['the A-INV-2 record is not a JSON object']
    if rec.get('schema') != 'c8-d2-gate-1' or rec.get('gate') != 'A-INV-2 regress':
        out.append(f'not an A-INV-2 regress record (schema {rec.get("schema")!r}, gate {rec.get("gate")!r})')
    if rec.get('passed') is not True or rec.get('failures') != []:
        out.append('the record is not a pass without failures')
    loops, threads = rec.get('loops'), rec.get('threads')
    if loops != list(REGRESS_LOOPS):
        out.append(f'loops {loops!r}: H1 needs every loop 3..7')
        loops = list(REGRESS_LOOPS)
    if (not isinstance(threads, list) or len(threads) < 2 or 1 not in threads or len(set(map(repr, threads))) != len(threads)
            or any(type(t) is not int or t < 1 for t in threads)):
        out.append(f'threads {threads!r}: H1 needs at least two distinct positive thread counts, one of them 1 '
                   '(thread identity)')
        return out
    builds = rec.get('builds') if isinstance(rec.get('builds'), list) else []
    want = {(t, s, L) for t in threads for s in SECTORS for L in loops}
    got = [(b.get('threads'), b.get('sector'), b.get('L')) for b in builds if isinstance(b, dict) and b.get('rc') == 0]
    if len(builds) != len(want) or set(got) != want or len(got) != len(want):
        out.append(f'builds: {len(got)} successful of {len(builds)} recorded, {len(want)} required (every thread '
                   'count, sector and loop)')
    ti = rec.get('threads_identical') if isinstance(rec.get('threads_identical'), dict) else {}
    keys = {f'{t}_vs_{threads[-1]}' for t in threads[:-1]}
    if set(ti) != keys or not all(isinstance(ti[k], dict) and ti[k].get('identical') is True for k in keys):
        out.append(f'thread identity: {sorted(ti)} recorded, {sorted(keys)} required, all identical')
    sectors = rec.get('sectors') if isinstance(rec.get('sectors'), dict) else {}
    names = {f'{s}_L{L}' for s in SECTORS for L in loops}
    if set(sectors) != names:
        out.append(f'sectors: {sorted(set(sectors) ^ names)} missing or extra')
    for name in sorted(names & set(sectors)):
        row = sectors[name]
        legacy = name.startswith('free_') and int(name.split('_L')[1]) <= 6
        n = row.get('frozen_gfiles') if isinstance(row, dict) else None
        if not isinstance(row, dict) or type(n) is not int or n < 1:
            out.append(f'{name}: no G-file count')
            continue
        relab = row.get('accepted_relabelling')
        hdr = row.get('header_inventory_mismatches')
        count = lambda k: row.get(k, 0) if type(row.get(k, 0)) is int else -1  # noqa: E731
        accounted = count('identical') + count('rate_only') + (len(relab) if isinstance(relab, list) else 0)
        if (row.get('same_file_set') is not True or row.get('new_gfiles') != n or row.get('other') != []
                or not isinstance(relab, list) or accounted != n):
            out.append(f'{name}: not every one of the {n} G-files is accounted for (same set, identical, rate-only or '
                       'relabelled, nothing else)')
        if row.get('inventory_equal') is not True:
            out.append(f'{name}: inventory.json differs')
        if not isinstance(hdr, dict) or set(hdr) != {'new', 'frozen'}:
            out.append(f'{name}: no header-row check of the new and the frozen tree (a record from before CK-K02)')
        elif any(hdr[k] != [] for k in hdr):
            out.append(f'{name}: G-file headers disagree with their inventory rows')
        if not legacy and row.get('identical') != n:
            out.append(f'{name}: {row.get("identical")} of {n} G-files byte-identical (only free L <= 6 may differ)')
    controls = rec.get('controls') if isinstance(rec.get('controls'), dict) else {}
    need = [f'side_files_free_eq_power_L{L}' for L in loops] + ['side_file_L7_eq_c8d1_L7_inventory']
    if not all(controls.get(k) is True for k in need):
        out.append(f'controls: {[k for k in need if controls.get(k) is not True]} not true')
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--classes', type=Path, required=True)
    ap.add_argument('--threads', default='1,8')
    ap.add_argument('--loops', default='3-7')
    ap.add_argument('--bin', type=Path, default=ROOT / 'bin/gen')
    ap.add_argument('--work', type=Path)
    ap.add_argument('--explain', action='store_true')
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    try:
        threads, loops = threads_arg(a.threads), loops_arg(a.loops)
    except ValueError as e:
        ap.error(str(e))  # exits 2
        return 2  # not reached; it tells tests/ast_scan.py that threads and loops are bound below
    work = a.work or Path(tempfile.mkdtemp(prefix='c8d2_regress_'))
    work.mkdir(parents=True, exist_ok=True)
    legacy = {int(r['L']): r['maps'] for r in json.loads(LEGACY.read_text())}
    rec: dict = dict(schema='c8-d2-gate-1', gate='A-INV-2 regress', classes=str(a.classes), threads=threads,
                     loops=loops, coverage=coverage(loops, threads), work=str(work), builds=[], sectors={},
                     threads_identical={}, controls={})
    failures: list[str] = []
    # 1. regenerate
    for t in threads:
        for sector in ('free', 'power'):
            for L in loops:
                out = work / f't{t}' / sector / f'L{L}'
                side = work / f't{t}' / sector / f'L{L}.subgraphs.txt'
                if out.exists():
                    raise SystemExit(f'{out} exists: use a fresh --work directory')
                t0 = time.time()
                r = subprocess.run([str(a.bin / f'build_{sector}'), str(a.classes / f'classes{L}.txt'), str(out),
                                    str(side)], env=builder_env(t),
                                   capture_output=True, text=True)
                rec['builds'].append(dict(threads=t, sector=sector, L=L, rc=r.returncode,
                                          seconds=round(time.time() - t0, 3), stderr_tail=r.stderr[-300:]))
                if r.returncode != 0:
                    failures.append(f'build_{sector} L{L} t{t} exited {r.returncode}')
                print(f'built {sector} L{L} threads={t} rc={r.returncode} {time.time() - t0:.1f}s', flush=True)
    if failures:
        rec.update(passed=False, failures=failures)
        return finish(rec, a.output)
    base = work / f't{threads[-1]}'
    # 2. thread identity
    for t in threads[:-1]:
        d = same_tree(work / f't{t}', base)
        rec['threads_identical'][f'{t}_vs_{threads[-1]}'] = dict(identical=not d, differences=d[:20])
        if d:
            failures.append(f'outputs differ between {t} and {threads[-1]} threads: {d[:3]}')
    # 3. against the frozen payloads
    for sector in ('free', 'power'):
        for L in loops:
            new, old = base / sector / f'L{L}', FROZEN[sector] / f'L{L}'
            gn = {p.name for p in new.glob('G*.txt')}
            go = {p.name for p in old.glob('G*.txt')}
            row = dict(frozen_gfiles=len(go), new_gfiles=len(gn), same_file_set=gn == go, identical=0,
                       rate_only=0, rate_whitespace_only=0, rate_entries_differing=0, other=[],
                       accepted_relabelling=[])
            if gn != go:
                failures.append(f'{sector} L{L}: G-file sets differ ({sorted(gn ^ go)[:5]})')
            for name in sorted(gn & go, key=lambda s: int(s[1:-4])):
                tn, to = (new / name).read_bytes(), (old / name).read_bytes()  # W5: bytes, never newline-translated text
                verdict, info = judge(sector, L, name, tn, to, legacy)
                if verdict == 'identical':
                    row['identical'] += 1
                elif verdict == 'rate_only':
                    row['rate_only'] += 1
                    row['rate_entries_differing'] += info['rate_entries_differing']
                    row['rate_whitespace_only'] += info['whitespace_only']
                elif verdict == 'relabelled':
                    row['accepted_relabelling'].append(dict(file=name, parts=info['parts'], proof=info['proof']))
                else:
                    row['other'].append(dict(file=name, parts=info['parts'] if a.explain else ['(run with --explain)']))
            if row['other']:
                failures.append(f'{sector} L{L}: {len(row["other"])} G-files differ beyond the allowed rate lines')
            # CK-K02: each G-file header against its own inventory row, in the new tree and in the frozen one
            hdr = {'new': header_inventory_mismatches(base / sector, L),
                   'frozen': header_inventory_mismatches(FROZEN[sector], L)}
            row['header_inventory_mismatches'] = {k: v[:30] for k, v in hdr.items()}
            for k, v in hdr.items():
                if v:
                    failures.append(f'{sector} L{L}: {len(v)} G-file headers of the {k} tree disagree with their '
                                    f'inventory rows ({v[0]})')
            inv = compare_inventories(new / 'inventory.json', old / 'inventory.json')
            row['inventory_equal'] = not inv
            row['inventory_differences'] = inv[:30]
            row['inventory_bytes_identical'] = (new / 'inventory.json').read_bytes() == (old / 'inventory.json').read_bytes()
            if inv:
                failures.append(f'{sector} L{L}: inventory.json differs field by field ({len(inv)} differences)')
            rec['sectors'][f'{sector}_L{L}'] = row
            print(f'{sector} L{L}: {row["identical"]}/{len(go)} identical, rate-only {row["rate_only"]}, '
                  f'relabelled {len(row["accepted_relabelling"])}, other {len(row["other"])}, inventory equal {not inv}, '
                  f'headers agree with the rows {not any(hdr.values())}', flush=True)
    # 4. controls for gate A-INV-3(b): subgraph side files
    for L in loops:
        sf, sp = base / 'free' / f'L{L}.subgraphs.txt', base / 'power' / f'L{L}.subgraphs.txt'
        same = sf.read_bytes() == sp.read_bytes()
        rec['controls'][f'side_files_free_eq_power_L{L}'] = same
        if not same:
            failures.append(f'L{L}: the free and power builders classify subgraphs differently')
    if 7 in loops:
        ok = (base / 'free/L7.subgraphs.txt').read_bytes() == (C8D1 / 'L7_inventory.txt').read_bytes()
        rec['controls']['side_file_L7_eq_c8d1_L7_inventory'] = ok
        if not ok:
            failures.append('L7 subgraph side file differs from C8(1) L7_inventory.txt')
    rec.update(passed=not failures, failures=failures)
    rec['free_L3_L6_rate_line_files'] = sum(rec['sectors'].get(f'free_L{L}', {}).get('rate_only', 0) for L in loops if L <= 6)
    rec['free_L3_L6_rate_whitespace_only_files'] = sum(rec['sectors'].get(f'free_L{L}', {}).get('rate_whitespace_only', 0)
                                                       for L in loops if L <= 6)
    return finish(rec, a.output)


def finish(rec: dict, output: Path | None) -> int:
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(rec, indent=1) + '\n')
    print('A-INV-2', 'PASSED' if rec['passed'] else 'FAILED', '; '.join(rec.get('failures', []))[:2000])
    return 0 if rec['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
