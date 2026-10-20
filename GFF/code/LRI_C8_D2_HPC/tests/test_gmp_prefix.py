#!/usr/bin/env python3
"""Stage 4b R4f (the opt-in GMP_PREFIX knob of the Makefile, the GMP identity in the build record, and the R4f
development scripts): Mac-runnable tests of the pure logic. No native build: make runs with -n, the worker is
tests/fake_worker.py, perf is tests/fake_perf.py, the topology is --fake-topology with --no-pin.

  default       GMP_PREFIX unset: the dry-run commands of every worker target (decimal, gmp, the gmp diagnostic and
                sanitizer builds, the probe, the inspector, R3a's quaddiff tools) are the delivered ones word for word, with and without the
                user hooks (CXX, CPPFLAGS, OPTFLAGS, CXXFLAGS, LDFLAGS, LDLIBS)
  prefix        GMP_PREFIX=<dir>: -I<dir>/include right after CXX and -L<dir>/lib -Wl,-rpath,<dir>/lib
                -Wl,--disable-new-dtags first in the link words of every GMP-linked command; the decimal command, the
                inspector and the required flags are unchanged; C8B_GMP_PREFIX reaches the build-record step
  refusals      a relative path, a path with a space, a prefix without include/gmp.h or without lib/libgmp.*
  build_record  the ldd and readelf -d parsers and gmp_library() where the tools are missing (all fields None)
  r4f_scripts   the R4f job scripts (default build, GMP builds, validation, speed, layout control): bash syntax,
                #SBATCH account, names, logs, --mem, --time, admission before every sbatch
  r4f_speed     r4f_bench.py speed on a mini fixture: rotated order, medians, speedups, identical rows; a deadline of
                0 skips every run and fails
  r4f_profile   r4f_bench.py profile with fake perf: libgmp table, shares, tier timers, identical rows
  targets       every tests/test_*.py and gen/test_*.py is run by make test-python/test-full (make -n) or by J-GEN-1
                (slurm/gen/regress.slurm)
--only NAME,... runs the named tests.
Usage: python3 -B tests/test_gmp_prefix.py [--output FILE] [--only NAME,...]"""
from __future__ import annotations
import argparse,json,os,re,shlex,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PY=sys.executable
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
RESULTS=[]
R4F=ROOT/'benchmarks/expanse_2026-10-c8/stage4b/dev_r4f/scripts'
def ok(name,**info):RESULTS.append({'test':name,'status':'passed',**info});print('PASS',name,flush=True)

TARGETS=('bin/c8d2_decimal','bin/c8d2_gmp','bin/c8d2_gmp_prof','bin/c8d2_gmp_ratiohist','bin/c8d2_decimal_san','bin/c8d2_gmp_san',
         'bin/c8d2_interleave_probe','bin/c8d2_inspect','bin/c8d2_quad_differential','bin/c8d2_quad_ranges')
HOOKS=('CXX','CPPFLAGS','OPTFLAGS','CXXFLAGS','LDFLAGS','LDLIBS','GMP_PREFIX')
def dry(*args,targets=TARGETS)->subprocess.CompletedProcess:
    env={k:v for k,v in os.environ.items()if k not in HOOKS}
    return subprocess.run(['make','-s','-n','-B','-C',str(ROOT),'PYTHON=python3',*targets,*args],capture_output=True,text=True,env=env,timeout=120)
def compiles(text:str)->dict:
    """{output: compile-and-link words} of a dry run (lines that end in -o bin/<x>, not the build-record lines)."""
    out={}
    for line in text.splitlines():
        w=shlex.split(line)
        if len(w)>2 and w[-2]=='-o'and w[-1].startswith('bin/')and 'build_record.py'not in line:out[w[-1]]=w
    return out
def records(text:str)->dict:
    out={}
    for line in text.splitlines():
        w=shlex.split(line)
        if 'tools/build_record.py'in w:out[w[w.index('tools/build_record.py')+1]]=w[w.index('--')+1:]
    return out

