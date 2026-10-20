"""Shared helpers of the gen3/ tools (PLAN.md component A). Standard library only.

- The refusal of C62d's trees (A.2 step 0, A-INV-6): no gen3/ tool writes an output, scratch or staging path under
  /expanse/lustre/scratch/zzheng8/temp_project/c8d2/ or under any .../LRI_C8_shared/inventory/ (the Expanse copy and
  the Mac mirror of H1). `refuse_c62d` exits 2 naming the path. The only exceptions are the A.5 report-back's two
  coordination files, by exact name (`gates_d3.py handoff-gate6`: the `c63d` block of HANDOFF_inventory8_d2.json under
  DECISIONS A3; `decisions-ack`: one line appended to DECISIONS.md's acknowledgment log); no payload tree is among them.
- Hashes of exact file bytes.
- H1's code, authenticated before anything of it runs (S4-001): `h1_code_snapshot` checks the tree's MANIFEST.json
  against the external pin, SHA256SUMS against the MANIFEST and every file under src/ against SHA256SUMS (and the
  MANIFEST's gen_sources_sha256), with no unlisted entry, link or special file there (a stray module next to the
  verifier would be imported before the standard library), then copies src/gen/ into a private directory and checks the
  copied bytes; only that snapshot is executed or built (gates_d3.py h1-copy, `h1-auth`, gen3/run_d3.sh).
- The names of the H1 gate records and their supporting records, and gate 1(a)'s platform rule (`expanse_run`).
- A strict G-file parser (the format of C7(2)/C8(2) d=2 and C7(3)/C8(3) d=3 kernel files; the same rules as
  regenerate_rates.cpp's reader) and a pure-Python recomputation of the d=3 rate line and of the raw valuations
  (regenerate_rates.cpp's formula), used as an independent check in the tests and the rate audit.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

C8D2_PREFIX = '/expanse/lustre/scratch/zzheng8/temp_project/c8d2'
SHARED_INVENTORY = ('LRI_C8_shared', 'inventory')
MAGICS = ('C7D2GRAPH1', 'C7D3GRAPH1')


class Gen3Error(Exception):
    """A refusal or a failed check that the tool reports as '<path>: <reason>' with exit 2."""


def die(msg: str, code: int = 2) -> 'NoReturn':  # noqa: F821
    print(msg, file=sys.stderr)
    raise SystemExit(code)


# ---- C62d's trees ------------------------------------------------------------------------------------------------
def _c62d_hit(p: PurePosixPath) -> str:
    s = p.as_posix()
    if s == C8D2_PREFIX or s.startswith(C8D2_PREFIX + '/'):
        return C8D2_PREFIX
    parts = p.parts
    for i in range(len(parts) - 1):
        if (parts[i], parts[i + 1]) == SHARED_INVENTORY:
            return '.../LRI_C8_shared/inventory'
    return ''


def under_c62d(path) -> str:
    """The C62d tree that `path` lies under ('' if none), lexically and after resolving existing symlinks."""
    a = Path(os.path.abspath(os.fspath(path)))
    hit = _c62d_hit(PurePosixPath(os.path.normpath(a.as_posix())))
    if hit:
        return hit
    try:
        r = a.resolve(strict=False)
    except (OSError, RuntimeError):
        return ''
    return _c62d_hit(PurePosixPath(r.as_posix()))


def refuse_c62d(path, what: str) -> Path:
    """Exit 2 if `path` (an output, scratch or staging path) lies under one of C62d's trees; else return it."""
    hit = under_c62d(path)
    if hit:
        die(f'{path}: {what} is under C62d\'s tree {hit} (refused: nothing of this package writes there)')
    return Path(path)


# ---- H1's code (S4-001) ------------------------------------------------------------------------------------------
H1_ROW = re.compile(r'([0-9a-f]{64})  (\S+)')


def _regular(p: Path, what: str) -> bytes:
    if p.is_symlink() or not p.is_file():
        raise Gen3Error(f'{p}: {what} is not a regular file')
    return p.read_bytes()


