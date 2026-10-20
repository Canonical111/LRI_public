"""Independent input check for the L = 46..72 exact shifts: per-L dconn JSON minus raw (data.json) vs the CSV,
C0..C3 unchanged, dC4/dC5 vs dC_reconciled.json; thermal_d7 vs raw at C0..C7."""
import sys, os, json, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import load_ht, load_recon
P = '<PROJECT>/lri_1d_coefficient_flow_review/s10_production'
ht = load_ht(); rc = load_recon()
rows = {int(r['L']): r for r in csv.DictReader(open(P + '/dconn_minus_raw_L46_72.csv'))}
m = dict(csv_vs_json=0., c03=0., dC4=0., dC5=0., th_vs_raw_rel=0.)
for L in range(46, 73, 2):
    d = json.load(open(P + '/dconn_L%d_d8.json' % L)); C = d['C']; raw = ht['raw'][L]; th = ht['thermal_d7'][L]
    assert d['cutoff'] == L and d['scheme'] == 'dconn' and d['degree'] == 8
    for k in (6, 7, 8):
        m['csv_vs_json'] = max(m['csv_vs_json'], abs((C[k] - raw[k]) - float(rows[L]['dC%d' % k])) / max(1, abs(C[k])))
    m['c03'] = max(m['c03'], max(abs(C[k] - raw[k]) for k in range(4)))
    m['dC4'] = max(m['dC4'], abs((C[4] - raw[4]) - rc[L][4])); m['dC5'] = max(m['dC5'], abs((C[5] - raw[5]) - rc[L][5]))
    m['th_vs_raw_rel'] = max(m['th_vs_raw_rel'], max(abs(th[k] - raw[k]) / max(1e-300, abs(raw[k])) for k in range(2, 8)))
print(json.dumps(m))