REQ=['-std=c++17','-fopenmp','-ffp-contract=off','-fno-fast-math']
def expected_default(cxx,cpp,opt,cxxf,ld,libs):
    """The delivered commands (C7(2)'s with the C8 names; Makefile before R4f)."""
    c=[cxx,*cpp,*opt,*cxxf,*REQ];san=[cxx,*cpp,'-O1','-g','-fno-omit-frame-pointer','-fsanitize=address,undefined','-fno-sanitize-recover=all','-D_GLIBCXX_ASSERTIONS',*cxxf,*REQ]
    src='src/c8d2_integrate.cpp'
    return {'bin/c8d2_decimal':[*c,src,*ld,'-lquadmath',*libs,'-o','bin/c8d2_decimal'],
            'bin/c8d2_gmp':[*c,'-DC8_USE_GMP',src,*ld,'-lquadmath','-lgmp',*libs,'-o','bin/c8d2_gmp'],
            'bin/c8d2_gmp_prof':[*c,'-DC8_USE_GMP','-DC8_TIER_TIMERS',src,*ld,'-lquadmath','-lgmp',*libs,'-o','bin/c8d2_gmp_prof'],
            'bin/c8d2_gmp_ratiohist':[*c,'-DC8_USE_GMP','-DC8_RATIO_HISTOGRAM',src,*ld,'-lquadmath','-lgmp',*libs,'-o','bin/c8d2_gmp_ratiohist'],
            'bin/c8d2_decimal_san':[*san,src,*ld,'-lquadmath',*libs,'-o','bin/c8d2_decimal_san'],
            'bin/c8d2_gmp_san':[*san,'-DC8_USE_GMP',src,*ld,'-lquadmath','-lgmp',*libs,'-o','bin/c8d2_gmp_san'],
            'bin/c8d2_interleave_probe':[*c,'-DC8_USE_GMP','benchmarks/probes/interleave_probe.cpp',*ld,'-lquadmath','-lgmp',*libs,'-o','bin/c8d2_interleave_probe'],
            'bin/c8d2_inspect':[*c,'src/c8d2_inspect.cpp',*ld,'-lquadmath',*libs,'-o','bin/c8d2_inspect'],
            # R3a's proof tools (make quaddiff; integration of R3a and R4f): quad_differential links no GMP,
            # quad_ranges links it like the worker and takes the GMP_PREFIX words.
            'bin/c8d2_quad_differential':[*c,'tests/quad_differential.cpp','-o','bin/c8d2_quad_differential'],
            'bin/c8d2_quad_ranges':[*c,'-DC8_USE_GMP','tests/quad_ranges.cpp',*ld,'-lquadmath','-lgmp',*libs,'-o','bin/c8d2_quad_ranges']}

def test_default():
    for hooks in ({'CXX':'g++'},{'CXX':'g++-13','CPPFLAGS':'-I/x -DFOO','OPTFLAGS':'-O2','CXXFLAGS':'-g','LDFLAGS':'-L/y -Wl,-z,now','LDLIBS':'-lfoo'}):
        cp=dry(*[f'{k}={v}'for k,v in hooks.items()]);assert cp.returncode==0,cp.stderr[-800:]
        got=compiles(cp.stdout);sp=lambda k,d='':shlex.split(hooks.get(k,d))
        want=expected_default(hooks['CXX'],sp('CPPFLAGS'),sp('OPTFLAGS','-O3'),sp('CXXFLAGS'),sp('LDFLAGS'),sp('LDLIBS'))
        assert got==want,{k:(got.get(k),want[k])for k in want if got.get(k)!=want[k]}
        rec=records(cp.stdout)
        for t,w in rec.items():assert w==got[t],t  # the build record receives the command that ran
        assert not any('-rpath'in ' '.join(w)or '--disable-new-dtags'in w for w in got.values())
    ok('default_commands_unchanged',targets=len(TARGETS))

def fake_prefix(td:Path,lib='libgmp.so.10')->Path:
    p=td/'gmp prefix'.replace(' ','_');(p/'include').mkdir(parents=True);(p/'lib').mkdir();(p/'include/gmp.h').write_text('/* fake */\n')
    if lib:(p/'lib'/lib).write_text('')
    return p

