"""Selection for the second L8 margin probe: the steady-xi candidates of the pilot N-trend (PLAN-REVIEW-LOG 2026-10-08),
built with margin_probe8's own row fields. Usage (from the package root): python3 -B mk_sel2.py OUT.json"""
import collections, csv, hashlib, json, sys
from pathlib import Path
sys.path.insert(0, 'tools')
import margin_probe8 as mp
import members
from common import dump, utc
BOTH = [10091, 14810, 20760]
ONE = [3974, 5008, 6987, 9992, 10044, 11017, 11840, 14775, 14792, 19545, 21810, 26175, 26482]
DONE = {('power', 10044), ('power', 11840)}   # already in probe 571479 (verified below)
rp = Path('benchmarks/symmetry_2026-10-c8/pilot/evidence/pilot_report.json')
data = rp.read_bytes(); rep = json.loads(data)
inputs = members.inputs_dir(None); inv = members.inventory(inputs)
inv8 = {s: {r['id']: r for r in inv[s]['8']} for s in ('free', 'power')}
audit = mp.rate_audit(inputs, 8)
conf = rep['action2_confirm']['confirmations']
by = {(x['sector'], x['graph']): x for x in conf}
piv = {(x['sector'], x['graph']) for x in rep['action2_confirm']['possible_infinite_variance']}
first = json.loads(Path(sys.argv[2]).read_text())
done = {(r['sector'], r['id']) for r in first['graphs']}
graphs = []
for g in BOTH + ONE:
    hits = [s for s in ('free', 'power') if (s, g) in by]
    assert hits == ['power'], (g, hits)
    if ('power', g) in done:
        continue
    x = by[('power', g)]; r = inv8['power'][g]; ccs = x.get('cross_campaign_shift') or {}; au = audit.get(('power', g)) or {}
    why = ('steady fixed-k Hill xi between 4,096 (PF) and 32,768 (PC) points in both campaigns' if g in BOTH else
           'steady fixed-k Hill xi between 4,096 (PF) and 32,768 (PC) points in one campaign')
    graphs.append(dict(sector='power', L=8, id=g, role='steady', why=why, rank=None, share=None, share_pf=None,
                       xi_mean_32768=x.get('xi_mean_32768'), xi_a=ccs.get('xi_a'), xi_b=ccs.get('xi_b'),
                       face_model_xi_b=ccs.get('face_model_xi_b'), possible_infinite_variance=('power', g) in piv,
                       double_lift=r['double_lift'], monomials=r['monomials'], terms=r['terms'], s_G=r['s_G'],
                       clamped=au.get('clamped'), raw_histogram=au.get('raw_histogram')))
doc = dict(schema=mp.SCHEMA_SELECTION, made_utc=utc(),
           purpose='L8 margin re-derivation, second probe: the steady-xi candidates of the pilot N-trend '
                   '(PLAN-REVIEW-LOG 2026-10-08) not already in probe 571479',
           rule=dict(both_campaigns=BOTH, one_campaign=ONE, skipped_already_probed=sorted(g for s, g in done if g in BOTH + ONE)),
           sources=dict(pilot_report=dict(path=str(rp), sha256=hashlib.sha256(data).hexdigest(), made_utc=rep.get('made_utc'),
                                          pc=rep.get('pc')),
                        first_selection=dict(path=sys.argv[2], sha256=mp.sha256_file(Path(sys.argv[2]))),
                        inputs_manifest_sha256=mp.sha256_file(inputs / 'manifest.json')),
           counts=dict(power=dict(chosen=len(graphs))), graphs=graphs)
out = Path(sys.argv[1])
assert not out.exists()
dump(out, doc)
print(len(graphs), [r['id'] for r in graphs])