def h1_code_hashes(tree, pin: str) -> dict:
    """{path under the tree: sha256} of every file under the H1 tree's src/, through the checksum chain from the external
    pin: sha256(MANIFEST.json) = pin; sha256(SHA256SUMS) = MANIFEST sha256sums_sha256; the SHA256SUMS rows under src/,
    which must equal the MANIFEST's gen_sources_sha256 (keys without the src/ prefix) and include
    src/gen/verify_inventory.py. Reads only; raises Gen3Error."""
    tree = Path(tree)
    mb = _regular(tree / 'MANIFEST.json', 'the H1 MANIFEST')
    if not re.fullmatch(r'[0-9a-f]{64}', str(pin)) or sha256_bytes(mb) != pin:
        raise Gen3Error(f'{tree}/MANIFEST.json: sha256 {sha256_bytes(mb)} is not the H1 pin {pin}')
    try:
        man = json.loads(mb)
    except ValueError as e:
        raise Gen3Error(f'{tree}/MANIFEST.json: not JSON ({e})') from None
    sb = _regular(tree / 'SHA256SUMS', 'the H1 SHA256SUMS')
    if not isinstance(man, dict) or sha256_bytes(sb) != man.get('sha256sums_sha256'):
        raise Gen3Error(f'{tree}/SHA256SUMS: sha256 {sha256_bytes(sb)} is not the MANIFEST\'s sha256sums_sha256')
    rows: dict = {}
    for k, line in enumerate(sb.decode('utf-8', 'replace').split('\n')[:-1] if sb.endswith(b'\n') else [None], 1):
        m = H1_ROW.fullmatch(line or '')
        if not m or m.group(2) in rows:
            raise Gen3Error(f'{tree}/SHA256SUMS: line {k}: malformed or duplicate row')
        rows[m.group(2)] = m.group(1)
    code = {q: h for q, h in rows.items() if q.startswith('src/')}
    gen = man.get('gen_sources_sha256')
    if not isinstance(gen, dict) or {f'src/{q}': h for q, h in gen.items()} != code or 'src/gen/verify_inventory.py' not in code:
        raise Gen3Error(f'{tree}: the SHA256SUMS rows under src/ differ from the MANIFEST\'s gen_sources_sha256 '
                        '(or src/gen/verify_inventory.py is not listed)')
    return code


def h1_code_snapshot(tree, pin: str, snapshot) -> dict:
    """S4-001: authenticate the H1 tree's code with h1_code_hashes (every file under src/ listed, a regular file at its
    hash; no other entry: no unlisted file or directory, no symlink) and copy src/gen/ into `snapshot` (created here; it
    must not exist), checking the copied bytes. Run or build only the snapshot. Returns a record; raises Gen3Error and
    then leaves no snapshot."""
    tree, snapshot = Path(tree), Path(snapshot)
    code = h1_code_hashes(tree, pin)
    e = []
    seen = set()
    for q in sorted((tree / 'src').rglob('*')) if (tree / 'src').is_dir() and not (tree / 'src').is_symlink() else []:
        rel = q.relative_to(tree).as_posix()
        if q.is_symlink() or not (q.is_dir() or q.is_file()):
            e.append(f'{rel}: a link or special file')
        elif q.is_dir():
            if not any(k.startswith(rel + '/') for k in code):
                e.append(f'{rel}/: a directory SHA256SUMS does not list')
        elif rel not in code:
            e.append(f'{rel}: not listed in SHA256SUMS (an unlisted file next to H1\'s code)')
        else:
            seen.add(rel)
            if sha256_file(q) != code[rel]:
                e.append(f'{rel}: sha256 differs from SHA256SUMS')
    e += [f'{k}: listed but missing' for k in sorted(set(code) - seen)]
    if e:
        raise Gen3Error(f'{tree}: H1 code not authenticated: ' + '; '.join(e[:5]) + (f' (and {len(e) - 5} more)' if len(e) > 5 else ''))
    gen = {k[len('src/gen/'):]: h for k, h in code.items() if k.startswith('src/gen/') and '/' not in k[len('src/gen/'):]}
    snapshot = refuse_c62d(snapshot, 'H1 code snapshot')
    if snapshot.exists() or snapshot.is_symlink():
        raise Gen3Error(f'{snapshot}: exists (the H1 code snapshot is made fresh)')
    snapshot.mkdir(parents=True)
    try:
        for name, h in sorted(gen.items()):
            b = (tree / 'src/gen' / name).read_bytes()
            if sha256_bytes(b) != h:
                raise Gen3Error(f'{tree}/src/gen/{name}: changed while it was copied')
            with open(snapshot / name, 'xb') as f:
                f.write(b)
            shutil.copystat(tree / 'src/gen' / name, snapshot / name)   # mode and times, as `cp -p` did
        if sorted(x.name for x in snapshot.iterdir()) != sorted(gen) or any(sha256_file(snapshot / n) != h for n, h in gen.items()):
            raise Gen3Error(f'{snapshot}: the copied H1 code differs from SHA256SUMS')
    except BaseException:
        shutil.rmtree(snapshot, ignore_errors=True)
        raise
    return dict(passed=True, tree=str(tree), pin=pin, snapshot=str(snapshot), files_authenticated=len(code), snapshot_files=len(gen),
                verifier_sha256=code['src/gen/verify_inventory.py'])


