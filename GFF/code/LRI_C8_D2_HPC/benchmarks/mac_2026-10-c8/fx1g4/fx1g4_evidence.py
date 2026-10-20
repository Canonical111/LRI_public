#!/usr/bin/env python3
"""Stage-6 fix round 1, group G4 (X17-X20): the before/after evidence, from a git checkout of the package.

1. Every self-test probe of the current tests/ast_scan.py, counted by the current analyser and by the one at BASE
   (e88bf4f, the inspected tree): a probe that the old analyser miscounts is a test that fails before the fix.
2. The delivery-verifier test at BASE and the current one, each run against tools/verify_delivery.py and against
   mutants of its safe_file with path-safety checks removed (whole guards, then one sub-check at a time): the BASE
   test passes the mutant without the path-syntax guard (S6E-04); the current test fails every mutant.
Usage: python3 -B benchmarks/mac_2026-10-c8/fx1g4/fx1g4_evidence.py [--output FILE]"""
from __future__ import annotations
import argparse,ast,importlib.util,json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
BASE='e88bf4f'

def at_base(rel:str)->str:
    return subprocess.run(['git','-C',str(ROOT),'show',f'{BASE}:{rel}'],capture_output=True,text=True,check=True).stdout

def module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def probes(tmp:Path)->dict:
    old_path=tmp/'ast_scan_base.py';old_path.write_text(at_base('tests/ast_scan.py'))
    new,old=module(ROOT/'tests/ast_scan.py','ast_scan_now'),module(old_path,'ast_scan_base')
    table={}
    # the current self-test's probes, read from its source (a dict literal assigned to `probes`)
    fn=next(n for n in ast.walk(ast.parse((ROOT/'tests/ast_scan.py').read_text()))if isinstance(n,ast.FunctionDef)and n.name=='selftest')
    lit=next(n.value for n in ast.walk(fn)if isinstance(n,ast.Assign)and isinstance(n.targets[0],ast.Name)and n.targets[0].id=='probes')
    for name,(src,want) in ast.literal_eval(lit).items():
        t=ast.parse(src)
        got_new=len(new.unreachable(t,name)+new.unbound(t,name));got_old=len(old.unreachable(t,name)+old.unbound(t,name))
        table[name]=dict(expected=want,current=got_new,base=got_old)
    return dict(probes=table,current_failures=[k for k,v in table.items()if v['current']!=v['expected']],
                base_failures=[k for k,v in table.items()if v['base']!=v['expected']])

def mutants(tmp:Path)->dict:
    src=(ROOT/'tools/verify_delivery.py').read_text()
    g1="if not name or p.is_absolute() or '..' in p.parts or '\\\\' in name or p.as_posix() != name:"
    g2="if target.is_symlink() or not target.resolve().is_relative_to(root):"
    if g1 not in src or g2 not in src:raise SystemExit('tools/verify_delivery.py safe_file changed: update the mutants')
    muts={'unmodified':src,'no_path_syntax_guard':src.replace(g1,'if False:'),'no_path_guards':src.replace(g1,'if False:').replace(g2,'if False:')}
    for drop in ('p.is_absolute() or ',"'..' in p.parts or ","'\\\\' in name or ",' or p.as_posix() != name'):
        muts[f'drop {drop.strip()}']=src.replace(g1,g1.replace(drop,'',1))
    tests={'base_test':at_base('tests/test_delivery_verifier.py'),'current_test':(ROOT/'tests/test_delivery_verifier.py').read_text()}
    out={}
    for i,(m,code) in enumerate(muts.items()):
        for tn,t in tests.items():
            d=tmp/f'mut{i}_{tn}';(d/'tools').mkdir(parents=True);(d/'tests').mkdir()
            (d/'tools/verify_delivery.py').write_text(code);(d/'tests/test_delivery_verifier.py').write_text(t)
            cp=subprocess.run([sys.executable,'-B',str(d/'tests/test_delivery_verifier.py')],capture_output=True,text=True)
            err=(cp.stderr.strip().splitlines()or[''])[-1]
            out[f'{m} | {tn}']=dict(exit=cp.returncode,failed_case=(err.split("'")[1]if err.startswith('AssertionError: (')else err)[:120])
    return out

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('--output',type=Path);a=ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='c8d2_fx1g4_') as t:
        rec=dict(schema='c8-d2-fx1g4-evidence-1',base=BASE,python=sys.version.split()[0],ast_scan=probes(Path(t)),delivery_mutants=mutants(Path(t)))
    d=rec['delivery_mutants']
    ok=(not rec['ast_scan']['current_failures']and d['unmodified | base_test']['exit']==0 and d['unmodified | current_test']['exit']==0
        and d['no_path_syntax_guard | base_test']['exit']==0 and all(v['exit']!=0 for k,v in d.items()if k.endswith('current_test')and not k.startswith('unmodified')))
    rec['passed']=ok
    s=json.dumps(rec,indent=1)+'\n'
    if a.output:a.output.write_text(s)
    print(s,end='')
    return 0 if ok else 1

if __name__=='__main__':sys.exit(main())
