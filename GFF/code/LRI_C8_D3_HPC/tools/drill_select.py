#!/usr/bin/env python3
"""J-DRL-9's hand-made selections (PLAN J-DRL-9, A-DES-7 (c) and (f), A-SMK-2; schema c8-d3-selection-1).

  drill_select.py drl9 --cost-model M --out-dir DIR [--inputs DIR]

The subset-pilot drill plans a test-only `--pilot --graphs` campaign from a stage_a selection of 4 L8 graphs and tries
an empty confirm selection, which `production.py plan` must refuse (65) without creating anything. This tool writes
both files; tools/pilot_select.py (pinned for the PA plan, Stage 6 PINNED_TOOLS) is not touched.

Rule, per sector free and power: the candidates are the inventory's L8 rows without the zero-channel graphs
(pilot_select.zero_channel_l8: s_G = 4, never selected in a pilot), ranked by the measured model's mean seconds per
point of campaigns a and b (pilot_select.costs: (spp[a:s:8:g] + spp[b:s:8:g]) / 2), ties by id; a candidate without
an a or a b key refuses (1, naming it). The cheapest is {"id", "points": 1024, "nest": [256], "label": "drill_nested"}
(256 >= MIN_CHUNK and divides 1024), the second {"id", "points": 512, "label": "drill"}.
  DIR/stage_a_drl9.json        role stage_a, seed null (no draw; the plan's own seed is registered by the plan job),
                               groups {"free:8": [...], "power:8": [...]}, empty_reason null
  DIR/confirm_empty_drl9.json  role confirm, groups {}, empty_reason "J-DRL-9 drill: ..."
Both carry the inputs_manifest_sha256 (digest of inputs/manifest.json), the purpose, the rule, the cost model's path and
sha256 and made_utc. M is read with production.read_cost_model (unmeasured, synthetic and pooled models refused).

Self-check before writing (any surprise exits 1 and writes nothing): production.read_selection accepts the stage_a
file for a test-only plan and refuses it for any other ("power of two >= 4096"), and refuses the empty one with 65.
An existing output refuses (64): selection files are never overwritten. It prints JSON with both files, the four graph
ids and the estimated busy core-seconds of the drill, 2 replicates x the sum over campaigns a and b of spp x points (for
J-DRL-0's sizing). Exit codes: 0, 64 usage or an existing output, 1 input errors.

The drill (runbook): a plan job runs `production.py plan D9 --pilot --graphs DIR/stage_a_drl9.json --replicates 2
--test-only --threads <w> --backend gmp --mp-check on --cost-model cost_models/$C8_SITE_MODEL --seed S`, then seeds.py
add and ledger.py register; the same plan with DIR/confirm_empty_drl9.json exits 65 and leaves no directory; then
`slurm_submit.py lanes 1` in drill mode (C8_LANE_DRILL=1).
"""
from __future__ import annotations
import argparse,json,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import Refuse,digest,dump,load,utc
import production as prod
import pilot_select as ps

NESTED_POINTS=1024;NEST=[256];POINTS=512;REPLICATES=2
PURPOSE='J-DRL-9 drill: test-only plans only (points < 4096)'
EMPTY_REASON='J-DRL-9 drill: an empty confirm selection (A-DES-7 (c), (f)); plan --graphs must exit 65 and create nothing'
RULE=('per sector free and power: the inventory\'s L8 rows without the zero-channel graphs (s_G = 4, pilot_select.zero_channel_l8), ranked by the '
      'measured model\'s (spp[a:s:8:g] + spp[b:s:8:g]) / 2, ties by id; the cheapest at 1,024 points nested at [256] (drill_nested), the second at 512 '
      'points (drill)')

def pick(inv:dict,cost:dict,zero_channel=ps.zero_channel_l8)->dict:
    """{sector: [cheapest id, second id]} (zero_channel: the hook that names the excluded graphs; tests replace it)."""
    zc=zero_channel(inv);out={}
    for s in ('free','power'):
        cand=[r['id']for r in (inv.get(s)or{}).get('8',[])if (s,r['id'])not in zc]
        miss=[g for g in cand if set(cost.get((s,g),{}))<{'a','b'}]
        if miss:raise ValueError(f'the cost model has no a and b seconds for L8 {s} graph {miss[0]} ({len(miss)} graphs without them)')
        ranked=sorted(cand,key=lambda g:((cost[(s,g)]['a']+cost[(s,g)]['b'])/2,g))
        if len(ranked)<2:raise ValueError(f'L8 {s}: {len(ranked)} candidate graphs, the drill needs 2')
        out[s]=ranked[:2]
    return out

