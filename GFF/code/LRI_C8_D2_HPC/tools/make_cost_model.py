#!/usr/bin/env python3
"""Measured planning cost model of a merged campaign (schema c8-d2-cost-model-1; PLAN component B/D, R05).

  make_cost_model.py RUN OUTPUT [--note TEXT] [--reuse-identical]
        seconds per point for every campaign:sector:L:graph key of the campaign (campaigns a and b are measured and
        kept separately, never pooled), from the merged groups' graph_costs.csv (sum of native row seconds over the
        points, every replicate), each verified through its merged.json; also the quad and MP promotion fractions per
        key (P5), the rates identity the costs were measured under (`default`, or the frozen map's sha256; D15), the
        backend, numerics, executable sha256, the CPU models, hosts and Slurm job ids of the checkpoints, and the
        lane width. The reference CPU models get class factor 1 in the lane deadline. OUTPUT is published no-clobber;
        with --reuse-identical (tools/sweep.py, O09) an existing OUTPUT is kept when it is this campaign's model, i.e.
        equal in every field to the model recomputed now from the campaign's verified merged tables and checkpoints
        except derived_utc and note, and refused (exit 3, naming the fields) when it is not.
  make_cost_model.py class-factors MODEL RUN OUTPUT
        J-SWEEP-3: a copy of MODEL with cpu_class_factors[<CPU model of RUN>][campaign][sector][L] for L >= 6, the
        ratio of RUN's seconds to MODEL's over their common graphs (identical points on another CPU class). RUN and
        MODEL must have the same backend, rates identity and numerics (X10: a factor between two numerics profiles
        would mix a profile's speed-up into the CPU class; a model without a numerics identity is refused).
Never changes integration weights or sample allocations; never reads tools/bootstrap_proxy.json.
"""
from __future__ import annotations
import argparse,csv,json,sys
from decimal import Decimal as D
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import production as prod
from common import digest,dump,load,slurm_ids,utc

def graph_costs(run:Path)->tuple[dict,dict,dict]:
    """({key: seconds per point}, {key: quad fraction}, {key: mp fraction}) of a merged campaign."""
    run=Path(run).resolve();m,I,mh,_=prod.verify_base(run,check_executable=False,vendored=True);sec={};qf={};mf={}
    for g in m['groups']:
        p,cfg=prod.group_of(run,m,g['name'])
        if not (p/'merged.json').exists():raise ValueError(f'group {g["name"]} is not merged; run production.py merge first')
        prod.validate_merged(p,cfg,m,mh)
        with (p/'graph_costs.csv').open()as f:
            for r in csv.DictReader(f):
                k=f'{cfg["campaign"]}:{cfg["sector"]}:{cfg["L"]}:{r["graph"]}';n=int(r['points'])
                sec[k]=max(1e-12,float(D(r['row_seconds'])/n));qf[k]=int(r['quad'])/n;mf[k]=int(r['mp'])/n
        want={f'{cfg["campaign"]}:{cfg["sector"]}:{cfg["L"]}:{x}'for x in cfg['counts']}
        if not want<=set(sec):raise ValueError(f'group {g["name"]}: merged costs miss {len(want-set(sec))} selected graphs')
    return sec,qf,mf

def provenance(run:Path,m:dict)->dict:
    cpus=set();hosts=set();jobs=set()
    for j in m['jobs']:
        d=run/'groups'/j['group']/'checkpoints'
        for k in range(j['blocks']):
            f=d/f'{prod.block_name(j["shard"],k)}.json'
            if not f.exists():continue
            fp=(prod.checkpoint_runtime(f)or{}).get('fingerprint')or{}
            if fp.get('cpu_model'):cpus.add(' '.join(fp['cpu_model'].split()))
            if fp.get('host'):hosts.add(fp['host'])
            jobs.update(slurm_ids(fp))
    return {'cpu_models':sorted(cpus),'hosts':sorted(hosts),'job_ids':sorted(jobs,key=lambda x:(len(x),x))}

