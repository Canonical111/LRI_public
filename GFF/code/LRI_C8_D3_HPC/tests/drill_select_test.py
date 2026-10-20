#!/usr/bin/env python3
"""tools/drill_select.py (J-DRL-9's hand-made selections; PLAN J-DRL-9, A-DES-7 (c), (f)) on the committed L8 inventory
and the committed measured model cost_models/gmp_expanse_epyc7742_c8.json, in a temporary out dir. Mac; seconds.

  * per sector exactly 2 graphs, equal to an independent recomputation of the two cheapest L8 graphs without a zero
    channel (s_G = 4) by the mean of the a and b seconds per point (ties by id); the cheapest at 1,024 points nested at
    [256], the other at 512; inputs_manifest_sha256 = sha256 of inputs/manifest.json; seed null, role stage_a;
  * production.read_selection accepts the stage_a file for a test-only plan and refuses it otherwise ("power of two
    >= 4096"); the empty confirm selection is refused with 65 ("empty selection");
  * negative controls: a second run into the same directory exits 64 and leaves both files byte-unchanged; the
    synthetic fixture and a model copy without one candidate's b key are refused (1, nothing written); with an inputs
    copy that marks one free L8 graph zero-channel (the committed L8 inventory has none: s_G is 0 or 2) and a model copy
    that makes it the cheapest, that graph is left out, while the same pick with the zero-channel filter disabled
    (drill_select.pick's hook) takes it: the filter is what excludes it.
Usage: python3 -B tests/drill_select_test.py
"""
from __future__ import annotations
import hashlib,json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools')]
import drill_select as ds  # noqa: E402
import pilot_select as ps  # noqa: E402
import production as prod  # noqa: E402
from common import Refuse  # noqa: E402
MODEL=ROOT/'cost_models/gmp_expanse_epyc7742_c8.json'
RESULTS=[]
def ok(name):RESULTS.append(name);print('PASS',name,flush=True)
def sha(p:Path)->str:return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(*args)->subprocess.CompletedProcess:return subprocess.run([sys.executable,'-B',str(ROOT/'tools/drill_select.py'),*map(str,args)],capture_output=True,text=True)

def cheapest(inv:dict,spp:dict,zero_channel=True)->dict:
    """The two cheapest L8 graphs per sector by (a + b) / 2, ties by id, recomputed here from the files."""
    out={}
    for s in ('free','power'):
        c=[(( float(spp[f'a:{s}:8:{r["id"]}'])+float(spp[f'b:{s}:8:{r["id"]}']))/2,r['id'])for r in inv[s]['8']if not(zero_channel and r.get('s_G')==4)]
        out[s]=[g for _,g in sorted(c)[:2]]
    return out

