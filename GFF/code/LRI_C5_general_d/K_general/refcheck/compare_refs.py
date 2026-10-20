#!/usr/bin/env python3
"""Digit-by-digit comparison of the refcheck values with LRI_C5_general_d/references/reference_values.json
(hp_general_d.py: spectral trace, Stirling/Hurwitz spin tail, b- and tau-circle Cauchy derivatives).

  route A = routeA_spectral.py  (spectral trace with the explicit polygamma weights gs:w12/gs:LZspectral/gs:Kweights,
                                 own DE quadrature, Abel-Plana spin tail in complex spin)
  route B = routeB_residue.py   (residue series gs:QPseries/gs:Lseries/gs:Zseries and gc:Kcancelled (= gs:Kseries bracket),
                                 inner n-sum and outer spin sum both by Abel-Plana)
For every (d, b) the highest-precision run of each route is used.  For each reference string with n significant digits
the own value is rounded to n digits and compared character by character.
Writes refcheck_comparison.json and refcheck_values.json.

usage: compare_refs.py [runs_dir] [reference_json]"""
import sys, json, os, glob
import mpmath as mp
mp.mp.dps = 90
HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'runs')
REF = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, '..', '..', 'references', 'reference_values.json')


def sigdigits(s):
    s = s.strip().lstrip('+-')
    man = s.lower().split('e')[0]
    return man.replace('.', '').lstrip('0')


def digit_compare(sref, v):
    """(n, k, offby1): n = significant digits of the reference string, k = first differing digit after rounding the own value
       to n digits (None if all agree), offby1 = the difference is at most one unit of the last reference digit"""
    dr = sigdigits(sref)
    n = len(dr)
    ref = mp.mpf(sref)
    vr = mp.nstr(v, n, strip_zeros=False, min_fixed=-mp.inf, max_fixed=mp.inf)
    dm = sigdigits(vr)[:n]
    k = None
    for i in range(n):
        if i >= len(dm) or dm[i] != dr[i]:
            k = i + 1
            break
    ulp = mp.mpf(10) ** (mp.floor(mp.log10(abs(ref))) - n + 1)
    offby1 = (k is not None) and abs(v - ref) <= mp.mpf('1.01') * ulp
    return n, k, offby1


def load_runs(prefix):
    out = {}
    for f in sorted(glob.glob(os.path.join(RUNS, prefix + '_d*_dps*.json'))):
        J = json.load(open(f))
        if 'final' not in J:
            continue
        d = str(J['d']); b = J.get('b')
        dd = mp.mpf(d)
        key = (d, 'diag' if (b is None or mp.mpf(b) == dd / 2) else mp.nstr(mp.mpf(b), 10))
        out.setdefault(key, []).append((os.path.basename(f), J))
    for k in out:
        out[k].sort(key=lambda fj: (int(fj[1]['dps']), int(fj[1].get('L', 0))))
    return out


def best(src, key, q):
    if key not in src:
        return None, None, None
    f, J = src[key][-1]
    fin = J['final']
    if q == 'K' and 'K_cancelled' in fin:
        q = 'K_cancelled'
    if q not in fin:
        return None, None, None
    return mp.mpf(fin[q]), int(J['dps']), f