def test_prefix():
    with tempfile.TemporaryDirectory()as td:
        P=fake_prefix(Path(td).resolve());hooks={'CXX':'g++','CPPFLAGS':'-I/x','LDFLAGS':'-L/y'}
        cp=dry(*[f'{k}={v}'for k,v in hooks.items()],f'GMP_PREFIX={P}');assert cp.returncode==0,cp.stderr[-800:]
        got=compiles(cp.stdout);base=expected_default('g++',['-I/x'],['-O3'],[],['-L/y'],[])
        link=[f'-L{P}/lib',f'-Wl,-rpath,{P}/lib','-Wl,--disable-new-dtags']
        for t,w in base.items():
            if t in('bin/c8d2_decimal','bin/c8d2_decimal_san','bin/c8d2_inspect','bin/c8d2_quad_differential'):assert got[t]==w,(t,got[t]);continue
            i=w.index('-L/y');want=[w[0],f'-I{P}/include',*w[1:i],*link,*w[i:]]
            assert got[t]==want,(t,got[t],want)
        # the build-record step sees GMP_PREFIX through the exported C8B_GMP_PREFIX (empty when unset)
        cp=subprocess.run(['make','-s','-C',str(ROOT),'-f','-',f'GMP_PREFIX={P}','show'],input=(ROOT/'Makefile').read_text()+'\nshow:\n\t@echo "C8B_GMP_PREFIX=$$C8B_GMP_PREFIX"\n',
                          capture_output=True,text=True,env={k:v for k,v in os.environ.items()if k not in HOOKS},timeout=120)
        assert cp.returncode==0 and cp.stdout.strip()==f'C8B_GMP_PREFIX={P}',(cp.stdout,cp.stderr[-400:])
        cp=subprocess.run(['make','-s','-C',str(ROOT),'-f','-','show'],input=(ROOT/'Makefile').read_text()+'\nshow:\n\t@echo "C8B_GMP_PREFIX=[$$C8B_GMP_PREFIX]"\n',
                          capture_output=True,text=True,env={k:v for k,v in os.environ.items()if k not in HOOKS},timeout=120)
        assert cp.returncode==0 and cp.stdout.strip()=='C8B_GMP_PREFIX=[]',cp.stdout
    ok('prefix_commands',targets=len(TARGETS))

def test_refusals():
    with tempfile.TemporaryDirectory()as td:
        td=Path(td).resolve();good=fake_prefix(td/'g');nolib=fake_prefix(td/'n',lib=None);nohdr=td/'h';(nohdr/'lib').mkdir(parents=True);(nohdr/'lib/libgmp.a').write_text('')
        cases=(('rel/gmp','must be an absolute path'),('/a b','one absolute path without spaces'),(str(nohdr),'include/gmp.h does not exist'),(str(nolib),'no libgmp library'))
        for val,msg in cases:
            cp=dry(f'GMP_PREFIX={val}',targets=('bin/c8d2_gmp',));assert cp.returncode!=0 and msg in cp.stderr,(val,cp.returncode,cp.stderr[-300:])
        cp=dry(f'GMP_PREFIX={nohdr.parent/"g"/"gmp_prefix"}',targets=('bin/c8d2_gmp',));assert cp.returncode==0,cp.stderr[-300:]
    ok('prefix_refusals',cases=4)

def test_build_record():
    import build_record as br
    ldd='\tlinux-vdso.so.1 (0x00007ffd)\n\tlibquadmath.so.0 => /usr/lib64/libquadmath.so.0 (0x1)\n\tlibgmp.so.10 => /home/u/c8d2/opt/gmp-6.2.1-zen2/lib/libgmp.so.10 (0x2)\n'
    assert br.parse_ldd(ldd)=={'soname':'libgmp.so.10','path':'/home/u/c8d2/opt/gmp-6.2.1-zen2/lib/libgmp.so.10'}
    assert br.parse_ldd('\tlibgmp.so.10 => not found\n')=={'soname':'libgmp.so.10','path':None}
    assert br.parse_ldd('\tlibm.so.6 => /lib64/libm.so.6 (0x3)\n')is None
    dyn=' 0x0000000000000001 (NEEDED)             Shared library: [libgmp.so.10]\n 0x000000000000000f (RPATH)              Library rpath: [/p/lib]\n'
    assert br.parse_dynamic(dyn)=={'RPATH':'/p/lib','RUNPATH':None}
    assert br.parse_dynamic(' 0x000000000000001d (RUNPATH)            Library runpath: [/a:/b]\n')=={'RPATH':None,'RUNPATH':'/a:/b'}
    with tempfile.TemporaryDirectory()as td:
        f=Path(td)/'x';f.write_text('');saved=os.environ.get('PATH')
        try:
            os.environ['PATH']=td  # no ldd, readelf or nm: every field None, never an exception
            g=br.gmp_library(f)
        finally:os.environ['PATH']=saved or ''
        assert all(g[k]is None for k in('soname','path','realpath','sha256','fat','rpath','runpath')),g
    src=(ROOT/'tools/build_record.py').read_text()
    for need in ("'GMP_PREFIX':e.get('C8B_GMP_PREFIX')","'gmp_header':","'gmp_library':gmp_library(exe)if backend=='gmp'else None"):assert need in src,need
    ok('build_record_gmp_identity')