def main()->int:
    inv=json.loads((ROOT/'inputs/inventory.json').read_text());spp=json.loads(MODEL.read_text())['seconds_per_point'];im=sha(ROOT/'inputs/manifest.json')
    with tempfile.TemporaryDirectory(prefix='c8d3_drill_select_')as td:
        td=Path(td);out=td/'drl9';cp=run('drl9','--cost-model',MODEL,'--out-dir',out)
        assert cp.returncode==0,(cp.returncode,cp.stderr[-800:])
        a=json.loads((out/'stage_a_drl9.json').read_text());e=json.loads((out/'confirm_empty_drl9.json').read_text());rep=json.loads(cp.stdout)
        want=cheapest(inv,spp)
        assert set(a['groups'])=={'free:8','power:8'}and all(len(v)==2 for v in a['groups'].values())
        for s,(g1,g2) in want.items():
            r1,r2=a['groups'][f'{s}:8'];assert (r1['id'],r2['id'])==(g1,g2),(s,r1,r2,want)
            assert (r1['points'],r1['nest'],r1['label'])==(1024,[256],'drill_nested')and (r2['points'],r2.get('nest'),r2['label'])==(512,None,'drill'),(r1,r2)
        assert rep['graphs']==want and not ({(s,g)for s,v in want.items()for g in v}&ps.zero_channel_l8(inv))
        for doc,role in ((a,'stage_a'),(e,'confirm')):
            assert doc['schema']=='c8-d3-selection-1'and doc['inputs_manifest_sha256']==im and doc['role']==role and doc['seed']is None,doc
            assert doc['cost_model']['sha256']==sha(MODEL)and doc['purpose'].startswith('J-DRL-9 drill')and doc['made_utc']
        assert a['empty_reason']is None and e['groups']=={}and 'must exit 65 and create nothing'in e['empty_reason']
        busy=2*sum((float(spp[f'a:{s}:8:{r["id"]}'])+float(spp[f'b:{s}:8:{r["id"]}']))*r['points']for k,v in a['groups'].items()for s in [k.split(':')[0]]for r in v)
        assert abs(rep['estimated_busy_core_seconds']-busy)<=1e-12*busy,(rep,busy)
        doc,_=prod.read_selection(out/'stage_a_drl9.json',im,inv,True,prod.MIN_CHUNK);assert doc['role']=='stage_a'
        try:prod.read_selection(out/'stage_a_drl9.json',im,inv,False,prod.MIN_CHUNK);raise AssertionError('accepted for a non-test plan')
        except ValueError as x:assert 'power of two >= 4096'in str(x),x
        try:prod.read_selection(out/'confirm_empty_drl9.json',im,inv,True,prod.MIN_CHUNK);raise AssertionError('empty selection accepted')
        except Refuse as x:assert x.code==65 and 'empty selection'in str(x),x
        ok('drl9: per sector the two cheapest non-zero-channel L8 graphs by (a + b) / 2 (independent recomputation), the cheapest at 1,024 points '
           'nested at [256], the other at 512; inputs_manifest_sha256, seed null, the busy estimate; read_selection accepts the stage_a file '
           'only for a test-only plan and refuses the empty confirm selection with 65')
        # negative controls
        before={f.name:sha(f)for f in out.iterdir()}
        cp=run('drl9','--cost-model',MODEL,'--out-dir',out);assert cp.returncode==64 and 'never overwritten'in cp.stderr,(cp.returncode,cp.stderr)
        assert {f.name:sha(f)for f in out.iterdir()}==before
        cp=run('drl9','--cost-model',ROOT/'tests/fixtures/cost_model_synthetic.json','--out-dir',td/'syn')
        assert cp.returncode==1 and 'synthetic'in cp.stderr and not (td/'syn').exists(),(cp.returncode,cp.stderr)
        m=json.loads(MODEL.read_text());g=want['power'][1];del m['seconds_per_point'][f'b:power:8:{g}'];(td/'nob.json').write_text(json.dumps(m))
        cp=run('drl9','--cost-model',td/'nob.json','--out-dir',td/'nob');assert cp.returncode==1 and f'power graph {g}'in cp.stderr and not (td/'nob').exists(),(cp.returncode,cp.stderr)
        # the committed L8 inventory has no zero-channel graph (s_G 0 or 2): an inputs copy marks one free L8 graph s_G = 4
        # and a model copy makes it the cheapest of all
        zc=inv['free']['8'][-1]['id'];inp=td/'inputs_zc';inp.mkdir();(inp/'manifest.json').write_bytes((ROOT/'inputs/manifest.json').read_bytes())
        iz=json.loads(json.dumps(inv));next(r for r in iz['free']['8']if r['id']==zc)['s_G']=4;(inp/'inventory.json').write_text(json.dumps(iz))
        assert ps.zero_channel_l8(iz)=={('free',zc)}and zc not in want['free']
        m=json.loads(MODEL.read_text())
        for c in 'ab':m['seconds_per_point'][f'{c}:free:8:{zc}']=1e-12
        (td/'zc.json').write_text(json.dumps(m));cp=run('drl9','--cost-model',td/'zc.json','--out-dir',td/'zc','--inputs',inp);assert cp.returncode==0,cp.stderr
        got=[r['id']for r in json.loads((td/'zc'/'stage_a_drl9.json').read_text())['groups']['free:8']]
        assert zc not in got and got==cheapest(iz,m['seconds_per_point'])['free']==want['free'],(got,zc)
        cost=ps.costs(td/'zc.json');assert ds.pick(iz,cost)['free']==got and ds.pick(iz,cost,zero_channel=lambda inv:set())['free'][0]==zc
        assert cheapest(iz,m['seconds_per_point'],zero_channel=False)['free'][0]==zc
        ok('drl9 refusals: a second run exits 64 with both files unchanged; the synthetic fixture and a model without a candidate\'s b key exit 1 '
           'writing nothing; a zero-channel graph made the cheapest is left out, and the same pick without the zero-channel filter takes it')
    print(json.dumps({'status':'passed','tests':len(RESULTS)}));return 0
if __name__=='__main__':sys.exit(main())