def documents(picked:dict,im_sha:str,model:Path)->tuple[dict,dict]:
    head={'schema':prod.SELECTION_SCHEMA,'inputs_manifest_sha256':im_sha,'seed':None,'purpose':PURPOSE,'rule':RULE,
          'cost_model':{'path':str(model),'sha256':digest(model)},'made_utc':utc()}
    groups={f'{s}:8':[{'id':g1,'points':NESTED_POINTS,'nest':list(NEST),'label':'drill_nested'},{'id':g2,'points':POINTS,'label':'drill'}]
            for s,(g1,g2) in picked.items()}
    return {**head,'role':'stage_a','groups':groups,'empty_reason':None},{**head,'role':'confirm','groups':{},'empty_reason':EMPTY_REASON}

def self_check(stage_a:dict,empty:dict,im_sha:str,inv:dict)->None:
    """production.read_selection on both documents: the stage_a file only for a test-only plan, the empty one 65."""
    with tempfile.TemporaryDirectory(prefix='c8d3_drl9_')as td:
        a=Path(td)/'a.json';e=Path(td)/'e.json';a.write_text(json.dumps(stage_a));e.write_text(json.dumps(empty))
        prod.read_selection(a,im_sha,inv,True,prod.MIN_CHUNK)
        try:prod.read_selection(a,im_sha,inv,False,prod.MIN_CHUNK)
        except ValueError as x:
            if 'power of two >= 4096'not in str(x):raise ValueError(f'self-check: a non-test read of the stage_a file failed for another reason: {x}')
        else:raise ValueError('self-check: the stage_a file was accepted for a non-test plan')
        try:prod.read_selection(e,im_sha,inv,True,prod.MIN_CHUNK)
        except Refuse as x:
            if x.code!=65 or 'empty selection'not in str(x):raise ValueError(f'self-check: the empty selection was refused otherwise: {x}')
        else:raise ValueError('self-check: the empty confirm selection was accepted')

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);s=p.add_subparsers(dest='cmd',required=True)
    q=s.add_parser('drl9');q.add_argument('--cost-model',type=Path,required=True);q.add_argument('--out-dir',type=Path,required=True);q.add_argument('--inputs',type=Path)
    try:a=p.parse_args(argv)
    except SystemExit as e:return 64 if e.code else 0
    fa=a.out_dir/'stage_a_drl9.json';fe=a.out_dir/'confirm_empty_drl9.json'
    try:
        old=[str(f)for f in (fa,fe)if f.exists()]
        if old:raise Refuse(64,f'{", ".join(old)} exist(s): a selection file is never overwritten')
        import prepare_inputs as pi
        d=Path(a.inputs).resolve()if a.inputs else pi.inputs_dir();inv=load(d/'inventory.json');im_sha=digest(d/'manifest.json')
        cost=ps.costs(a.cost_model);picked=pick(inv,cost);doc_a,doc_e=documents(picked,im_sha,a.cost_model)
        self_check(doc_a,doc_e,im_sha,inv)
        busy=REPLICATES*sum((cost[(sec,r['id'])]['a']+cost[(sec,r['id'])]['b'])*r['points']for k,rows in doc_a['groups'].items()for sec in [k.split(':')[0]]for r in rows)
        a.out_dir.mkdir(parents=True,exist_ok=True);dump(fa,doc_a);dump(fe,doc_e)
    except Refuse as e:print(f'drill_select: {e}',file=sys.stderr);return e.code
    except (ValueError,OSError,KeyError)as e:print(f'drill_select: {e}',file=sys.stderr);return 1
    print(json.dumps({'stage_a':str(fa),'confirm_empty':str(fe),'graphs':{s:g for s,g in picked.items()},'inputs_manifest_sha256':im_sha,
                      'estimated_busy_core_seconds':busy,'replicates':REPLICATES}))
    return 0
if __name__=='__main__':sys.exit(main())
