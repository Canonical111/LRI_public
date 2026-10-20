"""Audit actual full-model outputs without requiring agreement with thermal targets."""
from pathlib import Path
import sys,json,csv,hashlib,runpy
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'))
from analyze import main as analyze

def main():
    summary=analyze()
    assert summary['complete_degree8_cutoffs']==list(range(2,45,2))
    assert summary['new_C8_cutoffs']==list(range(26,45,2))
    assert summary['new_C6_C7_cutoffs']==list(range(30,45,2))
    assert summary['forecast_records']==416
    f=ROOT/'results/frozen_forecasts.json'
    assert hashlib.sha256(f.read_bytes()).hexdigest()==(ROOT/'results/forecast_sha256.txt').read_text().split()[0]
    frozen=json.loads(f.read_text());assert len(frozen)==16
    assert all(r['status']=='completed' for r in frozen)
    files=list((ROOT/'results/new_coefficients').glob('*.json'))
    assert len(files)==26,len(files)
    for p in files:
        a=json.loads(p.read_text())
        assert np.isfinite(a['C']).all(),p.name
        assert a['C'][0]==.5 and abs(a['C'][1]+1/6)<1e-12
        assert a['degree'] in (7,8)
    vals=json.loads((ROOT/'results/independent_validation.json').read_text())
    assert len(vals)==10,len(vals)
    assert max(r['scaled_error'] for r in vals)<1e-10
    with (ROOT/'results/leading_polynomial_probes.csv').open() as h:probes=list(csv.DictReader(h))
    counts={}
    for r in probes:counts[r['status']]=counts.get(r['status'],0)+1
    assert len(probes)==60,(len(probes),counts)
    result=dict(new_full_model_records=len(files),forecast_designs=16,new_higher_order_forecasts=416,
      complete_degree8_cutoffs=summary['complete_degree8_cutoffs'],max_fresh_reference_scaled_error=max(r['scaled_error'] for r in vals),
      polynomial_probe_status_counts=counts,derived_complete_analytic_C6_C7_C8_tails=0,
      scope='No measured continuum or low-order reference value selects or alters a model in this audit.')
    (ROOT/'results/saved_validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
