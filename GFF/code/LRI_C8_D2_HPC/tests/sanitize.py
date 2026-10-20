#!/usr/bin/env python3
"""A-KER-4 (J-VAL-4): the sanitizer builds bin/c8d2_{decimal,gmp}_san (make sanitize: -O1 -g -fno-omit-frame-pointer
-fsanitize=address,undefined -fno-sanitize-recover=all -D_GLIBCXX_ASSERTIONS plus the required flags) run with
ASAN_OPTIONS=detect_leaks=0:abort_on_error=1 and UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 on the L=2 graph
and the 2 lightest and 2 heaviest kernels of every (sector, L) at L3-L8, 2 replicates x 64 points, layouts 0/1/2,
4 threads, both orders where valid (order 7 for L <= 7, order 8 for L = 2 and L3-L8). tests/point_checks.cpp is built
with the same flags and run on the same kernels; its gmp tool with the GMP_PREFIX of bin/c8d2_gmp_san's build record
and the same libgmp at run time (pc_tool, verify_pc_tool; Stage-6 fix round 2). Every run must exit 0 with no sanitizer or assertion report.
Every run gets ENV: common.omp_child_env(4) (no inherited OMP_*, GOMP_*, KMP_* control; R2) plus the sanitizer options.
--selftest builds three probes with the same flags and requires each to abort with its report: a one-past-the-end
std::array write through operator[] (_GLIBCXX_ASSERTIONS), the same write through a raw pointer (AddressSanitizer),
and a signed overflow (UndefinedBehaviorSanitizer). The probes run with stdout and stderr on a pseudo-terminal
(F4, Stage 5): libstdc++ of GCC <= 12 prints a failed _GLIBCXX_ASSERTIONS check on STDOUT with __builtin_printf and then
aborts, so on a pipe the text stays in stdio's full buffer and is lost at the abort; a terminal is line-buffered (GCC
>= 13 prints it on stderr). --capture-check checks that capture without a compiler: a Python probe prints a report on
stdout without flushing and aborts; on a pipe the report is lost, on the pty it is read. The record goes only to
--output."""
from __future__ import annotations
from pathlib import Path
import argparse,json,os,re,shlex,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'tests'))
from common import REQUIRED_CXXFLAGS,dump,digest,environment_record,gmp_prefix_words,load,omp_child_env
from validate import stage,by_cost,tasks_text,task_rows,native_cmd,make_net,GAMMA7,GAMMA8,inventory

