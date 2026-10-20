#!/usr/bin/env python3
"""Cost benchmark for sizing the C8 pilot: per-tree power-quadrature seconds versus degree (L6..L8), per-point QMC
seconds with precision fallbacks (L6..L8), and a binary128 contraction replay at L8. A cost model
seconds = a_L * terms_g * (N+1)^(L-1) (power) and b_L * terms_g (qmc) is fitted and extrapolated to whole campaigns
(per replicate, one tree or point per active graph).
Usage: bench8.py --c8 PKG --inputs DIR --out DIR [--threads N]
"""
from __future__ import annotations
import argparse, json, math, subprocess, sys
from decimal import Decimal as D
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from campaign import plan_counts,net_file

def run(cmd):
    cmd=[str(x) for x in cmd];r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode:raise RuntimeError(' '.join(cmd)+'\n'+r.stderr[-2000:])

def tasks(path,ng,work):Path(path).write_text(f'C8TASKS1 {ng} {len(work)}\n'+''.join(' '.join(map(str,w))+'\n' for w in work))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--c8',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--threads',type=int,default=16);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);rep={}
    exe=a.c8/'bin/c8_integrate'
    for L,degs,sample in [(6,[1,3,5,6,7,8],24),(7,[1,3,5,6,7,8],24),(8,[1,3,5,6,7],32)]:
        rows,cp=plan_counts(a.inputs,L,'power','power',None,1,1);act=[r for r in rows if cp[r['id']]];act.sort(key=lambda r:r['terms'])
        pick=[act[int(i*(len(act)-1)/(sample-1))] for i in range(sample)];ng=len(rows);tot_terms=sum(r['terms'] for r in act)
        res={}
        for N in degs:
            if L==8 and N>=7:pick_n=pick[::4]
            else:pick_n=pick
            work=[(i,0,r['id'],0,1,1) for i,r in enumerate(pick_n)];d=a.out/f'power_L{L}_N{N}';d.mkdir(exist_ok=True);tasks(d/'t.txt',ng,work);(d/'o.json').unlink(missing_ok=True)
            run([exe,'--mode','power','--inputs',a.inputs,'--L',L,'--tasks',d/'t.txt','--seed',5,'--rate','.8','--output',d/'o.json','--degree',N,'--threads',a.threads])
            o=json.loads((d/'o.json').read_text());sec=sum(r['seconds'] for r in o['rows']);terms=sum(r2['terms'] for r2 in pick_n)
            coef=sec/(terms*(N+1)**(L-1));res[N]={'graphs':len(pick_n),'seconds':sec,'a':coef,'per_replicate_all_graphs_core_hours':coef*tot_terms*(N+1)**(L-1)/3600}
            print(L,N,res[N],flush=True)
        rep[f'power_L{L}']={'active_graphs':len(act),'total_terms':tot_terms,'degrees':res}
        rows,cq=plan_counts(a.inputs,L,'qmc','free',None,1,1);actq=[r for r in rows if cq[r['id']]];actq.sort(key=lambda r:r['terms'])
        pickq=[actq[int(i*(len(actq)-1)/(47))] for i in range(48)];n=64;work=[(i,r2,g['id'],0,n,n) for i,(r2,g) in enumerate([(r2,g) for r2 in range(2) for g in pickq])]
        d=a.out/f'qmc_L{L}';d.mkdir(exist_ok=True);net=d/'net'
        if not net.exists():net_file(net,2,2*L-1,1234+L)
        tasks(d/'t.txt',len(rows),work);(d/'o.json').unlink(missing_ok=True)
        run([exe,'--mode','qmc','--inputs',a.inputs,'--L',L,'--tasks',d/'t.txt','--seed',6,'--rate','.8','--output',d/'o.json','--net',net,'--threads',a.threads])
        o=json.loads((d/'o.json').read_text());sec=sum(r['seconds'] for r in o['rows']);terms=sum(g['terms'] for g in pickq)*2*n
        nq=sum(r['quad_calls'] for r in o['rows']);nm=sum(r['mp_calls'] for r in o['rows'])
        b=sec/terms;rep[f'qmc_L{L}']={'active_graphs':len(actq),'total_terms':sum(r['terms'] for r in actq),'b':b,'binary128_fraction':nq/(len(work)*n),'mp100_fraction':nm/(len(work)*n),'per_point_all_graphs_core_hours':b*sum(r['terms'] for r in actq)/3600}
        print(L,'qmc',rep[f'qmc_L{L}'],flush=True)
        (a.out/'bench.json').write_text(json.dumps(rep,indent=1))
    # binary128 replay at L8 (contraction rounding), degree 5, four graphs of increasing size
    rows,cp=plan_counts(a.inputs,8,'power','power',None,1,1);act=sorted([r for r in rows if cp[r['id']]],key=lambda r:r['terms']);pick=[act[int(i*(len(act)-1)/3)] for i in range(4)]
    work=[(i,0,r['id'],0,1,1) for i,r in enumerate(pick)];d=a.out/'replay_L8';d.mkdir(exist_ok=True);tasks(d/'t.txt',len(rows),work)
    for bits,f in (('64','ld.json'),('113','q.json')):
        (d/f).unlink(missing_ok=True);run([exe,'--mode','power','--inputs',a.inputs,'--L',8,'--tasks',d/'t.txt','--seed',7,'--rate','.8','--output',d/f,'--degree',5,'--threads',a.threads,'--quad-bits',bits])
    load=lambda f:{int(r['graph']):list(r['value']) for r in json.loads((d/f).read_text(),parse_float=D,parse_int=D)['rows']} # exact Decimal parsing
    rl,rq=load('ld.json'),load('q.json')
    worst=max(abs(x-y)/max(abs(z) for z in rq[g]) for g in rq for x,y in zip(rl[g],rq[g]))
    reg=max(abs(x-y)/abs(y) for g in rq for x,y in list(zip(rl[g],rq[g]))[7:8]+list(zip(rl[g],rq[g]))[15:16] if y)
    rep['replay_L8_N5']={'graphs':[r['id'] for r in pick],'max_diff_over_row_scale':str(worst),'max_relative_top_slot':str(reg)}
    (a.out/'bench.json').write_text(json.dumps(rep,indent=1));print(json.dumps(rep['replay_L8_N5']))
if __name__=='__main__':main()
