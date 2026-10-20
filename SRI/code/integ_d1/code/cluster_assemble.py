"""Assemble cluster_engine output: J^{(k)}(K) = sum_patterns factor * sum_j Gamma^{(j)}(alpha) A^{(k)}_j, alpha = 2n-1-2nK.
cx mode: values at one complex K.  ser mode: Laurent coefficients in w = 1 - K of A^{(k)}_j and of J^{(k)}."""
import sys, re
import mpmath as mp


class OutputError(ValueError):
    pass


def hx(s):
    v = mp.mpf(float.fromhex(s))
    if not mp.isfinite(v):
        raise OutputError(f'nonfinite value {s}')
    return v


def read_out(path, strict=True):
    """Read and VALIDATE one engine output file. Rejects (OutputError) truncated or malformed files:
    header present; every sector block has the complete record set (cx: A k j for k <= kmax, j <= 2k;
    ser: exactly LS contiguous exponents per (k, j)); no duplicates; finite values; the '# total' footer;
    for files written by the fingerprinting engine also the per-sector 'end sector' markers and the
    '# complete sectors s0 s1' footer matching the sector set. Returns (header, sectors); header['fingerprint']
    holds the run fingerprint (None for legacy files written before fix round 1)."""
    hdr, secs, cur = None, {}, None
    fp, total, complete, ends, legacy_args = None, False, None, set(), None
    with open(path) as fh:
        lines = fh.read().split('\n')
    if lines and lines[-1] == '':
        lines = lines[:-1]
    for ln, line in enumerate(lines, 1):
        def bad(msg):
            raise OutputError(f'{path}:{ln}: {msg}')
        try:
            if line.startswith('# n '):
                if hdr is not None: bad('second header')
                p = line.split()[1:]; hdr = {}; i = 0
                nval = {'K': 2, 'Kdd': 4}
                while i < len(p):
                    k = p[i]; m = nval.get(k, 1)
                    hdr[k] = p[i + 1] if m == 1 else p[i + 1:i + 1 + m]; i += 1 + m
            elif line.startswith('# fingerprint'):
                p = line.split()[2:]; fp = dict(zip(p[0::2], p[1::2]))
            elif line.startswith('# args'):
                legacy_args = line[len('# args '):]
            elif line.startswith('# total'):
                total = True
            elif line.startswith('# complete sectors'):
                p = line.split(); complete = (int(p[3]), int(p[4]))
            elif line.startswith('sector '):
                if hdr is None: bad('sector before header')
                if total: bad('sector after footer')
                p = line.split(); cur = int(p[1])
                if cur in secs: bad(f'sector {cur} twice')
                secs[cur] = dict(pat=int(p[3]), time=float(p[5]), A={}, S={},
                                 nterm=int(p[7]) if len(p) > 7 and p[6] == 'nterm' else None)
            elif line.startswith('end sector '):
                if int(line.split()[2]) != cur: bad('end marker for the wrong sector')
                ends.add(cur)
            elif line.startswith('A '):
                if cur is None: bad('record outside a sector')
                p = line.split(); k, j = int(p[1]), int(p[2])
                if (k, j) in secs[cur]['A']: bad('duplicate record')
                secs[cur]['A'][(k, j)] = mp.mpc(hx(p[3]) + hx(p[4]), hx(p[5]) + hx(p[6]))
            elif line.startswith('B '):
                # magnitude bounds (MSC-020): ser 'B k j e v', cx 'B k j v'; unique keys; finite, nonnegative
                if cur is None: bad('record outside a sector')
                if hdr is None or hdr.get('bound') != '1': bad('magnitude-bound record in an output without bound 1')
                p = line.split()
                want = 5 if hdr['mode'] == 'ser' else 4
                if len(p) != want: bad(f'B record with {len(p) - 1} fields (expected {want - 1})')
                key = tuple(int(x) for x in p[1:-1])
                v = float.fromhex(p[-1])
                if not (v >= 0 and v < float('inf')): bad('bad magnitude bound')
                Bd = secs[cur].setdefault('B', {})
                if key in Bd: bad(f'duplicate B record {key}')
                Bd[key] = v
            elif line.startswith('S '):
                if cur is None: bad('record outside a sector')
                p = line.split(); k, j, e = int(p[1]), int(p[2]), int(p[3])
                if (k, j, e) in secs[cur]['S']: bad('duplicate record')
                secs[cur]['S'][(k, j, e)] = mp.mpc(hx(p[4]) + hx(p[5]), hx(p[6]) + hx(p[7]))
            elif line.startswith('#') or not line.strip():
                continue
            else:
                bad(f'unrecognized line {line[:40]!r}')
        except OutputError:
            raise
        except (ValueError, IndexError, KeyError, TypeError) as ex:
            bad(f'malformed line ({ex.__class__.__name__}): {line[:60]!r}')
    if hdr is None:
        raise OutputError(f'{path}: no header')
    hdr['fingerprint'] = fp
    hdr['args'] = legacy_args
    if not strict:
        return hdr, secs
    if not total:
        raise OutputError(f'{path}: no completion footer (truncated run)')
    kmax = int(hdr['kmax'])
    LS = int(hdr['LS'])
    for s, d in secs.items():
        if hdr['mode'] == 'cx':
            want = {(k, j) for k in range(kmax + 1) for j in range(2 * k + 1)}
            if set(d['A']) != want or d['S']:
                raise OutputError(f'{path}: sector {s} incomplete coefficient records')
        elif hdr['mode'] == 'ser':
            if d['A']: raise OutputError(f'{path}: sector {s} has cx records in a ser file')
            for k in range(kmax + 1):
                for j in range(2 * k + 1):
                    es = sorted(e for (kk, jj, e) in d['S'] if (kk, jj) == (k, j))
                    if len(es) != LS or es != list(range(es[0], es[0] + LS)):
                        raise OutputError(f'{path}: sector {s} (k={k}, j={j}) has {len(es)} of {LS} coefficients')
            if any(kk > kmax or jj > 2 * kk for (kk, jj, e) in d['S']):
                raise OutputError(f'{path}: sector {s} has records beyond kmax')
        else:
            raise OutputError(f'{path}: unknown mode')
        # MSC-020: bound-enabled outputs carry a complete magnitude-bound set (same shape as the values)
        if hdr.get('bound') == '1':
            B = d.get('B')
            if not B: raise OutputError(f'{path}: sector {s} has no magnitude bounds although bound 1')
            # MSC-026: valid indices (0 <= k <= kmax, 0 <= j <= 2k) and EXACT key-set equality with the values
            # (cx: the A keys; ser: the S keys, i.e. the same LS-coefficient window for every (k, j))
            klen = 2 if hdr['mode'] == 'cx' else 3
            if any(len(key) != klen or not (0 <= key[0] <= kmax) or not (0 <= key[1] <= 2 * key[0]) for key in B):
                raise OutputError(f'{path}: sector {s} has magnitude bounds with invalid (k, j) indices')
            if hdr['mode'] == 'cx':
                if set(B) != set(d['A']):
                    raise OutputError(f'{path}: sector {s} magnitude-bound keys differ from the value keys')
            else:
                if set(B) != set(d['S']):
                    raise OutputError(f'{path}: sector {s} magnitude-bound windows differ from the value windows')
        elif d.get('B'):
            raise OutputError(f'{path}: sector {s} has magnitude bounds although bound is not 1')
    if fp is not None or ends or complete is not None:
        # fingerprinting engine: markers are mandatory
        if fp is None: raise OutputError(f'{path}: markers without fingerprint')
        if ends != set(secs): raise OutputError(f'{path}: missing end markers for {sorted(set(secs) - ends)}')
        if complete is None or set(range(*complete)) != set(secs):
            raise OutputError(f'{path}: completion footer does not match the sector set')
    return hdr, secs


