#!/usr/bin/env python3
"""Stage-4c framework identity checks of a built export (run by s4c_build.slurm from the export's root; PLAN A-RPL-8,
A-FLAG-1). Writes OUT/identity.json and exits 3 when a check fails.

  s4c_identity.py OUT REF_PACKAGE PROFILE...

1. A-RPL-8: bin/c8d2_decimal and bin/c8d2_gmp have the sha256 of the final default binary (99a51c1d..., 1d2a2181...:
   the G4b build of b47b008, src/ of d46e736, on Expanse with Spack GCC 13.3.0 and GMP 6.2.1).
2. Preprocessed program: `<compile options> -E -P src/c8d2_integrate.cpp` with each default executable's own compile
   options (its build record, link words removed), here and in REF_PACKAGE (an export whose src/ is the final default
   binary's: its four sources are checked against their sha256 below), compared with all whitespace removed (and byte
   for byte, reported). Equal token streams mean the hooks expand to the exact path's own tokens.
3. --describe of every profile executable bin/c8d2_gmp_<p> (numerics <p>, numerics_params), its build record's
   numerics_sources, and the stub identity: a profile executable whose profiles are all stubs writes rows identical to
   bin/c8d2_gmp (every scientific field) on L7 and L8 blocks of both sectors (the 8 heaviest and 8 random kernels,
   2 replicates x 64 points, rate .8 and .9).
"""
from __future__ import annotations
import hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path.cwd();sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
from common import digest,link_only
import validate as V

FINAL={'bin/c8d2_decimal':'99a51c1d3f520f16a846eea90149e6cb9d42772db819dbdb2286cb12cb13bcbf',
       'bin/c8d2_gmp':'1d2a218147ef52b5d0ac37dd8aaead55045ab4fe68e48ec963ea4b8e93024faa'}
REF_SOURCES={'src/kernel.hpp':'375f06f1873b66256e660e435bf731cecd8740b6cb24012b1cdc34d494155e9c',
             'src/c8d2_integrate.cpp':'f59ba6a6e06203dd321d496b1b1a3eb6ccbfff8830cea8a842e09a93d0fb48ff',
             'src/quadfast.hpp':'b31ffc5968dd333aa924525fb2e479e5910da264ea57234ff0a9aaadb0db59a4',
             'src/diagnostics.hpp':'fa65d87f74247ab7e450476f52eff505f00f209b7b5b0b85b1bc3144555deccf'}

def preprocess(cmd:list[str],cwd:Path)->bytes:
    """The compile options of a build command (no -o, no link words, no source), then -E -P of the worker source."""
    opts=[];skip=False
    for w in cmd:
        if skip:skip=False;continue
        if w=='-o':skip=True;continue
        if w.endswith('src/c8d2_integrate.cpp')or link_only(w):continue
        opts.append(w)
    cp=subprocess.run([*opts,'-E','-P','src/c8d2_integrate.cpp'],cwd=cwd,capture_output=True)
    if cp.returncode:raise RuntimeError(f'preprocessing in {cwd} failed: {cp.stderr[-2000:]!r}')
    return cp.stdout

