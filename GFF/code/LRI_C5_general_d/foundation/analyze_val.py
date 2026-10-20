#!/usr/bin/env python3
"""Compare a run_validation.py output with the references (C63d JSON for noninteger d; closed forms / archive for
d = 1, 2, 3).  usage: analyze_val.py VAL.json [REF.json]  -> prints tables, writes VAL_summary.json"""
import sys, json
import mpmath as mp
mp.mp.dps = 80
val = json.load(open(sys.argv[1]))
refp = sys.argv[2] if len(sys.argv) > 2 else '<PROJECT>/LRI_C5_general_d/references/reference_values.json'
ref = json.load(open(refp))['values']
M = mp.mpmathify
def rel(a, b):
    return abs(a - b) / abs(b)
summary = dict(center=[], offdiag=[], spectral=[], circles=[], fourier=[])
refs123 = val.get('refs', {})
def refval(d, key):
    if d in refs123:
        return M(refs123[d][key])
    dd = {'0.8': 'd=0.8', '1.25': 'd=1.25', '1.5': 'd=1.5', '2.5': 'd=2.5', '2.75': 'd=2.75'}[d]
    return M(ref[dd][key]['value'])
def refdig(d, key):
    if d in refs123:
        return 80
    dd = 'd=' + d
    return ref[dd][key]['digits']
pts = {}
for p in val['points']:
    k = p['kind']; pay = tuple(p['payload']); out = p['out']
    pts[(k,) + pay] = out
print('== b = d/2: finite-sample W vs reference (P4 for r=4, 3Q for r=3) ==')
for d in ['1', '2', '3', '0.8', '1.25', '1.5', '2.5', '2.75']:
    for r in (3, 4):
        b = str(M(d) / 2)
        bkey = [key for key in pts if key[0] == 'point' and key[1] == r and key[2] == d and key[4] == 'fixed' and abs(M(key[3]) - M(d)/2) < 1e-30]
        nkey = [key for key in pts if key[0] == 'point' and key[1] == r and key[2] == d and key[4] == 'note' and abs(M(key[3]) - M(d)/2) < 1e-30]
        wf = M(pts[bkey[0]]['W']); wn = M(pts[nkey[0]]['W'])
        R = refval(d, 'P4' if r == 4 else 'threeQ')
        e1, e2 = rel(mp.re(wf), R), rel(mp.re(wn), R)
        top = pts[bkey[0]].get('top_mode_rel'); trig = pts[bkey[0]].get('trig_check'); asy = pts[bkey[0]].get('asym')
        c = [M(x) for x in pts[bkey[0]]['c']]
        print('d=%-5s r=%d  W=%s  rel(fixed-ref)=%s rel(note-ref)=%s (ref digits %s) |Im|=%s top=%s trig=%s' % (
            d, r, mp.nstr(mp.re(wf), 30), mp.nstr(e1, 3), mp.nstr(e2, 3), refdig(d, 'P4' if r == 4 else 'threeQ'),
            mp.nstr(abs(mp.im(wf)), 3), mp.nstr(M(top), 3), mp.nstr(M(trig), 3)))
        summary['center'].append(dict(d=d, r=r, W=mp.nstr(mp.re(wf), 50), rel_fixed=mp.nstr(e1, 3), rel_note=mp.nstr(e2, 3),
                                      ref_digits=refdig(d, 'P4' if r == 4 else 'threeQ'), top_mode_rel=mp.nstr(M(top), 3),
                                      trig_check=mp.nstr(M(trig), 3), asym=mp.nstr(M(asy), 3),
                                      c=[mp.nstr(mp.re(x), 25) for x in c], c_imag_max=mp.nstr(max(abs(mp.im(x)) for x in c), 3)))
print('\n== off-diagonal b = d/2 +- 0.05: finite-sample vs C63d spectral (56 digits) ==')
for d in ['0.8', '1.25', '1.5', '2.5', '2.75']:
    for item in ref['d=' + d]['offdiag']:
        b = item['b']
        for r in (3, 4):
            keyf = [key for key in pts if key[0] == 'point' and key[1] == r and key[2] == d and key[4] == 'fixed' and abs(M(key[3]) - M(b)) < 1e-30]
            keyn = [key for key in pts if key[0] == 'point' and key[1] == r and key[2] == d and key[4] == 'note' and abs(M(key[3]) - M(b)) < 1e-30]
            if not keyf or not keyn:
                print('d=%-5s b=%-6s r=%d  (not computed in this run)' % (d, b, r)); continue
            wf = M(pts[keyf[0]]['W']); wn = M(pts[keyn[0]]['W'])
            R = M(item['W%d' % r])
            print('d=%-5s b=%-6s r=%d  W=%s  rel(fixed-C63d)=%s rel(note-C63d)=%s top=%s' % (d, b, r, mp.nstr(mp.re(wf), 30),
                  mp.nstr(rel(mp.re(wf), R), 3), mp.nstr(rel(mp.re(wn), R), 3), mp.nstr(M(pts[keyf[0]]['top_mode_rel']), 3)))
            summary['offdiag'].append(dict(d=d, b=b, r=r, W=mp.nstr(mp.re(wf), 50), rel_fixed=mp.nstr(rel(mp.re(wf), R), 3),
                                           rel_note=mp.nstr(rel(mp.re(wn), R), 3), top_mode_rel=mp.nstr(M(pts[keyf[0]]['top_mode_rel']), 3)))
