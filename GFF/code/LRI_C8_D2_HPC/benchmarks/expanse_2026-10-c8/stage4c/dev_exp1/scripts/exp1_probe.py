#!/usr/bin/env python3
"""R4c `exp1` development probe (Stage 4c; PLAN A-FLAG-5), run from the root of a built export on a cluster node.

exp1 changes only calls of the binary128 and MP tiers whose point is shifted (shift != 0, i.e. some lx_j < -600 or
> 0). F1's A-RPL-5 point set and F2's streams contain (almost) none, so the F-gates alone neither exercise exp1 nor
size its gain. This driver compiles exp1_probe.cpp with the exact compile command of bin/c8d2_gmp and of the exp1
executable (as numerics_flags.py compiles tests/numerics_f1.cpp) and runs, per sector:
  census    sample() on every point, exp1 build: per tier (level) the points and the shifted points, at rates .8 and
            .9, on the L8 sweep sample (tests/validate.py l8self_sample: 1,600 free / 400 power graphs) and on 400 L7
            graphs per sector (100 heaviest + 300 random); --census-points per graph.
  lxcensus  the log-coordinates only, --lxcensus-points per graph on the same graphs: the shifted fraction and the
            min_j lx_j histogram with far more points (sample()'s statements, checked bit for bit against sample()).
  forced    forced shifted points (each sampled point with a tail of its sampling order lowered by D = 700, 2000,
            4500, 9000, 15000) on --forced-graphs graphs per (sector, L in 7, 8) x --forced-points points: the exact
            build writes the exact path's values and independent 450-digit references, the exp1 build compares. Gate:
            exp1 adds no violation of the A-RPL-5 tier bounds and, within the precision policy's range (|f450| >=
            1e-274 (1 + err)), none of F1's bound (relative error <= 1e-6 of the accepted value) that the exact path
            does not have, evaluate() throws exactly where the exact path throws, and every
            exp1 shifted coordinate is within (|shift/L| + 8) ulps (binary128) or (|shift/L| + 1000) eps (MP) of
            exp(lx_j - shift/L).
  timing    per-call time of calculate_shared<Q> and calculate_shared<MP,false> on natural and forced shifted points
            (D = 700, 2000), --timing-rounds interleaved runs of each build; medians; the saving per shifted call.
  bound     every graph of L in --bound-loops (default 3..8, all of them): the largest |min_j lx_j| a point can reach
            with the native nets (bits <= 60, u >= 2^-61), i.e. whether a shifted point is possible at all, at the
            campaign rates and nets (a: .8 and 52 bits, b: .9 and 60 bits) and at the worst case .8 with 60 bits; the
            rate below which it becomes possible (R7 maps may lower rates); and a tail bound on its probability.
Writes OUTPUT/<part>.json per part and OUTPUT/exp1_probe.json (OUTPUT must not exist). Exit 0 when the forced-point
gate passes, 1 otherwise.
--compile-only compiles the two probes and exits (a pre-check of the working tree: submit_exp1.sh probecheck).
  exp1_probe.py --output DIR [--profile exp1] [--threads N] [--parts census,lxcensus,forced,timing] [sizes]"""
from __future__ import annotations
import argparse,json,math,os,statistics,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path.cwd()
if not (ROOT/'src/kernel.hpp').is_file()or not (ROOT/'tools/common.py').is_file():raise SystemExit('run from the root of a built export')
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
from common import digest,dump,environment_record,load
V=None   # tests/validate.py, imported by main() unless --compile-only (a pre-check tree has no tests/validate.py)
HERE=Path(__file__).resolve().parent;SRC=HERE/'exp1_probe.cpp';SECTORS=('free','power')
SEED=4402177

def log(m):print(f'[{time.strftime("%H:%M:%S")}] {m}',flush=True)

def compile_probe(exe:Path,out:Path)->dict:
    br=load(exe.with_name(exe.name+'.build.json'))
    if br.get('executable_sha256')!=digest(exe):raise SystemExit(f'{exe}: build record of another executable')
    cmd=list(br['command']);src=[i for i,w in enumerate(cmd)if w.endswith('src/c8d2_integrate.cpp')]
    if len(src)!=1 or '-o'not in cmd:raise SystemExit(f'{exe}: unexpected build command')
    cmd[src[0]]=str(SRC);cmd[cmd.index('-o')+1]=str(out);t0=time.time()
    cp=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    if cp.returncode:raise SystemExit(f'compiling the probe from {exe.name} failed:\n{cp.stderr[-4000:]}')
    log(f'compiled {out.name} from {exe.name}\'s build command in {time.time()-t0:.0f} s')
    return {'executable':str(exe),'executable_sha256':digest(exe),'command':cmd}