def main()->int:
    out=Path(sys.argv[1]);ref=Path(sys.argv[2]);profiles=sys.argv[3:];rec={'package':str(ROOT),'reference_package':str(ref)};fail=[]
    # 1. A-RPL-8
    rec['A-RPL-8']={k:{'this':digest(ROOT/k),'final_default':v,'identical':digest(ROOT/k)==v}for k,v in FINAL.items()}
    if not all(x['identical']for x in rec['A-RPL-8'].values()):fail.append('A-RPL-8: a default executable differs from the final default binary')
    # 2. preprocessed program against the reference export
    src={k:{'sha256':digest(ref/k),'expected':v,'equal':digest(ref/k)==v}for k,v in REF_SOURCES.items()}
    rec['reference_sources']=src
    if not all(x['equal']for x in src.values()):fail.append(f'{ref}: its src/ is not the final default binary\'s')
    pp={}
    for exe in ('bin/c8d2_decimal','bin/c8d2_gmp'):
        cmd=json.loads((ROOT/(exe+'.build.json')).read_text())['command'];new,old=preprocess(cmd,ROOT),preprocess(cmd,ref)
        tok=lambda b:b''.join(b.split())
        pp[exe]={'bytes_this':len(new),'bytes_reference':len(old),'byte_identical':new==old,'tokens_identical':tok(new)==tok(old),
                 'sha256_this':hashlib.sha256(new).hexdigest(),'sha256_reference':hashlib.sha256(old).hexdigest()}
        if not pp[exe]['tokens_identical']:fail.append(f'{exe}: the preprocessed program differs from the reference export\'s')
    rec['preprocessed']=pp
    # 3. the profile executables
    prof={}
    for p in profiles:
        exe=ROOT/'bin'/f'c8d2_gmp_{p}';d=json.loads(subprocess.run([str(exe),'--describe'],capture_output=True,text=True,check=True).stdout)
        br=json.loads((ROOT/'bin'/f'c8d2_gmp_{p}.build.json').read_text())
        stub=sorted(k for k,v in (d.get('numerics_params')or{}).items()if v.get('stub'))
        prof[p]={'sha256':digest(exe),'describe':d,'numerics_sources':br.get('numerics_sources'),'command':br['command'],'all_stubs':stub==sorted(p.split('+'))}
        if d.get('numerics')!=p:fail.append(f'{exe}: --describe numerics {d.get("numerics")!r}')
        if br.get('NUMERICS')!=p or br.get('executable_sha256')!=digest(exe):fail.append(f'{exe}: build record NUMERICS {br.get("NUMERICS")!r} or a stale record')
    rec['profiles']=prof
    stubs=[p for p in profiles if prof[p]['all_stubs']]
    if stubs:
        rows={};threads=len(os.sched_getaffinity(0))
        with tempfile.TemporaryDirectory(prefix='s4c_ident_')as td:
            td=Path(td)
            for sector in ('free','power'):
                for L in (7,8):
                    ids=V.by_cost(sector,L)[:8]+V.heavy_and_random(sector,L,0,8,6161+L+(9 if sector=='power'else 0));ids=sorted(set(ids))
                    root=V.stage(td/sector,sector,L,ids);net=td/f'{sector}_L{L}.bin';V.make_net(net,2,4*L-1,60,4242+L,64);tf=td/f'{sector}_L{L}.tasks'
                    tf.write_text(V.tasks_text(8,L,V.task_rows(ids,2,64)))
                    for rate in ('.8','.9'):
                        o=td/'exact.json';base=V.fresh_output(V.native_cmd(ROOT/'bin/c8d2_gmp',root,V.GAMMA8,net,tf,o,V.SEED,0,rate,threads),o)
                        want=[V.scientific(r)for r in base['rows']]
                        for p in stubs:
                            o=td/f'{p}.json';x=V.fresh_output(V.native_cmd(ROOT/'bin'/f'c8d2_gmp_{p}',root,V.GAMMA8,net,tf,o,V.SEED,0,rate,threads),o)
                            same=[V.scientific(r)for r in x['rows']]==want and x['numerics']==p
                            rows.setdefault(p,[]).append({'sector':sector,'L':L,'rate':rate,'rows':len(want),'quad':sum(r['quad']for r in base['rows']),
                                                          'mp':sum(r['mp']for r in base['rows']),'identical':same})
                            if not same:fail.append(f'stub profile {p}: rows differ from bin/c8d2_gmp ({sector} L{L} rate {rate})')
        rec['stub_identity']={'rule':'every scientific field equal to bin/c8d2_gmp; the native header says numerics <p>','blocks':rows}
    rec['failures']=fail;rec['passed']=not fail
    out.mkdir(parents=True,exist_ok=True);(out/'identity.json').write_text(json.dumps(rec,indent=1)+'\n')
    print(json.dumps({'A-RPL-8':{k:v['identical']for k,v in rec['A-RPL-8'].items()},'preprocessed':{k:(v['tokens_identical'],v['byte_identical'])for k,v in pp.items()},
                      'stub_identity':{p:all(b['identical']for b in v)for p,v in rec.get('stub_identity',{}).get('blocks',{}).items()},'failures':fail},indent=1))
    return 0 if not fail else 3

if __name__=='__main__':sys.exit(main())
