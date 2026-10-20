#!/usr/bin/env python3
"""450-digit independent point checks of the kernel formulas for both backends (tests/point_checks.cpp), compiled with
the Makefile's flags (common.cxx_command: CXX, CPPFLAGS, OPTFLAGS, CXXFLAGS + required flags). C8(2): every (sector, L)
at L3-L8, the first 2 kernels of the inventory and the 2 heaviest, staged from the packs (the L8 packs must be built:
make inputs-l8). Each point's MP value must agree with the 450-digit value to 1e-280 scaled by the absolute terms,
and the shared binary128 path must equal the unshared reference. The record goes only to --output (A-L7).
Y1 (Stage-6 fix round 2): each backend's tool is bound to the worker it speaks for (--decimal-worker, --gmp-worker;
default bin/c8d2_decimal and bin/c8d2_gmp) through that worker's build record (tools/build_record.py
bound_tool_command): the same make flags and compiler, and for gmp the worker's GMP_PREFIX words and gmp.h, and after
linking the gmp tool must resolve the libgmp whose sha256 the record names, as the worker itself must here. Anything
else is refused before a point is checked; each result carries its binding.
Z1 (Stage-6 fix round 3): each tool is also bound to its worker's code: it is compiled from a read-only snapshot of
src/ and tests/point_checks.cpp, in which the worker is first rebuilt with its build record's command and must come out
byte for byte (tools/build_record.py source_snapshot, reproduce_worker). A stale worker (src/ edited since its build),
an older worker with the same flags and GMP, or a Boost changed through the include environment is refused before
anything is staged; binding.source_binding records the snapshot and the reproduction."""
from pathlib import Path
import argparse,sys,json,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'tests'))
from common import dump,environment_record
from build_record import BindingRefused,bound_tool_command,verify_tool
from validate import inventory,stage,by_cost
BACKENDS=('decimal','gmp')

def tool_build(backend:str,exe:Path,worker:Path)->tuple[list,dict]:
    """The bound compile command of the backend's point-check tool and its binding (Y1); SystemExit when refused."""
    try:return bound_tool_command([ROOT/'tests/point_checks.cpp'],exe,worker,backend,defines=['C8_USE_GMP']if backend=='gmp'else[],
                                  libs=('-lquadmath','-lgmp')if backend=='gmp'else('-lquadmath',))
    except BindingRefused as e:raise SystemExit(f'check_points ({backend}): {e}')

def main(argv=None)->dict:
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,help='write the JSON record here (must not exist)')
    ap.add_argument('--decimal-worker',type=Path,default=ROOT/'bin/c8d2_decimal');ap.add_argument('--gmp-worker',type=Path,default=ROOT/'bin/c8d2_gmp')
    a=ap.parse_args(argv);workers={'decimal':a.decimal_worker,'gmp':a.gmp_worker}
    if a.output and a.output.exists():raise SystemExit(f'{a.output} exists')
    inv=inventory();results=[];selected={}
    with tempfile.TemporaryDirectory(prefix='c8d2_points_')as temp:
        t=Path(temp);builds={b:tool_build(b,t/b,workers[b])for b in BACKENDS}  # Y1: both bound before anything is staged
        paths=[]
        for sector in ('free','power'):
            for L in range(3,9):
                if not (ROOT/f'inputs/packs/{sector}_L{L}.pack').exists():raise SystemExit(f'inputs/packs/{sector}_L{L}.pack is missing (make inputs-l8 INVENTORY=...)')
                rows=inv[sector][str(L)];ids=sorted({r['id']for r in rows[:2]}|set(by_cost(sector,L)[:2]))
                root=stage(t/sector,sector,L,ids);selected[f'{sector}_L{L}']=ids
                paths+=[str(root/f'L{L}/G{g}.txt')for g in ids]
        f=t/'list';f.write_text('\n'.join(paths)+'\n')
        for backend in BACKENDS:
            exe=t/backend;cmd,binding=builds[backend]
            subprocess.run(cmd,check=True)
            try:verify_tool(exe,binding)
            except BindingRefused as e:raise SystemExit(f'check_points ({backend}): {e}')
            cp=subprocess.run([exe,f],capture_output=True,text=True,check=True);r=json.loads(cp.stdout);r['compile_command']=cmd;r['binding']=binding
            results.append(r);print(cp.stdout,flush=True)
    rec={'status':'passed','graphs':selected,'results':results,'environment':environment_record()}
    if a.output:dump(a.output,rec)
    return rec

if __name__=='__main__':main()
