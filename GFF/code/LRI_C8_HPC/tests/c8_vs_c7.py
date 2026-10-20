#!/usr/bin/env python3
"""Regression of the order-eight kernel against the reviewed C7 kernel on identical work (run on x86-64 Linux).

T1 weights: C8WEIGHTS1 slots r=-1..6 equal the C7 native .bin weights exactly (long double), Gamma jets likewise.
T2 power: identical tasks/seeds/trees at L5..L7, degrees 1,3,5,6: C8 slots 0..6 (both channels) bitwise equal C7.
T3 qmc: identical Sobol streams at L5..L7: C8 slots 0..6 equal C7 to rounding (one more Taylor slot can only make
   the precision escalation stricter, never weaker).
T4 exact: C8 exact all-tree quadrature at L4, N=20 equals the archived C7 exact record (first seven slots).
T5 replay: --quad-bits 113 versus long double on the same power tasks (contraction rounding), L7 and, if present, L8.
Usage: c8_vs_c7.py --c7 C7_PACKAGE --c8 C8_PACKAGE --inputs C8_INPUTS --out DIR [--threads N]
"""
from __future__ import annotations
import argparse, json, subprocess, sys, os
from decimal import Decimal as D
from pathlib import Path
import numpy as np
NW=8

def run(cmd):
    cmd=[str(x) for x in cmd];r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode:raise RuntimeError(' '.join(map(str,cmd))+'\n'+r.stderr[-2000:])
    return r

def rows(path):
    """Rows keyed by (replicate, graph, begin); numbers parsed directly as Decimal (no binary64 rounding)."""
    d=json.loads(Path(path).read_text(),parse_float=D,parse_int=D)
    return {(int(r['replicate']),int(r['graph']),int(r['begin'])):list(r['value']) for r in d['rows']}

def inventory(inputs,L):
    out=[]
    with open(Path(inputs)/f'L{L}_coord.txt') as f:
        _,ng=map(int,f.readline().split())
        for gi in range(ng):
            a=f.readline().split();out.append(dict(id=gi,power=int(a[3]),primitive=int(a[4]),terms=int(a[5])))
            for _ in range(int(a[5])):f.readline()
    return out

def zeros(inputs,L):
    p=Path(inputs)/f'exact_zero_L{L}.txt'
    if not p.exists():return set()
    z=list(map(int,p.read_text().split()));return set(z[1:])

def tasks(path,magic,ng,work):
    Path(path).write_text(f'{magic} {ng} {len(work)}\n'+''.join(' '.join(map(str,w))+'\n' for w in work))

def t1(c7in,c8in,report):
    bad=[]
    for L in (5,6,7):
        nn_list=[1,3,5,6]
        for N in nn_list:
            nn=N+1;Dx=L-1;B=2*L+1
            old=np.fromfile(c7in/f'cw_L{L}_N{N}.bin',dtype=np.longdouble).reshape(Dx,B,8,nn)
            txt=(c8in/f'cw_L{L}_N{N}.txt').read_text().split();assert txt[0]=='C8WEIGHTS1' and int(txt[1])==Dx*B*(NW+1)*nn
            new=np.array([np.longdouble(x) for x in txt[2:]],dtype=np.longdouble).reshape(Dx,B,NW+1,nn)
            same=np.array_equal(old,new[:,:,:8,:])
            if not same:bad.append(f'L{L} N{N}: max |diff| {float(np.max(np.abs(old-new[:,:,:8,:])))}')
        g7=[np.longdouble(x) for x in (c7in/f'cgamma_L{L}.txt').read_text().split()];g8=[np.longdouble(x) for x in (c8in/f'cgamma_L{L}.txt').read_text().split()]
        if len(g8)!=NW or g7!=g8[:7]:bad.append(f'cgamma L{L}')
    report['T1_weights']={'passed':not bad,'failures':bad}

def power_work(inputs,L,graphs,reps,n):
    w=[];uid=0
    for r in range(reps):
        for g in graphs:w.append((uid,r,g,0,n,n));uid+=1
    return w