def build(run:Path,note:str|None=None)->dict:
    run=Path(run).resolve();m=load(run/'manifest.json');sec,qf,mf=graph_costs(run);pv=provenance(run,m)
    return {'schema':prod.COST_SCHEMA,'dimension':2,'order':prod.ORDER,'backend':m['backend'],'numerics':m['numerics'],'rates_identity':m['rates_identity'],
            'executable_sha256':m['executable_sha256'],'build':m['build'],'source_manifest_sha256':digest(run/'manifest.json'),'source_campaign':str(run),
            'source_test_only':m['test_only'],'lane_width':m['threads'],'cpu_models':pv['cpu_models'],'hosts':pv['hosts'],'job_ids':pv['job_ids'],
            'derived_utc':utc(),'keys':len(sec),'seconds_per_point':dict(sorted(sec.items())),'quad_fraction':dict(sorted(qf.items())),
            'mp_fraction':dict(sorted(mf.items())),'cpu_class_factors':{},'note':note,
            'scope':'Planning only (chunking, index sizing, estimates, lane deadlines, design costs); sample counts and random streams unchanged. '
                    'Per-task native wall seconds per point on the listed CPU models, not an isolated cycle count.'}

VOLATILE=('derived_utc','note')
def publish_model(out:Path,doc:dict,reuse:bool=False)->str:
    """Publish a cost model no-clobber: 'written'; with reuse an existing file equal to doc in every field but
    VOLATILE is kept ('reused'), any other existing file refuses (ValueError naming the differing fields; O09)."""
    out=Path(out)
    if reuse and out.exists():
        try:old=json.loads(out.read_bytes())
        except ValueError as e:raise ValueError(f'{out} exists and is not a cost model ({e}); move it away or give another output')
        new=json.loads(json.dumps(doc,allow_nan=False))
        diff=sorted(k for k in set(old)|set(new)if k not in VOLATILE and old.get(k)!=new.get(k))if isinstance(old,dict)else['(not an object)']
        if diff:raise ValueError(f'{out} exists and is not this campaign\'s cost model: it differs from the model recomputed from the campaign\'s '
                                 f'merged tables in {", ".join(diff[:8])}; move it away or give another output')
        return 'reused'
    dump(out,doc);return 'written'

def class_factors(model:dict,run:Path)->dict:
    """cpu_class_factors[cpu][c][s][L] (L >= 6) = sum of RUN's seconds / sum of MODEL's seconds over the common keys."""
    run=Path(run).resolve();m=load(run/'manifest.json')
    if m['rates_identity']!=model['rates_identity']or m['backend']!=model['backend']:raise ValueError('class factors need the same backend and rates identity')
    if model.get('numerics')is None or m.get('numerics')!=model.get('numerics'):  # X10: never a factor across numerics profiles
        raise ValueError(f'class factors need the same numerics: the model was measured under {model.get("numerics")!r}, {run} ran under {m.get("numerics")!r}')
    sec,_,_=graph_costs(run);pv=provenance(run,m)
    if len(pv['cpu_models'])!=1:raise ValueError(f'{run} ran on {len(pv["cpu_models"])} CPU models; a class factor needs exactly one')
    cpu=pv['cpu_models'][0];acc={}
    for k,v in sec.items():
        if k not in model['seconds_per_point']:continue
        c,s,L,_=k.split(':')
        if int(L)<6:continue
        a=acc.setdefault((c,s,L),[0.,0.]);a[0]+=v;a[1]+=model['seconds_per_point'][k]
    if not acc:raise ValueError('no common L >= 6 graphs between the model and the run')
    out=json.loads(json.dumps(model));t=out.setdefault('cpu_class_factors',{}).setdefault(cpu,{})
    for (c,s,L),(x,y)in sorted(acc.items()):t.setdefault(c,{}).setdefault(s,{})[L]=x/y
    out.setdefault('class_factor_sources',{})[cpu]={'campaign':str(run),'manifest_sha256':digest(run/'manifest.json'),'derived_utc':utc()}
    return out

def main(argv=None)->int:
    if argv is None:argv=sys.argv[1:]
    if argv[:1]==['class-factors']:
        p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('run',type=Path);p.add_argument('output',type=Path);a=p.parse_args(argv[1:])
        try:doc=class_factors(load(a.model),a.run)
        except ValueError as e:print(f'make_cost_model: {e}',file=sys.stderr);return 3
        dump(a.output,doc);print(json.dumps({'output':str(a.output)}));return 0
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);p.add_argument('run',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--note');p.add_argument('--reuse-identical',action='store_true',help='keep an existing OUTPUT that is this campaign\'s model (sweep restart, O09)')
    a=p.parse_args(argv)
    doc=build(a.run,a.note)
    try:state=publish_model(a.output,doc,a.reuse_identical)
    except ValueError as e:print(f'make_cost_model: {e}',file=sys.stderr);return 3
    print(json.dumps({'output':str(a.output),'state':state,'keys':doc['keys'],'backend':doc['backend'],'rates_identity':doc['rates_identity'],'cpu_models':doc['cpu_models']}));return 0
if __name__=='__main__':sys.exit(main())