def h1_snapshot_unchanged(snapshot, tree, pin: str) -> dict:
    """An existing snapshot (h1_code_snapshot's) still holds exactly the authenticated src/gen/ files."""
    code = h1_code_hashes(tree, pin)
    gen = {k[len('src/gen/'):]: h for k, h in code.items() if k.startswith('src/gen/') and '/' not in k[len('src/gen/'):]}
    snapshot = Path(snapshot)
    names = sorted(x.name for x in snapshot.iterdir()) if snapshot.is_dir() and not snapshot.is_symlink() else None
    bad = [n for n in gen if names is not None and n in names and ((snapshot / n).is_symlink() or sha256_file(snapshot / n) != gen[n])]
    if names != sorted(gen) or bad:
        raise Gen3Error(f'{snapshot}: not the authenticated H1 code snapshot (entries {names if names is None else len(names)}, '
                        f'expected {len(gen)}; differing {bad[:5]})')
    return dict(passed=True, snapshot=str(snapshot), snapshot_files=len(gen))


# ---- hashes and JSON ---------------------------------------------------------------------------------------------
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def md5_file(p) -> str:
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, obj, what: str = 'record') -> None:
    """Write JSON through a temporary sibling and one rename (refusing C62d's trees)."""
    path = refuse_c62d(path, what)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f'.{path.name}.tmp.{os.getpid()}')
    tmp.write_text(json.dumps(obj, indent=1, sort_keys=False) + '\n')
    os.replace(tmp, path)


# ---- the H1 gate records and the gate-1(a) platform rule -------------------------------------------------------
# J-GEN-D3 writes, into its gates directory, one gate record "<gate>.json" per H1 gate (schema c8-d3-gate-1, with
# "passed") and the gate's supporting records: the gate tools' own outputs (each with "passed") and H1's raw
# check_edge_forests outputs (schema {L, graphs, failures, seconds, rows}, no "passed": gate 3's record is their
# verdict). publish_d3.py publishes all of them under d3_payload/gates/ (A.2 step 5) and the four builder side files
# of A.2 step 2a under d3_payload/gates/gate5/.
H1_GATES = ('gate1b', 'gate2', 'gate3', 'gate4', 'gate5', 'gate7', 'determinism')
GATE_SUPPORT = {'gate2': ('gate2_opcount.json', 'gate2_weights.json'),
                'gate3': ('gate3_edge_forests_L7.json', 'gate3_edge_forests_L8.json'),
                'gate4': ('gate4_kirchhoff.json',),
                'gate5': ('gate5_forest_check.json',),
                'gate7': ('gate7_check_dimension8.json',)}
SIDE_STEMS = ('L7_free', 'L7_power', 'L8_free', 'L8_power')
SIDE_DIR = 'gates/gate5'   # in d3_payload/: <stem>.subgraphs.txt


