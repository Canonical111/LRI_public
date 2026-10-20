#!/usr/bin/env python3
"""Negative and positive controls of tc_cert (v2), with explicit assertions on the expected outcomes.

  tc_negctl.py make INPUTS_DIR OUTDIR [FREE_L FREE_ID POWER_L POWER_ID]
                                           write the control payloads (OUTDIR/payloads/), the tc_cert list
                                           (OUTDIR/negctl_list.txt) and their description (OUTDIR/negctl_inputs.json);
                                           default sources free L8 G26268 and power L8 G26451 (others: tests only)
  tc_negctl.py check OUTDIR CERT.jsonl CERT_EXIT OUT.json
                                           assert every control's expected outcome; exit 1 on any failed assertion

The source graphs are read from the inputs' packs and checked against inventory.json's sha256: free L8 G26268 (the
largest variance contributor of the production) and power L8 G26451 (the largest double-lift contributor). Each
mutation edits whitespace-separated tokens of the C7D2GRAPH1 payload and leaves the rest unchanged:

  pos_free, pos_power        unmodified (builder table): must be certified and bounded
  pos_given_free             unmodified, table taken as given (every subset expanded): certified and bounded
  drop_term_free/_power      forest term 0 removed: the forest cancellation fails (failures > 0), a face with
                             m <= 0, i.e. a divergent integral (xi_bound >= 1 at both rates), not certified
  double_num_free            numerator of term 0 doubled (support unchanged, so the rate table still matches): the
                             cancellation fails (failures > 0, rate_mismatch 0), xi_bound >= 1, not certified
  rate_x3_free               every stored rate x3, taken as given: m >= alpha but rho * 3 alpha > 2 m at the tight
                             faces, so INFINITE VARIANCE with a finite mean at both rates: no cancellation failure,
                             min (2m - rho alpha) < 0 at a and b, 1/2 <= xi_bound < 1 at a and b, not certified
  rate_x2.4_free             every stored rate x2.4, taken as given: finite variance at rate a (2 - 0.8*2.4 > 0) but
                             infinite at rate b (2 - 0.9*2.4 < 0); unbounded at both: min_second_a > 0 > min_second_b,
                             xi_a < 1/2 <= xi_b < 1, not certified
  rate_tamper_free           one stored rate (subset 3 = {e0, e1}) raised by 1/2 (builder table): exactly one
                             rate-table mismatch, not certified
tc_cert must exit 3 on this list (records not certified, none with an error)."""
import hashlib, json, sys
from pathlib import Path



def read_member(inputs, s, L, g):
    inv = json.loads((inputs / 'inventory.json').read_bytes())
    r = next(x for x in inv[s][str(L)] if x['id'] == g)
    with open(inputs / 'packs' / f'{s}_L{L}.pack', 'rb') as f:
        f.seek(r['offset']); data = f.read(r['length'])
    if hashlib.sha256(data).hexdigest() != r['sha256']:
        raise SystemExit(f'{s} L{L} G{g}: member sha256 mismatch')
    return data.decode(), r['sha256']


def parse(text):
    tok = text.split()
    i = 0
    head = tok[:7]; i = 7
    L = int(head[1]); E = 2 * L; M = int(head[5]); T = int(head[6])
    masks = tok[i:i + M]; i += M
    terms = []
    for _ in range(T):
        n = int(tok[i]); ids = tok[i + 1:i + 1 + n]; co = tok[i + 1 + n:i + 1 + n + E]; i += 1 + n + E
        terms.append([ids, co])
    nr = int(tok[i]); rates = tok[i + 1:i + 1 + nr]; i += 1 + nr
    assert i == len(tok) and nr == 1 << E
    return dict(head=head, masks=masks, terms=terms, rates=rates)


def emit(p):
    lines = [' '.join(p['head'][:6] + [str(len(p['terms']))]), ' '.join(p['masks'])]
    for ids, co in p['terms']:
        lines.append(' '.join([str(len(ids))] + ids + co))
    lines.append(' '.join([str(len(p['rates']))] + p['rates']))
    return '\n'.join(lines) + '\n'


def fmt(v):
    s = repr(float(v))
    return s[:-2] if s.endswith('.0') else s