def run(tool:Path,*args)->dict:
    cp=subprocess.run([str(tool),*map(str,args)],capture_output=True,text=True)
    if cp.returncode:raise RuntimeError(f'{tool.name} {" ".join(map(str,args[:2]))} exited {cp.returncode}: {cp.stderr[-3000:]}')
    return json.loads(cp.stdout)

class Stage:
    """Graph lists and nets (one Sobol matrix, 60 bits) per (sector, L, graph set), staged once."""
    def __init__(self,td:Path):self.td=td;self.done={}
    def get(self,sector:str,L:int,ids:list,name:str,points:int)->tuple[Path,Path]:
        key=(sector,L,name)
        if key in self.done:return self.done[key]
        root=V.stage(self.td/'graphs'/sector,sector,L,ids);lst=self.td/f'{name}_{sector}_L{L}.list'
        lst.write_text(''.join(f'{root}/L{L}/G{g}.txt\n'for g in ids));net=self.td/f'{name}_{sector}_L{L}.bin'
        V.make_net(net,1,4*L-1,60,SEED+L+(9 if sector=='power'else 0)+(100 if name=='timing'else 0),points)
        self.done[key]=(lst,net);return lst,net

def census_graphs(sector:str,L:int)->list:
    return V.l8self_sample()[sector]if L==8 else V.heavy_and_random(sector,7,100,300,8813+(1 if sector=='power'else 0))

def frac(a,b):return a/b if b else None