def side_file(stem: str) -> str:
    return f'{stem}.subgraphs.txt'


def expanse_run(env: dict) -> tuple[bool, list[str]]:
    """Gate 1(a) counts for A-INV-2(a) only on Expanse x86-64 (PLAN A.3 1(a)): the environment record of the run must
    say machine x86_64, a numeric Slurm job id and C8_SITE=expanse (set by the site's env.sh). Anything else is a
    rehearsal. Returns (qualifies, the reasons it does not)."""
    why = []
    if env.get('machine') != 'x86_64':
        why.append(f'machine {env.get("machine")!r} is not x86_64')
    if not re.fullmatch(r'[1-9][0-9]*', str(env.get('slurm_job_id') or '')):
        why.append(f'SLURM_JOB_ID {env.get("slurm_job_id")!r} is not a Slurm job id')
    if env.get('site') != 'expanse':
        why.append(f'C8_SITE {env.get("site")!r} is not expanse')
    return not why, why


# ---- G-files -----------------------------------------------------------------------------------------------------
INT_RE = re.compile(r'0|-?[1-9][0-9]*')
UINT_RE = re.compile(r'0|[1-9][0-9]*')
NUM_RE = re.compile(r'[-+]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][-+]?[0-9]+)?')


@dataclass
class GFile:
    magic: str
    L: int
    id: int
    wa: str
    wb: str
    M: int
    T: int
    masks: list = field(default_factory=list)
    terms: list = field(default_factory=list)      # [(indices, coefficients)]
    rates: list = field(default_factory=list)      # the rate tokens as text

    @property
    def E(self) -> int:
        return 2 * self.L


def parse_gfile(data: bytes, path: str = '<G-file>') -> GFile:
    """Strict parser with regenerate_rates.cpp's rules; raises Gen3Error('<path>: <field> <reason>')."""
    try:
        toks = data.decode('ascii').split()
    except UnicodeDecodeError:
        raise Gen3Error(f'{path}: not ASCII')
    pos = [0]

    def tok(fld):
        if pos[0] >= len(toks):
            raise Gen3Error(f'{path}: truncated or malformed {fld} (end of file)')
        pos[0] += 1
        return toks[pos[0] - 1]

    def integer(fld, lo, hi, neg=True):
        s = tok(fld)
        if not (INT_RE.fullmatch(s) if neg else UINT_RE.fullmatch(s)):
            raise Gen3Error(f'{path}: truncated or malformed {fld} {s[:40]!r}')
        v = int(s)
        if not lo <= v <= hi:
            raise Gen3Error(f'{path}: {fld} {v} out of range [{lo},{hi}]')
        return v

    def number(fld):
        s = tok(fld)
        if not NUM_RE.fullmatch(s) or s.lower().lstrip('+-') in ('inf', 'nan') or not _finite(s):
            raise Gen3Error(f'{path}: {fld} {s[:40]!r} is not a finite decimal number')
        return s

    magic = tok('magic')
    if magic not in MAGICS:
        raise Gen3Error(f'{path}: magic {magic[:40]!r} unknown')
    L = integer('L', 2, 8)
    E, ALL = 2 * L, (1 << (2 * L)) - 1
    s = tok('id')
    if not UINT_RE.fullmatch(s) or int(s) >= 1 << 64:
        raise Gen3Error(f'{path}: id {s[:40]!r} is not a non-negative integer')
    gid = int(s)
    wa, wb = number('wa'), number('wb')
    M, T = integer('M', 1, 16384), integer('T', 1, 10000)
    masks = []
    for k in range(M):
        v = integer(f'mask {k}', 0, ALL, neg=False)
        if bin(v).count('1') != L:
            raise Gen3Error(f'{path}: mask {k} {v} has popcount {bin(v).count("1")}, expected L = {L}')
        if masks and v <= masks[-1]:
            raise Gen3Error(f'{path}: mask {k} {v} is not above the previous mask')
        masks.append(v)
    terms = []
    for i in range(T):
        n = integer(f'term {i} length', 1, M)
        idx = []
        for j in range(n):
            v = integer(f'term {i} index {j}', 0, M - 1)
            if idx and v <= idx[-1]:
                raise Gen3Error(f'{path}: term {i} index {j} {v} is not above the previous index')
            idx.append(v)
        co = [integer(f'term {i} coefficient {j}', -2**31, 2**31 - 1) for j in range(E)]
        terms.append((idx, co))
    integer('rate count', ALL + 1, ALL + 1)
    rates = [number(f'rate {s}') for s in range(ALL + 1)]
    if pos[0] != len(toks):
        raise Gen3Error(f'{path}: trailing data {toks[pos[0]][:40]!r} after the rate list')
    return GFile(magic, L, gid, wa, wb, M, T, masks, terms, rates)