def make_manifest(input_path):
    """Independent sector manifest of an engine input file: sha256, n, and per sector its pattern index and
    number of terms (parsed from the input itself)."""
    import hashlib
    raw = open(input_path, 'rb').read()
    toks = raw.decode().split('\n')
    n = int(toks[0].split()[1])
    sectors, pat = [], -1
    for line in toks:
        if line.startswith('pattern '): pat += 1
        elif line.startswith('sector '): sectors.append({'pat': pat})
        elif line.startswith('nterm '): sectors[-1]['nterm'] = int(line.split()[1])
    return {'input': input_path.rsplit('/', 1)[-1], 'input_sha256': hashlib.sha256(raw).hexdigest(), 'n': n,
            'nsec': len(sectors), 'sectors': sectors}


def check_against_manifest(secs, hdrs, manifest, expected=None):
    """Exact sector-set equality with the manifest (or with `expected`, a subset of its sectors, e.g. the sectors of
    nonzero mirror weight), pattern and term counts per sector, and (for fingerprinted files) the input hash.
    Raises OutputError."""
    want = set(range(manifest['nsec'])) if expected is None else set(expected)
    if not want <= set(range(manifest['nsec'])):
        raise OutputError('expected sector set is not a subset of the manifest')
    got = set(secs)
    if got != want:
        raise OutputError(f'sector set mismatch: missing {sorted(want - got)[:20]}, unexpected {sorted(got - want)[:20]}')
    for s, d in secs.items():
        m = manifest['sectors'][s]
        if d['pat'] != m['pat']:
            raise OutputError(f'sector {s}: pattern {d["pat"]} != manifest {m["pat"]}')
        if d.get('nterm') is not None and d['nterm'] != m['nterm']:
            raise OutputError(f'sector {s}: {d["nterm"]} terms != manifest {m["nterm"]}')
    for path, h in hdrs.items():
        fp = h.get('fingerprint')
        if fp is not None and fp.get('input_sha256') != manifest['input_sha256']:
            raise OutputError(f'{path}: engine input hash {fp.get("input_sha256")} != manifest {manifest["input_sha256"]}')


