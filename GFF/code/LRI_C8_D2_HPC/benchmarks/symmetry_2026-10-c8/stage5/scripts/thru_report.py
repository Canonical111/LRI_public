#!/usr/bin/env python3
"""J-SMK-4 report (symmetry Stage 5): A-PERF-3 and the real-Slurm part of A-ORC-13 for one lane-mode campaign run by
ONE whole-node lane worker job. Read-only on the campaign; standard library plus the package's own modules.

  thru_report.py PACKAGE RUN --job JOBID --cost-model CM2 [--sweep-cost-model CM1] [--rchar-dir DIR]
                 [--p4-stage4a P4JSON] [--p4-final P4JSON] --output OUT.json

A-PERF-3 (8 x 8 NUMA lanes, >= 1 h of L8 work):
  busy        sum of task row seconds / (64 x W), W = the lane job's sacct ElapsedRaw (whole allocation);
  omp         per checkpoint block: sum of row seconds / (threads x integration_seconds); the time-weighted mean
              (weights threads x integration_seconds), the median, P10, the share of blocks >= 0.95, all and L8 only;
  throughput  sum over tasks of CM2 seconds per point x points / W (cost-model seconds per node-second), compared with
              the best P4 shape (8x8) re-expressed in CM2 units: (a) the Stage-4a P4 job 569788 (Stage-3 binary)
              scaled by CM2/CM1 over its workload, (b) the P4 8x8 rerun with the final binary (--p4-final);
  speed       per task: CM2 seconds per point x points / row seconds; the median against 1 (the sweep's own speed).
A-ORC-13 (real Slurm): per production.py run (one per index claim): rchar from the measurement hook
(scripts/rchar_hook), fingerprint_bytes from the index log; own bytes = the index's task file + per block 2 x the
staged pack members (staging read + native read) + the tasks.txt the native reads + its native.json read back (sized
as the checkpoint's native payload) + the net and gamma files the native reads per block + the net and gamma staged
once; non-own = rchar - own (with and without fingerprint_bytes); compared between indices of the smallest and the
largest group by tasks.sqlite size (must differ by > 10x): agreement within 10% or 2 MB."""
import argparse,csv,glob,json,math,os,re,statistics,subprocess,sys
from pathlib import Path

def sacct(job):
    out=subprocess.run(['sacct','-X','--duplicates','-n','-P','-j',str(job),'-o','JobID,State,ElapsedRaw,Start,End,NodeList,AllocCPUS'],capture_output=True,text=True).stdout
    rows=[l.split('|')for l in out.strip().splitlines()if l.strip()]
    return [{'job':r[0],'state':r[1],'elapsed':int(r[2]),'start':r[3],'end':r[4],'nodes':r[5],'cpus':int(r[6])}for r in rows]

def q(xs,p):
    xs=sorted(xs);return xs[min(len(xs)-1,max(0,int(round(p*(len(xs)-1)))))]if xs else None

