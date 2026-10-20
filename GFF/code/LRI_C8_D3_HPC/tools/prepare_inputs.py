#!/usr/bin/env python3
"""The C8(3) inputs (PLAN.md component B, HD3, HD4, HD7, A.2 step 6): `make inputs` builds them, verify() checks them.

build (`make inputs` = tools/prepare_inputs.py build [--out DIR]):
  * inputs/two_loop.json (7 B2 strings, order 8) and inputs/gamma_d3_8.txt are byte copies of the vendored
    vendor/c8_assembly/inputs_d3/ files (HD4). They are read only after the HANDOFF copy has matched its pin
    (f5ff6a35..., tools/VENDORED.json) and every vendored file the sha256 the HANDOFF records. Then the vendored
    prepare_low8.py --d 3 runs in compare mode as a separate process with LRI_ROOT = vendor/c8_assembly_fixtures; it
    writes nothing, and exit 0 with all three files "identical" is required. Nothing here imports a vendored module.
  * inputs/order7/{two_loop.json,gamma_d3_7.txt}: byte copies of C7(3)'s order-7 files (reference/inputs/, the bytes
    LRI_C7_D3_HPC@a6ce987 kept in inputs/; sha256 3dddb802..., d5008ca0...).
  * inputs/packs/{free,power}_L{3..6}.pack: the C7(3) members reference/inputs/<sector>/L<L>/G<id>.txt, with ids and
    primitive flags from reference/inputs/inventory.json, ascending id within (sector, L); every pack has the sha256 of
    a6ce987's inputs/manifest.json.
  * inputs/packs/{free,power}_L7.pack: before Stage 2b (Stage 2a state) C7(3)'s 2,298 + 590 kernels only, byte-identical
    to a6ce987 (l7_complete false). From Stage 2b on, every L7 kernel of H1's selection.json, 2,441 + 709: the C7(3)
    members from reference/inputs/ (their sha256 equal to C7(3)'s rows and to MEMBERS_d3.sha256: gate 6) and the
    143 + 119 s_G = 4 kernels from the d=3 payload (each at its MEMBERS_d3.sha256 hash).
  * inputs/packs/{free,power}_L8.pack (Stage 2b; not in git, pinned in the manifest): the 16,064 + 4,336 L8 kernels of
    selection.json from the d=3 payload, ascending id. `make inputs-l8` writes them into the content-addressed store
    $C8_STORE/packs/<sha256>.pack (read-only, never overwritten) and hard-links them into inputs/packs/ (HD3);
    `make link-l8 STORE=...` links them into another package export. A plain `make inputs` never writes them: with the
    packs present it re-derives the L8 rows from them (each member against MEMBERS_d3.sha256, the pack against its
    pin); without them (the Mac) it carries the committed L8 rows forward after checking each row's sha256, id,
    primitive flag and double_lift against MEMBERS_d3.sha256, selection.json and rate_audit_L8.json.
  * The Stage-2b small files (byte copies, committed; their chain ends at the two external pins): selection.json (H1's,
    PLAN B), h1/MANIFEST.json and h1/SHA256SUMS (H1 MANIFEST -> SHA256SUMS -> selection.json), and d3/MANIFEST_d3.json,
    d3/SHA256SUMS, d3/MEMBERS_d3.sha256, d3/rate_audit_L{7,8}.json (MANIFEST_d3 -> SHA256SUMS -> the members list and
    the rate audits). `make inputs-l8` copies them from the payload and from the H1 copy; later builds read the
    package's copies. Their chain is re-checked by every build and by verify().
  * inputs/inventory.json: "inspect_complete" and, per sector and loop, one row per kernel (ROW_FIELDS):
      id, primitive                   from reference/inputs/inventory.json (C7(3) kernels) or selection.json (L7, L8);
      s_G, wa, wb                     wa and wb are the payload header's tokens (text, as the worker reads them);
                                      s_G = 12 wb / wa, an integer (w_B = w_A s_G / 12; s_G = 4 <=> 3 w_B = w_A);
      offset, length, sha256          the member's place in its pack and its sha256;
      monomials, terms, cost          M and T of the header, cost = max(1, M T);
      products, segments, addends, numerators, kernel_bytes, fmax
                                      the inspect fields, from inspect/inspect.json (`make inputs-inspect`:
                                      bin/c8d3_inspect and gen3's size probe, tools/inspect_inputs.py; L <= 7 in
                                      Stage 3a, L8 in Stage 2b) for every row whose member sha256 it records; null for
                                      a row it does not list (a listed row with another sha256 is refused as stale);
                                      inspect_complete is true when every row has them;
      double_lift                     the number of subsets 0 < s < 2^E - 1 whose raw d=3 valuation p4 is <= -5
                                      (regenerate_rates.cpp's double_lift_subsets; the d=3 double lift is raw -6):
                                      computed here (numpy) at L <= 7, and equal there to rate_audit_L7.json's count
                                      for every L7 kernel; taken from rate_audit_L8.json at L8.
  * inputs/manifest.json (schema c8-d3-hpc-inputs-1), written last: the sha256 of every input file (the L8 packs
    included), the counts, l7_complete, l8_present, inspect_complete, the H1 and d3 pins (copies of the external pins:
    HANDOFF_inventory8_d2.json's and the A.5 gate record's; null before Stage 2b), the vendored pins copied from
    tools/VENDORED.json, the prepare_low8 comparison and reference_manifest_sha256.
  Every output is deterministic. The files are built in a staging directory and moved into place one by one, the
  manifest last; files whose bytes are unchanged are left alone. tests/check_inputs.py rebuilds into a scratch
  directory and compares byte for byte.

l8 (`make inputs-l8 D3PAYLOAD=<d3_payload tree> D3PIN=<sha256 of MANIFEST_d3.json> STORE=$C8_STORE [H1=<H1 copy>]
  [GATE_RECORD=<A.5 gate record>]`; Stage 2b, J-IN-1): refuses without D3PIN (the Makefile, then this tool); checks the
  pin against the gate record when one is given; runs gen3/verify_d3.py TREE --pin D3PIN (A.2 step 6: the four steps)
  before reading any member, and refuses unless it passes; then builds the Stage-2b inputs from the payload (members by
  tar offset) and from the H1 copy ($C8_STORE/h1/<H1 sha12>/ by default: selection.json through H1's MANIFEST ->
  SHA256SUMS), the L8 packs into the store. The manifest carries D3PIN as a copy, never as the authority.
link-l8 (`make link-l8 STORE=$C8_STORE`): hard-links the store's L8 packs named by inputs/manifest.json's pins into
  inputs/packs/ (a copy on another filesystem); never overwrites a different file. verify() then hashes them.
mini (`make inputs-mini`, after `make inputs-inspect`; needs the L8 packs): tests/fixtures/inputs_mini/, the 8
  smallest L8 kernels per sector (by bytes, then id; each at its inventory and MEMBERS_d3.sha256 hash) in their own
  packs, an inventory with the package's L3-L7 rows and those L8 rows, and a manifest pinning the package's other
  inputs (`package_files`). materialize_mini(DEST) (tools/members.py mini) assembles a C8_INPUTS directory from it:
  its own files copied, the package files hard-linked; verify() accepts it, and any plan on it is test-only. Both
  refuse an --out / DEST overlapping the package inputs/ (equal, inside or containing; symlinks resolved) before
  anything is read or written (S4-003), the default --out included, and so every path they write below it (each
  directory on the way, each file): one overlapping the package inputs/ or existing as a symbolic link is refused before
  anything is written (R2-S1-05). mini builds its files in a fresh private directory under --out and moves each into
  place (a rename replaces the entry: nothing is written through an existing file or link); materialize_mini needs a
  fresh DEST (absent or an empty directory) and creates every file exclusively.

verify(inputs=None) (what `plan` calls first; tools/prepare_inputs.py verify [--inputs DIR]): the manifest's schema,
  dimension and order (a C7(3) manifest and a dimension-2 manifest are refused, HD7); every file it pins, by sha256;
  with the d3 pin set, the chain of the Stage-2b small files to the manifest's H1 and d3 pins; the vendored HANDOFF copy
  and the 13 vendored files at the manifest's pins, which must equal tools/VENDORED.json. Missing L8 packs are skipped
  only with C8_ALLOW_NO_L8=1, printing SKIPPED. It writes nothing. A failure raises InputsError naming the file. A
  manifest carrying a test_inputs marker (inputs_mini) adds a test-only reason wherever the tree lies (S4-003).
plan_inputs(test_only) (the plan's input gate; tools/prepare_inputs.py gate [--test-only]): C8_INPUTS selects an
  inputs directory (default: the package's inputs/); a non-test plan with any other C8_INPUTS is refused before
  anything is read. Then verify(). The plan is test-only if it was asked to be, or if l7_complete or l8_present is
  false, or an L8 pack was skipped, or C8_INPUTS is foreign, or the manifest has test_inputs; the reasons are
  returned. A plan that stays non-test then needs inventory_complete(): the inventory holds exactly H1's selection.json
  (L7, L8; H1's own pin), C7(3)'s L3-L6 kernels (each graph id once), and the manifest's counts, else it is refused
  (S4-003, R2-S1-03). A manifest with a "synthetic" entry makes the plan test-only (R2-S1-02): its contents never lift
  that. Only the test seam C8_TEST_SYNTHETIC_INPUTS=1, honoured under C8_SITE=fake on a host that is no real site (and
  refused elsewhere), lets a non-test plan use tests/c8pkg.py's synthetic scratch inputs (SYNTHETIC_INPUTS_LABEL exactly,
  neither pin), the skipped check recorded in the result ("inventory_complete": {"skipped": ...}).
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from fractions import Fraction
from pathlib import Path

from common import ROOT, digest, verified_bytes

SCHEMA = 'c8-d3-hpc-inputs-1'
C7_SCHEMA = 'c7-d3-hpc-inputs-1'
HANDOFF_SHA256 = 'f5ff6a353371abdc22a296d106e83af03885dfa672a25662fa59f468b9948437'   # PLAN F11, HD4
VENDOR = 'vendor/c8_assembly'
FIXTURES = 'vendor/c8_assembly_fixtures'
LOW_LOOP = ('two_loop.json', 'gamma_d3_8.txt')
# C7(3)'s order-7 files (LRI_C7_D3_HPC@a6ce987 inputs/ = reference/inputs/; PLAN HD4).
ORDER7 = {'two_loop.json': '3dddb80233989e2397ede19d575a80437297d3d59c70e444a67daf3a0df34aca',
          'gamma_d3_7.txt': 'd5008ca0c882f34bffc2e7713b7ed8ed9a2cdeda940ecd4f8c5b715fb43522c0'}
# reference/inputs/inventory.json (the delivered C7(3) inventory: ids and primitive flags)
REFERENCE_INVENTORY_SHA256 = 'acf5e3ddc88aeea703a5b9902dab2c082341707d7744f3630903d36d624e5160'
SECTORS = ('free', 'power')
LOOPS = (3, 4, 5, 6, 7)   # Stage 2a; L8 by `make inputs-l8` (Stage 2b)
# The packs of LRI_C7_D3_HPC@a6ce987 inputs/manifest.json (PLAN B: L3-L6 byte-identical; before Stage 2b L7 too).
C7D3_PACK_SHA256 = {
    'packs/free_L3.pack': 'f0dc01c18bc84db965d1c8a81ffe100a4e6bd1687ca9764586b12d14cae2dabf',
    'packs/free_L4.pack': 'd22ea31e92b871f7820af8a7b8930f5389d3a003eadc59c42e42b74238d1ee03',
    'packs/free_L5.pack': '2337d0a7a6817ad37501def832f33d5a556e78454476ac8186d5d7c9f3eb8144',
    'packs/free_L6.pack': '2c040a402e0d4ab4c0b6df1482d5fc5fa0ae7b59734cef09e2c7e19b6d8fe4a1',
    'packs/free_L7.pack': '9e7f0e8f19e170a1af3d0dbd419a871841b2068e73c8fc11d8b6681bacd06c5b',
    'packs/power_L3.pack': '2f6a20a7e7d35518c0b1456ff6db1201d7755c117715725e9f5ee84d93880c07',
    'packs/power_L4.pack': '8126070b748a9e4d05bd1bac7038495e0889925848c31754d0f68cd6edd6c730',
    'packs/power_L5.pack': '9a03834a137819f9270f4f6cdbb436656839be17414d17cb4fcf5ae198c0650c',
    'packs/power_L6.pack': '3ae3e5e43df4d1b4bafb904513899a2408da6a77fc87872a31b3a2784b3f5d6a',
    'packs/power_L7.pack': '965c65fc8435d7e3a3f58599d824dae4c763fc51a20e211c6aa78887306dbaf9',
}
C7D3_COUNTS = {'free': {3: 5, 4: 16, 5: 76, 6: 395, 7: 2298}, 'power': {3: 1, 4: 3, 5: 20, 6: 107, 7: 590}}
L8_PACKS = ('packs/free_L8.pack', 'packs/power_L8.pack')
INSPECT_FIELDS = ('products', 'segments', 'addends', 'numerators', 'kernel_bytes', 'fmax')
ROW_FIELDS = ('id', 'primitive', 's_G', 'wa', 'wb', 'offset', 'length', 'sha256', 'monomials', 'terms', 'cost',
              *INSPECT_FIELDS, 'double_lift')
INSPECT_DATA = 'inspect/inspect.json'   # make inputs-inspect (tools/inspect_inputs.py); a source of `make inputs`
INSPECT_SCHEMA = 'c8-d3-inspect-data-1'
DOUBLE_LIFT_RAW = -5   # raw p4 <= -5 (regenerate_rates.cpp; the d=3 double lift is raw -6, RECON:1346-1350)
# Stage 2b (PLAN B, A.2 step 6). H1's MANIFEST.json pin (HANDOFF_inventory8_d2.json, DECISIONS A3; both sessions pin it).
H1_MANIFEST_SHA256 = '46341a3c0f11d74f0cf7c08cdd685d9cf073a142160de5a0ca408e021b4ff099'
D3_SCHEMA = 'c8-d3-d3-payload-1'
SELECTION_SCHEMA = 'c8-inventory-d2-selection-1'
SELECTION = 'selection.json'
# inputs/<copy> -> the file of the H1 tree / of the d3_payload tree (byte copies; the chains end at the two pins)
H1_COPIES = {'h1/MANIFEST.json': 'MANIFEST.json', 'h1/SHA256SUMS': 'SHA256SUMS', SELECTION: 'selection.json'}
D3_COPIES = {'d3/MANIFEST_d3.json': 'MANIFEST_d3.json', 'd3/SHA256SUMS': 'SHA256SUMS',
             'd3/MEMBERS_d3.sha256': 'MEMBERS_d3.sha256', 'd3/rate_audit_L7.json': 'rate_audit_L7.json',
             'd3/rate_audit_L8.json': 'rate_audit_L8.json'}
STAGE2B_FILES = (*H1_COPIES, *D3_COPIES)
LOOPS_2B = (3, 4, 5, 6, 7, 8)
STAGE2B_COUNTS = {'free': {7: 2441, 8: 16064}, 'power': {7: 709, 8: 4336}}   # H1 selection.json (A-IN-3)
STAGE2B_PRIMITIVES = {7: 44, 8: 248}
STORE_PACKS = 'packs'   # $C8_STORE/packs/<sha256>.pack: the content-addressed, read-only L8 pack store (HD3)
MINI = 'tests/fixtures/inputs_mini'
MINI_LABEL = ('inputs_mini (PLAN B, tests only): the 8 smallest real L8 kernels per sector of the d=3 payload in their '
              'own packs; every other input is the package\'s (package_files, hard-linked by materialize_mini); select '
              'it with C8_INPUTS (any plan on it is test-only)')
MINI_PER_SECTOR = 8
# tests/c8pkg.py's scratch packages: SYNTHETIC complete inputs (no H1 or d3 pin) on which NON-test plans must stay
# possible in the Mac fakes; a manifest with a "synthetic" entry makes any plan test-only unless the test seam
# SYNTHETIC_SEAM is honoured (plan_inputs; R2-S1-02): only then do this label and neither pin skip inventory_complete
SYNTHETIC_INPUTS_LABEL = 'SYNTHETIC test inputs (tests/c8pkg.py): not physics data'
SYNTHETIC_SEAM = 'C8_TEST_SYNTHETIC_INPUTS'
SUMS_ROW = re.compile(r'([0-9a-f]{64})  (\S.*)')
SHA_RE = re.compile(r'[0-9a-f]{64}')
GFILE_NAME = re.compile(r'L([78])_(free|power)/G(0|[1-9][0-9]*)\.txt')


class InputsError(ValueError):
    """A refused or failed input build or check; the message names the file."""


# ---- the vendored HANDOFF (HD4) ----------------------------------------------------------------------------------
def vendored_pins() -> dict:
    """The HANDOFF copy at its pin and every vendored file at the sha256 the HANDOFF records, equal to
    tools/VENDORED.json. Vendored bytes are opened only through common.digest and common.verified_bytes."""
    v = json.loads((ROOT / 'tools/VENDORED.json').read_bytes())
    if v['handoff']['sha256'] != HANDOFF_SHA256 or v['handoff']['path'] != f'{VENDOR}/HANDOFF_assembly.json':
        raise InputsError(f'tools/VENDORED.json: HANDOFF pin {v["handoff"]["sha256"]} is not {HANDOFF_SHA256} (HD4)')
    try:
        handoff = json.loads(verified_bytes(ROOT / VENDOR / 'HANDOFF_assembly.json', HANDOFF_SHA256))
    except (OSError, ValueError) as e:
        raise InputsError(f'{VENDOR}/HANDOFF_assembly.json: not the HANDOFF at {HANDOFF_SHA256} ({e})') from None
    listed = {f['path']: f['sha256'] for f in handoff['files']}
    recorded = {f['path']: f for f in v['files']}
    if set(recorded) != set(listed) or any((recorded[n]['sha256'], recorded[n]['vendored_path'])
                                           != (listed[n], f'{VENDOR}/{n}') for n in listed):
        raise InputsError('tools/VENDORED.json: the vendored file pins differ from the HANDOFF')
    files = {}
    for n, sha in listed.items():
        p = ROOT / VENDOR / n
        if p.is_symlink() or not p.is_file() or digest(p) != sha:
            raise InputsError(f'Checksum mismatch: {VENDOR}/{n} is not the vendored file at {sha} '
                              f'(HANDOFF {HANDOFF_SHA256[:12]})')
        files[f'{VENDOR}/{n}'] = sha
    return {'handoff_sha256': HANDOFF_SHA256, 'files': files}


def low8_compare() -> dict:
    """The vendored prepare_low8.py --d 3 in compare mode, as a separate process (HD4): exit 0 and all three files
    identical. LRI_ROOT is the fixture tree; PYTHONPYCACHEPREFIX is unset and no bytecode is written (H2 run rules)."""
    env = {k: x for k, x in os.environ.items() if k not in ('PYTHONPYCACHEPREFIX', 'PYTHONPATH', 'PYTHONSTARTUP')}
    env.update(LRI_ROOT=str(ROOT / FIXTURES), PYTHONDONTWRITEBYTECODE='1')
    with tempfile.TemporaryDirectory(prefix='c8d3_low8_') as td:
        cp = subprocess.run([sys.executable, '-B', str(ROOT / VENDOR / 'prepare_low8.py'), '--d', '3'], cwd=td,
                            env=env, capture_output=True, text=True)
    lines = cp.stdout.splitlines()
    states = {}
    for ln in lines:
        parts = ln.split()
        if len(parts) >= 3 and parts[0] == 'd=3' and parts[1].endswith(':'):
            states[parts[1][:-1]] = parts[2]
    want = {'two_loop.json': 'identical', 'gamma_d3_8.txt': 'identical', 'checks.json': 'identical'}
    if cp.returncode != 0 or states != want:
        raise InputsError(f'{VENDOR}/prepare_low8.py --d 3 (compare mode) exited {cp.returncode} with {states}; '
                          f'expected exit 0 and {want}: {(cp.stdout + cp.stderr)[-800:]}')
    return {'command': f'python3 -B {VENDOR}/prepare_low8.py --d 3', 'LRI_ROOT': FIXTURES, 'exit_status': 0,
            'files': states}


# ---- payloads ----------------------------------------------------------------------------------------------------
class Member:
    """A d=3 G-file (C7D3GRAPH1): header, masks and forest terms, with the structural checks of
    gen3/regenerate_rates.cpp's reader (the rate line is counted, not parsed)."""

    def __init__(self, data: bytes, where: str):
        def bad(msg):
            raise InputsError(f'{where}: {msg}')
        if not data.endswith(b'\n'):
            bad('no final newline')
        lines = data[:-1].split(b'\n')
        h = lines[0].split()
        if len(h) != 7:
            bad(f'header has {len(h)} tokens, expected 7')
        try:
            self.magic = h[0].decode('ascii')
            self.L, self.id, self.M, self.T = int(h[1]), int(h[2]), int(h[5]), int(h[6])
            self.wa, self.wb = h[3].decode('ascii'), h[4].decode('ascii')
            if not (2 <= self.L <= 8 and self.id >= 0 and 1 <= self.M <= 16384 and 1 <= self.T <= 10000):
                bad('header out of range')
            E = 2 * self.L
            if len(lines) != self.T + 4:
                bad(f'{len(lines)} lines, expected T + 4 = {self.T + 4}')
            self.masks = [int(x) for x in lines[1].split()]
            if len(self.masks) != self.M or any(not 0 <= m < 1 << E or m.bit_count() != self.L for m in self.masks) \
                    or any(a >= b for a, b in zip(self.masks, self.masks[1:])):
                bad('masks: not M strictly increasing masks of popcount L below 2^E')
            self.terms = []
            for i, ln in enumerate(lines[2:2 + self.T]):
                t = [int(x) for x in ln.split()]
                n = t[0] if t else 0
                idx, co = t[1:1 + n], t[1 + n:]
                if not 1 <= n <= self.M or len(co) != E or any(not 0 <= j < self.M for j in idx) \
                        or any(a >= b for a, b in zip(idx, idx[1:])):
                    bad(f'term {i} malformed')
                self.terms.append((idx, co))
            if int(lines[2 + self.T]) != 1 << E or len(lines[3 + self.T].split()) != 1 << E:
                bad('rate block is not 2^E rates')
        except (ValueError, UnicodeDecodeError) as e:
            bad(f'malformed ({e})')