def legacy_allowlist():
    """The hash-listed legacy outputs (results/legacy_outputs.json). Tests may add entries for temporary copies through
    LRI_TEST_LEGACY_ALLOWLIST (a JSON file of the same form); the gates refuse to publish while it is set."""
    import json, os, sys
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results', 'legacy_outputs.json')
    files = json.load(open(p))['files'] if os.path.exists(p) else {}
    extra = os.environ.get('LRI_TEST_LEGACY_ALLOWLIST')
    if extra:
        print('WARNING: test allowlist override LRI_TEST_LEGACY_ALLOWLIST in use', file=sys.stderr)
        files = dict(files); files.update(json.load(open(extra))['files'])
    return files


def verify_runner_sidecar(path, hdr, secs):
    """MSC-022: a fingerprinted engine output is consumed only together with the runner's sidecar PATH.fp
    (m3_tasks.sbatch / m4_tasks.sbatch): line 1 'engine_sha256=.. build=.. input_sha256=.. args=..', line 2
    'output_sha256=..'. The recorded output checksum must equal the file's, and build, input hash, argument list
    (without -o) and sector range must agree with the output header and its sector set."""
    import hashlib, os, shlex, re
    fpf = path + '.fp'
    if not os.path.isfile(fpf):
        raise OutputError(f'{path}: no runner fingerprint sidecar {os.path.basename(fpf)}')
    lines = open(fpf).read().split('\n')
    m = re.match(r'engine_sha256=(\S+) build=(\S+) input_sha256=(\S+) args=(.*)$', lines[0] if lines else '')
    if not m or len(lines) < 2 or not lines[1].startswith('output_sha256='):
        raise OutputError(f'{fpf}: malformed runner fingerprint')
    if lines[1][len('output_sha256='):] != hashlib.sha256(open(path, 'rb').read()).hexdigest():
        raise OutputError(f'{path}: content differs from the runner-recorded output checksum')
    fp = hdr['fingerprint']
    if m.group(2) != fp.get('build') or m.group(3) != fp.get('input_sha256'):
        raise OutputError(f'{path}: runner sidecar build/input differ from the output header')
    rargs = shlex.split(m.group(4))
    hargs = shlex.split(hdr.get('args') or '')
    if '-o' in hargs:
        i = hargs.index('-o'); del hargs[i:i + 2]
    if rargs != hargs:
        raise OutputError(f'{path}: runner-recorded arguments differ from the output header')
    if '-sec' in rargs:
        i = rargs.index('-sec'); rng = (int(rargs[i + 1]), int(rargs[i + 2]))
    else:
        rng = (0, int(fp['nsec_input']))
    if (int(fp['sec0']), int(fp['sec1'])) != rng or set(secs) != set(range(*rng)):
        raise OutputError(f'{path}: sector range differs from the runner-recorded arguments')