def t2(a,report):
    res={}
    for L,N_list,n in [(5,[1,3,5,6],3),(6,[1,3,5,6],2),(7,[1,3,5,6],1)]:
        inv=inventory(a.inputs,L);z=zeros(a.inputs,L);ids=[r['id'] for r in inv if r['power'] and r['terms'] and r['id'] not in z]
        pick=ids[:: max(1,len(ids)//6)][:6];ng=len(inv);work=power_work(a.inputs,L,pick,2,n)
        for N in N_list:
            d=a.out/f'T2_L{L}_N{N}';d.mkdir(parents=True,exist_ok=True)
            tasks(d/'t7.txt','C7TASKS1',ng,work);tasks(d/'t8.txt','C8TASKS1',ng,work)
            for f in ('o7.json','o8.json'):(d/f).unlink(missing_ok=True)
            run([a.c7/'bin/c7_integrate','--mode','power','--inputs',a.c7/'reference/inputs','--L',L,'--tasks',d/'t7.txt','--seed',4242,'--rate','.8','--output',d/'o7.json','--degree',N,'--threads',a.threads])
            run([a.c8/'bin/c8_integrate','--mode','power','--inputs',a.inputs,'--L',L,'--tasks',d/'t8.txt','--seed',4242,'--rate','.8','--output',d/'o8.json','--degree',N,'--threads',a.threads])
            r7,r8=rows(d/'o7.json'),rows(d/'o8.json');mism=0;maxrel=D(0)
            if set(r7)!=set(r8):raise ValueError(f'T2 L{L} N{N}: row sets differ')
            for k in r7:
                a7,a8=r7[k],r8[k]
                for i in range(7):
                    for x,y in ((a7[i],a8[i]),(a7[7+i],a8[NW+i])):
                        if x!=y:mism+=1;maxrel=max(maxrel,abs(x-y)/max(abs(x),D('1e-300')))
            res[f'L{L}_N{N}']={'rows':len(r7),'graphs':pick,'mismatched_values':mism,'max_relative':str(maxrel)}
    report['T2_power_bitwise']={'passed':all(v['mismatched_values']==0 for v in res.values()),'cases':res}

def t3(a,report):
    sys.path.insert(0,str(a.c8/'tools'));from campaign import net_file
    res={}
    for L,n in [(5,64),(6,32),(7,16)]:
        inv=inventory(a.inputs,L);z=zeros(a.inputs,L);ids=[r['id'] for r in inv if not r['power'] and r['terms'] and r['id'] not in z]
        pick=ids[:: max(1,len(ids)//8)][:8];ng=len(inv);work=power_work(a.inputs,L,pick,2,n)
        d=a.out/f'T3_L{L}';d.mkdir(parents=True,exist_ok=True)
        net=d/'sobol.net'
        if not net.exists():net_file(net,2,2*L-1,9183517+L)
        tasks(d/'t7.txt','C7TASKS1',ng,work);tasks(d/'t8.txt','C8TASKS1',ng,work)
        for f in ('o7.json','o8.json'):(d/f).unlink(missing_ok=True)
        run([a.c7/'bin/c7_integrate','--mode','qmc','--inputs',a.c7/'reference/inputs','--L',L,'--tasks',d/'t7.txt','--seed',777,'--rate','.8','--output',d/'o7.json','--net',net,'--threads',a.threads])
        run([a.c8/'bin/c8_integrate','--mode','qmc','--inputs',a.inputs,'--L',L,'--tasks',d/'t8.txt','--seed',777,'--rate','.8','--output',d/'o8.json','--net',net,'--threads',a.threads])
        r7,r8=rows(d/'o7.json'),rows(d/'o8.json');maxrel=D(0);exact=0;tot=0
        if set(r7)!=set(r8):raise ValueError(f'T3 L{L}: row sets differ')
        for k in r7:
            a7,a8=r7[k],r8[k]
            for i in range(7):
                for x,y in ((a7[i],a8[i]),(a7[7+i],a8[NW+i])):
                    if x==0 and y==0:continue
                    tot+=1;exact+=x==y;maxrel=max(maxrel,abs(x-y)/max(abs(x),abs(y)))
        res[f'L{L}']={'graphs':pick,'values':tot,'bitwise_equal':exact,'max_relative':str(maxrel)}
    report['T3_qmc']={'passed':all(D(v['max_relative'])<D('1e-12') for v in res.values()),'tolerance':'1e-12 relative','cases':res}

def t4(a,report):
    L,N=4,20;inv=inventory(a.inputs,L);z=zeros(a.inputs,L);ng=len(inv)
    import math
    T=math.factorial(L+1)//2*math.comb(2*L,L)//(L+1)
    work=[];uid=0
    for r in inv:
        if r['terms'] and r['id'] not in z:work.append((uid,0,r['id'],0,T,T));uid+=1
    d=a.out/'T4';d.mkdir(parents=True,exist_ok=True);tasks(d/'t8.txt','C8TASKS1',ng,work);(d/'o8.json').unlink(missing_ok=True)
    run([a.c8/'bin/c8_integrate','--mode','exact','--inputs',a.inputs,'--L',L,'--tasks',d/'t8.txt','--seed',1,'--rate','.8','--output',d/'o8.json','--degree',N,'--threads',a.threads])
    tot=[D(0)]*(2*NW)
    for v in rows(d/'o8.json').values():tot=[x+y for x,y in zip(tot,v)]
    ref=list(json.loads((a.c7/'reference/records/trefexact_L4_N20.json').read_text(),parse_float=D,parse_int=D)['batches'][0])
    rel=[];G=max(abs(x) for x in ref) # pole slots are cancellation residues of exactly vanishing quantities: compare to the row scale
    for i in range(7):
        for x,y in ((ref[i],tot[i]),(ref[7+i],tot[NW+i])):rel.append(abs(x-y)/G)
    report['T4_exact_L4_N20']={'passed':max(rel)<D('1e-12'),'max_relative_to_row_scale':str(max(rel)),'c8_top_slots':[str(tot[NW-1]),str(tot[2*NW-1])],'tolerance':'1e-12 of the row scale'}

def t5(a,report):
    res={}
    for L,N in [(7,6),(8,6)]:
        if not (Path(a.inputs)/f'L{L}_coord.txt').exists():continue
        inv=inventory(a.inputs,L);z=zeros(a.inputs,L);ids=[r['id'] for r in inv if r['power'] and r['terms'] and r['id'] not in z]
        pick=ids[:: max(1,len(ids)//4)][:4];ng=len(inv);work=power_work(a.inputs,L,pick,1,1)
        d=a.out/f'T5_L{L}';d.mkdir(parents=True,exist_ok=True);tasks(d/'t8.txt','C8TASKS1',ng,work)
        for f in ('ld.json','q.json'):(d/f).unlink(missing_ok=True)
        for bits,f in (('64','ld.json'),('113','q.json')):
            run([a.c8/'bin/c8_integrate','--mode','power','--inputs',a.inputs,'--L',L,'--tasks',d/'t8.txt','--seed',99,'--rate','.8','--output',d/f,'--degree',N,'--threads',a.threads,'--quad-bits',bits])
        rl,rq=rows(d/'ld.json'),rows(d/'q.json');worst=D(0);scale_rel=D(0)
        if set(rl)!=set(rq):raise ValueError(f'T5 L{L}: row sets differ')
        for k in rq:
            G=max(abs(x) for x in rq[k])
            for x,y in zip(rl[k],rq[k]):
                scale_rel=max(scale_rel,abs(x-y)/G if G else D(0))
                if y!=0:worst=max(worst,abs(x-y)/abs(y))
        res[f'L{L}_N{N}']={'graphs':pick,'max_relative_per_slot':str(worst),'max_relative_to_row_scale':str(scale_rel)}
    report['T5_binary128_replay']={'passed':all(D(v['max_relative_to_row_scale'])<D('1e-14') for v in res.values()),'tolerance':'1e-14 of the row scale','cases':res,'note':'long double minus binary128 contraction on identical weights and trees'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--c7',type=Path,required=True);p.add_argument('--c8',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--threads',type=int,default=8);p.add_argument('--only',nargs='*');a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True);report={}
    steps={'T1':lambda:t1(a.c7/'reference/inputs',a.inputs,report),'T2':lambda:t2(a,report),'T3':lambda:t3(a,report),'T4':lambda:t4(a,report),'T5':lambda:t5(a,report)}
    for k,f in steps.items():
        if a.only and k not in a.only:continue
        try:f()
        except Exception as e:report[k+'_error']=repr(e)[-3000:]
        (a.out/'report.json').write_text(json.dumps(report,indent=2))
        print(k,'done',flush=True)
    summary={k:(v.get('passed') if isinstance(v,dict) else v) for k,v in report.items()};print(json.dumps(summary,indent=1))
    failed=[k for k,v in summary.items() if v is not True]
    if failed:print('FAILED:',failed,file=sys.stderr);sys.exit(1)
if __name__=='__main__':main()
