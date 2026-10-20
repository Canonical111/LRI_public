#!/usr/bin/env python3
"""The ARCHIVED driver's seed arithmetic (reference/code/run_campaign.py), which this package never derives: native seed
S (+348612 for power), net seed S + 27403 L (+592731 for power), 52-bit nets for both campaigns, B = replicates.
Checked against all 160 archived production records: the record's native seed, rate, and the net header. One archived
net is regenerated with reference/code/sobol_net.py; the archive does not record its SciPy version, so a byte match is
recorded as evidence and a mismatch is reported, not failed. Pure Python."""
from __future__ import annotations
import hashlib,importlib.util,json,struct,sys,tempfile
from decimal import Decimal as D
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'reference'

def run():
    checked=0
    for tag,rate in (('production_a','0.8'),('production_b','0.7')):
        cfg=json.loads((R/'records'/tag/'config.json').read_text());man=json.loads((R/'records'/tag/'manifest.json').read_text());S=cfg['seed']
        if D(str(cfg['rate']))!=D(rate)or cfg['layout']!=0:raise AssertionError(f'{tag}: unexpected rate/layout')
        for rec in man['records']:
            f=R/rec['file'];data=f.read_bytes()
            if hashlib.sha256(data).hexdigest()!=rec['sha256']:raise AssertionError('record hash mismatch '+str(f))
            doc=json.loads(data);want=S+(348612 if rec['sector']=='power'else 0)
            if doc['seed']!=want or abs(D(doc['rate'])-D(rate))>D(2)**-62 or doc['L']!=rec['L']:raise AssertionError(f'{f.name}: seed/rate/L {doc["seed"]}/{doc["rate"]}/{doc["L"]} != {want}/{rate}/{rec["L"]}')
            net=R/'records'/tag/f'{rec["sector"]}_L{rec["L"]}.net';B,dim,bits=struct.unpack('<III',net.read_bytes()[:12])
            if (B,dim,bits)!=(man['args']['replicates'],4*rec['L']-1,52)or hashlib.sha256(net.read_bytes()).hexdigest()!=rec['net_sha256']:raise AssertionError(f'{net.name}: header {B,dim,bits}')
            checked+=1
    if checked!=160:raise AssertionError(f'{checked} records checked, expected 160')
    spec=importlib.util.spec_from_file_location('sobol_net',R/'code/sobol_net.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    import scipy
    cfg=json.loads((R/'records/production_a/config.json').read_text());L=3;target=R/'records/production_a/power_L3.net'
    with tempfile.TemporaryDirectory(prefix='c7d3_archived_net_')as td:
        out=Path(td)/'net.bin';mod.make_net(out,cfg['replicates'],4*L-1,52,cfg['seed']+L*27403+592731);match=out.read_bytes()==target.read_bytes()
    return {'status':'passed','test':'archived_driver_arithmetic','records_checked':checked,
            'net_regeneration':{'net':'production_a/power_L3.net','scipy':scipy.__version__,'byte_identical':match,'note':'evidence only: the archive does not record its SciPy version'}}
if __name__=='__main__':print(json.dumps(run(),indent=2))