def main()->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--profile',default='exp1')
    p.add_argument('--exact',type=Path,default=ROOT/'bin/c8d2_gmp');p.add_argument('--threads',type=int,default=len(os.sched_getaffinity(0)))
    p.add_argument('--parts',default='bound,census,lxcensus,forced,timing');p.add_argument('--scratch',type=Path)
    p.add_argument('--bound-loops',default='3,4,5,6,7,8');p.add_argument('--bound-graphs',type=int,help='development: the first N graphs per (sector, L)')
    p.add_argument('--census-points',type=int,default=1024);p.add_argument('--lxcensus-points',type=int,default=1<<18)
    p.add_argument('--census-loops',default='7,8');p.add_argument('--census-graphs',type=int,help='development: the first N graphs per (sector, L)')
    p.add_argument('--forced-graphs',type=int,default=64);p.add_argument('--forced-points',type=int,default=8)
    p.add_argument('--timing-graphs',type=int,default=64);p.add_argument('--timing-points',type=int,default=4);p.add_argument('--timing-reps',type=int,default=3)
    p.add_argument('--timing-rounds',type=int,default=2);p.add_argument('--timing-loops',default='7,8')
    p.add_argument('--compile-only',action='store_true')
    a=p.parse_args()
    global V
    if not a.compile_only:import validate as V
    if a.output.exists():raise SystemExit(f'{a.output} exists')
    parts=[x.strip()for x in a.parts.split(',')if x.strip()]
    prof=(ROOT/'bin'/f'c8d2_gmp_{a.profile}').resolve();exact=a.exact.resolve()
    if 'exp1'not in a.profile.split('+'):raise SystemExit('--profile must contain exp1')
    a.output.mkdir(parents=True);t0=time.time()
    rec={'schema':'c8-d2-exp1-probe-1','utc_start':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'probe_source_sha256':digest(SRC),'parts':parts,
         'args':{k:(str(v)if isinstance(v,Path)else v)for k,v in vars(a).items()},'threads':a.threads}
    ok=True
    with tempfile.TemporaryDirectory(prefix='c8d2_exp1probe_',dir=a.scratch)as td:
        td=Path(td);st=Stage(td)
        tools={'exact':td/'probe_exact','exp1':td/'probe_exp1'}
        rec['tools']={'exact':compile_probe(exact,tools['exact']),'exp1':compile_probe(prof,tools['exp1'])}
        if a.compile_only:parts=[];rec['parts']=['compile only']
        if 'bound'in parts:
            LN=math.log(2);res={};summ={}
            for sector in SECTORS:
                for L in map(int,a.bound_loops.split(',')):
                    ids=sorted(r['id']for r in V.inventory()[sector][str(L)])
                    if a.bound_graphs:ids=ids[:a.bound_graphs]
                    s=time.time();root=V.stage(td/'graphs'/sector,sector,L,ids);lst=td/f'bound_{sector}_L{L}.list';lst.write_text(''.join(f'{root}/L{L}/G{g}.txt\n'for g in ids))
                    w=time.time()-s;s=time.time();r=run(tools['exact'],'bound',lst,a.threads);rows=r['graphs']
                    if [x[0]for x in rows]!=ids or any(x[1]!=L for x in rows):raise RuntimeError(f'bound {sector} L{L}: graphs out of order')
                    c0=max(rows,key=lambda x:x[2]);am=min(rows,key=lambda x:x[3]);pb=max(rows,key=lambda x:x[4])
                    det=lambda rate,bits:(bits+1)*LN/rate*c0[2]
                    d={'graphs':len(rows),'max_C0':c0[2],'max_C0_graph':c0[0],'min_amin':am[3],'min_amin_graph':am[0],
                       'max_abs_min_lx':{'a_rate.8_bits52':det(.8,52),'b_rate.9_bits60':det(.9,60),'worst_rate.8_bits60':det(.8,60)},
                       'graphs_that_can_shift':{'a_rate.8_bits52':sum(1 for x in rows if 53*LN/.8*x[2]>600),'b_rate.9_bits60':sum(1 for x in rows if 61*LN/.9*x[2]>600),
                                                'worst_rate.8_bits60':sum(1 for x in rows if 61*LN/.8*x[2]>600)},
                       'critical_rate_bits60':61*LN*c0[2]/600,'max_log10_P_shift_bound_rate.8':pb[4],'max_log10_P_shift_bound_graph':pb[0],
                       'stage_seconds':round(w,1),'seconds':round(time.time()-s,1)}
                    summ[f'{sector}:L{L}']=d;res[f'{sector}:L{L}']=rows
                    log(f'bound {sector} L{L}: {len(rows)} graphs, max C0 {c0[2]:.4g} (G{c0[0]}): |min lx| <= {det(.8,52):.1f} (a), {det(.9,60):.1f} (b), {det(.8,60):.1f} (.8/60 bits); '
                        f'graphs that can shift {d["graphs_that_can_shift"]}; critical rate {d["critical_rate_bits60"]:.4f}; log10 P <= {pb[4]:.1f} ({w:.0f} s staging)')
            tot={'graphs':sum(d['graphs']for d in summ.values()),'graphs_that_can_shift':{k:sum(d['graphs_that_can_shift'][k]for d in summ.values())for k in ('a_rate.8_bits52','b_rate.9_bits60','worst_rate.8_bits60')},
                 'max_abs_min_lx':{k:max(d['max_abs_min_lx'][k]for d in summ.values())for k in ('a_rate.8_bits52','b_rate.9_bits60','worst_rate.8_bits60')},
                 'critical_rate_bits60':max(d['critical_rate_bits60']for d in summ.values()),'max_log10_P_shift_bound_rate.8':max(d['max_log10_P_shift_bound_rate.8']for d in summ.values())}
            rec['bound']={'summary':summ,'total':tot,'complete':not a.bound_graphs,'rule':'-min_j lx_j <= (bits+1) ln2 / rate * C0, C0 = max over sampling chains of sum 1/alpha0[S]; shifted iff some lx_j < -600',
                          'columns':['id','L','C0','amin','log10_P_shift_bound_rate_0.8']}
            dump(a.output/'bound.json',{**rec['bound'],'graphs':res})
        if 'census'in parts or 'lxcensus'in parts:
            res={}
            for mode,npts in (('census',a.census_points),('lxcensus',a.lxcensus_points)):
                if mode not in parts:continue
                for sector in SECTORS:
                    for L in map(int,a.census_loops.split(',')):
                        ids=census_graphs(sector,L)
                        if a.census_graphs:ids=ids[:a.census_graphs]
                        lst,net=st.get(sector,L,ids,'census',max(npts,a.census_points,a.lxcensus_points))
                        for rate in ('.8','.9'):
                            s=time.time();r=run(tools['exp1'],mode,L,lst,net,0,npts,SEED,rate,a.threads);r['wall_seconds']=round(time.time()-s,1)
                            res[f'{mode}:{sector}:L{L}:rate{rate}']=r
                            log(f'{mode} {sector} L{L} rate {rate}: {r["points"]} points, {r["shifted_points"]} shifted, min lx {r["min_lx"]} ({r["wall_seconds"]} s)')
            # shifted fractions: of all points, and (census) of the binary128 and MP calls (level >= 1 is one binary128
            # call, level 2 one MP call)
            summ={}
            for k,r in res.items():
                d={'points':r['points'],'shifted_points':r['shifted_points'],'shifted_fraction':frac(r['shifted_points'],r['points']),
                   'upper_95_if_zero':(3.0/r['points']if r['shifted_points']==0 else None),'min_lx':r['min_lx']}
                if r['mode']=='census':
                    lv,sh=r['level'],r['shifted_by_level'];q=lv[1]+lv[2];qs=sh[1]+sh[2]
                    d.update(binary128_calls=q,binary128_calls_shifted=qs,binary128_shifted_fraction=frac(qs,q),mp_calls=lv[2],mp_calls_shifted=sh[2],mp_shifted_fraction=frac(sh[2],lv[2]),
                             exp1_factored={k2:v['factored']for k2,v in r['exp1_counters'].items()if isinstance(v,dict)})
                summ[k]=d
            tot={}
            for mode in ('census','lxcensus'):
                rows=[v for k,v in summ.items()if k.startswith(mode+':')]
                if not rows:continue
                n=sum(x['points']for x in rows);s=sum(x['shifted_points']for x in rows);t={'points':n,'shifted_points':s,'shifted_fraction':frac(s,n),'upper_95_if_zero':3.0/n if s==0 else None}
                if mode=='census':
                    q=sum(x['binary128_calls']for x in rows);qs=sum(x['binary128_calls_shifted']for x in rows);m=sum(x['mp_calls']for x in rows);ms=sum(x['mp_calls_shifted']for x in rows)
                    t.update(binary128_calls=q,binary128_calls_shifted=qs,binary128_shifted_fraction=frac(qs,q),mp_calls=m,mp_calls_shifted=ms,mp_shifted_fraction=frac(ms,m))
                tot[mode]=t
            rec['census']={'runs':res,'summary':summ,'total':tot};dump(a.output/'census.json',rec['census'])
        if 'forced'in parts:
            res={};gate={'status_mismatch':0,'f1_new_in_range':0,'q_bound_new':0,'m_bound_new':0,'xs_q_violations':0,'xs_mp_violations':0,'points':0,'f1_new_beyond_range':0,'f1_fixed_by_exp1':0,'beyond_range_points':0}
            for sector in SECTORS:
                for L in (7,8):
                    ids=V.heavy_and_random(sector,L,a.forced_graphs//2,a.forced_graphs-a.forced_graphs//2,6601+L+(9 if sector=='power'else 0))
                    lst,net=st.get(sector,L,ids,'forced',a.forced_points);ref=td/f'forced_{sector}_L{L}.ref';s=time.time()
                    run(tools['exact'],'forced',L,lst,net,0,a.forced_points,SEED,a.threads,ref,'write');w=time.time()-s;s=time.time()
                    r=run(tools['exp1'],'forced',L,lst,net,0,a.forced_points,SEED,a.threads,ref,'read');r['wall_seconds']={'write':round(w,1),'read':round(time.time()-s,1)}
                    r['ref_sha256']=digest(ref);ref.unlink();res[f'{sector}:L{L}']=r;T=r['total']
                    gate['points']+=T['points'];gate['status_mismatch']+=T['evaluate_threw']['mismatch'];gate['f1_new_in_range']+=T['f1']['new_violations_in_range'];gate['f1_new_beyond_range']+=T['f1']['new_violations']-T['f1']['new_violations_in_range']
                    gate['f1_fixed_by_exp1']+=T['f1']['fixed_by_exp1'];gate['beyond_range_points']+=T['beyond_policy_range']
                    gate['q_bound_new']+=T['binary128_forced']['new_violations'];gate['m_bound_new']+=T['mp_forced']['new_violations']
                    gate['xs_q_violations']+=T['xs']['binary128_violations'];gate['xs_mp_violations']+=T['xs']['mp_violations']
                    log(f'forced {sector} L{L}: {T["points"]} points ({T["shifted"]} shifted), F1 max rel exact {T["f1"]["max_rel_exact"]} exp1 {T["f1"]["max_rel_exp1"]}, '
                        f'new violations F1 {T["f1"]["new_violations_in_range"]} in range + {T["f1"]["new_violations"]-T["f1"]["new_violations_in_range"]} beyond (fixed by exp1 {T["f1"]["fixed_by_exp1"]}) q {T["binary128_forced"]["new_violations"]} mp {T["mp_forced"]["new_violations"]}, '
                        f'xs ulps exp1 {T["xs"]["binary128_max_ulps_exp1"]} exact {T["xs"]["binary128_max_ulps_exact"]}, mp eps exp1 {T["xs"]["mp_max_eps_exp1"]} exact {T["xs"]["mp_max_eps_exact"]}')
                    for k,R in r['regimes'].items():
                        I=R['in_range']
                        log(f'  {k}: max|shift/L| {R["max_abs_shift_over_L"]}, beyond the policy range {R["beyond_policy_range"]} (in range: F1 viol {I["f1_violations_exact"]}/{I["f1_violations_exp1"]}, '
                            f'y identical {I["y_identical"]}, max paired {I["max_paired_rel"]}, max rel exp1 {I["max_rel_exp1"]}), threw {R["evaluate_threw"]["exact"]}/{R["evaluate_threw"]["exp1"]}, levels {R["level_transitions"]}, '
                            f'F1 viol {R["f1"]["violations_exact"]}/{R["f1"]["violations_exp1"]} (y identical {R["f1"]["identical"]}, max paired {R["f1"]["max_paired_rel"]}), '
                            f'q bound viol {R["binary128_forced"]["bound_violations_exact"]}/{R["binary128_forced"]["bound_violations_exp1"]} identical {R["binary128_forced"]["identical"]}, '
                            f'mp max {R["mp_forced"]["max_scaled_exact"]}/{R["mp_forced"]["max_scaled_exp1"]}, xs q edges {R["xs"]["binary128_edges_exp1"]}+{R["xs"]["binary128_edges_exact_expression"]} max ulps {R["xs"]["binary128_max_ulps_exp1"]}/{R["xs"]["binary128_max_ulps_exact"]}')
            gate['passed']=all(gate[k]==0 for k in ('status_mismatch','f1_new_in_range','q_bound_new','m_bound_new','xs_q_violations','xs_mp_violations'))and gate['points']>0;ok&=gate['passed']
            rec['forced']={'runs':res,'gate':gate,'regimes':[700,2000,4500,9000,15000],
                           'rule':'exp1 adds no A-RPL-5 tier-bound violation the exact path lacks (binary128 |q-ref| <= 1e-29 err, MP |m-ref|/(1+err) <= 1e-280, every forced point) and no F1 (1e-6) violation within the precision policy\'s range |ref| >= 1e-274 (1+err) (beyond it the policy guarantees no relative accuracy on either path; counted, not gated); evaluate() throws where the exact path throws; exp1 xs within (|a|+8) ulps (binary128) / (|a|+1000) eps (MP)'}
            dump(a.output/'forced.json',rec['forced'])
        if 'timing'in parts:
            res={}
            for sector in SECTORS:
                for L in map(int,a.timing_loops.split(',')):
                    ids=V.heavy_and_random(sector,L,a.timing_graphs//2,a.timing_graphs-a.timing_graphs//2,7307+L+(9 if sector=='power'else 0))
                    lst,net=st.get(sector,L,ids,'timing',a.timing_points);runs=[]
                    for k in range(a.timing_rounds):
                        for b in (('exact','exp1')if k%2==0 else('exp1','exact')):
                            r=run(tools[b],'timing',L,lst,net,0,a.timing_points,SEED,a.threads,a.timing_reps);r['build']=b;runs.append(r)
                    med={b:{v:{t:statistics.median(x['variants'][v][t]for x in runs if x['build']==b)/runs[0]['variants'][v]['calls']/1e3 for t in ('binary128_ns','mp_ns')}
                            for v in runs[0]['variants']}for b in ('exact','exp1')}
                    sav={v:{t:1-med['exp1'][v][t]/med['exact'][v][t]for t in ('binary128_ns','mp_ns')}for v in runs[0]['variants']}
                    res[f'{sector}:L{L}']={'runs':runs,'us_per_call_median':med,'saving_exp1':sav,'shifted':{v:runs[0]['variants'][v]['shifted']for v in runs[0]['variants']},
                                           'calls':{v:runs[0]['variants'][v]['calls']for v in runs[0]['variants']}}
                    log(f'timing {sector} L{L}: '+'; '.join(f'{v} q {med["exact"][v]["binary128_ns"]:.1f}->{med["exp1"][v]["binary128_ns"]:.1f} us, mp {med["exact"][v]["mp_ns"]:.0f}->{med["exp1"][v]["mp_ns"]:.0f} us'for v in med['exact']))
            rec['timing']={'runs':res,'metric':'per variant: median over rounds of the summed per-point minimum over reps of one call, divided by the calls, in microseconds; saving = 1 - exp1/exact'}
            dump(a.output/'timing.json',rec['timing'])
    rec['passed']=ok;rec['wall_seconds']=round(time.time()-t0,1);rec['environment']=environment_record();dump(a.output/'exp1_probe.json',rec)
    print(json.dumps({'passed':ok,'forced_gate':rec.get('forced',{}).get('gate'),'census_total':rec.get('census',{}).get('total')},indent=1))
    return 0 if ok else 1

if __name__=='__main__':sys.exit(main())