def _finite(s: str) -> bool:
    try:
        return abs(float(s)) != float('inf')
    except (ValueError, OverflowError):
        return False


def gfile_lines(data: bytes) -> list[bytes]:
    """The lines of a G-file (split at LF, the final LF required)."""
    if not data.endswith(b'\n'):
        raise Gen3Error('no final newline')
    return data[:-1].split(b'\n')


def same_body(d2: bytes, d3: bytes) -> bool:
    """check_dimension8 (i): the d=3 file equals the d=2 file except the magic and the last line (the rate line)."""
    a, b = gfile_lines(d2), gfile_lines(d3)
    if len(a) != len(b) or len(a) < 4:
        return False
    if not (a[0].startswith(b'C7D2GRAPH1 ') and b[0].startswith(b'C7D3GRAPH1 ')):
        return False
    return a[0][len(b'C7D2GRAPH1'):] == b[0][len(b'C7D3GRAPH1'):] and a[1:-1] == b[1:-1]


def d3_rates(g: GFile) -> tuple[list[int], list[int]]:
    """regenerate_rates.cpp's formula in pure Python: (lifted rates in quarters, raw p4) for every subset s
    (entries 0 and 2^E-1 unused). p4 = 3|s| + 4 nu_N - 6 h per forest term; h from the Hamming distance of the
    complement of s to the term's nearest monomial mask; a non-positive p4 is lifted into (0, 4]; minimum over terms."""
    L, E = g.L, g.E
    ALL = (1 << E) - 1
    pc = [bin(s).count('1') for s in range(ALL + 1)]
    positive = [1000] * (ALL + 1)
    raw = [1000] * (ALL + 1)
    for idx, co in g.terms:
        dist = [100] * (ALL + 1)
        for m in idx:
            dist[g.masks[m]] = 0
        bit = 1
        while bit <= ALL:
            for base in range(0, ALL + 1, 2 * bit):
                for j in range(bit):
                    s, t = base + j, base + j + bit
                    x, y = dist[s], dist[t]
                    dist[s], dist[t] = min(x, y + 1), min(y, x + 1)
            bit <<= 1
        supp = 0
        for j in range(E):
            if co[j]:
                supp |= 1 << j
        for s in range(1, ALL):
            h = (L - E + pc[s] + dist[ALL ^ s]) // 2     # the C++ division truncates; the operand is never negative
            nu = 0 if supp & ~s else 1
            p4 = 3 * pc[s] + 4 * nu - 6 * h
            raw[s] = min(raw[s], p4)
            if p4 <= 0:
                p4 = p4 % 4 or 4
            positive[s] = min(positive[s], p4)
    return positive, raw


def quarter_text(q: int) -> str:
    """How regenerate_rates prints q * 0.25L with setprecision(22): exact quarters, shortest decimal."""
    whole, frac = divmod(q, 4)
    return str(whole) + ('', '.25', '.5', '.75')[frac]


def d3_rate_line(g: GFile) -> bytes:
    """The d=3 rate line regenerate_rates writes (with its trailing space), from d3_rates."""
    positive, _ = d3_rates(g)
    ALL = (1 << g.E) - 1
    return ''.join(('0 ' if s in (0, ALL) else quarter_text(positive[s]) + ' ') for s in range(ALL + 1)).encode()