def make(inputs, out, kF=('free', 8, 26268), kP=('power', 8, 26451)):
    out.mkdir(parents=True, exist_ok=True); (out / 'payloads').mkdir(exist_ok=True)
    src = {k: read_member(inputs, *k) for k in (kF, kP)}
    ctl = []

    def add(label, key, text, mode, what):
        f = out / 'payloads' / f'{label}.txt'; f.write_text(text)
        data = f.read_bytes()
        ctl.append(dict(label=label, sector=key[0], L=key[1], id=key[2], mode=mode, mutation=what, file=f'payloads/{label}.txt',
                        bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), source_sha256=src[key][1]))
    add('pos_free', kF, src[kF][0], 'builder', 'none')
    add('pos_power', kP, src[kP][0], 'builder', 'none')
    add('pos_given_free', kF, src[kF][0], 'given', 'none (table taken as given)')
    for name, k in (('free', kF), ('power', kP)):
        p = parse(src[k][0]); p['terms'] = p['terms'][1:]
        add(f'drop_term_{name}', k, emit(p), 'builder', 'forest term 0 removed')
    p = parse(src[kF][0]); p['terms'][0][1] = [str(2 * int(c)) for c in p['terms'][0][1]]
    add('double_num_free', kF, emit(p), 'builder', 'numerator coefficients of term 0 doubled')
    for fac in ('3', '2.4'):
        p = parse(src[kF][0]); p['rates'] = [fmt(float(r) * float(fac)) for r in p['rates']]
        add(f'rate_x{fac}_free', kF, emit(p), 'given', f'every stored rate x{fac}, taken as the proposal rates')
    p = parse(src[kF][0]); p['rates'][3] = fmt(float(p['rates'][3]) + 0.5)
    add('rate_tamper_free', kF, emit(p), 'builder', 'stored rate of subset 3 = {e0, e1} raised by 1/2')
    with (out / 'negctl_list.txt').open('w') as f:
        for c in ctl:
            f.write(f"{c['sector']} {c['L']} {c['id']} {(out / c['file']).resolve()} 0 {c['bytes']} {c['label']} {c['mode']}\n")
    (out / 'negctl_inputs.json').write_text(json.dumps(dict(sources={f'{s} L{L} G{g}': src[(s, L, g)][1] for s, L, g in src}, controls=ctl), indent=1))
    print(f'{len(ctl)} controls written to {out}')


EXPECT = {  # label: (assertion, test)
    'pos_free': ('certified and bounded, failures 0, rate_mismatch 0',
                 lambda r: r['certified'] and r['bounded'] and r['failures'] == 0 and r['rate_mismatch'] == 0),
    'pos_power': ('certified and bounded, failures 0, a double-lift graph (max_orders_cancelled >= 2)',
                  lambda r: r['certified'] and r['bounded'] and r['failures'] == 0 and r['max_orders_cancelled'] >= 2),
    'pos_given_free': ('certified and bounded, failures 0, every proper subset expanded (2^E - 2)',
                       lambda r: r['certified'] and r['bounded'] and r['failures'] == 0 and r['series_subsets'] == (1 << r['E']) - 2),
    'drop_term_free': ('failures > 0, not certified, not bounded, xi_bound >= 1 at both rates (a face with m <= 0)',
                       lambda r: r['failures'] > 0 and not r['certified'] and not r['bounded'] and r['xi_bound_a'] >= 1 and r['xi_bound_b'] >= 1),
    'drop_term_power': ('failures > 0, not certified, not bounded, xi_bound >= 1 at both rates (a face with m <= 0)',
                        lambda r: r['failures'] > 0 and not r['certified'] and not r['bounded'] and r['xi_bound_a'] >= 1 and r['xi_bound_b'] >= 1),
    'double_num_free': ('failures > 0, rate_mismatch 0, not certified, xi_bound >= 1 at both rates',
                        lambda r: r['failures'] > 0 and r['rate_mismatch'] == 0 and not r['certified'] and r['xi_bound_a'] >= 1 and r['xi_bound_b'] >= 1),
    'rate_x3_free': ('infinite variance with a finite mean at both rates: failures 0, min_second_margin_a < 0 and _b < 0, '
                     '1/2 <= xi_bound_a < 1 and 1/2 <= xi_bound_b < 1, not certified, not bounded',
                     lambda r: (r['failures'] == 0 and r['min_second_margin_a'] < 0 and r['min_second_margin_b'] < 0 and 0.5 <= r['xi_bound_a'] < 1
                                and 0.5 <= r['xi_bound_b'] < 1 and not r['certified'] and not r['bounded'])),
    'rate_x2.4_free': ('finite variance at rate a, infinite at rate b: failures 0, min_second_margin_a > 0 > min_second_margin_b, '
                       'xi_bound_a < 1/2 <= xi_bound_b < 1, not certified, not bounded',
                       lambda r: (r['failures'] == 0 and r['min_second_margin_a'] > 0 > r['min_second_margin_b'] and r['xi_bound_a'] < 0.5 <= r['xi_bound_b'] < 1
                                  and not r['certified'] and not r['bounded'])),
    'rate_tamper_free': ('exactly one rate-table mismatch, failures 0, not certified',
                         lambda r: r['rate_mismatch'] == 1 and r['failures'] == 0 and not r['certified']),
}
SHOW = ('certified', 'bounded', 'failures', 'rate_mismatch', 'tight', 'higher', 'series_subsets', 'max_orders_cancelled', 'min_bound_margin_a',
        'min_bound_margin_b', 'min_second_margin_a', 'min_second_margin_b', 'xi_bound_a', 'xi_bound_b', 'failed_sets', 'trial_disagreements',
        'degenerate_retries', 'log10_err_max', 'error')


