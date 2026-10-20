#!/usr/bin/env python3
"""Replay of the d = 1 eighth-order frozen-cutoff HT campaign (HT_Pert/code/lri_c8_hpc, records data/HT_1d/c8).

Recomputes every quoted number of this package from the shipped records and the shipped code, without a solver run,
and prints a table  id | verdict | quoted | computed  (also written to <work>/replay_lri_c8_hpc.txt). Standard library
only; under a second. Exit status 1 on any FAIL.  Rows (ids as in results_map.md and the note's reproduction table):
  c8.manifest    MANIFEST_SHA256.json: its 164 files are shipped byte-identical (files in public/SCRUBBED.txt count as
                 scrubbed; nothing under src/ may be)
  c8.source      sha256 source digest of the shipped src/lri_c8/**/*.py (the solver's io.source_digest, recomputed
                 here) equals dd811aca... and the source_sha256 of the receipt, the campaign, all 42 outputs and both
                 export sidecars
  c8.envelopes   every lri-c8-sha256-v1 envelope under data/HT_1d/c8 (42 outputs, 42 lane journals, the campaign, the
                 validation receipt, 2 export sidecars = 88) verifies: sha256 of the canonical JSON of its payload
                 (sort_keys, separators (',', ':')); the campaign id 654fb90d19a573c1 is its sha256 prefix
  c8.reach       \\HTpLamCeight = 92: the accepted outputs and the campaign items are exactly {raw, vacuum_only} x even
                 Lambda = 52..92 (42 items); largest cutoff 92
  c8.lanes       42 lane journals of campaign 654fb90d19a573c1: one attempt each, exit 0, Slurm array 569698, task id =
                 lane, the lane's item = the campaign's lane, item status accepted with return code 0 and output_sha256
                 = the accepted envelope's sha256 (the 42 output hashes are exactly the accepted ones);
                 c8_L52-92/submissions.txt names array 569698, the campaign and lanes 0..41; total solver time
  c8.exports     exports/{raw,vacuum_only}_L52-92.json: sha256 of the bytes = the sidecar's sha256_export (cf3fec9e...,
                 dd98c5a4...), and the bytes equal json.dumps(accepted payloads sorted by cutoff, indent=2) + newline,
                 the serialization of `python -m lri_c8 export`
  c8.gates       all 42 outputs: |shell residual| <= 1.6e-14, low-order residual <= 7.9e-13, tuning residual <= 1.95e-9
                 (the bounds quoted with the C8 table); the tuning residual recomputed from the energy series equals the
                 recorded one; the solver's own acceptance (shell 1e-10, tuning 1e-6, low order 1e-7, E3 - E0 = C,
                 caps P <= 19, Q <= 16) holds
  c8.values      C8_raw(92) = 2883374.2546683108 and C8_vac(92) = 2883433.2067096015, exact (repr) in the outputs, the
                 exports and data.json
  c8.table       the C8 table of the HT note (Lambda = 50, 52, 56, ..., 88, 90, 92: C8 raw, C8 vac, vac - raw, raw C7,
                 raw C6, rounded as printed); Lambda = 50 from inputs/ (the original runs), the rest from the exports
  c8.validation  validation receipt of job 569659 (compute node, Xeon Gold 6148, production stack): pass, 164 manifest
                 files, pytest 74 of 74 with a fresh Numba cache, 38-point saved-grid replay bitwise, BeeGFS probe pass;
                 the campaign embeds this receipt. RECORDED: rerun by make test (pytest, grid) and make replay-full
  c8.original    original-solver comparison at Lambda = 60 in the receipt: raw C8 2488157.173328419 (original) vs
                 2488157.1733284392 (new), max |dC| 2.0e-8; vacuum_only 2488207.44642163 vs 2488207.4464216377,
                 7.5e-9; stored = ranked; the new values equal the production outputs at Lambda = 60 exactly.
                 RECORDED: recomputed by make replay-full (scripts/compare_original.py)
  c8.thermal     raw C0..C7 of the C8 code vs the separate thermal-d7 campaign of the HT solver lri_hpc_Hamitonian
                 (same lri_hpc core: src/lri_c8/_core/{basis,cache,kernels,operators,parallel}.py are its lri_hpc
                 files; different driver, cluster and runs), both tables of data.json: max over the 46 common
                 cutoffs (2..92) and k = 0..7 of |raw - thermal| / max(1, |raw|) = 6.1e-14 (2 significant digits);
                 raw C4(52) 26.246793314472836 vs 26.246793314472797. It checks the eighth-order driver, the
                 assembly and the runs, not the Fock-space and operator construction both codes share
  c8.datajson    data/HT_1d/c8/extrapolation/data.json has sha256 ccc77dfa...; its raw and vacuum_only tables equal the
                 shipped records exactly; public/build_data_json.py rebuilds it byte-identically from the records and the
                 thermal records of ../lri_hpc_Hamitonian/analysis/extended (SKIP for the rebuild when those are absent)
usage: python3 public/replay_c8.py [--data ../../data/HT_1d] [--thermal ../lri_hpc_Hamitonian/analysis/extended]
                                   [--work .work]"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
SRC = 'dd811aca899543c4533e0c3f5e54cea67ae0cd06e875ceae8d68edaf4247cb81'
CAMPAIGN = '654fb90d19a573c1'
ARRAY = '569698'
VALJOB = '569659'
DATA_SHA = 'ccc77dfa1e7d3955f3b8f22b2ea3b99ba649976605c5bac6bae39b5f2ad92faa'
EXPORT_SHA = {'raw': 'cf3fec9e80c434ef5afa62b396f016ec8a9ce18ae396fc6372b8e00dca0285aa',
              'vacuum_only': 'dd98c5a4af5f6b04de978da2e594fdda8057bf64efae03083e09d06fa169b443'}
SCHEMES = ('raw', 'vacuum_only')
CUTOFFS = tuple(range(52, 93, 2))
N_MANIFEST = 164
QUOTED = {
    'c8.reach': '92',
    'c8.values': ('2883374.2546683108', '2883433.2067096015'),
    'c8.gates': (1.6e-14, 7.9e-13, 1.95e-9),
    'c8.thermal': '6.1e-14',
    'c8.c4_52': ('26.246793314472836', '26.246793314472797'),
    'c8.original': {'raw': ('2488157.173328419', '2488157.1733284392', '2.0e-8'),
                    'vacuum_only': ('2488207.44642163', '2488207.4464216377', '7.5e-9')},
}
# HT note, Table "C8 data": Lambda: (C8 raw, C8 vac, vac - raw, raw C7, raw C6) as printed
QUOTED_TABLE = """
50 2317638.0112 2317684.6306 46.62 - -
52 2354391.0706 2354438.4716 47.4009 -110708.0765 5859.015488
56 2423734.8939 2423783.7786 48.8847 -113535.6573 5985.676553
60 2488157.1733 2488207.4464 50.2731 -116154.1200 6102.545624
64 2548286.6872 2548338.2640 51.5768 -118591.0097 6210.954445
68 2604639.8204 2604692.6253 52.8048 -120868.8211 6311.984075
72 2657645.7761 2657699.7411 53.9650 -123006.1568 6406.523716
76 2707665.1024 2707720.1664 55.0640 -125018.5724 6495.313304
80 2755003.5532 2755059.6606 56.1075 -126919.2046 6578.974934
84 2799922.6225 2799979.7230 57.1005 -128719.2459 6658.036463
88 2842647.6681 2842705.7155 58.0474 -130428.3080 6732.949501
90 2863249.5651 2863308.0699 58.5048 -131251.3643 6768.974104
92 2883374.2547 2883433.2067 58.9520 -132054.7049 6804.103321
"""
ROWS = []


def row(rid, verdict, quoted, detail):
    if verdict is True:
        verdict = 'PASS'
    elif verdict is False:
        verdict = 'FAIL'
    ROWS.append((rid, verdict, quoted, detail))


def sci(x, d):
    """x in scientific notation with d decimals and no exponent padding, as the note prints it (2.0e-8, 6.1e-14)."""
    m, e = f'{x:.{d}e}'.split('e')
    return f'{m}e{int(e)}'


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def envelope_ok(d):
    return (isinstance(d, dict) and d.get('format') == 'lri-c8-sha256-v1'
            and hashlib.sha256(canonical(d['payload'])).hexdigest() == d.get('sha256'))


def source_digest(root):
    """io.source_digest() of the solver, recomputed (standard library)."""
    h = hashlib.sha256()
    for p in sorted(root.rglob('*.py')):
        h.update(str(p.relative_to(root)).encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def scrubbed():
    p = HERE / 'SCRUBBED.txt'
    if not p.exists():
        return set()
    return {l.strip() for l in p.read_text().splitlines() if l.strip() and not l.startswith('#')}


def guard(rid, quoted):
    """Decorator: an exception inside a row's check is that row's FAIL, not a crash of the replay."""
    def wrap(f):
        def g(*a, **k):
            try:
                return f(*a, **k)
            except Exception as e:  # noqa: BLE001
                row(rid, False, quoted, f'error: {type(e).__name__}: {e}')
        return g
    return wrap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', type=Path, default=PKG / '..' / '..' / 'data' / 'HT_1d')
    ap.add_argument('--thermal', type=Path, default=PKG / '..' / 'lri_hpc_Hamitonian' / 'analysis' / 'extended')
    ap.add_argument('--work', type=Path, default=PKG / '.work')
    a = ap.parse_args()
    D = a.data / 'c8'
    ACC = D / 'c8_L52-92' / 'accepted'
    JRN = D / 'c8_L52-92' / 'journals' / CAMPAIGN
    load = lambda p: json.loads(Path(p).read_text())
    acc = {}       # (scheme, cutoff) -> envelope
    for s in SCHEMES:
        for L in CUTOFFS:
            p = ACC / f'{s}_L{L}_d8.json'
            if p.exists():
                acc[s, L] = load(p)
    receipt = load(D / 'validation' / f'receipt_{SRC[:16]}.json')
    campaign = load(D / 'campaigns' / 'c8_L52-92.json')
    sidecar = {s: load(D / 'exports' / f'{s}_L52-92.provenance.json') for s in SCHEMES}
    datajson = D / 'extrapolation' / 'data.json'
    dj = load(datajson)

    # c8.manifest
    @guard('c8.manifest', f'{N_MANIFEST} files')
    def c_manifest():
        man, scr = load(PKG / 'MANIFEST_SHA256.json'), scrubbed()
        same = [k for k, v in man.items() if (PKG / k).is_file() and sha_file(PKG / k) == v]
        scr_seen = [k for k in man if k not in same and k in scr and (PKG / k).is_file() and not k.startswith('src/')]
        bad = [k for k in man if k not in same and k not in scr_seen]
        row('c8.manifest', len(man) == N_MANIFEST and not bad, f'{N_MANIFEST} files',
            f'{len(same)}/{len(man)} byte-identical, {len(scr_seen)} scrubbed (public/SCRUBBED.txt), mismatched {bad}')
    c_manifest()

    # c8.source
    @guard('c8.source', SRC[:16] + '...')
    def c_source():
        d = source_digest(PKG / 'src' / 'lri_c8')
        holders = {'receipt': receipt['payload']['source_sha256'], 'campaign': campaign['payload']['source_sha256']}
        holders.update({f'sidecar {s}': sidecar[s]['payload']['config']['source_sha256'] for s in SCHEMES})
        outs = {e['payload']['config']['source_sha256'] for e in acc.values()}
        ok = d == SRC and all(v == SRC for v in holders.values()) and outs == {SRC} and len(acc) == 42
        n = len(list((PKG / 'src' / 'lri_c8').rglob('*.py')))
        row('c8.source', ok, SRC[:16] + '...',
            f'digest of the shipped src/lri_c8 ({n} .py files) {d[:16]}...; receipt, campaign, 2 sidecars and '
            f'{len(acc)} outputs name {SRC[:16]}...: {ok}')
    c_source()

    # c8.envelopes
    @guard('c8.envelopes', '88 envelopes verify')
    def c_envelopes():
        flat = {D / 'extrapolation' / 'data.json'} | {D / 'exports' / f'{s}_L52-92.json' for s in SCHEMES}
        files = sorted(p for p in D.rglob('*.json') if p not in flat)
        bad = [str(p.relative_to(D)) for p in files if not envelope_ok(load(p))]
        kinds = {'outputs': len(list(ACC.glob('*.json'))), 'journals': len(list(JRN.glob('lane_*.json'))),
                 'campaign': 1, 'receipt': 1, 'sidecars': 2}
        ok = not bad and len(files) == 88 and campaign['sha256'][:16] == CAMPAIGN and sum(kinds.values()) == 88
        row('c8.envelopes', ok, '88 envelopes verify',
            f'{len(files) - len(bad)}/{len(files)} envelopes verify ({kinds}); campaign id {campaign["sha256"][:16]}; '
            f'bad {bad}')
    c_envelopes()

    # c8.reach
    @guard('c8.reach', QUOTED['c8.reach'])
    def c_reach():
        want = {(s, L) for s in SCHEMES for L in CUTOFFS}
        have = {(e['payload']['scheme'], e['payload']['cutoff']) for e in acc.values()}
        files = {p.name for p in ACC.glob('*.json')}
        items = {(i['scheme'], i['cutoff']) for i in campaign['payload']['items']}
        lanes = campaign['payload']['lanes']
        lam = max(L for _, L in have)
        ok = (have == want and len(files) == 42 and items == want and len(lanes) == 42
              and all(len(x) == 1 for x in lanes) and str(lam) == QUOTED['c8.reach'] and max(map(int, dj['raw'])) == lam)
        row('c8.reach', ok, QUOTED['c8.reach'],
            f'Lambda_max = {lam}; {len(have)} accepted outputs = {{raw, vacuum_only}} x even 52..92: {have == want}; '
            f'campaign {len(items)} items, {len(lanes)} lanes of one item')
    c_reach()

    # c8.lanes
    @guard('c8.lanes', f'42 lanes, 1 attempt each, exit 0, array {ARRAY}')
    def c_lanes():
        accsha = {(s, L): e['sha256'] for (s, L), e in acc.items()}
        lanes = campaign['payload']['lanes']
        problems, outs, hosts, secs = [], set(), set(), 0.0
        jfiles = sorted(JRN.glob('lane_*.json'))
        for k in range(42):
            p = JRN / f'lane_{k}.json'
            if not p.exists():
                problems.append(f'lane {k} missing'); continue
            j = load(p)['payload']
            at = j['attempts']
            good = j['campaign'] == CAMPAIGN and j['lane'] == k and len(at) == 1
            if good:
                t = at[0]
                good = (t.get('exit') == 0 and t.get('slurm_array_job_id') == ARRAY
                        and t.get('slurm_array_task_id') == str(k) and len(t['items']) == 1)
                if good:
                    it = t['items'][0]
                    key = (it['item']['scheme'], it['item']['cutoff'])
                    good = (it['item'] == lanes[k][0] and it['status'] == 'accepted' and it['returncode'] == 0
                            and accsha.get(key) == it['output_sha256'])
                    outs.add(it['output_sha256']); hosts.add(t['host']); secs += it['seconds']
            if not good:
                problems.append(f'lane {k}')
        sub = (D / 'c8_L52-92' / 'submissions.txt').read_text().split()
        sub_ok = (len(sub) == 4 and sub[0] == ARRAY and sub[1].endswith(CAMPAIGN)
                  and sub[3] == 'lanes=' + ','.join(map(str, range(42))))
        ok = not problems and len(jfiles) == 42 and outs == set(accsha.values()) and sub_ok
        row('c8.lanes', ok, f'42 lanes, 1 attempt each, exit 0, array {ARRAY}',
            f'{len(jfiles)} journals, problems {problems}; output hashes = accepted: {outs == set(accsha.values())}; '
            f'submissions.txt: {sub_ok}; {len(hosts)} hosts; total solver time {secs:.1f} s')
    c_lanes()

    # c8.exports
    @guard('c8.exports', 'sha256_export cf3fec9e..., dd98c5a4...')
    def c_exports():
        msgs, ok = [], True
        for s in SCHEMES:
            b = (D / 'exports' / f'{s}_L52-92.json').read_bytes()
            h = hashlib.sha256(b).hexdigest()
            pl = sorted((acc[s, L]['payload'] for L in CUTOFFS), key=lambda r: r['cutoff'])
            blob = (json.dumps(pl, indent=2, allow_nan=False) + '\n').encode()
            sc = sidecar[s]['payload']
            good = (h == sc['sha256_export'] == EXPORT_SHA[s] and blob == b and sc['config']['scheme'] == s
                    and envelope_ok(sidecar[s]))
            ok = ok and good
            msgs.append(f'{s}: sha256 {h[:8]}... = sidecar {sc["sha256_export"][:8]}..., bytes = re-serialized outputs: '
                        f'{blob == b}')
        row('c8.exports', ok, 'sha256_export cf3fec9e..., dd98c5a4...', '; '.join(msgs))
    c_exports()

    # c8.gates
    q = QUOTED['c8.gates']

    qs = f'shell <= {sci(q[0], 1)}, low order <= {sci(q[1], 1)}, tuning <= {sci(q[2], 2)}'

    @guard('c8.gates', qs)
    def c_gates():
        mx = [0.0, 0.0, 0.0]
        bad = []
        spin, shadow = [.25, -.25] + [0.] * 7, [.75, .25] + [0.] * 7
        for (s, L), e in sorted(acc.items()):
            p = e['payload']
            E, C = p['energies'], p['C']
            tun = max(max(abs(E[1][i] - E[0][i] - spin[i]) for i in range(9)),
                      max(abs(E[2][i] - E[0][i] - shadow[i]) for i in range(9)))
            v = (abs(p['second_order_shell_residual']), p['low_order_residual'], p['tuning_residual'])
            mx = [max(x, y) for x, y in zip(mx, v)]
            own = (v[0] <= 1e-10 and v[1] <= 1e-7 and v[2] <= 1e-6 and p['particle_cap'] == 19
                   and p['nonzero_particle_cap'] == 16 and p['degree'] == 8 and p['dtype'] == 'float64'
                   and not p['fastmath']
                   and all(abs(E[3][i] - E[0][i] - C[i]) <= 1e-8 + 2e-14 * abs(C[i]) for i in range(9)))
            if not (tun == p['tuning_residual'] and own and all(x <= y for x, y in zip(v, q))):
                bad.append(f'{s} {L}')
        row('c8.gates', not bad and len(acc) == 42, qs,
            f'max over 42 outputs: shell {mx[0]:.3e}, low order {mx[1]:.3e}, tuning {mx[2]:.4e} (recomputed from the '
            f'energies = recorded); solver acceptance holds; failing {bad}')
    c_gates()

    # c8.values
    qv = QUOTED['c8.values']

    @guard('c8.values', f'C8_raw(92) = {qv[0]}, C8_vac(92) = {qv[1]}')
    def c_values():
        got, ok = [], True
        for s, want in zip(SCHEMES, qv):
            vals = {repr(acc[s, 92]['payload']['C'][8]), repr(dj[s]['92'][8])}
            vals |= {repr(r['C'][8]) for r in load(D / 'exports' / f'{s}_L52-92.json') if r['cutoff'] == 92}
            ok = ok and vals == {want}
            got.append(f'{s} {sorted(vals)}')
        row('c8.values', ok, f'C8_raw(92) = {qv[0]}, C8_vac(92) = {qv[1]}',
            '; '.join(got) + ' (outputs, exports, data.json)')
    c_values()

    # c8.table
    @guard('c8.table', 'HT note C8 table, 13 rows')
    def c_table():
        ex = {s: {r['cutoff']: r for r in load(D / 'exports' / f'{s}_L52-92.json')} for s in SCHEMES}
        for s in SCHEMES:
            ex[s][50] = load(PKG / 'inputs' / s / f'{s}_L50_d8.json')
        bad, n = [], 0
        for line in QUOTED_TABLE.strip().split('\n'):
            t = line.split()
            L = int(t[0])
            a, b = ex['raw'][L]['C'], ex['vacuum_only'][L]['C']
            dec = len(t[3].split('.')[1])
            got = [str(L), f'{a[8]:.4f}', f'{b[8]:.4f}', f'{b[8] - a[8]:.{dec}f}',
                   f'{a[7]:.4f}' if t[4] != '-' else '-', f'{a[6]:.6f}' if t[5] != '-' else '-']
            n += 1
            if got != t:
                bad.append((L, got))
        row('c8.table', not bad and n == 13, 'HT note C8 table, 13 rows',
            f'{n} rows (Lambda = 50 from inputs/, 52..92 from the exports) rounded as printed; mismatches {bad}')
    c_table()

    # c8.validation
    @guard('c8.validation', f'job {VALJOB}: 74/74 tests, 38-point grid bitwise')
    def c_validation():
        r = receipt['payload']
        st = r['steps']
        grid = re.search(r"'bitwise_equal': (\d+), 'points': (\d+), 'outside_tolerance': (\d+)", st['grid_replay']['tail'])
        fs = json.loads(st['fs_probe']['tail'])
        stack = r['stack']
        ok = (envelope_ok(receipt) and campaign['payload']['receipt'] == r and r['status'] == 'pass'
              and r['returncode'] == 0 and r['kind'] == 'compute-node' and r['full'] is True
              and r['slurm']['slurm_job_id'] == VALJOB and r['slurm']['slurm_job_partition'] == 'defq'
              and 'Xeon(R) Gold 6148' in r['cpu_model'] and r['compare_cutoff'] == 60
              and (stack['python'], stack['numpy'], stack['numba'], stack['scipy']) == ('3.11.4', '1.24.3', '0.57.0', '1.10.1')
              and r['numba_threading_layer_setting'] == 'tbb'
              and all(s['returncode'] == 0 for s in st.values())
              and st['manifest']['tail'].strip() == f'{N_MANIFEST} manifest-listed files verified'
              and st['pytest']['counts'] == {'passed': 74} and st['pytest']['collected'] == 74
              and st['pytest']['fresh_numba_cache'] is True
              and grid is not None and grid.groups() == ('38', '38', '0') and fs['pass'] is True)
        verdict = 'RECORDED' if ok else 'FAIL'
        row('c8.validation', verdict, f'job {VALJOB}: 74/74 tests, 38-point grid bitwise',
            f'receipt (self-hashed, embedded in the campaign): {r["status"]}, {r["kind"]}, {r["cpu_model"]}, '
            f'Python {stack["python"]} numpy {stack["numpy"]} numba {stack["numba"]}; manifest '
            f'{st["manifest"]["tail"].split()[0]} files; pytest {st["pytest"]["counts"]} of {st["pytest"]["collected"]}; '
            f'grid {grid.group(1) if grid else "?"}/{grid.group(2) if grid else "?"} bitwise; {r["seconds"]:.1f} s '
            f'[rerun: make test, make replay-full]')
    c_validation()

    # c8.original
    qo = QUOTED['c8.original']

    @guard('c8.original', 'Lambda = 60: raw 2.0e-8, vacuum_only 7.5e-9')
    def c_original():
        st = receipt['payload']['steps']['original_comparison']
        recs = {}
        for ln in st['tail'].strip().split('\n'):
            j = json.loads(ln)
            recs[j['scheme']] = j
        msgs, ok = [], st['returncode'] == 0 and set(recs) == set(SCHEMES)
        for s in SCHEMES:
            j = recs[s]
            want_o, want_n, want_d = qo[s]
            same_prod = j['C8_new'] == acc[s, 60]['payload']['C'][8]
            good = (j['cutoff'] == 60 and repr(j['C8_original']) == want_o and repr(j['C8_new']) == want_n
                    and sci(j['max_abs']['C'], 1) == want_d and j['stored_equals_ranked'] is True
                    and j['within_tolerance'] is True and same_prod)
            ok = ok and good
            msgs.append(f'{s}: original {j["C8_original"]!r}, new {j["C8_new"]!r} (= production output at 60: '
                        f'{same_prod}), max |dC| {j["max_abs"]["C"]:.1e}, r {j["max_abs"]["r"]:.1e}, '
                        f'g {j["max_abs"]["g"]:.1e}, E {j["max_abs"]["energies"]:.1e}, stored = ranked '
                        f'{j["stored_equals_ranked"]}')
        row('c8.original', 'RECORDED' if ok else 'FAIL', 'Lambda = 60: raw 2.0e-8, vacuum_only 7.5e-9',
            '; '.join(msgs) + ' [rerun: make replay-full]')
    c_original()

    # c8.thermal
    @guard('c8.thermal', QUOTED['c8.thermal'])
    def c_thermal():
        raw, th = dj['raw'], dj['thermal_d7']
        common = [k for k in raw if k in th]
        worst, arg, worst52 = 0.0, None, 0.0
        for k in common:
            for i in range(8):
                v = abs(raw[k][i] - th[k][i]) / max(1.0, abs(raw[k][i]))
                if v > worst:
                    worst, arg = v, (k, i)
                if int(k) >= 52:
                    worst52 = max(worst52, v)
        c4 = (repr(raw['52'][4]), repr(th['52'][4]))
        ok = (sci(worst, 1) == QUOTED['c8.thermal'] and c4 == QUOTED['c8.c4_52']
              and len(common) == 46 and min(map(int, common)) == 2 and max(map(int, common)) == 92)
        row('c8.thermal', ok, QUOTED['c8.thermal'],
            f'max |raw - thermal|/max(1,|raw|) over {len(common)} cutoffs x C0..C7 = {worst:.4e} at Lambda = '
            f'{arg[0]}, k = {arg[1]} (Lambda = 52..92 alone: {worst52:.2e}); raw C4(52) {c4[0]} vs thermal {c4[1]}')
    c_thermal()

    # c8.datajson
    @guard('c8.datajson', f'sha256 {DATA_SHA[:8]}...')
    def c_datajson():
        h = sha_file(datajson)
        tables_ok = True
        for s in SCHEMES:
            rows = {}
            for p in sorted((PKG / 'inputs' / s).glob(f'{s}_L*_d8.json')):
                r = load(p)
                rows[int(r['cutoff'])] = r['C']
            for r in load(D / 'exports' / f'{s}_L52-92.json'):
                rows[int(r['cutoff'])] = r['C']
            tables_ok = tables_ok and dj[s] == {str(k): rows[k] for k in sorted(rows)}
        need = [a.thermal / f for f in ('thermal_new.json', 'C7_extension.json', 'prior_c7/C7_completed_runs.json')]
        base = f'shipped sha256 {h[:8]}...; raw and vacuum_only tables = records: {tables_ok}'
        if not (h == DATA_SHA and tables_ok):
            row('c8.datajson', False, f'sha256 {DATA_SHA[:8]}...', base)
            return
        if not all(p.exists() for p in need):
            row('c8.datajson', 'SKIP', f'sha256 {DATA_SHA[:8]}...',
                base + f'; rebuild skipped: thermal records absent ({a.thermal})')
            return
        out = a.work.resolve() / 'c8_data_rebuilt.json'
        r = subprocess.run([sys.executable, str(HERE / 'build_data_json.py'), str(out), '--data', str(a.data),
                            '--thermal', str(a.thermal)], capture_output=True, text=True)
        h2 = sha_file(out) if out.exists() else 'missing'
        row('c8.datajson', r.returncode == 0 and h2 == DATA_SHA, f'sha256 {DATA_SHA[:8]}...',
            base + f'; public/build_data_json.py rebuild sha256 {h2[:8]}... byte-identical: {h2 == DATA_SHA}')
    a.work.mkdir(parents=True, exist_ok=True)
    c_datajson()

    w = max(len(r[0]) for r in ROWS)
    lines = [f'{"id":{w}s}  verdict   quoted  |  computed']
    for rid, st, qq, det in ROWS:
        lines.append(f'{rid:{w}s}  {st:8s}  {qq}  |  {det}')
    cnt = {k: sum(r[1] == k for r in ROWS) for k in ('PASS', 'FAIL', 'INFO', 'RECORDED', 'SKIP')}
    lines.append(f'# replay_c8: {cnt["PASS"]} PASS, {cnt["FAIL"]} FAIL, {cnt["INFO"]} INFO, {cnt["RECORDED"]} RECORDED, '
                 f'{cnt["SKIP"]} SKIP ({len(ROWS)} rows)')
    text = '\n'.join(lines) + '\n'
    print(text, end='')
    (a.work / 'replay_lri_c8_hpc.txt').write_text(text)
    sys.exit(1 if cnt['FAIL'] else 0)


if __name__ == '__main__':
    main()