print('\n== own spectral code vs finite-sample ==')
for key, out in pts.items():
    if key[0] != 'spectral':
        continue
    r, d, b = key[1], key[2], key[3]
    keyf = [k2 for k2 in pts if k2[0] == 'point' and k2[1] == r and k2[2] == d and k2[4] == 'fixed' and abs(M(k2[3]) - M(b)) < 1e-30]
    ws = M(out['W'])
    if keyf:
        wf = M(pts[keyf[0]]['W'])
        print('d=%s b=%s r=%d  spectral=%s  rel(fixed-spectral)=%s' % (d, b, r, mp.nstr(mp.re(ws), 30), mp.nstr(rel(mp.re(wf), mp.re(ws)), 3)))
        summary['spectral'].append(dict(d=d, b=b, r=r, spectral=mp.nstr(mp.re(ws), 45), rel=mp.nstr(rel(mp.re(wf), mp.re(ws)), 3)))
    else:
        print('d=%s b=%s r=%d  spectral=%s  (no finite-sample point; C63d offdiag compare below)' % (d, b, r, mp.nstr(mp.re(ws), 30)))
        for item in ref['d=' + d]['offdiag']:
            if abs(M(item['b']) - M(b)) < 1e-30:
                print('      rel(own spectral - C63d spectral) =', mp.nstr(rel(mp.re(ws), M(item['W%d' % r])), 3))
                summary['spectral'].append(dict(d=d, b=b, r=r, spectral=mp.nstr(mp.re(ws), 45), rel_to_C63d=mp.nstr(rel(mp.re(ws), M(item['W%d' % r])), 3)))
print('\n== Cauchy circles in b around d/2: L_d = dW4/db, Z_d = (1/9) d2W3/db2 ==')
for name, cdat in val.get('circles', {}).items():
    r = int(name[1]); d = name.split('_d')[1]
    tay = [M(x) for x in cdat['taylor']]
    if r == 4:
        Lc = mp.re(tay[1]); Lr = refval(d, 'L')
        print('d=%-5s L_d(circle)=%s  ref=%s  rel=%s (ref digits %s) rho=%s M=%s' % (d, mp.nstr(Lc, 30), mp.nstr(Lr, 20), mp.nstr(rel(Lc, Lr), 3), refdig(d, 'L'), mp.nstr(M(cdat['rho']), 4), cdat['M']))
        summary['circles'].append(dict(d=d, quantity='L', circle=mp.nstr(Lc, 50), rel=mp.nstr(rel(Lc, Lr), 3), ref_digits=refdig(d, 'L'),
                                       W0_rel=mp.nstr(rel(mp.re(tay[0]), refval(d, 'P4')), 3), rho=cdat['rho'][:12], M=cdat['M']))
    else:
        Zc = mp.re(2 * tay[2] / 9); Zr = refval(d, 'Z')
        print('d=%-5s Z_d(circle)=%s  ref=%s  rel=%s (ref digits %s)  dW3/db=%s rho=%s' % (d, mp.nstr(Zc, 30), mp.nstr(Zr, 20), mp.nstr(rel(Zc, Zr), 3), refdig(d, 'Z'), mp.nstr(abs(tay[1]), 3), mp.nstr(M(cdat['rho']), 4)))
        summary['circles'].append(dict(d=d, quantity='Z', circle=mp.nstr(Zc, 50), rel=mp.nstr(rel(Zc, Zr), 3), ref_digits=refdig(d, 'Z'),
                                       dW3db=mp.nstr(abs(tay[1]), 3), W0_rel=mp.nstr(rel(mp.re(tay[0]), refval(d, 'threeQ')), 3), rho=cdat['rho'][:12], M=cdat['M']))
json.dump(summary, open(sys.argv[1].replace('.json', '_summary.json'), 'w'), indent=1)
