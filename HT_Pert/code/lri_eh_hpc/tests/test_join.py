import importlib.util,json
from pathlib import Path
import pytest
from lri_eh.runner import run
from lri_eh.runtime import atomic_json,fingerprint
from lri_eh._core.solver import second_order_shell_value
spec=importlib.util.spec_from_file_location('bridge',Path(__file__).resolve().parents[1]/'scripts/join_campaign.py')
bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)

def test_join_provenance_and_double_count(tmp_path):
    d=run(8,7,tmp_path/'correction',4,2.)
    correction=tmp_path/'d.json';atomic_json(correction,d)
    raw=tmp_path/'r.json'
    r=dict(cutoff=8,C=[.5,-1/6,second_order_shell_value(8),0.,0.,0.,0.,0.],source_sha256='a'*64,tuning_residual=0.)
    atomic_json(raw,[r])
    rows=bridge.join([raw],[correction],5,'a'*12,fingerprint())
    assert len(rows[0]['C'])==6 and rows[0]['uncorrected_higher_coefficients_omitted']
    assert rows[0]['C'][4]==d['delta_C'][4]
    atomic_json(raw,rows)
    with pytest.raises(ValueError,match='double'):bridge.join([raw],[correction],5,'a'*12,fingerprint())
    r['tuning_residual']=float('nan')
    raw.write_text(json.dumps([r]))
    with pytest.raises(ValueError,match='tuning'):bridge.join([raw],[correction],5,'a'*12,fingerprint())