def check(outdir, cert, code, out):
    desc = json.loads((outdir / 'negctl_inputs.json').read_text())
    recs = [json.loads(l) for l in open(cert)]
    by = {}
    for r in recs:
        by.setdefault(r['label'], []).append(r)
    rows = []; ok_all = True
    for c in desc['controls']:
        data = (outdir / c['file']).read_bytes()
        rs = by.get(c['label'], [])
        sha_ok = hashlib.sha256(data).hexdigest() == c['sha256']
        if len(rs) != 1:
            rows.append(dict(label=c['label'], passed=False, reason=f'{len(rs)} records')); ok_all = False; continue
        r = rs[0]
        passed = sha_ok and r['error'] == '' and r['rates_mode'] == c['mode'] and bool(EXPECT[c['label']][1](r))
        ok_all &= passed
        rows.append(dict(label=c['label'], graph=f"{c['sector']} L{c['L']} G{c['id']}", mutation=c['mutation'], mode=c['mode'], assertion=EXPECT[c['label']][0],
                         passed=passed, payload_sha256_ok=sha_ok, **{k: r[k] for k in SHOW}))
        print(f"{'PASS' if passed else 'FAIL'} {c['label']:20s} " + ' '.join(f'{k}={r[k]}' for k in SHOW[:14]), flush=True)
    extra = sorted(set(by) - {c['label'] for c in desc['controls']})
    exit_ok = int(code) == 3
    ok_all &= exit_ok and not extra and len(recs) == len(desc['controls'])
    doc = dict(tc_cert_exit=int(code), tc_cert_exit_expected=3, exit_ok=exit_ok, records=len(recs), controls=len(desc['controls']),
               unexpected_labels=extra, all_passed=ok_all, assertions={k: v[0] for k, v in EXPECT.items()}, results=rows)
    Path(out).write_text(json.dumps(doc, indent=1))
    print(f"tc_cert exit {code} (expected 3): {'ok' if exit_ok else 'WRONG'}; all controls passed: {ok_all}")
    return 0 if ok_all else 1


if __name__ == '__main__':
    if len(sys.argv) in (4, 8) and sys.argv[1] == 'make':
        if len(sys.argv) == 8:
            make(Path(sys.argv[2]), Path(sys.argv[3]), ('free', int(sys.argv[4]), int(sys.argv[5])), ('power', int(sys.argv[6]), int(sys.argv[7])))
        else:
            make(Path(sys.argv[2]), Path(sys.argv[3]))
    elif len(sys.argv) == 6 and sys.argv[1] == 'check':
        sys.exit(check(Path(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]))
    else:
        print(__doc__); sys.exit(2)
