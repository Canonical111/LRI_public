#!/usr/bin/env python3
"""R3b `dd` development helper (Stage 4c; PLAN A-FLAG-4), run from the root of a built export on Expanse (never the
Mac). Development evidence only; the gate runs are tests/numerics_flags.py's.

  dd_dev.py variants NAME=DEFINES...   build development variants of bin/c8d2_gmp_dd: bin/c8d2_gmp_<NAME> is compiled
                                       with bin/c8d2_gmp_dd's own build-record command plus -DC8_DD_DEVELOPMENT and
                                       the given comma-separated -D definitions (e.g. dd_direct=C8_DD_ROUTING=0), and
                                       gets its build record (tools/build_record.py), so that numerics_flags.py
                                       --profile dd --profile-exe bin/c8d2_gmp_<NAME> accepts it and compiles its F1
                                       tool with the same definitions. An existing variant with a current record is
                                       kept.
  dd_dev.py accuracy OUT N THREADS     compile tests/dd_accuracy.cpp with bin/c8d2_gmp_dd's compiler and options (the
                                       profile's -mavx2 -mfma and the required flags; no -D of the profile, which the
                                       test defines itself) and run it: OUT/dd_accuracy.json; exit 1 when a bound fails
  dd_dev.py summary OUT DIR...         collect from numerics_flags.py records (DIR/numerics_flags.json and DIR/f1/f1.json)
                                       the F1 verdicts, tiers, transitions, the dd routes and checks, the dd-ratio decade
                                       table against binary128's verdict (the C8_DD_CASCADE_LOW data), and F4's medians
                                       and speedups: OUT (JSON)
"""
from __future__ import annotations
import json,os,re,subprocess,sys,time
from pathlib import Path
ROOT=Path.cwd()

def rec_of(exe:Path)->dict:return json.loads(exe.with_name(exe.name+'.build.json').read_text())

def sha(p:Path)->str:
    import hashlib;return hashlib.sha256(p.read_bytes()).hexdigest()

def variants(specs:list[str])->int:
    base=ROOT/'bin/c8d2_gmp_dd';rec=rec_of(base);cmd0=list(rec['command'])
    if rec.get('NUMERICS')!='dd'or '-DC8_NUMERICS_DD'not in cmd0:raise SystemExit(f'{base}: not a dd profile build')
    out={}
    for spec in specs:
        name,_,defs=spec.partition('=')
        if not re.fullmatch(r'dd_[a-z0-9_]+',name)or not defs:raise SystemExit(f'variant {spec!r}: NAME=DEF[,DEF...] with NAME dd_*')
        exe=ROOT/'bin'/f'c8d2_gmp_{name}';extra=['-DC8_DD_DEVELOPMENT',*[f'-D{d}'for d in defs.split(',')]]
        cmd=list(cmd0);i=cmd.index('-DC8_NUMERICS_DD');cmd[i+1:i+1]=extra;cmd[cmd.index('-o')+1]=str(exe.relative_to(ROOT))
        br=exe.with_name(exe.name+'.build.json')
        if exe.exists()and br.exists()and json.loads(br.read_text()).get('command')==cmd and json.loads(br.read_text()).get('executable_sha256')==sha(exe):
            print(f'{exe.name}: kept');out[name]={'command':cmd,'sha256':sha(exe),'kept':True};continue
        t0=time.time();subprocess.run(cmd,cwd=ROOT,check=True)
        env=dict(os.environ,C8B_CXX=rec.get('CXX')or cmd[0],C8B_CPPFLAGS=rec.get('CPPFLAGS')or'',C8B_OPTFLAGS=rec.get('OPTFLAGS')or'',C8B_CXXFLAGS=rec.get('CXXFLAGS')or'',
                 C8B_REQUIRED=rec.get('required_flags')or'',C8B_LDFLAGS=rec.get('LDFLAGS')or'',C8B_LDLIBS=rec.get('LDLIBS')or'',C8B_NUMERICS='dd',C8B_GMP_PREFIX=rec.get('GMP_PREFIX')or'')
        subprocess.run([sys.executable,'-B','tools/build_record.py',str(exe.relative_to(ROOT)),'gmp','--',*cmd],cwd=ROOT,env=env,check=True)
        d=json.loads(subprocess.run([str(exe),'--describe'],capture_output=True,text=True,check=True).stdout)
        out[name]={'command':cmd,'sha256':sha(exe),'seconds':round(time.time()-t0,1),'numerics_params':d.get('numerics_params')}
        print(f'{exe.name}: built in {time.time()-t0:.0f} s, {d.get("numerics_params")}')
    print(json.dumps(out,indent=1));return 0