def read_many(paths, manifest=None, approved_builds=None, expected=None):
    """Read and validate several sector files, merge (no sector twice), check run-parameter consistency and the
    manifest. Build consistency (MSC-014): either every file carries a fingerprint with ONE common build id (in
    approved_builds if given), or every file is a pre-fix-round-1 legacy output whose sha256 is listed in
    results/legacy_outputs.json. Returns (header0, sectors, headers)."""
    import hashlib, os
    secs, hdrs, hdr0 = {}, {}, None
    builds, legacy = set(), []
    allow = None
    for p in paths:
        h, s = read_out(p)
        if hdr0 is None: hdr0 = h
        for key in ('n', 'mode', 'kmax', 'tau', 'nseg', 'm', 'nplain', 'taurat', 'LS', 'VMIN', 'K', 'Kdd', 'plainR', 'conj', 'generic', 'radii', 'bound'):
            if h.get(key) != hdr0.get(key):
                raise OutputError(f'inconsistent run parameter {key} in {p}')
        fp = h.get('fingerprint')
        if fp is None:
            if allow is None: allow = legacy_allowlist()
            rel = os.path.relpath(os.path.abspath(p), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results'))
            sha = hashlib.sha256(open(p, 'rb').read()).hexdigest()
            if rel not in allow or allow[rel]['sha256'] != sha:
                raise OutputError(f'{p}: legacy output (no fingerprint) not in the hash-listed allowlist')
            legacy.append(p)
        else:
            builds.add(fp.get('build'))
            verify_runner_sidecar(p, h, s)
        for k, v in s.items():
            if k in secs: raise OutputError(f'sector {k} appears in two files')
            secs[k] = v
        hdrs[p] = h
    if legacy and builds:
        raise OutputError('legacy and fingerprinted outputs cannot be merged')
    if len(builds) > 1:
        raise OutputError(f'outputs from different engine builds cannot be merged: {sorted(builds)}')
    if builds and approved_builds is not None and not builds <= set(approved_builds):
        raise OutputError(f'engine build {sorted(builds)} is not approved')
    if manifest is not None:
        check_against_manifest(secs, hdrs, manifest, expected)
    return hdr0, secs, hdrs


def pattern_factors(n):
    sys.path.insert(0, __file__.rsplit('/', 1)[0])
    import cluster_gen
    out, done = [], set()
    for pat in cluster_gen.dyck(n):
        if pat in done: continue
        m = cluster_gen.mirror(pat); done.add(pat); done.add(m)
        out.append(1 if m == pat else 2)
    return out


def bell_m(s, nmax):
    psi = [mp.polygamma(k, s) for k in range(nmax + 1)]
    m = [mp.mpf(1)]
    for nn in range(nmax):
        m.append(sum(mp.binomial(nn, k) * psi[k] * m[nn - k] for k in range(nn + 1)))
    return m


def gamma_derivs(a, nmax):
    m = bell_m(a, nmax); g = mp.gamma(a)
    return [g * m[i] for i in range(nmax + 1)]


def assemble_cx(n, secs, K, kmax, weights=None):
    fac = pattern_factors(n)
    if weights is not None:
        bad = [s for s in secs if not weights[s] > 0]
        if bad: raise OutputError(f'sectors {bad[:5]} have mirror weight 0 but are present')
    A = {}
    for sid, s in secs.items():
        wt = fac[s['pat']] * (1 if weights is None else weights[sid])
        for key, v in s['A'].items():
            A[key] = A.get(key, 0) + wt * v
    alpha = 2 * n - 1 - 2 * n * K
    G = gamma_derivs(alpha, 2 * kmax)
    J = [sum(G[j] * A.get((k, j), 0) for j in range(2 * k + 1)) for k in range(kmax + 1)]
    return J, A


def laurent_gamma_derivs(n, jmax, lo, hi, rad=mp.mpf('0.05'), npts=256):
    """Laurent coefficients in w of Gamma^{(j)}(2n-1-2n(1-w)) = Gamma^{(j)}(-1 + 2n w), exponents lo..hi."""
    out = {j: {} for j in range(jmax + 1)}
    pts = [rad * mp.expjpi(2 * mp.mpf(m) / npts) for m in range(npts)]
    vals = [gamma_derivs(-1 + 2 * n * p, jmax) for p in pts]
    for j in range(jmax + 1):
        for e in range(lo, hi + 1):
            out[j][e] = mp.re(sum(v[j] * p ** (-e) for v, p in zip(vals, pts)) / npts)
    return out


def assemble_ser(n, secs, kmax, elo=-12, ehi=4, weights=None):
    """weights: optional per-sector multipliers (mirror reduction, cluster_gen.mirror_weights); sectors of weight 0 must
    be absent and every present sector must have a positive weight."""
    fac = pattern_factors(n)
    if weights is not None:
        bad = [s for s in secs if not weights[s] > 0]
        if bad: raise OutputError(f'sectors {bad[:5]} have mirror weight 0 but are present')
    A = {}
    for sid, s in secs.items():
        wt = fac[s['pat']] * (1 if weights is None else weights[sid])
        for (k, j, e), v in s['S'].items():
            A[(k, j, e)] = A.get((k, j, e), 0) + wt * v
    # valid exponent window per (k, j): minimum over sectors of top exponent
    top = {}
    for s in secs.values():
        tops = {}
        for (k, j, e) in s['S']: tops[(k, j)] = max(tops.get((k, j), -99), e)
        for key, t in tops.items(): top[key] = min(top.get(key, 99), t)
    Lg = laurent_gamma_derivs(n, 2 * kmax, -2 * kmax - 2, ehi + 12)
    J = {}
    for k in range(kmax + 1):
        J[k] = {}
        jtop = min(top[(k, j)] + min(Lg[j]) for j in range(2 * k + 1))
        for e in range(elo, min(ehi, jtop) + 1):
            acc = 0
            for j in range(2 * k + 1):
                for (kk, jj, ea), v in A.items():
                    if kk != k or jj != j: continue
                    eg = e - ea
                    if eg in Lg[j]: acc += Lg[j][eg] * v
            J[k][e] = acc
    return J, A, top