SAN_FLAGS=['-O1','-g','-fno-omit-frame-pointer','-fsanitize=address,undefined','-fno-sanitize-recover=all','-D_GLIBCXX_ASSERTIONS']
# R2 (Stage-6 residual): the 4-thread runs get the controlled OpenMP environment (common.omp_child_env(4): no inherited
# OMP_*, GOMP_*, KMP_* control, so an inherited OMP_THREAD_LIMIT=1 or OMP_DYNAMIC=true cannot make them serial and hide a
# data race or a per-thread state defect from the sanitizers), plus the sanitizer options.
ENV=dict(omp_child_env(4),ASAN_OPTIONS='detect_leaks=0:abort_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
REPORTS=('ERROR: AddressSanitizer','runtime error:','AddressSanitizer','UndefinedBehaviorSanitizer','Assertion','__glibcxx_assert','is out of range')

def san_command(sources,output,defines=(),libs=('-lquadmath',),gmp_prefix=None):
    """The Makefile's sanitizer command layout (SAN_COMPILE, GMP_SAN_CMD); with gmp_prefix, its GMP_INC words right after
    CXX and its GMP_LINK words ahead of LDFLAGS, as GMP_SAN_CMD places them (common.gmp_prefix_words)."""
    e=os.environ;sp=lambda k:shlex.split(e.get(k,''));inc,link=gmp_prefix_words(gmp_prefix)
    return [*shlex.split(e.get('CXX','g++')),*inc,*sp('CPPFLAGS'),*SAN_FLAGS,*sp('CXXFLAGS'),*REQUIRED_CXXFLAGS,*[f'-D{d}'for d in defines],*map(str,sources),
            *link,*sp('LDFLAGS'),*libs,*sp('LDLIBS'),'-o',str(output)]

def pc_tool(b:str,exe:Path,worker:Path)->tuple[list,dict]:
    """(The compile command of the point_checks sanitizer tool of backend b, its binding to the sanitizer worker of that
    backend). Stage-6 fix round 2 (Y1's defect class): the gmp tool used to link plain -lgmp whatever GMP_PREFIX
    `make sanitize` built bin/c8d2_gmp_san with. It now gets the GMP_PREFIX of the worker's build record (which must
    describe the worker: tools/build_record.py worker_record), placed as GMP_SAN_CMD places it; a GMP_PREFIX in this
    environment other than the record's is refused (make does not track the knob). verify_pc_tool then checks the
    libgmp the tool resolves. build_record.BindingRefused before anything is compiled."""
    import build_record as BR
    src=[ROOT/'tests/point_checks.cpp']
    if b!='gmp':return san_command(src,exe),{'backend':b,'worker':str(Path(worker).resolve())}
    rec=BR.worker_record(worker);prefix=rec.get('GMP_PREFIX')or None;envp=(os.environ.get('GMP_PREFIX')or'').strip()or None
    if envp is not None and envp!=prefix:
        raise BR.BindingRefused(f'{worker}: this environment names GMP_PREFIX={envp}, the sanitizer worker was built with GMP_PREFIX={prefix or "(unset)"} '
                                '(make does not track the knob: rebuild with make -B sanitize GMP_PREFIX=..., or unset it)')
    lib=rec.get('gmp_library')if isinstance(rec.get('gmp_library'),dict)else{}
    return (san_command(src,exe,defines=['C8_USE_GMP'],libs=('-lquadmath','-lgmp'),gmp_prefix=prefix),
            {'backend':'gmp','worker':str(Path(worker).resolve()),'worker_sha256':rec['executable_sha256'],'GMP_PREFIX':prefix,
             'gmp_library':{k:lib.get(k)for k in('soname','realpath','sha256')}})

def verify_pc_tool(tool:Path,binding:dict)->dict:
    """After the compile: the gmp point_checks tool and its sanitizer worker must both resolve the libgmp the worker's
    build record names (build_record.check_linked; refused when ldd cannot tell); the binding gains 'linked'."""
    import build_record as BR
    if binding['backend']=='gmp':
        if not binding['gmp_library'].get('sha256'):raise BR.BindingRefused(f'{binding["worker"]}: its build record names no sha256 of the libgmp it resolves')
        binding['linked']=BR.check_linked(tool,binding)
    return binding

def clean(p:subprocess.CompletedProcess,what:str)->None:
    text=p.stdout+p.stderr
    if p.returncode!=0 or any(r in text for r in REPORTS):raise AssertionError(f'{what}: exit {p.returncode}; {text[-3000:]}')

def kernels()->list:
    out=[('free',2,[0])]
    for sector in ('free','power'):
        for L in range(3,9):
            if not (ROOT/f'inputs/packs/{sector}_L{L}.pack').exists():raise SystemExit(f'inputs/packs/{sector}_L{L}.pack is missing (make inputs-l8 INVENTORY=...)')
            order=by_cost(sector,L);out.append((sector,L,sorted(set(order[-2:]+order[:2]))))
    return out

def runs(td:Path)->list:
    res=[]
    for b in ('decimal','gmp'):
        exe=ROOT/f'bin/c8d2_{b}_san'
        if not exe.exists():raise SystemExit(f'{exe} is missing (make sanitize)')
        d=json.loads(subprocess.run([exe,'--describe'],capture_output=True,text=True,check=True,env=ENV).stdout)
        if d.get('diagnostic')is not True or d.get('diagnostic_kind')!='sanitize':raise AssertionError(f'{exe} --describe: {d}')
        for sector,L,ids in kernels():
            root=stage(td/sector,sector,L,ids)
            for order in ((7,8)if L<=7 else(8,)):
                gamma=GAMMA7 if order==7 else GAMMA8
                for layout in (0,1,2):
                    net=td/f'san_{L}_{layout}.bin'
                    if not net.exists():make_net(net,2,2*L if layout==2 else 4*L-1,60,52201+L+100*layout,64)
                    tasks=td/'tasks';tasks.write_text(tasks_text(order,L,task_rows(ids,2,64)));out=td/'out.json';out.unlink(missing_ok=True)
                    s=time.time();p=subprocess.run(list(map(str,native_cmd(exe,root,gamma,net,tasks,out,4417,layout,.8,4))),capture_output=True,text=True,env=ENV)
                    clean(p,f'{b} {sector} L{L} order {order} layout {layout}')
                    rows=load(out)['rows']
                    res.append({'backend':b,'sector':sector,'L':L,'order':order,'layout':layout,'graphs':ids,'rows':len(rows),'quad':sum(r['quad']for r in rows),'mp':sum(r['mp']for r in rows),'seconds':round(time.time()-s,1)})
                    print(json.dumps(res[-1]),flush=True)
    return res

def point_checks(td:Path)->list:
    paths=[]
    for sector,L,ids in kernels():
        if L==2:continue
        root=stage(td/sector,sector,L,ids);paths+=[str(root/f'L{L}/G{g}.txt')for g in ids]
    lst=td/'points.list';lst.write_text('\n'.join(paths)+'\n');res=[]
    for b in ('decimal','gmp'):
        exe=td/f'point_checks_san_{b}';cmd,binding=pc_tool(b,exe,ROOT/f'bin/c8d2_{b}_san')  # bound to the sanitizer worker's GMP
        subprocess.run(cmd,check=True);binding=verify_pc_tool(exe,binding)
        p=subprocess.run([exe,lst],capture_output=True,text=True,env=ENV);clean(p,f'point_checks {b}')
        res.append({'backend':b,'command':cmd,'binding':binding,**json.loads(p.stdout)});print(json.dumps(res[-1])[:300],flush=True)
    return res

# Each probe writes one past the end of an EMAX-sized std::array (index EMAX, formed at run time from argc), or
# overflows an int; with the sanitizer flags each must abort with its own report: operator[] trips
# _GLIBCXX_ASSERTIONS; the write through a volatile pointer, whose object size UBSan cannot see, reaches
# AddressSanitizer's stack redzone; the int overflow trips UndefinedBehaviorSanitizer.
PROBES={
 'glibcxx_assertions':('#include "src/kernel.hpp"\nint main(int c,char**){std::array<ld,EMAX>a{};volatile int i=EMAX+c-1;a[i]=1;return int(a[0]);}\n','Assertion'),
 'address':('#include "src/kernel.hpp"\nint main(int c,char**){std::array<ld,EMAX>a{};volatile int i=EMAX+c-1;ld*volatile p=a.data();p[i]=1;return int(a[0]);}\n','AddressSanitizer: stack-buffer-overflow'),
 'undefined':('#include <climits>\nint main(int c,char**){volatile int x=INT_MAX;int y=x+c;return y==0;}\n','runtime error: signed integer overflow'),
}
ANSI=re.compile(r'\x1b\[[0-9;]*[A-Za-z]')

def run_on_pty(cmd,env,timeout:float=300.)->tuple[int,str]:
    """Run cmd with stdout and stderr on one pseudo-terminal; return (exit status, the text with colour codes removed).
    A terminal makes stdio line-buffered, so text printed before an abort is not lost (F4)."""
    import pty,select
    master,slave=pty.openpty()
    try:p=subprocess.Popen(list(map(str,cmd)),stdin=subprocess.DEVNULL,stdout=slave,stderr=slave,env=env,close_fds=True)
    finally:os.close(slave)
    chunks=[];deadline=time.monotonic()+timeout
    try:
        while True:
            left=deadline-time.monotonic()
            if left<=0:p.kill();p.wait();raise AssertionError(f'{cmd[0]}: output did not end within {timeout:.0f} s')
            ready,_,_=select.select([master],[],[],min(left,1.))
            if not ready:
                if p.poll()is not None:break  # exited, and nothing more to read
                continue
            try:data=os.read(master,65536)
            except OSError:break  # EIO: every slave descriptor is closed (Linux)
            if not data:break      # EOF (macOS)
            chunks.append(data)
    finally:os.close(master)
    rc=p.wait(timeout=max(1.,deadline-time.monotonic()))
    return rc,ANSI.sub('',b''.join(chunks).decode(errors='replace')).replace('\r\n','\n')

def selftest(td:Path)->list:
    out=[]
    for name,(code,expect) in PROBES.items():
        src=td/f'probe_{name}.cpp';src.write_text(code);exe=td/f'probe_{name}'
        subprocess.run(san_command([src],exe)+[f'-I{ROOT}'],check=True)
        rc,text=run_on_pty([exe],ENV)
        if rc==0 or expect not in text:raise AssertionError(f'self-test {name}: no {expect!r} report (exit {rc}): {text[-1500:]}')
        out.append({'probe':name,'exit':rc,'expected':expect,'captured':'pty (stdout and stderr)','report':next(l for l in text.splitlines()if expect in l)[:300]})
        print(json.dumps(out[-1]),flush=True)
    return out

# The capture check (F4): an unflushed stdout report followed by abort(), as libstdc++ <= 12 does on a failed assertion.
CAPTURE_PROBE="import os,sys;sys.stdout.write(\"/usr/include/c++/11/array:188: Assertion '__n < this->size()' failed.\\n\");os.abort()"

def capture_check()->dict:
    """The report of CAPTURE_PROBE is lost on a pipe and read on the pty."""
    cmd=[sys.executable,'-S','-c',CAPTURE_PROBE];env={k:v for k,v in os.environ.items()if k!='PYTHONUNBUFFERED'}  # stdout buffered as a C stdio stream
    piped=subprocess.run(cmd,capture_output=True,text=True,env=env)
    rc,text=run_on_pty(cmd,env,60.)
    rec={'piped_exit':piped.returncode,'piped_report_seen':'Assertion'in piped.stdout+piped.stderr,'pty_exit':rc,'pty_report_seen':'Assertion'in text}
    if rc==0 or not rec['pty_report_seen']:raise AssertionError(f'capture check: the pty run did not show the report: {rec} {text[-500:]}')
    if piped.returncode==0 or rec['piped_report_seen']:raise AssertionError(f'capture check: the piped control lost nothing, so it shows nothing: {rec}')
    print(json.dumps(rec),flush=True);return rec

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);ap.add_argument('--output',type=Path);ap.add_argument('--selftest',action='store_true')
    ap.add_argument('--capture-check',action='store_true',help='only the pty capture check (no compiler, no build; F4)')
    a=ap.parse_args()
    if a.output and a.output.exists():raise SystemExit(f'{a.output} exists')
    if a.capture_check:
        rec={'status':'passed','test':'sanitize --capture-check','capture':capture_check()}
        if a.output:dump(a.output,rec)
        sys.exit(0)
    t0=time.time()
    with tempfile.TemporaryDirectory(prefix='c8d2_san_')as td:
        td=Path(td);rec={'status':'passed','test':'sanitize','flags':SAN_FLAGS,'asan_options':ENV['ASAN_OPTIONS'],'ubsan_options':ENV['UBSAN_OPTIONS'],
                         'omp_environment':{k:v for k,v in sorted(ENV.items())if k.startswith(('OMP_','GOMP_','KMP_'))}}
        if a.selftest:rec['capture']=capture_check();rec['selftest']=selftest(td)
        rec['worker_runs']=runs(td);rec['point_checks']=point_checks(td)
        rec['executables']={b:digest(ROOT/f'bin/c8d2_{b}_san')for b in('decimal','gmp')}
    rec['wall_seconds']=round(time.time()-t0,1);rec['environment']=environment_record()
    if a.output:dump(a.output,rec)
    print(json.dumps({k:v for k,v in rec.items()if k not in('environment','worker_runs')},default=str)[:5000])
