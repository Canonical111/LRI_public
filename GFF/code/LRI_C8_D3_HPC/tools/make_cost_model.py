#!/usr/bin/env python3
"""Write a measured cost model (schema c8-d3-cost-model-1; PLAN B, D.14, HD11) from a merged sweep campaign.

  make_cost_model.py RUN OUTPUT [--previous PREV --refresh-report FILE]

seconds_per_point, keyed campaign:sector:L:graph (C62d's R05; never pooled over the campaigns), = the sum of the row
seconds over the sum of the row points of every checkpoint of the campaign, each checkpoint validated against its
frozen block (production.validate_checkpoint). The identity (HD11): the executable sha256 taken from the checkpoints'
runtime.executable_sha256 (they must agree with each other and with the manifest's), the CPU model of the checkpoints'
fingerprints (the most frequent; other classes give cpu_class_factors per campaign, sector and L), the MP self-check
mode, the lane width and the Slurm job ids. Provenance scheduled_with: the basis that scheduled the measuring sweep
(bootstrap, prior_model or measured) with the scheduling model's sha256 and executable sha256 as the manifest records
them (null under bootstrap).

Never a cost (D.5, A-ORC-3): this tool opens no tools/bootstrap_proxy.json, no synthetic fixture and no campaign copy of
a scheduling model (prior_cost_model.json, synthetic_cost_model.json); no number of the scheduling model enters the
fresh one. A validation campaign is refused (65): no model is ever measured from one.
--refresh-report (D.14): per (campaign, sector, L) the ratio of fresh to PREV seconds per point, the largest measured
task seconds against --max-task-seconds and the number of tasks whose measured seconds exceeded their planned
(prior-model) seconds; reported, not a gate. PREV is read for the report only, after the model is computed.
"""
from __future__ import annotations
import argparse,hashlib,json,math,sqlite3,sys
from collections import Counter,defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import Refuse,digest,dump,host_info,load,utc
import production as prod

def norm(s)->str:return ' '.join(str(s or'').split())

def measure(run:Path)->tuple[dict,dict]:
    run=Path(run).resolve();m,I,mh,_=prod.verify_base(run,check_executable=False,scheduling_copies=False)
    if m.get('plan_role')=='validation':raise Refuse(65,f'{run} is a validation campaign (--plan-role validation): no cost model is ever measured from one (D.5)')
    cost=defaultdict(lambda:[0.,0]);by_cpu=defaultdict(lambda:defaultdict(lambda:[0.,0]));exes=set();cpus=Counter();jobs=set();threads=set();tasks=[]
    for j in m['jobs']:
        p,cfg=prod.group_of(run,m,j['group'])
        for part,block in enumerate(prod.blocks_of_rows(prod.job_rows(run,j),j['blocks'])):
            f=p/'checkpoints'/f'{prod.block_name(j["shard"],part)}.json'
            if not f.exists():raise ValueError(f'incomplete sweep: {f} is missing; a model needs every block')
            doc=load(f);n=prod.validate_checkpoint(doc,block,cfg,m,mh);rt=doc['runtime'];exes.add(rt['executable_sha256'])
            fp=rt.get('fingerprint')or{};cpu=norm(fp.get('cpu_model'));cpus[cpu]+=1;threads.add(int(n['threads']))
            s=(fp.get('slurm')or{});jid=s.get('SLURM_ARRAY_JOB_ID')or s.get('SLURM_JOB_ID')
            if jid:jobs.add(str(jid))
            for r in n['rows']:
                k=f'{cfg["campaign"]}:{cfg["sector"]}:{cfg["L"]}:{r["graph"]}';c=cost[k];c[0]+=float(r['seconds']);c[1]+=r['end']-r['begin']
                g=by_cpu[cpu][(cfg['campaign'],cfg['sector'],cfg['L'])];g[0]+=float(r['seconds']);g[1]+=r['end']-r['begin']
                tasks.append((k,r['uid'],float(r['seconds']),r['end']-r['begin']))
    if len(exes)!=1:raise ValueError(f'the checkpoints name {len(exes)} executables {sorted(exes)}; a model measures one binary')
    exe=exes.pop()
    if exe!=m['executable_sha256']:raise ValueError(f'the checkpoints\' executable {exe} differs from the manifest\'s {m["executable_sha256"]}')
    ref=cpus.most_common(1)[0][0];factors={}
    for cpu,g in by_cpu.items():
        if cpu==ref:continue
        t={}
        for (c,s,L),(sec,pts) in g.items():
            r=by_cpu[ref].get((c,s,L))
            if r and r[1]and pts:t.setdefault(c,{}).setdefault(s,{})[str(L)]=(sec/pts)/(r[0]/r[1])
        if t:factors[cpu]=t
    sched={'basis':m['cost_basis']}
    if m['cost_basis']=='measured':sched.update(model_sha256=m['cost_model_sha256'],executable_sha256=m['cost_model_executable_sha256'])
    elif m['cost_basis']=='prior_model':sched.update(model_sha256=m['prior_model']['sha256'],executable_sha256=m['prior_model']['executable_sha256'],factor=m['prior_factor'])
    else:sched.update(model_sha256=None,executable_sha256=None)
    model={'schema':prod.COST_SCHEMA,'dimension':3,'order':prod.ORDER,'measured':True,'backend':m['backend'],'rates_identity':'default','numerics':m['numerics'],
           'executable_sha256':exe,'cpu_model':ref,'cpu_class_factors':factors,'lane_shape':{'threads':sorted(threads),'planned_lane_width':m['threads']},
           'mp_check':m['mp_check'],'job_ids':sorted(jobs),'seconds_per_point':{k:max(1e-12,t/n)for k,(t,n) in sorted(cost.items())},
           'scheduled_with':sched,'source':{'campaign':str(run),'manifest_sha256':mh,'plan_role':m['plan_role'],'inputs_manifest_sha256':m['inputs_manifest_sha256'],
           'checkpoint_files':sum(cpus.values())},'made_on':host_info(),'made_utc':utc(),
           'scope':'Placement and estimates only (chunking, blocks, shards, the lane deadline, the design and the cost table); sample counts and random streams unchanged. Wall cost per task.'}
    return model,{'tasks':tasks,'manifest':m,'run':run}