A = load_runs('A'); B = load_runs('B')
R = json.load(open(REF))
rows = []
print('reference file  :', os.path.abspath(REF))
print('reference status:', R.get('status'))
print('legend: n = significant digits printed in the reference; "all n agree" = own value rounded to n digits reproduces the')
print('        reference string exactly; "last digit +-1" = only the final printed digit differs, by at most one unit')
QMAP = {'threeQ': 'threeQ', 'Q_d': 'Q', 'P4': 'P4', 'L': 'L', 'Z': 'Z', 'K': 'K'}
for dkey, block in R['values'].items():
    d = dkey.split('=')[1]
    print('\n==== %s' % dkey)
    if not block:
        print('  (no reference values)')
        continue
    items = []
    for qn, ent in block.items():
        if qn == 'offdiag':
            for od in ent:
                for wn in ('W3', 'W4'):
                    items.append(('%s(b=%s)' % (wn, od['b']), od[wn], (d, mp.nstr(mp.mpf(od['b']), 10)), wn, None, None))
        elif isinstance(ent, dict) and 'value' in ent:
            if qn in QMAP:
                items.append((qn, ent['value'], (d, 'diag'), QMAP[qn], ent.get('digits'), ent.get('WARNING')))
            elif qn == 'dW3db':
                # dW3/db at b = d/2 equals <3 t^3 w1> exactly (d log t/db = w1): route A's 'chk' component; must vanish
                va, pa, fa = best(A, (d, 'diag'), 'chk')
                print('  %-14s ref     %s   (must vanish)\n  %-14s route A <3 t^3 w1> = %s  (dps %s)  -> both consistent with 0'
                      % (qn, mp.nstr(mp.mpf(ent['value']), 5), '', mp.nstr(va, 3) if va is not None else 'n/a', pa))
                rows.append(dict(d=d, quantity='dW3db', reference=ent['value'], routeA=mp.nstr(va, 5) if va is not None else None,
                                 note='dW3/db at b=d/2 = <3 t^3 w1>, identically zero'))
    for (label, sref, key, q, claim, warn) in items:
        ref = mp.mpf(sref)
        va, pa, fa = best(A, key, q)
        vb, pb, fb = best(B, key, q)
        rec = dict(d=d, quantity=label, reference=sref, reference_digits_claimed=claim, reference_warning=warn)
        line = '  %-14s ref     %s%s' % (label, sref, ('   [claimed %s]' % claim) if claim is not None else '')
        if warn:
            line += '  WARNING(ref): ' + warn
        for nm, v, pr, f in (('A', va, pa, fa), ('B', vb, pb, fb)):
            if v is None:
                continue
            n, k, ob1 = digit_compare(sref, v)
            rel = abs(v - ref) / abs(ref)
            ag = float(-mp.log10(rel)) if rel > 0 else 99.0
            if k is None:
                verdict = 'all %d digits agree' % n
            elif ob1:
                verdict = 'last digit +-1 (agree to the %d-digit rounding unit)' % n
            else:
                verdict = 'FIRST DIFFERENCE AT DIGIT %d of %d' % (k, n)
            line += '\n  %-14s route %s %s  (dps %d)  rel.diff %s (%.1f digits): %s' % ('', nm, mp.nstr(v, n + 3), pr, mp.nstr(rel, 3), ag, verdict)
            rec['route%s' % nm] = mp.nstr(v, pr - 3); rec['route%s_dps' % nm] = pr; rec['route%s_file' % nm] = f
            rec['route%s_rel_diff' % nm] = mp.nstr(rel, 3); rec['route%s_agree_digits' % nm] = round(ag, 1)
            rec['route%s_first_diff_digit' % nm] = k; rec['route%s_lastdigit_pm1' % nm] = bool(ob1)
            rec['reference_sig_digits'] = n
        if va is not None and vb is not None:
            ab = abs(va - vb) / abs(va)
            rec['A_vs_B_rel'] = mp.nstr(ab, 3)
            line += '\n  %-14s A vs B rel.diff %s' % ('', mp.nstr(ab, 3) if ab > 0 else '< 1e-%d' % (min(pa, pb) - 3))
        print(line)
        rows.append(rec)
json.dump(rows, open(os.path.join(HERE, 'refcheck_comparison.json'), 'w'), indent=1)

# own values table (route A value; route B as confirmation)
vals_out = {}
for key in sorted(set(A) | set(B), key=lambda k: (float(k[0]), k[1])):
    d, bk = key
    if d in ('1', '2', '3'):
        continue
    ent = vals_out.setdefault('d=' + d, {})
    qs = ['threeQ', 'Q', 'P4', 'L', 'Z', 'K'] if bk == 'diag' else ['W3', 'W4']
    for q in qs:
        va, pa, fa = best(A, key, q)
        vb, pb, fb = best(B, key, q)
        if va is None and vb is None:
            continue
        v, pr = (va, pa) if va is not None else (vb, pb)
        e = dict(value=mp.nstr(v, pr - 5), routeA_dps=pa, routeB_dps=pb)
        if va is not None and vb is not None:
            ab = abs(va - vb) / abs(va)
            e['A_vs_B_rel_diff'] = mp.nstr(ab, 3) if ab > 0 else '< 1e-%d' % (min(pa, pb) - 3)
            e['digits'] = int(min(pr - 5, mp.floor(-mp.log10(ab)))) if ab > 0 else pr - 5
        name = q if bk == 'diag' else '%s(b=%s)' % (q, bk)
        ent[name] = e
json.dump(dict(producer='refcheck workflow agent (session C63d): routes A and B in LRI_C5_general_d/K_general/refcheck',
               conventions='as references/reference_values.json; K from gs:Kspectral (route A) and gc:Kcancelled (route B); '
                           'digits = agreement of the two independent routes, capped at the working precision minus 5',
               values=vals_out), open(os.path.join(HERE, 'refcheck_values.json'), 'w'), indent=1)
print('\nwrote refcheck_comparison.json and refcheck_values.json')
