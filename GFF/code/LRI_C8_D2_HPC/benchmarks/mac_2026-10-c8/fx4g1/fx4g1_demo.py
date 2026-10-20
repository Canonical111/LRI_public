#!/usr/bin/env python3
"""Stage-6 fix round 4, G1: the four defects (W1, W2, W3, W22) shown on a package tree, before and after the fix.

  python3 -B benchmarks/mac_2026-10-c8/fx4g1/fx4g1_demo.py --root TREE --output FILE

TREE is a package directory whose tests/test_native_guards.py and tests/test_gmp_binding.py are the fx4-g1 versions
(their stand-ins are used here); for the before-fix run it is a git archive of 945e526 with those two files overlaid.
Each case records whether the defect shows ("defect": true) and what the tree did:
  W1   quad_differential with a stand-in differential tool and sanitizer compiler: the finding's run (--pairs 4
       --min-pairs 4 --ubsan-pairs 4, here also --no-ranges) said "passed"; after the fix --min-pairs is refused and
       the same run without it is a "development run" (exit 3).
  W2   validate's G-BK8 comparison of stand-in decimal and gmp rows in which one mp>0 row of the gmp output has a
       tampered max_abs, a tampered tail_top entry, or a moved tail_argmax without a near tie: accepted before.
  W22  thread_identity's main with stand-in blocks and --backends gmp: labelled "passed" before.
  W3   a worker built in a package copy with CPPFLAGS=-I../boost_rel (the fake toolchain of test_gmp_binding), bound
       from its build directory: refused as "stale" before (the relative word named nothing in the snapshot).
Standard library and the tree's own modules only; nothing is built for real and nothing runs on a cluster."""
from __future__ import annotations
import argparse,contextlib,io,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
from unittest import mock

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();root=a.root.resolve();sys.path[:0]=[str(root/'tools'),str(root/'tests')];os.environ.setdefault('C8_ALLOW_NO_L8','1')
    import test_native_guards as NG
    out={'schema':'c8-d2-fx4g1-demo-1','root':str(root),'cases':{}}
    # ---------------------------------------------------------------- W1
    import quad_differential as QD
    stored=json.loads((root/'benchmarks/symmetry_2026-10-c8/stage5/s5val3.570029.0/quad_differential.json').read_text())
    with tempfile.TemporaryDirectory(prefix='fx4g1_qd_')as td:
        td=Path(td);diff=td/'diff';diff.write_text(f'#!{sys.executable}\n'+NG.FAKE_DIFF);diff.chmod(0o755);cxx=td/'sancxx';cxx.write_text(f'#!{sys.executable}\n'+NG.FAKE_SANCXX);cxx.chmod(0o755)
        def go(*args):
            o=td/f'qd{len(list(td.glob("qd*.json")))}.json'
            with mock.patch.object(QD,'DIFF',diff),mock.patch.object(QD,'RANGES',diff),mock.patch.object(QD,'ranges',lambda a,scratch:stored['ranges']['blocks']),\
                 mock.patch.object(QD,'exe_record',lambda p:{'path':str(p),'sha256':'0'*64,'build':None}),\
                 mock.patch.dict(os.environ,{'CXX':str(cxx),'FAKE_DIFF_TOOL':str(diff)}),mock.patch.object(sys,'argv',['quad_differential.py','--output',str(o),'--scratch',str(td),*args]),\
                 contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO())as err:
                try:code=QD.main()
                except SystemExit as e:return {'exit':e.code,'stderr':err.getvalue().strip().splitlines()[-1:]}
            r=json.loads(o.read_text());return {'exit':code,'status':r['status'][:200]}
        finding=go('--pairs','4','--min-pairs','4','--ubsan-pairs','4','--no-ranges');small=go('--pairs','4','--ubsan-pairs','4','--no-ranges')
    out['cases']['W1']={'defect':finding.get('status')=='passed','finding_run':finding,'without_min_pairs':small}
    # ---------------------------------------------------------------- W2
    import validate as V
    from decimal import Decimal as D
    rows=NG._rows(8,V.task_rows([11,12,13],2,256));dec=NG._out(8,rows,'decimal');mp=next(r['uid']for r in rows if r['mp']>0)
    def tampered(fn):
        g=json.loads(json.dumps(NG._out(8,rows,'gmp')));fn(next(r for r in g['rows']if r['uid']==mp));return g
    w2={}
    for name,fn in (('max_abs',lambda r:r.update(max_abs=str(D(r['max_abs'])*(1+D('1e-20'))))),
                    ('tail_top',lambda r:r['tail_top'].__setitem__(3,str(D(r['tail_top'][3])*2))),
                    ('tail_argmax',lambda r:r.update(tail_argmax=r['begin']+(r['tail_argmax']-r['begin']+1)%(r['end']-r['begin'])))):
        g=tampered(fn)
        def item(td,it,threads,g=g):
            with mock.patch.object(V,'fresh_output',lambda cmd,o,env=None,threads=None:dec if 'decimal'in Path(str(cmd[0])).name else g):return V.bk8_item(td,it,threads)
        with tempfile.TemporaryDirectory()as td:
            try:item(Path(td),{'L':8,'ids':[11,12,13],'points':256,'root':td,'net':td},1);w2[name]='accepted'
            except AssertionError as e:w2[name]=f'refused: {str(e)[:160]}'
    out['cases']['W2']={'defect':any(v=='accepted'for v in w2.values()),'G-BK8 item on an mp>0 row with a tampered':w2}
    # ---------------------------------------------------------------- W22
    import thread_identity as TI
    with tempfile.TemporaryDirectory(prefix='fx4g1_ti_')as td:
        o=Path(td)/'ti.json';args=['--output',str(o),'--backends','gmp']
        with mock.patch.object(TI,'block',NG._ti_block),mock.patch.object(TI,'require',lambda *x,**k:None),contextlib.redirect_stdout(io.StringIO()):
            if hasattr(TI,'main'):code=TI.main(args)
            else:   # before the fix: the command line is the script's __main__ block; run it with the stand-in blocks
                src=Path(TI.__file__).read_text();g=dict(vars(TI),__name__='__main__',block=NG._ti_block,require=lambda *x,**k:None)
                with mock.patch.object(sys,'argv',['thread_identity.py',*args]):exec(compile(src[src.index("if __name__=='__main__':"):],TI.__file__,'exec'),g)
                code=0
        r=json.loads(o.read_text())
    out['cases']['W22']={'defect':r['status']=='passed','backends_gmp_only':{'exit':code,'status':r['status'][:200]}}
    # ---------------------------------------------------------------- W3
    import test_gmp_binding as GB
    import build_record as BR
    with tempfile.TemporaryDirectory(prefix='fx4g1_rel_')as td:
        W=GB.World(Path(td));pkg=W.td/'pkg';shutil.copytree(root/'src',pkg/'src');(W.td/'out').mkdir()
        (W.td/'boost_rel/boost').mkdir(parents=True);(W.td/'boost_rel/boost/version.hpp').write_text(GB.BOOST_H.format(lib='1_77',ver='107700',note=''))
        wk=W.worker('c8d2_gmp_rel',prefix=W.prefix,cwd=pkg,CPPFLAGS='-I../boost_rel')
        try:
            with W.active(CPPFLAGS='-I../boost_rel'),GB.chdir(pkg):
                cmd,b=BR.bound_tool_command([root/'tests/forced_tiers.cpp'],W.td/'out/tool',wk,'gmp',['C8_USE_GMP'],('-lquadmath','-lgmp'))
            res={'reproduced':b['source_binding']['reproduction']['reproduced'],'mirrored':b['source_binding']['reproduction'].get('mirrored')}
        except BR.BindingRefused as e:res={'refused':str(e)[:300]}
    out['cases']['W3']={'defect':'refused'in res,'relative_include_worker_bound_from_its_build_directory':res}
    out['defects']=sorted(k for k,v in out['cases'].items()if v['defect'])
    a.output.write_text(json.dumps(out,indent=1)+'\n');print(json.dumps({'root':str(root),'defects':out['defects']}));return 0

if __name__=='__main__':sys.exit(main())