def main():
    ap=argparse.ArgumentParser();ap.add_argument('package',type=Path);ap.add_argument('run',type=Path);ap.add_argument('--job',required=True)
    ap.add_argument('--cost-model',type=Path,required=True);ap.add_argument('--sweep-cost-model',type=Path);ap.add_argument('--rchar-dir',type=Path)
    ap.add_argument('--p4-stage4a',type=Path);ap.add_argument('--p4-final',type=Path);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    sys.path.insert(0,str(a.package/'tools'))
    import production as prod
    run=a.run.resolve();m=json.loads((run/'manifest.json').read_text());cm2=json.loads(a.cost_model.read_text())['seconds_per_point']
    inv=json.loads((a.package/'inputs/inventory.json').read_text())
    length={(s,int(L),r['id']):int(r['length'])for s in('free','power')for L,rows in inv[s].items()for r in rows}
    acct=sacct(a.job);W=sum(r['elapsed']for r in acct);ncores=64
    gamma_bytes=(a.package/'inputs/gamma_d2_8.txt').stat().st_size
    tasks=[];blocks=[];per_index={}
    for j in m['jobs']:
        d=run/'groups'/j['group']/'checkpoints';cfg=json.loads((run/'groups'/j['group']/'config.json').read_text())
        net_bytes=(run/'groups'/j['group']/'sobol.bin').stat().st_size;own=j['tasks_bytes']+net_bytes+gamma_bytes;fpb=set();nb=0
        for k in range(j['blocks']):
            f=d/f'{prod.block_name(j["shard"],k)}.json'
            if not f.exists():continue
            doc=json.loads(f.read_text());n=doc['native'];rows=n['rows'];nb+=1
            fpb.add(doc['runtime'].get('fingerprint_bytes'))
            rs=math.fsum(float(r['seconds'])for r in rows);th=int(n['threads']);integ=float(n['integration_seconds'])
            blocks.append({'index':j['id'],'group':j['group'],'L':cfg['L'],'tasks':len(rows),'threads':th,'integration_seconds':integ,'row_seconds':rs,
                           'omp':rs/(th*integ)if integ>0 else None,'load_seconds':float(n.get('load_seconds')or 0),'max_rss_kb':n.get('max_rss_kb')})
            graphs=set()
            for r in rows:
                pts=int(r['end'])-int(r['begin']);c2=cm2[f'{cfg["campaign"]}:{cfg["sector"]}:{cfg["L"]}:{r["graph"]}']*pts
                tasks.append({'L':cfg['L'],'row_seconds':float(r['seconds']),'cost2':c2,'speed':c2/float(r['seconds'])if float(r['seconds'])>0 else None});graphs.add(int(r['graph']))
            tasks_txt=sum(len(' '.join(str(r[k])for k in('uid','rep','graph','begin','end','total')))+1 for r in rows)+32
            own+=2*sum(length[(cfg['sector'],cfg['L'],g)]for g in graphs)+tasks_txt+len(json.dumps(n))+net_bytes+gamma_bytes
        per_index[j['id']]={'group':j['group'],'L':cfg['L'],'blocks':nb,'tasks_bytes':j['tasks_bytes'],'own_bytes_estimate':own,'fingerprint_bytes_ckpt':sorted(x for x in fpb if x is not None)}
    busy=math.fsum(t['row_seconds']for t in tasks)/(ncores*W)if W else None
    def omp_stats(bl):
        bl=[b for b in bl if b['omp']is not None];w=math.fsum(b['threads']*b['integration_seconds']for b in bl)
        return {'blocks':len(bl),'weighted_mean':math.fsum(b['row_seconds']for b in bl)/w if w else None,'median':q([b['omp']for b in bl],.5),
                'p10':q([b['omp']for b in bl],.1),'share_ge_0.95':sum(b['omp']>=0.95 for b in bl)/len(bl)if bl else None,'min':min((b['omp']for b in bl),default=None)}
    c2tot=math.fsum(t['cost2']for t in tasks);thr=c2tot/W if W else None
    sp=[t['speed']for t in tasks if t['speed']];sp8=[t['speed']for t in tasks if t['speed']and t['L']==8]
    rep={'campaign':str(run),'job':a.job,'sacct':acct,'wall_seconds':W,'cores':ncores,'tasks':len(tasks),'blocks':len(blocks),
         'row_seconds_total':math.fsum(t['row_seconds']for t in tasks),'L8_row_seconds':math.fsum(t['row_seconds']for t in tasks if t['L']==8),
         'busy_fraction':busy,'busy_rule':'>= 0.90','omp_all':omp_stats(blocks),'omp_L8':omp_stats([b for b in blocks if b['L']==8]),'omp_rule':'>= 0.95 per block',
         'cost2_seconds_total':c2tot,'throughput_cost2_per_node_second':thr,
         'speed_median_all':q(sp,.5),'speed_median_L8':q(sp8,.5),'speed_p10_p90_L8':[q(sp8,.1),q(sp8,.9)],'speed_rule':'median within 10% of the sweep (1.0)'}
    # P4 references, re-expressed in CM2 units over the P4 workload (fixture spp = J-SWEEP-1 campaign a)
    import benchmark as bm
    import benchkit as bk
    fm=bk.load_fixtures(a.package/'benchmarks/fixtures8')
    def p4_ref(path,label):
        if not path or not path.exists():return None
        d=json.loads(path.read_text());fr=d['workload']['fraction']
        items,parts=bm.workload_items(fm,d['workload']['name'],fr)
        c1=math.fsum(c for c,_,_ in items);c2=0.
        for _,(bn,_u),r in items:
            b=fm['blocks'][bn];c2+=cm2[f'a:{b["sector"]}:{b["L"]}:{r[2]}']*(r[4]-r[3])
        best=max(d['table'],key=lambda s:s['throughput_cost_model_s_per_node_s']or 0)
        row=next((s for s in d['table']if s['shape']=='8x8'),best)
        return {'label':label,'file':str(path),'shape':row['shape'],'wall_seconds':row['wall_seconds'],'throughput_cm1':row['throughput_cost_model_s_per_node_s'],
                'workload_cost1':c1,'workload_cost2':c2,'throughput_cm2':row['throughput_cost_model_s_per_node_s']*c2/c1,'best_shape':best['shape'],'busy':row.get('busy_fraction'),'omp':row.get('openmp_efficiency')}
    refs={}
    try:refs['p4_stage4a_569788']=p4_ref(a.p4_stage4a,'Stage-4a P4 (Stage-3 binary, job 569788)')
    except Exception as e:refs['p4_stage4a_569788']={'error':repr(e)}
    try:refs['p4_final_rerun']=p4_ref(a.p4_final,'P4 8x8 rerun with the final binary')
    except Exception as e:refs['p4_final_rerun']={'error':repr(e)}
    rep['p4_references']=refs
    for k,v in refs.items():
        if v and 'throughput_cm2'in v and thr:rep[f'throughput_ratio_vs_{k}']=thr/v['throughput_cm2']
    # A-ORC-13: rchar per run
    logs={}
    for f in glob.glob(str(run/'lanes/logs/idx*.log')):
        mt=re.search(r'fingerprint_bytes (\d+)',Path(f).read_text(errors='replace'));i=int(Path(f).name.split('.')[0][3:])
        if mt:logs.setdefault(i,[]).append(int(mt.group(1)))
    rch={}
    if a.rchar_dir and a.rchar_dir.exists():
        for f in a.rchar_dir.glob('rchar.*.json'):
            d=json.loads(f.read_text());rch.setdefault(int(d['index']),[]).append(d)
    sq={g['name']:(run/'groups'/g['name']/'tasks.sqlite').stat().st_size for g in m['groups']}
    with_rchar={per_index[i]['group']for i in rch if i in per_index}
    small=min(with_rchar,key=lambda g:sq[g],default=None);large=max(with_rchar,key=lambda g:sq[g],default=None)
    def row(i):
        r=rch[i][-1];fb=(logs.get(i)or[None])[-1];own=per_index[i]['own_bytes_estimate']
        return {'index':i,'group':per_index[i]['group'],'rchar':r['rchar'],'fingerprint_bytes':fb,'own_bytes_estimate':own,'non_own':r['rchar']-own,
                'non_own_without_fingerprint':r['rchar']-own-(fb or 0),'ru_maxrss_self_kb':r.get('ru_maxrss_self_kb'),'ru_maxrss_children_kb':r.get('ru_maxrss_children_kb')}
    runs=[row(i)for i in sorted(rch)if i in per_index]
    fps=sorted({x['fingerprint_bytes']for x in runs if x['fingerprint_bytes']is not None})
    cmp=None
    if small and large:
        A=[x for x in runs if x['group']==small];B=[x for x in runs if x['group']==large]
        def agree(key):
            a_=statistics.median(x[key]for x in A);b_=statistics.median(x[key]for x in B);d=abs(a_-b_)
            return {'smallest_group_median':a_,'largest_group_median':b_,'difference':d,'tolerance':max(0.10*max(a_,b_),2*2**20),'agree':d<=max(0.10*max(a_,b_),2*2**20)}
        cmp={'smallest_group':small,'largest_group':large,'tasks_sqlite_bytes':[sq[small],sq[large]],'ratio':sq[large]/max(1,sq[small]),
             'non_own':agree('non_own'),'non_own_without_fingerprint':agree('non_own_without_fingerprint')}
    rep['a_orc_13']={'runs_with_rchar':len(runs),'distinct_fingerprint_bytes':fps,'fingerprint_bytes_identical':len(fps)==1,'comparison':cmp,
                     'non_own_range':[min((x['non_own']for x in runs),default=None),max((x['non_own']for x in runs),default=None)]}
    rep['runs']=runs;rep['block_detail']=blocks
    a.output.write_text(json.dumps(rep,indent=1)+'\n')
    print(json.dumps({k:v for k,v in rep.items()if k not in('runs','block_detail','sacct')},indent=1)[:6000])

if __name__=='__main__':main()