def refresh_report(model:dict,ctx:dict,prev:Path)->dict:
    m=ctx['manifest'];run=ctx['run'];pm=json.loads(Path(prev).read_bytes());pc=pm.get('seconds_per_point')or{}
    planned={}
    for g in m['groups']:
        p=run/'groups'/g['name'];db=sqlite3.connect(p.joinpath('tasks.sqlite').resolve().as_uri()+'?mode=ro&immutable=1',uri=True)
        try:planned.update({(g['name'],u):c for u,c in db.execute('SELECT uid,cost FROM tasks')})
        finally:db.close()
    rows=defaultdict(lambda:{'fresh':[],'prev':[],'max_task_seconds':0.,'over_planned':0,'tasks':0})
    for k,uid,sec,pts in ctx['tasks']:
        c,s,L,_=k.split(':');e=rows[f'{c}:{s}:{L}'];e['max_task_seconds']=max(e['max_task_seconds'],sec);e['tasks']+=1
        if sec>planned.get((f'{c}_{s}_L{L}',uid),math.inf):e['over_planned']+=1
    for k,v in model['seconds_per_point'].items():
        c,s,L,_=k.split(':');e=rows[f'{c}:{s}:{L}'];e['fresh'].append(v)
        if k in pc:e['prev'].append(float(pc[k]))
    out={}
    for key,e in sorted(rows.items()):
        f=sum(e['fresh'])/len(e['fresh'])if e['fresh']else None;p=sum(e['prev'])/len(e['prev'])if e['prev']else None
        out[key]={'fresh_over_prev':(f/p if f and p else None),'max_task_seconds':e['max_task_seconds'],'max_task_limit':m['chunking']['max_task_seconds'],
                  'tasks_over_planned_seconds':e['over_planned'],'tasks':e['tasks']}
    return {'schema':'c8-d3-refresh-report-1','previous_model_sha256':hashlib.sha256(Path(prev).read_bytes()).hexdigest(),
            'previous_executable_sha256':pm.get('executable_sha256'),'fresh_executable_sha256':model['executable_sha256'],'basis':model['scheduled_with'],
            'rows':out,'note':'reported, not a gate: the measurement is what counts (D.14)'}

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);p.add_argument('run',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--previous',type=Path,help='the model the refresh replaces (report only)');p.add_argument('--refresh-report',type=Path);a=p.parse_args(argv)
    try:
        if bool(a.previous)!=bool(a.refresh_report):raise Refuse(64,'--previous and --refresh-report go together')
        model,ctx=measure(a.run)
        dump(a.output,model)
        if a.refresh_report:dump(a.refresh_report,refresh_report(model,ctx,a.previous))
    except Refuse as e:print(f'make_cost_model: {e}',file=sys.stderr);return e.code
    except (ValueError,OSError)as e:print(f'make_cost_model: {e}',file=sys.stderr);return 1
    print(json.dumps({'model':str(a.output),'sha256':digest(a.output),'executable_sha256':model['executable_sha256'],'keys':len(model['seconds_per_point']),
                      'cpu_model':model['cpu_model'],'scheduled_with':model['scheduled_with']}))
    return 0
if __name__=='__main__':sys.exit(main())