def accuracy(out:Path,n:int,threads:int)->int:
    rec=rec_of(ROOT/'bin/c8d2_gmp_dd');opts=[w for w in rec['compiler_options']if not w.startswith('-DC8_')]
    exe=Path(os.environ.get('TMPDIR','/tmp'))/'dd_accuracy';cmd=[*opts,str(ROOT/'tests/dd_accuracy.cpp'),'-o',str(exe)]
    t0=time.time();subprocess.run(cmd,cwd=ROOT,check=True);tc=time.time()-t0
    t0=time.time();cp=subprocess.run([str(exe),str(n),'20261005',str(threads)],capture_output=True,text=True)
    if cp.returncode not in(0,1):raise SystemExit(f'dd_accuracy failed ({cp.returncode}): {cp.stderr[-2000:]}')
    r=json.loads(cp.stdout);r.update(compile_command=cmd,compile_seconds=round(tc,1),run_seconds=round(time.time()-t0,1),threads=threads)
    out.mkdir(parents=True,exist_ok=True);(out/'dd_accuracy.json').write_text(json.dumps(r,indent=1)+'\n')
    print(json.dumps({k:{'max_u2':v['max_u2'],'bound':v['bound_u2_max'],'passed':v['passed']}for k,v in r['tests'].items()},indent=1));print('passed',r['passed'])
    return 0 if r['passed']else 1

def decade_table(checks:dict)->dict:
    """dd_ratio_decade_<d>_binary128_<pass|fail> -> {d: {pass, fail}} (d = floor(log10 |val|/err))."""
    t={}
    for k,v in checks.items():
        m=re.fullmatch(r'dd_ratio_decade_(-?\d+)_binary128_(pass|fail)',k)
        if m:t.setdefault(int(m[1]),{'pass':0,'fail':0})[m[2]]+=v
    return {str(d):t[d]for d in sorted(t,reverse=True)}

def summary(out:Path,dirs:list[str])->int:
    res={}
    for d in dirs:
        d=Path(d);r=json.loads((d/'numerics_flags.json').read_text());s={'status':r.get('status'),'verdicts':r.get('verdicts'),'profile':r.get('profile',{}).get('path'),
            'profile_sha256':r.get('profile',{}).get('sha256'),'numerics_params':r.get('profile',{}).get('describe',{}).get('numerics_params'),'development':r.get('development')}
        if (d/'f1/f1.json').exists():
            f1=json.loads((d/'f1/f1.json').read_text());tot=f1['total'];ch=tot.get('profile_checks')or{}
            s['F1']={'verdict':f1['verdict'],'points':tot['points'],'tiers':tot['tiers'],'paired_identical':(tot.get('paired')or{}).get('identical'),
                     'all_points_identical_to_exact':(tot.get('paired')or{}).get('identical')==tot['points'],
                     'transitions':(tot.get('paired')or{}).get('transitions'),'routes':{k[len('dd_route_'):]:v for k,v in ch.items()if k.startswith('dd_route_')},
                     'checks':{k:v for k,v in ch.items()if not k.startswith(('dd_route_','dd_ratio_decade_','dd_vs_binary128_scaled_decade_'))},
                     'ratio_decades_vs_binary128':decade_table(ch),
                     'dd_vs_binary128_scaled_decades':{k.rsplit('_',1)[1]:v for k,v in ch.items()if k.startswith('dd_vs_binary128_scaled_decade_')},
                     'by_sector_L':{sec:{L:{'tiers':{t:x['tiers_profile'][t]['points']for t in x['tiers_profile']},'max_rel_dd':x['tiers_profile']['double_double']['max_relative_error'],
                                            'max_scaled_dd':x['profile']['tiers']['double_double']['max_scaled_error'],
                                            'timers':{k:c for k,c in (x['profile'].get('profile_checks')or{}).items()if k.startswith('dd_timer_')}}for L,x in v.items()}
                                   for sec,v in f1['by_sector_L'].items()},
                     'max_scaled_error':{t:max((x['profile']['tiers'][t]['max_scaled_error']for v in f1['by_sector_L'].values()for x in v.values()),key=float)for t in tot['tiers']}}
        if 'F4'in r:
            f4=r['F4'];s['F4']={k:f4.get(k)for k in('medians','speedup_exact_over_profile','rows_repeatable','rows_identical_between_binaries','shape','sample','repeats')}
            runs=json.loads((d/'f4/f4.json').read_text())['runs'];s['F4']['runs']=[{k:x[k]for k in('binary','repeat','lane_thread_seconds','per_sector','node_wall_seconds','quad','mp')}for x in runs]
        res[d.name]=s
    out.write_text(json.dumps(res,indent=1)+'\n');print(json.dumps({k:{'status':v['status'],'F1':(v.get('F1')or{}).get('verdict'),'routes':(v.get('F1')or{}).get('routes'),
                                                                  'speedup':(v.get('F4')or{}).get('speedup_exact_over_profile')}for k,v in res.items()},indent=1))
    return 0

if __name__=='__main__':
    a=sys.argv[1:]
    if not a:sys.exit(__doc__)
    if a[0]=='variants':sys.exit(variants(a[1:]))
    if a[0]=='accuracy'and len(a)==4:sys.exit(accuracy(Path(a[1]),int(a[2]),int(a[3])))
    if a[0]=='summary'and len(a)>=3:sys.exit(summary(Path(a[1]),a[2:]))
    sys.exit(__doc__)
