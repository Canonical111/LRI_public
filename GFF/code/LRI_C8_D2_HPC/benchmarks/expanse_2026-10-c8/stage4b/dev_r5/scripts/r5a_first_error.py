#!/usr/bin/env python3
"""R5a development check (Stage 4b; not a plan gate): the parallel graph loading of src/c8d2_integrate.cpp reports the
same error as the serial loading of the Stage-3 baseline, whatever the thread count and timing, and loads valid
blocks identically.

  r5a_first_error.py --baseline DIR --output FILE [--repeats 5] [--threads 1 2 4 8 16]

DIR holds the Stage-3 baseline c8d2_decimal and c8d2_gmp (sha256 3dbd51bb..., 5c5328af...). Eight free L4 kernels
(the lightest, staged from the packs and checked against the inventory sha256) form one block of 2 replicates x 64
points; in each case some G-files are made bad: truncated (the parser's "truncated graph"), missing ("invalid graph
header"), or with another id in the header ("graph identity mismatch"), always at more than one id so that the lowest
bad id's error is the one the serial loop throws first. Each case runs the baseline once at 1 thread and the
candidate bin/c8d2_<backend> at every --threads value --repeats times: every candidate run must exit 2 with stderr
byte-identical to the baseline's and write no output. The all-valid case must give rows identical to the baseline's
in every scientific field and the same graphs_loaded. Both backends. The record goes to --output."""
from __future__ import annotations
import argparse,json,shutil,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'tests'))
from common import digest,dump,environment_record,load  # noqa: E402
from validate import BACKENDS,GAMMA8,by_cost,exe,make_net,native_cmd,scientific,stage,task_rows,tasks_text  # noqa: E402

def bad_file(p:Path,kind:str)->None:
    if kind=='truncated':t=p.read_text().split();p.write_text(' '.join(t[:len(t)-7])+'\n')       # cut inside the rate table
    elif kind=='missing':p.unlink()
    elif kind=='identity':t=p.read_text().split(' ',3);t[2]=str(int(t[2])+1000000);p.write_text(' '.join(t))  # header: magic L id ...
    else:raise ValueError(kind)

def run(cmd,out:Path)->tuple[int,str,bool]:
    out.unlink(missing_ok=True);p=subprocess.run(list(map(str,cmd)),capture_output=True,text=True)
    return p.returncode,p.stderr,out.exists()

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--baseline',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--repeats',type=int,default=5);ap.add_argument('--threads',type=int,nargs='+',default=[1,2,4,8,16])
    a=ap.parse_args()
    if a.output.exists():raise SystemExit(f'{a.output} exists')
    L=4;ids=sorted(by_cost('free',L)[-8:]);t0=time.time()
    # (case, {position in ids: kind}); the lowest bad id is never the only bad one
    cases=[('valid',{}),('truncated_then_identity',{2:'truncated',5:'identity'}),('missing_then_truncated',{1:'missing',3:'truncated',6:'identity'}),
           ('identity_then_missing',{0:'identity',7:'missing'}),('last_only',{7:'identity'})]
    rec={'schema':'c8-d2-dev-r5a-first-error-1','graphs':ids,'L':L,'sector':'free','points':64,'replicates':2,'threads':a.threads,'repeats':a.repeats,
         'baseline':{b:digest(a.baseline/f'c8d2_{b}')for b in BACKENDS},'candidate':{b:digest(exe(b))for b in BACKENDS},'cases':[],'environment':environment_record()}
    ok=True
    with tempfile.TemporaryDirectory(prefix='r5a_err_')as td:
        td=Path(td);clean=stage(td/'clean','free',L,ids);net=td/'net.bin';make_net(net,2,4*L-1,60,52611,64)
        tasks=td/'tasks';tasks.write_text(tasks_text(8,L,task_rows(ids,2,64)));out=td/'out.json'
        for name,bad in cases:
            root=td/name;shutil.copytree(clean,root)
            for pos,kind in bad.items():bad_file(root/f'L{L}'/f'G{ids[pos]}.txt',kind)
            for b in BACKENDS:
                base_cmd=native_cmd(a.baseline/f'c8d2_{b}',root,GAMMA8,net,tasks,out,threads=1)
                code0,err0,wrote0=run(base_cmd,out);base_rows=[scientific(r)for r in load(out)['rows']]if wrote0 else None
                base_loaded=load(out)['graphs_loaded']if wrote0 else None
                c={'case':name,'backend':b,'bad':{str(ids[p]):k for p,k in bad.items()},'baseline_exit':code0,'baseline_stderr':err0.strip()[-400:],'runs':0,'mismatches':[]}
                if bad and (code0!=2 or wrote0):c['mismatches'].append(f'baseline: exit {code0}, wrote output {wrote0}')
                if not bad and code0!=0:c['mismatches'].append(f'baseline failed on the valid block: {err0[-300:]}')
                for th in a.threads:
                    for k in range(a.repeats):
                        code,err,wrote=run(native_cmd(exe(b),root,GAMMA8,net,tasks,out,threads=th),out);c['runs']+=1
                        if bad:
                            if code!=2 or wrote or err!=err0:c['mismatches'].append({'threads':th,'repeat':k,'exit':code,'wrote':wrote,'stderr':err.strip()[-400:]})
                        else:
                            d=load(out)if wrote else None
                            if code!=0 or d is None or [scientific(r)for r in d['rows']]!=base_rows or d['graphs_loaded']!=base_loaded:
                                c['mismatches'].append({'threads':th,'repeat':k,'exit':code,'stderr':err.strip()[-400:]})
                if not bad:c['rows']=len(base_rows or []);c['graphs_loaded']=base_loaded
                c['passed']=not c['mismatches'];ok&=c['passed'];rec['cases'].append(c)
                print(f"{name} {b}: {'passed' if c['passed'] else 'FAILED'} ({c['runs']} candidate runs); baseline: {c['baseline_stderr'][-160:]!r}",flush=True)
    rec['status']='passed'if ok else'failed';rec['wall_seconds']=round(time.time()-t0,1)
    dump(a.output,rec);print(json.dumps({'status':rec['status'],'cases':len(rec['cases']),'wall_seconds':rec['wall_seconds']}))
    return 0 if ok else 1

if __name__=='__main__':sys.exit(main())