def s_g(wa: str, wb: str, where: str) -> int:
    """s_G = 12 w_B / w_A from the header's weight tokens (w_B = w_A s_G / 12, PLAN A.3 gate 2(b)); the tokens carry
    22 significant digits, so the ratio is an integer to far better than 1e-12."""
    fa, fb = Fraction(wa), Fraction(wb)
    if fa <= 0 or fb < 0:
        raise InputsError(f'{where}: weights wa={wa} wb={wb} out of range')
    x = 12 * fb / fa
    s = round(x)
    if abs(x - s) > Fraction(1, 10 ** 12):
        raise InputsError(f'{where}: 12 wb / wa = {float(x)!r} is not an integer (s_G)')
    return int(s)


def raw_valuations(L: int, masks: list, terms: list):
    """regenerate_rates.cpp's raw d=3 valuation, raw(s) = min over forest terms of p4 = 3|s| + 4 nu_N - 6 h, for
    s = 1 .. 2^E - 2 (numpy int16 array). h = (L - E + |s| + d)/2 with d the Hamming distance of the complement of s
    to the term's nearest monomial mask; d and |s| + L have the same parity (every mask has popcount L), so
    p4 = 3L - 3d + 4 nu_N exactly, nu_N = 1 when the term's support (its non-zero coefficients) lies inside s.
    The distance table is regenerate_rates' E-pass transform over the hypercube, done with vectorized passes (the
    low half of the bits on a transposed copy, so every pass works on long contiguous runs). tests/check_inputs.py
    compares it with gen3/g3common.d3_rates, the line-by-line pure-Python port."""
    import numpy as np
    E = 2 * L
    N = 1 << E
    ALL = N - 1
    T = len(terms)
    dist = np.full((T, N), 100, dtype=np.int8)
    marr = np.asarray(masks, dtype=np.int64)
    supp = []
    for t, (idx, co) in enumerate(terms):
        dist[t, marr[idx]] = 0
        supp.append(sum(1 << j for j, c in enumerate(co) if c))

    def sweep(a, bit):
        step = 1 << bit
        v = a.reshape(T, N // (2 * step), 2, step)
        x, y = v[:, :, 0, :], v[:, :, 1, :]
        np.minimum(y, x + 1, out=y)   # min(x, y_new + 1) == min(x, y_old + 1), so the in-place order is exact
        np.minimum(x, y + 1, out=x)
    K = E // 2
    for bit in range(K, E):
        sweep(dist, bit)
    a = np.ascontiguousarray(dist.reshape(T, N >> K, 1 << K).transpose(0, 2, 1)).reshape(T, N)
    for bit in range(E - K, E):   # the low K bits of s, now the top K bits of the index
        sweep(a, bit)
    dist = np.ascontiguousarray(a.reshape(T, 1 << K, N >> K).transpose(0, 2, 1)).reshape(T, N)
    s = np.arange(1, ALL, dtype=np.int64)
    comp = dist[:, ALL - 1:0:-1]   # d(ALL ^ s) for s = 1 .. ALL - 1
    best = None
    for u in sorted(set(supp)):   # terms with one support u share nu_N: min_t(4 nu - 3 d_t) = 4 nu - 3 max_t d_t
        rows = [t for t in range(T) if supp[t] == u]
        val = 4 * ((u & (ALL ^ s)) == 0).astype(np.int16) - 3 * comp[rows].max(axis=0).astype(np.int16)
        best = val if best is None else np.minimum(best, val)
    return (3 * L + best).astype(np.int16)


def inspect_data() -> tuple[dict, dict | None]:
    """{(sector, L, id): (sha256, {field: value})} from inspect/inspect.json, and its provenance; ({}, None) if absent."""
    p = ROOT / INSPECT_DATA
    if not p.exists():
        return {}, None
    data = p.read_bytes()
    try:
        d = json.loads(data)
    except ValueError as e:
        raise InputsError(f'{INSPECT_DATA}: not JSON ({e})') from None
    if d.get('schema') != INSPECT_SCHEMA or d.get('fields') != ['id', 'sha256', *INSPECT_FIELDS]:
        raise InputsError(f'{INSPECT_DATA}: schema {d.get("schema")!r} or fields {d.get("fields")!r} are not '
                          f'{INSPECT_SCHEMA} with id, sha256 and {", ".join(INSPECT_FIELDS)}')
    rows = {}
    for s, loops in d['rows'].items():
        for L, rs in loops.items():
            for r in rs:
                if (len(r) != 2 + len(INSPECT_FIELDS) or not isinstance(r[0], int) or not isinstance(r[1], str)
                        or len(r[1]) != 64 or not all(isinstance(x, int) and x >= 0 for x in r[2:])):
                    raise InputsError(f'{INSPECT_DATA}: malformed row {r!r} ({s} L{L})')
                rows[(s, int(L), r[0])] = (r[1], dict(zip(INSPECT_FIELDS, r[2:])))
    prov = {'path': INSPECT_DATA, 'sha256': hashlib.sha256(data).hexdigest(), 'rows': len(rows),
            'inspector_sha256': d.get('inspector', {}).get('executable_sha256'),
            'fmax': (d.get('fmax_source') or {}).get('definition')}
    return rows, prov


def light_member(data: bytes, where: str) -> tuple:
    """The structural checks that size an L8 member (its header, T + 4 lines, M masks, a rate block of 2^E rates),
    without parsing every term (the inspector reads each member with the worker's own reader, `make inputs-inspect`,
    and regenerate_rates' checked reader wrote them, A.1). Returns (magic, L, id, wa, wb, M, T)."""
    if not data.endswith(b'\n'):
        raise InputsError(f'{where}: no final newline')
    lines = data[:-1].split(b'\n')
    h = lines[0].split()
    if len(h) != 7:
        raise InputsError(f'{where}: header has {len(h)} tokens, expected 7')
    try:
        magic, wa, wb = h[0].decode('ascii'), h[3].decode('ascii'), h[4].decode('ascii')
        L, gid, M, T = int(h[1]), int(h[2]), int(h[5]), int(h[6])
    except (ValueError, UnicodeDecodeError) as e:
        raise InputsError(f'{where}: malformed header ({e})') from None
    if not (2 <= L <= 8 and gid >= 0 and 1 <= M <= 16384 and 1 <= T <= 10000):
        raise InputsError(f'{where}: header out of range')
    if len(lines) != T + 4:
        raise InputsError(f'{where}: {len(lines)} lines, expected T + 4 = {T + 4}')
    if len(lines[1].split()) != M:
        raise InputsError(f'{where}: the mask line does not hold M = {M} masks')
    if lines[2 + T].strip() != str(1 << 2 * L).encode() or len(lines[3 + T].split()) != 1 << 2 * L:
        raise InputsError(f'{where}: rate block is not 2^E rates')
    return magic, L, gid, wa, wb, M, T


def member_row(payload: bytes, sector: str, L: int, gid: int, primitive: bool, offset: int, inspect=None, *,
               where: str | None = None, audit: int | None = None) -> dict:
    """One inventory row. L <= 7: the full structural parse and the numpy double_lift, which must equal the rate
    audit's count when one is given (Stage 2b, L7). L8: the light parse; double_lift is the rate audit's (required)."""
    where = where or f'reference/inputs/{sector}/L{L}/G{gid}.txt'
    if L <= 7:
        g = Member(payload, where)
        magic, gL, gid_, wa, wb, M, T = g.magic, g.L, g.id, g.wa, g.wb, g.M, g.T
        raw = raw_valuations(g.L, g.masks, g.terms)
        dl = int((raw <= DOUBLE_LIFT_RAW).sum())
        if audit is not None and dl != audit:
            raise InputsError(f'{where}: double_lift {dl} differs from rate_audit_L{L}.json ({audit} subsets)')
    else:
        magic, gL, gid_, wa, wb, M, T = light_member(payload, where)
        if audit is None:
            raise InputsError(f'{where}: no rate-audit double_lift count for an L8 kernel')
        dl = int(audit)
    if (magic, gL, gid_) != ('C7D3GRAPH1', L, gid):
        raise InputsError(f'{where}: header {magic} {gL} {gid_} is not C7D3GRAPH1 {L} {gid}')
    sha = hashlib.sha256(payload).hexdigest()
    fields = {k: None for k in INSPECT_FIELDS}
    if inspect is not None:
        if inspect[0] != sha:
            raise InputsError(f'{INSPECT_DATA}: {sector} L{L} G{gid} was inspected at member sha256 {inspect[0]}, '
                              f'not {sha} (stale inspect data: run make inputs-inspect)')
        fields = inspect[1]
    row = dict(id=gid, primitive=primitive, s_G=s_g(wa, wb, where), wa=wa, wb=wb, offset=offset,
               length=len(payload), sha256=sha, monomials=M, terms=T,
               cost=max(1, M * T), **fields, double_lift=dl)
    assert tuple(row) == ROW_FIELDS
    return row


def inventory_text(inv: dict) -> str:
    """inventory.json with one row per line (deterministic; json.loads gives `inv` back)."""
    lines = ['{', f' "inspect_complete": {json.dumps(inv["inspect_complete"])},']
    for si, sector in enumerate(SECTORS):
        loops = list(inv[sector])
        lines.append(f' "{sector}": {{')
        for li, L in enumerate(loops):
            rows = inv[sector][L]
            lines.append(f'  "{L}": [')
            lines += [f'   {json.dumps(r, allow_nan=False)}' + (',' if k < len(rows) - 1 else '')
                      for k, r in enumerate(rows)]
            lines.append('  ]' + (',' if li < len(loops) - 1 else ''))
        lines.append(' }' + (',' if si < len(SECTORS) - 1 else ''))
    lines.append('}')
    text = '\n'.join(lines) + '\n'
    if json.loads(text) != inv:
        raise AssertionError('inventory serialization does not round-trip')
    return text


# ---- Stage 2b: the verified sources (PLAN B, A.2 step 6) ----------------------------------------------------------
def sums_rows(data: bytes, what: str) -> dict:
    """A checksum list's exact bytes: rows "<64 hex>  <relative path>" each ending in LF, no duplicate path."""
    try:
        text = data.decode('ascii')
    except UnicodeDecodeError as e:
        raise InputsError(f'{what}: not ASCII ({e})') from None
    if text and not text.endswith('\n'):
        raise InputsError(f'{what}: no final newline')
    out = {}
    for ln in text.splitlines():
        m = SUMS_ROW.fullmatch(ln)
        if not m or m.group(2) in out:
            raise InputsError(f'{what}: malformed or duplicate row {ln[:100]!r}')
        out[m.group(2)] = m.group(1)
    return out


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class Stage2b:
    """The Stage-2b small files, checked as one chain from the two pins (A.2 step 6; PLAN B):
      d3:  sha256(MANIFEST_d3.json) = d3_pin, schema c8-d3-d3-payload-1, its h1_manifest_sha256 = h1_pin;
           SHA256SUMS at the manifest's sha256 and md5; MEMBERS_d3.sha256 and both rate audits at their SHA256SUMS rows;
      H1:  sha256(MANIFEST.json) = h1_pin; SHA256SUMS at its sha256sums_sha256; selection.json at its SHA256SUMS row.
    Then selection.json (schema, ascending unique ids, counts; with `expect`, the A-IN-3 counts and primitives: by
    default whenever h1_pin is H1's real pin, so only a test fixture's own H1 tree escapes them), the member hashes and
    the rate audits' double_lift counts, every selected kernel present in both.
    files: {inputs-relative path (STAGE2B_FILES): bytes}; `where` names their directory in messages."""

    def __init__(self, files: dict, d3_pin: str, h1_pin: str, where: str, expect='auto'):
        if expect == 'auto':
            expect = STAGE2B_COUNTS if h1_pin == H1_MANIFEST_SHA256 else None
        def need(rel: str) -> bytes:
            if files.get(rel) is None:
                raise InputsError(f'{where}/{rel}: missing (a Stage-2b input)')
            return files[rel]
        for name, pin in (('d3 pin (D3PIN, the sha256 of MANIFEST_d3.json)', d3_pin), ('H1 pin', h1_pin)):
            if not isinstance(pin, str) or not SHA_RE.fullmatch(pin):
                raise InputsError(f'{where}: the {name} {pin!r} is not a sha256')
        self.files = {rel: need(rel) for rel in STAGE2B_FILES}
        self.d3_pin, self.h1_pin = d3_pin, h1_pin
        mb = need('d3/MANIFEST_d3.json')
        if _sha(mb) != d3_pin:
            raise InputsError(f'Checksum mismatch: {where}/d3/MANIFEST_d3.json has sha256 {_sha(mb)}, not the d3 pin '
                              f'{d3_pin}')
        try:
            man = json.loads(mb)
        except ValueError as e:
            raise InputsError(f'{where}/d3/MANIFEST_d3.json: not JSON ({e})') from None
        if not isinstance(man, dict) or man.get('schema') != D3_SCHEMA or man.get('h1_manifest_sha256') != h1_pin:
            raise InputsError(f'{where}/d3/MANIFEST_d3.json: not a {D3_SCHEMA} manifest of the H1 tree {h1_pin}')
        sb = need('d3/SHA256SUMS')
        if _sha(sb) != man.get('sha256sums_sha256') or hashlib.md5(sb).hexdigest() != man.get('sha256sums_md5'):
            raise InputsError(f'Checksum mismatch: {where}/d3/SHA256SUMS is not the file MANIFEST_d3.json pins '
                              '(sha256sums_sha256, sha256sums_md5)')
        listed = sums_rows(sb, f'{where}/d3/SHA256SUMS')
        for rel, name in D3_COPIES.items():
            if name not in ('MANIFEST_d3.json', 'SHA256SUMS') and listed.get(name) != _sha(need(rel)):
                raise InputsError(f'Checksum mismatch: {where}/{rel} is not the {name} the d=3 SHA256SUMS lists')
        hb = need('h1/MANIFEST.json')
        if _sha(hb) != h1_pin:
            raise InputsError(f'Checksum mismatch: {where}/h1/MANIFEST.json has sha256 {_sha(hb)}, not the H1 pin {h1_pin}')
        try:
            hman = json.loads(hb)
        except ValueError as e:
            raise InputsError(f'{where}/h1/MANIFEST.json: not JSON ({e})') from None
        hs = need('h1/SHA256SUMS')
        if not isinstance(hman, dict) or _sha(hs) != hman.get('sha256sums_sha256'):
            raise InputsError(f'Checksum mismatch: {where}/h1/SHA256SUMS is not the file H1\'s MANIFEST.json pins')
        if sums_rows(hs, f'{where}/h1/SHA256SUMS').get('selection.json') != _sha(need(SELECTION)):
            raise InputsError(f'Checksum mismatch: {where}/{SELECTION} is not the selection.json H1\'s SHA256SUMS lists')
        self.manifest_d3 = man
        try:
            sel = json.loads(need(SELECTION))
            self.ids, self.primitive = {}, {}
            for L in (7, 8):
                for s in SECTORS:
                    ids = sel[f'L{L}'][s]
                    if not all(isinstance(x, int) and x >= 0 for x in ids) or ids != sorted(set(ids)):
                        raise InputsError(f'{where}/{SELECTION}: L{L} {s} ids are not ascending unique integers')
                    if sel['counts'][f'L{L}_{s}'] != len(ids):
                        raise InputsError(f'{where}/{SELECTION}: L{L} {s} lists {len(ids)} ids, its counts say '
                                          f'{sel["counts"][f"L{L}_{s}"]}')
                    self.ids[(s, L)] = ids
                self.primitive[L] = set(sel[f'L{L}']['primitive'])
                if not self.primitive[L] <= set(self.ids[('free', L)]):
                    raise InputsError(f'{where}/{SELECTION}: L{L} primitives outside the free selection')
        except (KeyError, TypeError, ValueError) as e:
            raise InputsError(f'{where}/{SELECTION}: malformed ({e!r})') from None
        if sel.get('schema') != SELECTION_SCHEMA:
            raise InputsError(f'{where}/{SELECTION}: schema {sel.get("schema")!r} is not {SELECTION_SCHEMA}')
        if expect is not None:
            got = {s: {L: len(self.ids[(s, L)]) for L in (7, 8)} for s in SECTORS}
            prim = {L: len(self.primitive[L]) for L in (7, 8)}
            if got != expect or prim != STAGE2B_PRIMITIVES:
                raise InputsError(f'{where}/{SELECTION}: counts {got} and primitives {prim} are not H1\'s '
                                  f'{expect} and {STAGE2B_PRIMITIVES} (A-IN-3)')
        self.members = {}
        for name, h in sums_rows(need('d3/MEMBERS_d3.sha256'), f'{where}/d3/MEMBERS_d3.sha256').items():
            m = GFILE_NAME.fullmatch(name)
            if not m:
                raise InputsError(f'{where}/d3/MEMBERS_d3.sha256: unexpected member {name!r}')
            self.members[(m.group(2), int(m.group(1)), int(m.group(3)))] = h
        self.double_lift = {}
        for L in (7, 8):
            try:
                audit = json.loads(need(f'd3/rate_audit_L{L}.json'))
                for r in audit:
                    m = GFILE_NAME.fullmatch(r['file'])
                    if not m or int(m.group(1)) != L or r['L'] != L or r['id'] != int(m.group(3)):
                        raise InputsError(f'{where}/d3/rate_audit_L{L}.json: unexpected record {r.get("file")!r}')
                    self.double_lift[(m.group(2), L, r['id'])] = int(r['double_lift_subsets'])
            except (KeyError, TypeError, ValueError) as e:
                raise InputsError(f'{where}/d3/rate_audit_L{L}.json: malformed ({e!r})') from None
        for (s, L), ids in self.ids.items():
            miss = [g for g in ids if (s, L, g) not in self.members or (s, L, g) not in self.double_lift]
            if miss:
                raise InputsError(f'{where}: selected {s} L{L} kernels {miss[:5]} are not in MEMBERS_d3.sha256 and '
                                  'the rate audit')

    def member_sha(self, sector: str, L: int, gid: int) -> str:
        return self.members[(sector, L, gid)]

    def name(self, sector: str, L: int, gid: int) -> str:
        return f'L{L}_{sector}/G{gid}.txt'


def stage2b_files_from(d3payload: Path, h1: Path) -> dict:
    """The Stage-2b small files from the published d=3 payload and the H1 copy (make inputs-l8)."""
    out = {}
    for rel, name in D3_COPIES.items():
        p = Path(d3payload) / name
        if p.is_symlink() or not p.is_file():
            raise InputsError(f'{p}: missing or not a regular file (the d=3 payload)')
        out[rel] = p.read_bytes()
    for rel, name in H1_COPIES.items():
        p = Path(h1) / name
        if p.is_symlink() or not p.is_file():
            raise InputsError(f'{p}: missing or not a regular file (the H1 copy)')
        out[rel] = p.read_bytes()
    return out


def stage2b_files_in(d: Path) -> dict:
    """The package's copies of the Stage-2b small files (None for a missing one)."""
    return {rel: ((Path(d) / rel).read_bytes() if (Path(d) / rel).is_file() else None) for rel in STAGE2B_FILES}


class TarMembers:
    """The d=3 payload's members by (sector, L, id): offsets from one pass over each tar's headers, members read by
    seek (a tar's name order is not numeric). Opened only after verify_d3.py has passed (make inputs-l8)."""

    def __init__(self, payload: Path):
        self.payload = Path(payload)
        self.where, self.fh = {}, {}
        for L in (7, 8):
            for s in SECTORS:
                tp = self.payload / 'payload' / f'L{L}_{s}.tar'
                try:
                    with tarfile.open(tp, 'r:') as tf:
                        for m in tf:
                            mm = GFILE_NAME.fullmatch(m.name)
                            if not m.isfile() or not mm or (int(mm.group(1)), mm.group(2)) != (L, s):
                                raise InputsError(f'{tp}: unexpected member {m.name!r}')
                            self.where[(s, L, int(mm.group(3)))] = (tp, m.offset_data, m.size)
                except (tarfile.TarError, OSError) as e:
                    raise InputsError(f'{tp}: unreadable tar ({e})') from None

    def read(self, s: str, L: int, gid: int) -> bytes:
        try:
            tp, off, n = self.where[(s, L, gid)]
        except KeyError:
            raise InputsError(f'{self.payload}: no member L{L}_{s}/G{gid}.txt in payload/L{L}_{s}.tar') from None
        f = self.fh.get(tp)
        if f is None:
            f = self.fh[tp] = open(tp, 'rb')
        f.seek(off)
        data = f.read(n)
        if len(data) != n:
            raise InputsError(f'{tp}: member L{L}_{s}/G{gid}.txt truncated')
        return data

    def label(self, s: str, L: int, gid: int) -> str:
        return f'{self.payload}/payload/L{L}_{s}.tar:L{L}_{s}/G{gid}.txt'

    def close(self) -> None:
        for f in self.fh.values():
            f.close()
        self.fh = {}


def _c62d_tree(p: Path) -> str:
    sys.path.insert(0, str(ROOT / 'gen3'))
    try:
        import g3common
    finally:
        sys.path.pop(0)
    return g3common.under_c62d(p)


def store_dir(store: Path) -> Path:
    """$C8_STORE/packs, refusing C62d's trees (nothing of this package writes there, A-INV-6)."""
    d = Path(store).resolve() / STORE_PACKS
    hit = _c62d_tree(d)
    if hit:
        raise InputsError(f'{d}: the pack store is under C62d\'s tree {hit} (refused)')
    return d


def link_into(src: Path, dst: Path) -> str:
    """A hard link of a store blob at dst (a copy when dst is on another filesystem); never writes through."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dst)
        return 'hard link'
    except OSError as e:
        if e.errno not in (errno.EXDEV, errno.EPERM, errno.EMLINK):
            raise
    shutil.copyfile(src, dst)
    return 'copy (the store is on another filesystem)'


def finish_store_blob(tmp: Path, sha: str, size: int) -> Path:
    """Publish a written pack as <store>/packs/<sha256>.pack, read-only and never overwritten: an existing blob of that
    name must have the same size and bytes, and the new copy is dropped."""
    final = tmp.parent / f'{sha}.pack'
    if final.exists():
        if final.is_symlink() or final.stat().st_size != size or digest(final) != sha:
            raise InputsError(f'{final}: exists in the store with other content (the store is content-addressed; '
                              'investigate before removing anything)')
        tmp.unlink()
    else:
        os.chmod(tmp, 0o444)
        os.rename(tmp, final)
    return final


# ---- make inputs -------------------------------------------------------------------------------------------------
class D3Build:
    """The sources of `make inputs-l8`: the verified small files (Stage2b), the payload's members (TarMembers) and the
    pack store."""

    def __init__(self, sources: Stage2b, tar: TarMembers, store: Path):
        self.sources, self.tar, self.store = sources, tar, Path(store)


def source_manifest() -> dict | None:
    """The package's committed inputs/manifest.json (the state a plain `make inputs` rebuilds), or None."""
    p = ROOT / 'inputs/manifest.json'
    try:
        m = json.loads(p.read_bytes())
    except (OSError, ValueError):
        return None
    return m if isinstance(m, dict) else None


def _l8_rows_from_pack(fh, sector: str, sb: Stage2b, inspected: dict, where: str,
                       tar: TarMembers | None = None) -> tuple[list, str, int]:
    """The L8 rows of one sector in selection order. With `tar` (make inputs-l8) each member comes from the payload
    and is written to fh; without it, fh is the existing pack, split member by member (header line, then T + 3 lines)
    and checked to end exactly there. Every member must be at its MEMBERS_d3.sha256 hash. Returns (rows, the pack's
    sha256, its size)."""
    h = hashlib.sha256()
    rows, off = [], 0
    for gid in sb.ids[(sector, 8)]:
        if tar is not None:
            data = tar.read(sector, 8, gid)
            fh.write(data)
            label = tar.label(sector, 8, gid)
        else:
            first = fh.readline()
            hdr = first.split()
            if len(hdr) != 7 or not hdr[6].isdigit():
                raise InputsError(f'{where}: no G-file header at offset {off} (expected G{gid})')
            parts = [first]
            for _ in range(int(hdr[6]) + 3):
                ln = fh.readline()
                if not ln.endswith(b'\n'):
                    raise InputsError(f'{where}: truncated member G{gid} at offset {off}')
                parts.append(ln)
            data = b''.join(parts)
            label = f'{where}:G{gid}'
        if _sha(data) != sb.member_sha(sector, 8, gid):
            raise InputsError(f'{label}: sha256 differs from MEMBERS_d3.sha256 ({sb.name(sector, 8, gid)})')
        rows.append(member_row(data, sector, 8, gid, gid in sb.primitive[8], off, inspected.get((sector, 8, gid)),
                               where=label, audit=sb.double_lift[(sector, 8, gid)]))
        h.update(data)
        off += len(data)
    if tar is None and fh.read(1):
        raise InputsError(f'{where}: data after the last selected member')
    return rows, h.hexdigest(), off


def _l8_rows_carried(old_rows, sector: str, sb: Stage2b, inspected: dict) -> list:
    """Without the L8 packs (the Mac): the committed rows, each checked against selection.json (id, primitive),
    MEMBERS_d3.sha256 (sha256), the rate audit (double_lift) and contiguity; the inspect fields re-applied from
    inspect/inspect.json (null where it has none)."""
    where = f'inputs/inventory.json {sector} L8'
    if not isinstance(old_rows, list) or [r.get('id') for r in old_rows] != sb.ids[(sector, 8)]:
        raise InputsError(f'{where}: the committed rows are not the selection\'s kernels (run make inputs-l8 with the '
                          'L8 packs present)')
    rows, off = [], 0
    for r in old_rows:
        key = (sector, 8, r['id'])
        if tuple(r) != ROW_FIELDS or r['offset'] != off or r['sha256'] != sb.member_sha(*key) \
                or r['primitive'] is not (r['id'] in sb.primitive[8]) or r['double_lift'] != sb.double_lift[key]:
            raise InputsError(f'{where} G{r["id"]}: the committed row disagrees with selection.json, '
                              'MEMBERS_d3.sha256, rate_audit_L8.json or its offset')
        fields = {k: None for k in INSPECT_FIELDS}
        ins = inspected.get(key)
        if ins is not None:
            if ins[0] != r['sha256']:
                raise InputsError(f'{INSPECT_DATA}: {sector} L8 G{r["id"]} was inspected at member sha256 {ins[0]}, '
                                  f'not {r["sha256"]} (stale inspect data: run make inputs-inspect)')
            fields = ins[1]
        rows.append({**r, **fields})
        off += r['length']
    return rows


def build(out=None, log=None, d3: D3Build | None = None, report: dict | None = None) -> dict:
    """`make inputs` (and, with d3, `make inputs-l8`): build every input into `out` (default: the package's inputs/);
    see the module text. Three modes: 2a (the committed manifest has no d3 pin), 2b-full (d3 given) and 2b-carry (the
    committed manifest has the d3 pin: the package's own copies are the sources). `report` receives a summary (mode,
    gate 6, the L8 packs)."""
    log = log or (lambda msg: print(msg, file=sys.stderr, flush=True))
    out = Path(out) if out is not None else ROOT / 'inputs'
    out.mkdir(parents=True, exist_ok=True)
    report = report if report is not None else {}
    src_m = source_manifest()
    if d3 is not None:
        mode, sb = '2b-full', d3.sources
    elif src_m is not None and src_m.get('d3_payload_manifest_sha256') is not None:
        mode = '2b-carry'
        sb = Stage2b(stage2b_files_in(ROOT / 'inputs'), src_m['d3_payload_manifest_sha256'],
                     src_m.get('inventory8_d2_manifest_sha256'), 'inputs')
    else:
        mode, sb = '2a', None
    report['mode'] = mode
    stage = Path(tempfile.mkdtemp(prefix='.build-', dir=out))
    blobs: list[Path] = []
    try:
        pins = vendored_pins()
        files: list[str] = []

        def put(rel: str, data: bytes) -> None:
            p = stage / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            files.append(rel)
        for name in LOW_LOOP:
            put(name, verified_bytes(ROOT / VENDOR / 'inputs_d3' / name, pins['files'][f'{VENDOR}/inputs_d3/{name}']))
        two = json.loads((stage / 'two_loop.json').read_bytes())
        if (two.get('dimension'), two.get('order'), len(two.get('B2') or ())) != (3, 8, 7):
            raise InputsError(f'{VENDOR}/inputs_d3/two_loop.json: not the d=3 order-8 jet with 7 B2 strings')
        compare = low8_compare()
        log('make inputs: vendored inputs_d3/ checked against the HANDOFF; prepare_low8.py --d 3 compare: identical')
        ref = ROOT / 'reference/inputs'
        for name, sha in ORDER7.items():
            put(f'order7/{name}', verified_bytes(ref / name, sha))
        if sb is not None:
            for rel in STAGE2B_FILES:
                put(rel, sb.files[rel])
        old = json.loads(verified_bytes(ref / 'inventory.json', REFERENCE_INVENTORY_SHA256))
        inspected, inspect_prov = inspect_data()
        used = set()
        inv: dict = {'inspect_complete': False}
        sha: dict[str, str] = {}
        loops = LOOPS if sb is None else LOOPS_2B
        gate6 = {'c7d3_members': 0, 'new_l7_members': 0, 'payload_c7d3_bytes_compared': 0}
        old_pack_rows = {}
        if mode == '2b-carry':
            cur = json.loads((ROOT / 'inputs/inventory.json').read_bytes())
            if _sha((ROOT / 'inputs/inventory.json').read_bytes()) != src_m['sha256'].get('inventory.json'):
                raise InputsError('inputs/inventory.json: not the inventory inputs/manifest.json pins')
            old_pack_rows = {(s, L): {r['id']: r for r in cur.get(s, {}).get(str(L), [])} for s in SECTORS for L in (7, 8)}
            old_pack_rows.update({(s, 'L8rows'): cur.get(s, {}).get('8') for s in SECTORS})
        l8_how = {}
        for sector in SECTORS:
            inv[sector] = {}
            for L in LOOPS:
                rel = f'packs/{sector}_L{L}.pack'
                c7 = {g['id']: g for g in old[sector][str(L)]}
                c7ids = [g['id'] for g in old[sector][str(L)]]
                if c7ids != sorted(set(c7ids)) or len(c7ids) != C7D3_COUNTS[sector][L]:
                    raise InputsError(f'reference/inputs/inventory.json: {sector} L{L} ids are not the '
                                      f'{C7D3_COUNTS[sector][L]} ascending C7(3) kernels')
                ids = c7ids if (sb is None or L < 7) else sb.ids[(sector, 7)]
                if not set(c7ids) <= set(ids):
                    raise InputsError(f'{SELECTION}: the L7 {sector} selection lacks C7(3) kernels '
                                      f'{sorted(set(c7ids) - set(ids))[:5]} (gate 6)')
                rows = []
                c7hash = hashlib.sha256()   # C7(3)'s members in ascending id: a6ce987's pack bytes (gate 6)
                (stage / 'packs').mkdir(exist_ok=True)
                with (stage / rel).open('xb') as f:
                    for gid in ids:
                        key = (sector, L, gid)
                        used.add(key)
                        audit = None
                        if gid in c7:
                            where = f'reference/inputs/{sector}/L{L}/G{gid}.txt'
                            payload = (ref / sector / f'L{L}' / f'G{gid}.txt').read_bytes()
                            primitive = bool(c7[gid].get('primitive', False))
                            c7hash.update(payload)
                            gate6['c7d3_members'] += 1
                        elif mode == '2b-full':
                            where = d3.tar.label(sector, L, gid)
                            payload = d3.tar.read(sector, L, gid)
                            primitive = gid in sb.primitive[7]
                            gate6['new_l7_members'] += 1
                        else:   # 2b-carry: the new L7 member from the committed pack, at its committed row
                            r = old_pack_rows[(sector, L)].get(gid)
                            if r is None:
                                raise InputsError(f'inputs/inventory.json: no committed row for {sector} L7 G{gid}')
                            where = f'inputs/{rel}:G{gid}'
                            with (ROOT / 'inputs' / rel).open('rb') as g:
                                g.seek(r['offset'])
                                payload = g.read(r['length'])
                            primitive = gid in sb.primitive[7]
                            gate6['new_l7_members'] += 1
                        if sb is not None and L == 7:
                            if _sha(payload) != sb.member_sha(sector, 7, gid):
                                raise InputsError(f'{where}: sha256 differs from MEMBERS_d3.sha256 '
                                                  f'({sb.name(sector, 7, gid)}; gate 6 / gate 1(b))')
                            if primitive is not (gid in sb.primitive[7]):
                                raise InputsError(f'{where}: primitive flag differs from {SELECTION}')
                            if mode == '2b-full' and gid in c7:
                                if d3.tar.read(sector, 7, gid) != payload:
                                    raise InputsError(f'{d3.tar.label(sector, 7, gid)}: differs from C7(3)\'s member '
                                                      '(gate 6)')
                                gate6['payload_c7d3_bytes_compared'] += 1
                            audit = sb.double_lift[(sector, 7, gid)]
                        rows.append(member_row(payload, sector, L, gid, primitive, f.tell(), inspected.get(key),
                                               where=where, audit=audit))
                        f.write(payload)
                files.append(rel)
                sha[rel] = digest(stage / rel)
                if (sb is None or L < 7) and sha[rel] != C7D3_PACK_SHA256[rel]:
                    raise InputsError(f'{rel}: sha256 {sha[rel]} differs from LRI_C7_D3_HPC@a6ce987 '
                                      f'({C7D3_PACK_SHA256[rel]}); PLAN B: the L3-L6 packs (and L7 before Stage 2b) '
                                      'are C7(3)\'s bytes')
                if c7hash.hexdigest() != C7D3_PACK_SHA256[rel]:
                    raise InputsError(f'{rel}: the C7(3) members, concatenated in id order, are not '
                                      f'LRI_C7_D3_HPC@a6ce987\'s pack {C7D3_PACK_SHA256[rel][:12]} (gate 6)')
                gate6.setdefault('c7d3_packs_reproduced', []).append(rel)
                inv[sector][str(L)] = rows
                log(f'make inputs: {rel}: {len(rows)} kernels')
            if sb is None:
                continue
            rel = f'packs/{sector}_L8.pack'
            used.update((sector, 8, g) for g in sb.ids[(sector, 8)])
            present = ROOT / 'inputs' / rel
            if mode == '2b-full':
                sd = store_dir(d3.store)
                sd.mkdir(parents=True, exist_ok=True)
                tmp = sd / f'.tmp-{sector}_L8-{os.getpid()}'
                try:
                    with tmp.open('xb') as f:
                        rows, sha[rel], size = _l8_rows_from_pack(f, sector, sb, inspected, str(tmp), tar=d3.tar)
                        f.flush()
                        os.fsync(f.fileno())
                    blob = finish_store_blob(tmp, sha[rel], size)
                finally:
                    if tmp.exists():
                        tmp.unlink()
                blobs.append(blob)
                l8_how[rel] = dict(store=str(blob), bytes=size, link=link_into(blob, stage / rel))
                files.append(rel)
            elif present.is_file():
                pin = src_m['sha256'].get(rel)
                with present.open('rb') as f:
                    rows, got, size = _l8_rows_from_pack(f, sector, sb, inspected, f'inputs/{rel}')
                if got != pin:
                    raise InputsError(f'Checksum mismatch: inputs/{rel} has sha256 {got}, not the pin {pin}')
                sha[rel] = got
                l8_how[rel] = dict(rederived_from='inputs/' + rel, bytes=size)
            else:
                rows = _l8_rows_carried(old_pack_rows.get((sector, 'L8rows')), sector, sb, inspected)
                sha[rel] = src_m['sha256'].get(rel)
                if not isinstance(sha[rel], str) or not SHA_RE.fullmatch(sha[rel]):
                    raise InputsError(f'inputs/manifest.json: no pin for {rel} to carry forward')
                l8_how[rel] = dict(carried='the committed rows (the L8 pack is not present here)')
            inv[sector]['8'] = rows
            log(f'make inputs: {rel}: {len(rows)} kernels ({next(iter(l8_how[rel]))})')
        extra = sorted(set(inspected) - used)
        if extra:
            raise InputsError(f'{INSPECT_DATA}: rows for kernels that are not in the inputs: {extra[:5]}')
        inv['inspect_complete'] = all(r[k] is not None for s in SECTORS for L in loops for r in inv[s][str(L)]
                                      for k in INSPECT_FIELDS)
        put('inventory.json', inventory_text(inv).encode())
        packs = [f'packs/{s}_L{L}.pack' for s in SECTORS for L in loops]
        hashes = {rel: (sha[rel] if rel in sha else digest(stage / rel)) for rel in files}
        hashes.update({rel: sha[rel] for rel in packs if rel in sha})
        pinned = (*LOW_LOOP, *(f'order7/{n}' for n in ORDER7), 'inventory.json', *packs,
                  *(STAGE2B_FILES if sb is not None else ()))
        if sb is None:
            l7_text = "C7(3)'s 2,298 + 590 kernels only (l7_complete: false; Stage 2b adds the s_G = 4 kernels)"
            l8_text = 'not present (l8_present: false; make inputs-l8, Stage 2b)'
        else:
            l7_text = ("selection.json's 2,441 + 709 kernels: C7(3)'s 2,298 + 590 from reference/inputs/ (gate 6) and "
                       "the 143 + 119 s_G = 4 kernels from the d=3 payload, each at its MEMBERS_d3.sha256 hash")
            l8_text = ("selection.json's 16,064 + 4,336 kernels from the d=3 payload (make inputs-l8), each at its "
                       "MEMBERS_d3.sha256 hash; not in git: $C8_STORE/packs/<sha256>.pack (read-only), hard-linked "
                       "into inputs/packs/ (make link-l8)")
        manifest = {
            'schema': SCHEMA, 'dimension': 3, 'order': 8, 'epsilon': '2s-3',
            'sha256': {rel: hashes[rel] for rel in pinned},
            'counts': {s: {str(L): len(inv[s][str(L)]) for L in loops} for s in SECTORS},
            'kernels': sum(len(inv[s][str(L)]) for s in SECTORS for L in loops),
            'l7_complete': sb is not None, 'l8_present': sb is not None, 'inspect_complete': inv['inspect_complete'],
            'inventory8_d2_manifest_sha256': sb.h1_pin if sb is not None else None,
            'd3_payload_manifest_sha256': sb.d3_pin if sb is not None else None,
            'vendored_assembly_handoff_sha256': pins['handoff_sha256'],
            'vendored_assembly': {'handoff_sha256': pins['handoff_sha256'], 'pins_from': 'tools/VENDORED.json',
                                  'files': pins['files']},
            'sources': {
                'two_loop.json, gamma_d3_8.txt': f'byte copies of {VENDOR}/inputs_d3/ at the HANDOFF sha256s (HD4)',
                'prepare_low8_compare': compare,
                'order7/': "byte copies of C7(3)'s order-7 files, reference/inputs/ (= LRI_C7_D3_HPC@a6ce987 inputs/)",
                'packs': ("C7(3)'s members reference/inputs/<sector>/L<L>/G<id>.txt, ids and primitive flags from "
                          'reference/inputs/inventory.json, ascending id; '
                          + ('every pack equals LRI_C7_D3_HPC@a6ce987' if sb is None else
                             'the L3-L6 packs equal LRI_C7_D3_HPC@a6ce987; the L7 and L8 ids and the new kernels\' '
                             'primitive flags from selection.json')),
                'L7': l7_text,
                'L8': l8_text,
                **({} if sb is None else {
                    'stage2b': ('selection.json, h1/{MANIFEST.json,SHA256SUMS}: byte copies from the H1 copy '
                                '(H1 MANIFEST -> SHA256SUMS -> selection.json); d3/{MANIFEST_d3.json,SHA256SUMS,'
                                'MEMBERS_d3.sha256,rate_audit_L7.json,rate_audit_L8.json}: byte copies from the d=3 '
                                'payload (MANIFEST_d3 -> SHA256SUMS -> the members list and the rate audits); the two '
                                'pins are copies of the external ones (HANDOFF_inventory8_d2.json, the A.5 gate record)')}),
                'inventory': ((f'inspect fields from {INSPECT_DATA} (make inputs-inspect)' if inspect_prov else
                               'inspect fields null (inspect_complete: false; make inputs-inspect, Stage 3a)')
                              + f'; double_lift = subsets with raw p4 <= {DOUBLE_LIFT_RAW}'
                              + ('' if sb is None else ' (numpy at L <= 7, equal to rate_audit_L7.json at L7; '
                                 'rate_audit_L8.json at L8)')),
                **({'inspect': inspect_prov} if inspect_prov else {}),
            },
            'reference_manifest_sha256': digest(ROOT / 'reference/DELIVERY_MANIFEST.json'),
        }
        put('manifest.json', (json.dumps(manifest, indent=2, allow_nan=False) + '\n').encode())
        changed = []
        for rel in files:   # manifest.json is the last entry
            src, dst = stage / rel, out / rel
            if rel in L8_PACKS:
                if dst.exists() and os.path.samefile(src, dst):
                    continue
            elif dst.is_file() and not dst.is_symlink() and digest(dst) == digest(src):
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.replace(src, dst)
            changed.append(rel)
        log(f'make inputs ({mode}): {len(files)} files in {out}; changed: {", ".join(changed) or "none"}')
        report.update(gate6=gate6, l8=l8_how, changed=changed, kernels=manifest['kernels'])
        return manifest
    finally:
        shutil.rmtree(stage, ignore_errors=True)
        if d3 is not None:
            d3.tar.close()


def prepare():
    """Transitional, until tools/production.py is ported (Stage 3a, PLAN D.1): the C7(3) planner calls prepare(),
    which built and returned the C7(3) inputs. inputs/ now holds the C8(3) inputs, so it refuses."""
    raise InputsError('inputs/ holds the C8(3) inputs (schema c8-d3-hpc-inputs-1): the C7(3) planner of '
                      'tools/production.py is ported to them in Stage 3a (PLAN D.1); `make inputs` builds them and '
                      '`tools/prepare_inputs.py verify` checks them')


# ---- verify and the plan gate ------------------------------------------------------------------------------------
def inputs_dir(env=None) -> Path:
    env = os.environ if env is None else env
    v = env.get('C8_INPUTS') or ''
    return Path(v).expanduser().resolve() if v else (ROOT / 'inputs').resolve()


def verify(inputs=None, env=None) -> dict:
    """Check the inputs at `inputs` (default: C8_INPUTS, else the package's inputs/); see the module text.
    Returns {inputs, manifest, manifest_sha256, skipped, test_only_reasons}."""
    env = os.environ if env is None else env
    d = Path(inputs).resolve() if inputs is not None else inputs_dir(env)
    mp = d / 'manifest.json'
    try:
        data = mp.read_bytes()
        m = json.loads(data)
    except (OSError, ValueError) as e:
        raise InputsError(f'{mp}: cannot read the inputs manifest ({e}); run make inputs') from None
    if not isinstance(m, dict):
        raise InputsError(f'{mp}: not an inputs manifest')
    if m.get('schema') == C7_SCHEMA:
        raise InputsError(f'{mp}: a C7(3) inputs manifest (schema {C7_SCHEMA}, LRI_C7_D3_HPC@a6ce987) is refused; '
                          'this package needs the C8(3) inputs (make inputs)')
    if m.get('dimension') != 3 or str(m.get('schema', '')).startswith('c8-d2'):
        raise InputsError(f'{mp}: dimension {m.get("dimension")!r} (schema {m.get("schema")!r}) is refused: this is '
                          'the d=3 package (a dimension-2 manifest belongs to C62d\'s LRI_C8_D2_HPC)')
    if (m.get('schema'), m.get('order'), m.get('epsilon')) != (SCHEMA, 8, '2s-3'):
        raise InputsError(f'{mp}: schema {m.get("schema")!r}, order {m.get("order")!r}, epsilon {m.get("epsilon")!r} '
                          f'are not {SCHEMA}, 8, 2s-3')
    pinned = m.get('sha256')
    counts = m.get('counts')
    if not isinstance(pinned, dict) or not isinstance(counts, dict):
        raise InputsError(f'{mp}: no sha256 or counts table')
    required = {*LOW_LOOP, *(f'order7/{n}' for n in ORDER7), 'inventory.json',
                *(f'packs/{s}_L{L}.pack' for s in SECTORS for L in counts.get(s, {}))}
    d3_pin, h1_pin = m.get('d3_payload_manifest_sha256'), m.get('inventory8_d2_manifest_sha256')
    if d3_pin is not None or h1_pin is not None:
        required |= set(STAGE2B_FILES)
    if not required <= set(pinned):
        raise InputsError(f'{mp}: no sha256 for {sorted(required - set(pinned))}')
    l8 = sorted(set(pinned) & set(L8_PACKS))
    if bool(m.get('l8_present')) != bool(l8) or (l8 and len(l8) != 2):
        raise InputsError(f'{mp}: l8_present is {m.get("l8_present")!r} but the L8 packs pinned are {l8}')
    allow_no_l8 = env.get('C8_ALLOW_NO_L8') == '1'
    skipped = []
    for rel, sha in pinned.items():
        if not isinstance(rel, str) or rel.startswith('/') or '..' in Path(rel).parts:
            raise InputsError(f'{mp}: pinned path {rel!r} is not inside the inputs directory')
        p = d / rel
        if rel in L8_PACKS and not p.exists() and allow_no_l8:
            print(f'SKIPPED {rel}: not present; C8_ALLOW_NO_L8=1, so every plan made now is test-only', file=sys.stderr)
            skipped.append(rel)
            continue
        if not p.is_file():
            raise InputsError(f'{p}: missing (pinned by {mp})' + (' (C8_ALLOW_NO_L8=1 skips a missing L8 pack, '
                                                                    'test-only)' if rel in L8_PACKS else ''))
        if digest(p) != sha:
            raise InputsError(f'Checksum mismatch: {p} is not the file {mp} pins')
    if d3_pin is not None or h1_pin is not None:   # Stage 2b: the small files' chain to the two (copied) pins
        Stage2b(stage2b_files_in(d), d3_pin, h1_pin, str(d), expect=None)
    # the vendored assembly: the manifest's pins, equal to tools/VENDORED.json, and the files at them
    va = m.get('vendored_assembly') or {}
    if m.get('vendored_assembly_handoff_sha256') != HANDOFF_SHA256 or va.get('handoff_sha256') != HANDOFF_SHA256:
        raise InputsError(f'{mp}: the vendored HANDOFF pin is not {HANDOFF_SHA256} (HD4)')
    vend = json.loads((ROOT / 'tools/VENDORED.json').read_bytes())
    if va.get('files') != {f['vendored_path']: f['sha256'] for f in vend['files']} \
            or vend['handoff']['sha256'] != HANDOFF_SHA256:
        raise InputsError(f'{mp}: the vendored file pins differ from tools/VENDORED.json')
    hp = ROOT / VENDOR / 'HANDOFF_assembly.json'
    if hp.is_symlink() or not hp.is_file() or digest(hp) != HANDOFF_SHA256:
        raise InputsError(f'Checksum mismatch: {VENDOR}/HANDOFF_assembly.json is not the HANDOFF {HANDOFF_SHA256}')
    for rel, sha in va['files'].items():
        p = ROOT / rel
        if p.is_symlink() or not p.is_file() or digest(p) != sha:
            raise InputsError(f'Checksum mismatch: {rel} is not the vendored file {mp} pins')
    reasons = []
    if m.get('l7_complete') is not True:
        reasons.append("l7_complete: false (L7 holds C7(3)'s 2,298 + 590 kernels only, before Stage 2b)")
    if m.get('l8_present') is not True:
        reasons.append('l8_present: false (no L8 packs before Stage 2b)')
    if skipped:
        reasons.append(f'C8_ALLOW_NO_L8=1: {", ".join(skipped)} skipped, not verified')
    if 'test_inputs' in m:   # inputs_mini or any tree its manifest marks as test inputs, wherever it lies (S4-003)
        reasons.append(f'test_inputs: the manifest marks a test inputs tree ({str(m["test_inputs"])[:60]}...)')
    return {'inputs': str(d), 'manifest': m, 'manifest_sha256': hashlib.sha256(data).hexdigest(), 'skipped': skipped,
            'test_only_reasons': reasons}


def inventory_complete(d: Path, m: dict, h1_pin: str = H1_MANIFEST_SHA256) -> dict:
    """A non-test plan's inventory against the authoritative selection (S4-003; PLAN B, A-IN-3): the manifest carries
    H1's pin (the package's own H1_MANIFEST_SHA256, not a copy's) and a d3 pin; Stage2b's chain from them with H1's
    counts and primitives; inventory.json read once at its pin; per sector loops 3..8 exactly, in each every graph id
    once (R2-S1-03: a duplicate would keep the count and hide a missing graph); L3-L6 C7(3)'s counts at
    a6ce987's pack pins; L7 and L8 exactly selection.json's ids, each row at its MEMBERS_d3.sha256 hash, the free
    primitives exactly selection.json's (none in power); every count and the kernel total equal to the manifest's.
    Raises InputsError naming what is missing; returns the per-(sector, loop) kernel counts."""
    mp = d / 'manifest.json'
    if m.get('inventory8_d2_manifest_sha256') != h1_pin or not isinstance(m.get('d3_payload_manifest_sha256'), str):
        raise InputsError(f'{mp}: a non-test plan needs the Stage-2b inputs of H1 {h1_pin} (selection.json, PLAN B); the '
                          f'manifest pins H1 {m.get("inventory8_d2_manifest_sha256")!r} and d3 '
                          f'{m.get("d3_payload_manifest_sha256")!r}')
    sb = Stage2b(stage2b_files_in(d), m['d3_payload_manifest_sha256'], h1_pin, str(d))
    data = verified_bytes(d / 'inventory.json', m['sha256']['inventory.json'])   # one read, at its pin
    try:
        inv = json.loads(data)
        bad, got, counts = [], {}, m['counts']
        for s in SECTORS:
            if sorted(inv[s]) != sorted(str(L) for L in LOOPS_2B):
                bad.append(f'{s} loops {sorted(inv[s])} are not {list(LOOPS_2B)}')
                continue
            for L in LOOPS_2B:
                rows = inv[s][str(L)]
                ids = [r['id'] for r in rows]
                got[f'{s}:{L}'] = len(rows)
                if len(set(ids)) != len(ids):   # R2-S1-03: a duplicate keeps the count and hides a missing graph
                    seen = set()
                    bad.append(f'{s} L{L}: graph ids repeated {sorted({g for g in ids if g in seen or seen.add(g)})[:5]} '
                               '(each kernel once)')
                if counts[s].get(str(L)) != len(rows):
                    bad.append(f'{s} L{L}: {len(rows)} rows, the manifest counts {counts[s].get(str(L))!r}')
                if L < 7:
                    pack = f'packs/{s}_L{L}.pack'
                    if len(rows) != C7D3_COUNTS[s][L] or m['sha256'].get(pack) != C7D3_PACK_SHA256[pack]:
                        bad.append(f'{s} L{L}: not C7(3)\'s {C7D3_COUNTS[s][L]} kernels at a6ce987\'s {pack}')
                    continue
                want = sb.ids[(s, L)]
                if ids != want:
                    miss = sorted(set(want) - set(ids))
                    bad.append(f'{s} L{L}: {len(ids)} kernels, selection.json selects {len(want)} (missing {miss[:5]}, '
                               f'extra {sorted(set(ids) - set(want))[:5]}{", or out of order" if not miss else ""})')
                    continue
                off = [g for g, r in zip(ids, rows) if r['sha256'] != sb.member_sha(s, L, g)]
                if off:
                    bad.append(f'{s} L{L}: kernels {off[:5]} are not at their MEMBERS_d3.sha256 hash')
                if {r['id'] for r in rows if r['primitive']} != (sb.primitive[L] if s == 'free' else set()):
                    bad.append(f'{s} L{L}: the primitive flags differ from selection.json\'s')
        if m.get('kernels') != sum(got.values()):
            bad.append(f'{sum(got.values())} kernels, the manifest says {m.get("kernels")!r}')
    except (KeyError, TypeError, AttributeError, ValueError) as e:
        raise InputsError(f'{d / "inventory.json"}: malformed for the completeness check ({e!r})') from None
    if bad:
        raise InputsError(f'{d / "inventory.json"}: incomplete against H1\'s selection.json, refused for a non-test plan '
                          f'(PLAN B, A-IN-3; a test plan may use it): {"; ".join(bad[:6])}')
    return got


def plan_inputs(test_only: bool, env=None) -> dict:
    """The plan's input gate (PLAN B, A-IN-4), called before the plan creates anything: refuses a non-test plan whose
    C8_INPUTS is not the package's inputs/, then verify(); the plan is test-only if asked or if any reason holds (a
    test_inputs marker among them). A plan that stays non-test needs inventory_complete() (S4-003)."""
    env = os.environ if env is None else env
    d = inputs_dir(env)
    foreign = d != (ROOT / 'inputs').resolve()
    if foreign and not test_only:
        raise InputsError(f'C8_INPUTS={env.get("C8_INPUTS")}: a non-test plan reads only the package inputs '
                          f'{ROOT / "inputs"} (PLAN B); unset C8_INPUTS or make a test-only plan')
    v = verify(d, env)
    if foreign:
        v['test_only_reasons'].append(f'C8_INPUTS={d} is not the package inputs/')
    v['test_only'] = bool(test_only or v['test_only_reasons'])
    if not v['test_only']:
        m = v['manifest']
        if 'synthetic' not in m:
            v['inventory_complete'] = inventory_complete(Path(v['inputs']), m)
        elif synthetic_seam(env, m):   # tests/c8pkg.py's synthetic scratch package under the Mac fakes only (R2-S1-02)
            v['inventory_complete'] = {'skipped': f'synthetic test inputs ({SYNTHETIC_INPUTS_LABEL}; no H1 or d3 pin; '
                                                  f'{SYNTHETIC_SEAM}=1 under C8_SITE=fake): no H1 selection to check against'}
        else:   # R2-S1-02: a manifest label never lifts the completeness check; the plan becomes test-only
            v['test_only_reasons'].append(f'synthetic: the manifest marks synthetic test inputs ({str(m["synthetic"])[:60]})')
            v['test_only'] = True
    return v


def synthetic_seam(env, m: dict) -> bool:
    """R2-S1-02: the test seam on which a NON-test plan may use tests/c8pkg.py's synthetic inputs, controlled by the
    environment, never by the manifest: SYNTHETIC_SEAM=1, honoured only under C8_SITE=fake on a host that is no real site
    (tools/ledger.py host_sites: Expanse or symmetry, whatever C8_SITE says), and then for SYNTHETIC_INPUTS_LABEL exactly
    with neither pin. Unset: False. Set otherwise: refused (as ledger.py's C8_TEST_HOOKS)."""
    if not env.get(SYNTHETIC_SEAM):
        return False
    if env.get(SYNTHETIC_SEAM) != '1' or env.get('C8_SITE') != 'fake':
        raise InputsError(f'{SYNTHETIC_SEAM}={env.get(SYNTHETIC_SEAM)!r} is a test seam honoured only as 1 under C8_SITE=fake '
                          f'(the Mac fakes), not under C8_SITE={env.get("C8_SITE")!r}: unset it')
    import ledger
    try:
        hosts = ledger.host_sites(env)
    except ledger.Refuse as e:
        raise InputsError(f'{SYNTHETIC_SEAM}: the host\'s site cannot be ruled out ({e})') from None
    if hosts:   # ledger.py's own refusal text, which val1 records as SITE_REFUSED (slurm/site.sh c8_site_refusal)
        raise InputsError(f'this host is {", ".join(sorted(hosts))} but C8_SITE is \'fake\': the test seam {SYNTHETIC_SEAM} is '
                          'refused on a real site')
    return m.get('synthetic') == SYNTHETIC_INPUTS_LABEL and m.get('inventory8_d2_manifest_sha256') is None \
        and m.get('d3_payload_manifest_sha256') is None


# ---- make inputs-l8, make link-l8 (Stage 2b) ----------------------------------------------------------------------
def inputs_l8(d3payload: Path, d3pin: str, store: Path, h1: Path | None = None, gate_record: Path | None = None,
              verify_output: Path | None = None, h1_pin: str = H1_MANIFEST_SHA256, expect=STAGE2B_COUNTS,
              log=None) -> dict:
    """`make inputs-l8` (A.2 step 6, PLAN B): see the module text. Nothing is read from a tar member, and nothing is
    written, before gen3/verify_d3.py TREE --pin D3PIN has passed."""
    if not isinstance(d3pin, str) or not SHA_RE.fullmatch(d3pin):
        raise InputsError(f'D3PIN {d3pin!r} is not a sha256: the sha256 of MANIFEST_d3.json is required (the A.5 gate '
                          'record\'s pin; PLAN A.2 step 6); nothing was read')
    payload, store = Path(d3payload).resolve(), Path(store).resolve()
    store_dir(store)
    h1 = Path(h1).resolve() if h1 else store / 'h1' / h1_pin[:12]
    rec = {'d3pin': d3pin, 'd3payload': str(payload), 'h1': str(h1), 'store': str(store)}
    if gate_record is not None:
        try:
            g = json.loads(Path(gate_record).read_bytes())
        except (OSError, ValueError) as e:
            raise InputsError(f'{gate_record}: cannot read the A.5 gate record ({e})') from None
        if g.get('manifest_d3_sha256') != d3pin or g.get('h1_manifest_sha256') != h1_pin:
            raise InputsError(f'{gate_record}: the gate record pins MANIFEST_d3.json {g.get("manifest_d3_sha256")} and H1 '
                              f'{g.get("h1_manifest_sha256")}, not D3PIN {d3pin} and {h1_pin}')
        rec['gate_record'] = dict(path=str(gate_record), sha256=digest(Path(gate_record)), pins_equal=True)
    cmd = [sys.executable, '-B', str(ROOT / 'gen3/verify_d3.py'), str(payload), '--pin', d3pin]
    if verify_output is not None:
        cmd += ['--output', str(verify_output)]
    cp = subprocess.run(cmd, capture_output=True, text=True)
    rec['verify_d3'] = dict(command=' '.join(cmd[1:]), returncode=cp.returncode, stdout=cp.stdout[-2000:])
    if cp.returncode != 0:
        raise InputsError(f'{payload}: gen3/verify_d3.py --pin {d3pin} failed (exit {cp.returncode}); no member was read '
                          f'and nothing was written:\n{(cp.stdout + cp.stderr)[-1500:]}')
    sources = Stage2b(stage2b_files_from(payload, h1), d3pin, h1_pin, f'{payload} + {h1}', expect=expect)
    report: dict = {}
    m = build(None, log=log, d3=D3Build(sources, TarMembers(payload), store), report=report)
    rec.update(report=report, manifest_sha256=digest(ROOT / 'inputs/manifest.json'), counts=m['counts'],
               kernels=m['kernels'], l8_packs={r: m['sha256'][r] for r in L8_PACKS})
    return rec


def link_l8(store: Path, inputs: Path | None = None) -> dict:
    """`make link-l8 STORE=...`: hard-link the store's L8 packs that inputs/manifest.json pins into inputs/packs/."""
    d = Path(inputs).resolve() if inputs else (ROOT / 'inputs').resolve()
    sd = store_dir(store)
    m = json.loads((d / 'manifest.json').read_bytes())
    out = {}
    for rel in L8_PACKS:
        pin = (m.get('sha256') or {}).get(rel)
        if not isinstance(pin, str) or not SHA_RE.fullmatch(pin):
            raise InputsError(f'{d / "manifest.json"}: no L8 pack pinned ({rel}); nothing to link before Stage 2b')
        src, dst = sd / f'{pin}.pack', d / rel
        if not src.is_file():
            raise InputsError(f'{src}: not in the store (make inputs-l8 publishes it there)')
        if dst.exists() or dst.is_symlink():
            if not dst.is_symlink() and os.path.samefile(src, dst):
                out[rel] = dict(store=str(src), link='present')
                continue
            raise InputsError(f'{dst}: exists and is not the store blob {src.name} (remove it first)')
        out[rel] = dict(store=str(src), link=link_into(src, dst))
    return out


# ---- inputs_mini (PLAN B) -----------------------------------------------------------------------------------------
MINI_OWN = ('manifest.json', 'inventory.json', *L8_PACKS)


def refuse_package_inputs(dest, what: str) -> Path:
    """Refuse a test-inputs destination that overlaps the package's production inputs/ (equal to it, inside it, or
    containing it), lexically and with symlinks resolved, before anything is read or written (S4-003)."""
    prod = {Path(os.path.normpath(ROOT / 'inputs')), (ROOT / 'inputs').resolve()}
    cand = {Path(os.path.normpath(os.path.abspath(dest))), Path(dest).resolve()}
    for c in cand:
        for q in prod:
            if c == q or q in c.parents or c in q.parents:
                raise InputsError(f'{dest}: {what} overlaps the package inputs {q} (refused: test inputs never go into or '
                                  'over the production inputs/; nothing was read or written)')
    return Path(dest)


def refuse_mini_targets(dest, rels, what: str) -> Path:
    """R2-S1-05: refuse_package_inputs(dest), then every path written below dest for rels (each directory on the way,
    the file): one overlapping the package inputs/ (a symlinked descendant directory or leaf resolved) or existing as a
    symbolic link (never followed) is refused before anything is written."""
    refuse_package_inputs(dest, what)
    for rel in rels:
        q = Path(dest)
        for part in Path(rel).parts:
            q = q / part
            refuse_package_inputs(q, what)
            if q.is_symlink():
                raise InputsError(f'{q}: {what}: a symbolic link below the destination (refused: never followed; nothing '
                                  'was written)')
    return Path(dest)


def build_mini(out: Path | None = None) -> dict:
    """`make inputs-mini`: tests/fixtures/inputs_mini/ from the package inputs with the L8 packs present (see the module
    text). Deterministic; refuses an --out (the default too) overlapping the package inputs/ first, or any path it
    writes there (R2-S1-05), then inputs without the L8 packs or without the Stage-2b pins."""
    out = refuse_mini_targets(out if out is not None else ROOT / MINI, MINI_OWN, 'the inputs_mini output')
    d = ROOT / 'inputs'
    v = verify(d, env={})
    m = v['manifest']
    if m.get('d3_payload_manifest_sha256') is None or m.get('l8_present') is not True:
        raise InputsError(f'{d / "manifest.json"}: not the Stage-2b inputs (make inputs-l8 first)')
    sb = Stage2b(stage2b_files_in(d), m['d3_payload_manifest_sha256'], m['inventory8_d2_manifest_sha256'], 'inputs')
    inv = json.loads((d / 'inventory.json').read_bytes())
    mini = {'inspect_complete': inv['inspect_complete']}
    packs = {}
    for s in SECTORS:
        mini[s] = {L: inv[s][L] for L in inv[s] if L != '8'}
        pick = sorted(sorted(inv[s]['8'], key=lambda r: (r['length'], r['id']))[:MINI_PER_SECTOR], key=lambda r: r['id'])
        rows, data, off = [], [], 0
        with (d / f'packs/{s}_L8.pack').open('rb') as f:
            for r in pick:
                f.seek(r['offset'])
                b = f.read(r['length'])
                if _sha(b) != r['sha256'] or r['sha256'] != sb.member_sha(s, 8, r['id']):
                    raise InputsError(f'inputs/packs/{s}_L8.pack: member G{r["id"]} differs from its inventory row or '
                                      'MEMBERS_d3.sha256')
                rows.append({**r, 'offset': off})
                data.append(b)
                off += len(b)
        mini[s]['8'] = rows
        packs[f'packs/{s}_L8.pack'] = b''.join(data)
    inv_text = inventory_text(mini).encode()
    package_files = sorted(r for r in m['sha256'] if r not in MINI_OWN)
    man = {k: m[k] for k in ('schema', 'dimension', 'order', 'epsilon')}
    man.update(test_inputs=MINI_LABEL,
               sha256={**{r: m['sha256'][r] for r in package_files}, 'inventory.json': _sha(inv_text),
                       **{r: _sha(b) for r, b in packs.items()}},
               counts={s: {**{L: n for L, n in m['counts'][s].items() if L != '8'}, '8': MINI_PER_SECTOR} for s in SECTORS},
               kernels=sum(len(mini[s][L]) for s in SECTORS for L in mini[s]),
               l7_complete=m['l7_complete'], l8_present=True, inspect_complete=mini['inspect_complete'],
               inventory8_d2_manifest_sha256=m['inventory8_d2_manifest_sha256'],
               d3_payload_manifest_sha256=m['d3_payload_manifest_sha256'],
               vendored_assembly_handoff_sha256=m['vendored_assembly_handoff_sha256'],
               vendored_assembly=m['vendored_assembly'], package_files=package_files,
               selection={s: [r['id'] for r in mini[s]['8']] for s in SECTORS},
               rule=f'the {MINI_PER_SECTOR} smallest L8 kernels per sector by bytes, then id (PLAN B inputs_mini)')
    files = {'inventory.json': inv_text, **packs, 'manifest.json': (json.dumps(man, indent=2) + '\n').encode()}
    refuse_mini_targets(out, files, 'the inputs_mini output')   # R2-S1-05: again, now that the inputs are read
    stale = sorted(q.relative_to(out).as_posix() for q in out.rglob('*') if q.is_file()
                   and q.relative_to(out).as_posix() not in files and q.name != '.DS_Store') if out.is_dir() else []
    if stale:
        raise InputsError(f'{out}: unexpected files {stale[:5]} (nothing was written)')
    out.mkdir(parents=True, exist_ok=True)
    changed = []
    stage = Path(tempfile.mkdtemp(prefix='.inputs_mini_stage_', dir=out))   # R2-S1-05: fresh and private, no temp pre-exists
    try:
        for rel, b in files.items():
            p = out / rel
            if p.is_file() and not p.is_symlink() and p.read_bytes() == b:
                continue
            t = stage / rel.replace('/', '_')
            with open(t, 'xb') as f:
                f.write(b)
            refuse_mini_targets(out, [rel], 'the inputs_mini output')
            p.parent.mkdir(exist_ok=True)
            os.replace(t, p)   # replaces the entry: never writes through an existing file or link
            changed.append(rel)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return {'out': str(out), 'changed': changed, 'kernels_l8': {s: len(mini[s]['8']) for s in SECTORS},
            'sha256': {r: _sha(b) for r, b in files.items()}}


def materialize_mini(dest: Path, mini: Path | None = None, package_inputs: Path | None = None) -> Path:
    """A C8_INPUTS directory from tests/fixtures/inputs_mini/: its own files copied, the package files it pins
    (package_files) hard-linked from the package's inputs/ (copied across filesystems). verify(dest) then accepts it.
    R2-S1-05: DEST must be fresh (absent or an empty directory, not a link) and no path written below it may overlap the
    package inputs/, checked before anything is written; every file is created exclusively (never through a link)."""
    dest = refuse_package_inputs(dest, 'the materialized inputs_mini')
    mini = Path(mini) if mini is not None else ROOT / MINI
    src = Path(package_inputs) if package_inputs is not None else ROOT / 'inputs'
    m = json.loads((mini / 'manifest.json').read_bytes())
    if not m.get('test_inputs') or not isinstance(m.get('package_files'), list):
        raise InputsError(f'{mini / "manifest.json"}: not the inputs_mini manifest')
    for rel in m['package_files']:
        if not isinstance(rel, str) or rel.startswith('/') or '..' in Path(rel).parts or rel in MINI_OWN:
            raise InputsError(f'{mini / "manifest.json"}: package file {rel!r} refused')
    dest = refuse_mini_targets(dest, [*MINI_OWN, *m['package_files']], 'the materialized inputs_mini')
    if dest.is_symlink() or (dest.exists() and (not dest.is_dir() or any(dest.iterdir()))):
        raise InputsError(f'{dest}: the materialized inputs_mini needs a fresh destination (absent or an empty directory, '
                          'not a symbolic link); nothing was written')
    dest.mkdir(parents=True, exist_ok=True)
    for rel in MINI_OWN:
        (dest / rel).parent.mkdir(exist_ok=True)
        with open(mini / rel, 'rb') as f, open(dest / rel, 'xb') as g:
            shutil.copyfileobj(f, g)
    for rel in m['package_files']:
        link_into(src / rel, dest / rel)
    return dest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build', help='make inputs: build the inputs (the Stage-2a state, or the Stage-2b state from '
                                     'the package\'s own copies once the d3 pin is set)')
    b.add_argument('--out', type=Path, help='output directory (default: the package inputs/)')
    v = sub.add_parser('verify', help="check an inputs directory (what `plan` calls)")
    v.add_argument('--inputs', type=Path, help='default: C8_INPUTS, else the package inputs/')
    g = sub.add_parser('gate', help="the plan's input gate (C8_INPUTS, verify, test-only reasons)")
    g.add_argument('--test-only', action='store_true')
    l8 = sub.add_parser('l8', help='make inputs-l8: the Stage-2b inputs from the d=3 payload (verify_d3.py --pin first)')
    l8.add_argument('--d3payload', type=Path, required=True)
    l8.add_argument('--d3pin', default='', help='the sha256 of MANIFEST_d3.json (the A.5 gate record\'s pin); required')
    l8.add_argument('--store', type=Path, required=True)
    l8.add_argument('--h1', type=Path, help='the H1 copy (default: STORE/h1/<H1 sha12>)')
    l8.add_argument('--gate-record', type=Path, help='the A.5 gate record: D3PIN must equal its manifest_d3_sha256')
    l8.add_argument('--verify-output', type=Path, help="verify_d3.py's record")
    l8.add_argument('--output', type=Path, help='a JSON record of this run')
    l8.add_argument('--fixture-h1-pin', help=argparse.SUPPRESS)   # tests only: a miniature H1 tree, any counts
    lk = sub.add_parser('link-l8', help='make link-l8: hard-link the store\'s L8 packs into inputs/packs/')
    lk.add_argument('--store', type=Path, required=True)
    lk.add_argument('--inputs', type=Path)
    mi = sub.add_parser('mini', help='make inputs-mini: tests/fixtures/inputs_mini/ (needs the L8 packs)')
    mi.add_argument('--out', type=Path)
    mm = sub.add_parser('mini-materialize', help='a C8_INPUTS directory from tests/fixtures/inputs_mini/')
    mm.add_argument('--to', type=Path, required=True)
    a = ap.parse_args(argv)
    if a.command == 'l8' and not a.d3pin:
        print('REFUSED: make inputs-l8 needs D3PIN=<sha256 of MANIFEST_d3.json> (the A.5 gate record\'s pin; PLAN A.2 '
              'step 6); nothing was read', file=sys.stderr)
        return 2
    try:
        if a.command == 'build':
            m = build(a.out)
            print(json.dumps({'schema': m['schema'], 'counts': m['counts'], 'kernels': m['kernels'],
                              'l7_complete': m['l7_complete'], 'l8_present': m['l8_present'],
                              'inspect_complete': m['inspect_complete']}))
            return 0
        if a.command == 'l8':
            fx = a.fixture_h1_pin
            rec = inputs_l8(a.d3payload, a.d3pin, a.store, a.h1, a.gate_record, a.verify_output,
                            h1_pin=fx or H1_MANIFEST_SHA256, expect=None if fx else STAGE2B_COUNTS)
            if a.output:
                a.output.parent.mkdir(parents=True, exist_ok=True)
                a.output.write_text(json.dumps(rec, indent=1) + '\n')
            print(json.dumps({k: rec[k] for k in ('manifest_sha256', 'counts', 'kernels', 'l8_packs')}))
            return 0
        if a.command == 'link-l8':
            print(json.dumps(link_l8(a.store, a.inputs)))
            return 0
        if a.command == 'mini':
            print(json.dumps(build_mini(a.out)))
            return 0
        if a.command == 'mini-materialize':
            d = materialize_mini(a.to)
            r = verify(d, env={})
            print(json.dumps({'materialized': str(d), 'manifest_sha256': r['manifest_sha256']}))
            return 0
        r = verify(a.inputs) if a.command == 'verify' else plan_inputs(a.test_only)
    except (ValueError, OSError) as e:   # InputsError, common.verified_bytes' checksum mismatch, a missing file
        print(f'{"make inputs: FAILED" if a.command in ("build", "l8", "mini") else "REFUSED"}: {e}', file=sys.stderr)
        return 1
    r.pop('manifest')
    print(json.dumps(dict(status='verified', **r), indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