def test_r4f_scripts():
    names=sorted(p.name for p in R4F.glob('*.slurm'));assert names==['r4f_control.slurm','r4f_default_build.slurm','r4f_gmp_build.slurm','r4f_speed.slurm','r4f_validate.slurm'],names
    for n in names:
        t=(R4F/n).read_text();cp=subprocess.run(['bash','-n',str(R4F/n)],capture_output=True,text=True);assert cp.returncode==0,(n,cp.stderr)
        sb=' '.join(l for l in t.splitlines()if l.startswith('#SBATCH'))
        assert '-A yun124'in sb and '--mem='in sb and re.search(r'(?:^| )-t \d\d:\d\d:\d\d',sb)and '--no-requeue'in sb,n
        assert re.search(r'#SBATCH -J c8d2-r4f-\w+',t)and '#SBATCH -o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out'in t,n
        assert 'source "$HOME/c8d2/env_expanse.sh"'in t and 'set -euo pipefail'in t,n
        if '-p compute'in sb:assert '--exclusive'in sb and re.search(r'-t 00:(?:[0-2]\d|30):00',sb),n  # the speed node: at most 30 min
        else:assert '-p shared'in sb and '--nodes=1'in sb,n
    sub=(R4F/'submit_r4f_expanse.sh').read_text();assert subprocess.run(['bash','-n',str(R4F/'submit_r4f_expanse.sh')]).returncode==0
    lines=sub.splitlines();sb=[i for i,l in enumerate(lines)if 'sbatch --parsable'in l];assert len(sb)==5,sb
    for i in sb:assert re.search(r'admit \$n (shared|compute)',lines[i-1]),lines[i-1]  # every sbatch right after its admission
    assert 'h7_admit.py'in sub and 'Master running'in sub and 'R4F_MAX_SHARED=8'in sub and 'R4F_MAX_NODES=1'in sub and 'declare -A'not in sub
    # the script works from the repository root (git archive exports only the current subtree) and finds h7_admit.py
    m=re.search(r'^S=\$\(cd "\$\(dirname "\$0"\)" && pwd\); cd "\$S/([./]+)"$',sub,re.M);assert m and (R4F/m[1]).resolve()==ROOT,m and m[1]
    assert 'git rev-parse --show-toplevel'in sub
    m=re.search(r'python3 "\$S/([^"]+h7_admit\.py)"',sub);assert m and (R4F/m[1]).resolve().is_file(),m and m[1]
    ok('r4f_scripts',scripts=len(names)+1)

def bench(*args,env=None)->subprocess.CompletedProcess:
    return subprocess.run([PY,'-B',str(R4F/'r4f_bench.py'),*map(str,args)],capture_output=True,text=True,env={**os.environ,**(env or{})},timeout=600)

def test_r4f_speed():
    import test_profiling as tp
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);fx=tp.mini_fixture(td);f=tp.fakes(td);fat=td/'fat';host=td/'host';shutil.copy2(f['gmp'],fat);shutil.copy2(f['gmp'],host)
        common=['--package',ROOT,'--fixtures',fx,'--fake-topology','2x1x2','--no-pin','--scratch',td,'--threads',2,'--exe',f'baseline={f["gmp"]}','--exe',f'fat={fat}','--exe',f'zen2={host}']
        cp=bench('speed',*common,'--repeats',2,'--output',td/'s');assert cp.returncode==0,cp.stdout[-1500:]+cp.stderr[-1500:]
        r=json.loads((td/'s/speed.json').read_text());assert r['stage']=='final'and not r['errors']and r['settings']['lanes']=={'heavy_free_L8':[0,1],'heavy_power_L8':[2,3]}
        done=[x for x in r['runs']if 'summary'in x];assert len(done)==12
        for b in ('heavy_free_L8','heavy_power_L8'):
            order=[x['exe']for x in r['runs']if x['block']==b];assert order==['baseline','fat','zen2','fat','zen2','baseline'],order
            assert r['results'][b]['_rows']['identical']and r['results'][b]['baseline']['speedup_wall']==1.0
            assert all(r['results'][b][x]['runs']==2 and r['results'][b][x]['median_wall']>0 for x in('baseline','fat','zen2'))
        cp=bench('speed',*common,'--repeats',1,'--deadline',0,'--output',td/'d');assert cp.returncode==1
        d=json.loads((td/'d/speed.json').read_text());assert all('skipped'in x for x in d['runs'])and len(d['runs'])==6
    ok('r4f_speed_dry_run',runs=12)

def test_r4f_profile():
    import test_profiling as tp
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);fx=tp.mini_fixture(td);f=tp.fakes(td);fat=td/'fat';shutil.copy2(f['gmp'],fat);pfat=td/'pfat';shutil.copy2(f['prof'],pfat)
        cp=bench('profile','--package',ROOT,'--fixtures',fx,'--fake-topology','1x1x4','--no-pin','--scratch',td,'--perf',f['perf'],'--stride',2,
                 '--exe',f'baseline={f["gmp"]}','--exe',f'fat={fat}','--prof',f'baseline={f["prof"]}','--prof',f'fat={pfat}','--output',td/'p')
        assert cp.returncode==0,cp.stdout[-1500:]+cp.stderr[-1500:]
        r=json.loads((td/'p/profile.json').read_text());assert r['stage']=='final'and not r['errors']and r['settings']['threads']==4
        for b in ('heavy_free_L8','heavy_power_L8'):
            x=r['results'][b];assert x['rows']['identical']and x['tasks']==(x['of']+1)//2
            for e in ('baseline','fat'):
                g=x['perf'][e]['gmp'];assert abs(g['libgmp_total']-14.0)<1e-9 and g['symbols'][0]=={'symbol':'__gmpn_mul_basecase','percent':6.0},g
                assert abs(x['perf'][e]['shares']['categories']['binary128_arith']-52.0)<1e-9
                assert x['tiers'][e]['seconds']=={'first_pass':.5,'quad':.3,'mp':.2}
            assert x['tiers']['fat']['speedup_per_call']['first_pass']==1.0
    ok('r4f_profile_dry_run')

def test_targets():
    """Every test program of the package (tests/test_*.py, gen/test_*.py) is run by a make target (test-python, test,
    test-full: `make -n`, so nothing runs) or by J-GEN-1 (slurm/gen/regress.slurm); a test that no gate runs proves
    nothing (Stage-6 fix round 2: tests/test_gmp_binding.py, Y1's test, was in no target)."""
    cp=dry(targets=('test-python','test-full'));assert cp.returncode==0,cp.stderr[-600:]
    run=set(re.findall(r'(?:tests|gen)/test_\w+\.py',cp.stdout+(ROOT/'slurm/gen/regress.slurm').read_text()))
    have={str(f.relative_to(ROOT))for d in('tests','gen')for f in (ROOT/d).glob('test_*.py')}
    missing=sorted(have-run);assert not missing,f'test programs that no make target or J-GEN-1 runs: {missing}'
    ok('every_test_program_in_a_make_target_or_j_gen_1',programs=len(have))

TESTS=(('targets',test_targets),('default',test_default),('prefix',test_prefix),('refusals',test_refusals),('build_record',test_build_record),('r4f_scripts',test_r4f_scripts),
       ('r4f_speed',test_r4f_speed),('r4f_profile',test_r4f_profile))
NAMES_T=[n for n,_ in TESTS]

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('--output',type=Path);ap.add_argument('--only',help='NAME,... of: '+', '.join(NAMES_T))
    a=ap.parse_args();sel=NAMES_T
    if a.only is not None:
        sel=[s.strip()for s in a.only.split(',')if s.strip()];bad=[s for s in sel if s not in NAMES_T]
        if not sel or bad:ap.error(f'--only: unknown test(s) {bad}'if bad else'--only: no test named')
    os.environ.pop('C8_FAKE_FAIL',None);os.environ.pop('FAKE_PERF_REFUSE',None);failed=[]
    for name,fn in TESTS:
        if name not in sel:continue
        try:fn()
        except Exception as e:  # report every failure, then fail
            import traceback;traceback.print_exc();failed.append(name);RESULTS.append({'test':name,'status':'failed','error':f'{type(e).__name__}: {e}'[:2000]});print('FAIL',name,flush=True)
    rec={'schema':'c8-d2-test-gmp-prefix-1','requested':sel,'executed':[r['test']for r in RESULTS],'results':RESULTS,'passed':not failed and bool(RESULTS),'failed':failed}
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(rec,indent=1)+'\n')
    print(json.dumps({'passed':rec['passed'],'tests':len(RESULTS),'failed':failed}));return 0 if rec['passed']else 1

if __name__=='__main__':sys.exit(main())
