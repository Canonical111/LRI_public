#!/usr/bin/env python3
"""tools/members.py (PLAN B "Member access"; F members_test row) on a scratch package's synthetic inputs (tests/c8pkg.py)
and on tests/fixtures/inputs_mini/ (Stage 2b: the 8 smallest real L8 kernels per sector). Mac; seconds.

  * extraction by offset: `members.py extract` writes <sector>/L<L>/G<id>.txt equal byte for byte to the member at its
    inventory offset and length (the synthetic G-file of c8pkg.gfile), for L3 and L8 and several ids;
  * the library form `with extract(...) as root` uses a private 0700 temporary directory, removed on exit, also when the
    body raises;
  * refusals: a one-byte change of a pack member (its inventory sha256), an unknown id, and at L >= 7 a member that differs
    from the inputs' copy of MEMBERS_d3.sha256 (d3/MEMBERS_d3.sha256, pinned in the manifest) or is not listed there, and
    a members list that differs from its manifest pin; each refusal leaves no temporary directory behind (TMPDIR is a
    private directory here);
  * inputs_mini (from Stage 2b; reported as skipped before): `members.py mini --to DIR` materializes it and verify()
    accepts it; every L8 member extracts byte for byte (its inventory and MEMBERS_d3.sha256 hash); a one-byte change of
    a mini L8 pack member is refused; `with mini_inputs()` removes its directory on exit.
Usage: python3 -B tests/members_test.py"""
from __future__ import annotations
import json,os,shutil,stat,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import c8pkg  # noqa: E402

def main()->int:
    td=Path(tempfile.mkdtemp(prefix='c8d3_members_test_'))
    try:
        pkg=c8pkg.make(td);tmp=td/'tmp';tmp.mkdir();inp=pkg/'inputs'
        def run(*args,check=True):
            cp=subprocess.run([sys.executable,'-B',str(pkg/'tools/members.py'),*map(str,args)],capture_output=True,text=True,env=c8pkg.env(TMPDIR=tmp))
            if check and cp.returncode:raise AssertionError(cp.stderr)
            return cp
        for s,L,ids in (('free',3,[0,1]),('power',8,[0,2,4]),('free',8,[5])):
            out=td/f'x_{s}_{L}';run('extract','--sector',s,'--L',L,'--ids',','.join(map(str,ids)),'--inputs',inp,'--to',out)
            for g in ids:assert (out/s/f'L{L}'/f'G{g}.txt').read_bytes()==c8pkg.gfile(s,L,g),(s,L,g)
        assert not list(tmp.iterdir()),'a temporary directory was left behind'
        # the library form: 0700, removed on exit and on an exception
        sys.path.insert(0,str(pkg/'tools'));os.environ['TMPDIR']=str(tmp);tempfile.tempdir=None
        import members
        with members.extract([('free',7,[1,2])],inp)as root:
            assert stat.S_IMODE(root.stat().st_mode)==0o700 and (root/'free/L7/G2.txt').read_bytes()==c8pkg.gfile('free',7,2);keep=root
        assert not keep.exists()
        try:
            with members.extract([('power',5,[1])],inp)as root:keep=root;raise RuntimeError('body failure')
        except RuntimeError:pass
        assert not keep.exists()
        # refusals
        cp=run('extract','--sector','free','--L',3,'--ids','99','--inputs',inp,'--to',td/'u',check=False);assert cp.returncode==1 and 'not in'in cp.stderr
        pack=inp/'packs/power_L8.pack';data=bytearray(pack.read_bytes());inv=json.loads((inp/'inventory.json').read_text());r=inv['power']['8'][2]
        data[r['offset']+3]^=1;pack.unlink();pack.write_bytes(bytes(data))
        cp=run('extract','--sector','power','--L',8,'--ids','2','--inputs',inp,'--to',td/'f',check=False)
        assert cp.returncode==1 and 'differs from its inventory sha256'in cp.stderr,cp.stderr
        assert run('extract','--sector','power','--L',8,'--ids','1','--inputs',inp,'--to',td/'f1').returncode==0   # other members unaffected
        import hashlib
        g1=hashlib.sha256(c8pkg.gfile('free',7,1)).hexdigest();lst=('0'*64+'  L7_free/G1.txt\n'+g1+'  L7_free/G1.txt\n').encode()
        (inp/'d3').mkdir();ml=inp/'d3/MEMBERS_d3.sha256';m=json.loads((inp/'manifest.json').read_text())
        def members_list(rows:str,pin=True):
            ml.write_text(rows)
            if pin:m['sha256']['d3/MEMBERS_d3.sha256']=hashlib.sha256(rows.encode()).hexdigest();(inp/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
        members_list('0'*64+'  L7_free/G1.txt\n')
        cp=run('extract','--sector','free','--L',7,'--ids','1','--inputs',inp,'--to',td/'m',check=False);assert cp.returncode==1 and 'differs from MEMBERS_d3.sha256'in cp.stderr,cp.stderr
        cp=run('extract','--sector','free','--L',7,'--ids','2','--inputs',inp,'--to',td/'m2',check=False);assert cp.returncode==1 and 'not listed there'in cp.stderr,cp.stderr
        members_list(g1+'  L7_free/G1.txt\n')
        assert run('extract','--sector','free','--L',7,'--ids','1','--inputs',inp,'--to',td/'m3').returncode==0
        members_list('0'*64+'  L7_free/G1.txt\n',pin=False)
        cp=run('extract','--sector','free','--L',7,'--ids','1','--inputs',inp,'--to',td/'m4',check=False);assert cp.returncode==1 and 'sha256 differs from'in cp.stderr and 'manifest.json'in cp.stderr,cp.stderr
        assert run('extract','--sector','free','--L',6,'--ids','1','--inputs',inp,'--to',td/'m6').returncode==0   # the member pins bind L >= 7 only
        assert not list(tmp.iterdir()),'a refusal left a temporary directory behind'
        print('PASS members.py: extraction by inventory offset (L3, L7, L8; byte-identical members), a private 0700 temporary directory removed on '
              'exit and on an exception, refusals of an unknown id, a one-byte pack change, an L7 member differing from d3/MEMBERS_d3.sha256 or '
              'not listed there and a members list off its manifest pin, no temporary directory left by any refusal')
        tests=1
        mini=ROOT/'tests/fixtures/inputs_mini'
        if (mini/'manifest.json').exists():
            out=td/'mini';cp=subprocess.run([sys.executable,'-B',str(ROOT/'tools/members.py'),'mini','--to',str(out)],capture_output=True,text=True,env=c8pkg.env(TMPDIR=tmp))
            assert cp.returncode==0,cp.stderr
            mm=json.loads((out/'manifest.json').read_text());inv=json.loads((out/'inventory.json').read_text())
            pins={}
            for line in (out/'d3/MEMBERS_d3.sha256').read_text().splitlines():h,n=line.split('  ',1);pins[n]=h
            def mrun(*args,check=True):
                cp=subprocess.run([sys.executable,'-B',str(ROOT/'tools/members.py'),*map(str,args)],capture_output=True,text=True,env=c8pkg.env(TMPDIR=tmp))
                if check and cp.returncode:raise AssertionError(cp.stderr)
                return cp
            n8=0
            for s in ('free','power'):
                rows=inv[s]['8'];assert len(rows)==8 and [r['id']for r in rows]==mm['selection'][s]
                x=td/f'mx_{s}';mrun('extract','--sector',s,'--L',8,'--ids',','.join(str(r['id'])for r in rows),'--inputs',out,'--to',x)
                pack=(out/f'packs/{s}_L8.pack').read_bytes()
                for r in rows:
                    b=(x/s/'L8'/f'G{r["id"]}.txt').read_bytes()
                    assert b==pack[r['offset']:r['offset']+r['length']] and hashlib.sha256(b).hexdigest()==r['sha256']==pins[f'L8_{s}/G{r["id"]}.txt'];n8+=1
            p=out/'packs/power_L8.pack';data=bytearray(p.read_bytes());r=inv['power']['8'][3];data[r['offset']+5]^=1;p.unlink();p.write_bytes(bytes(data))
            cp=mrun('extract','--sector','power','--L',8,'--ids',str(r['id']),'--inputs',out,'--to',td/'mf',check=False)
            assert cp.returncode==1 and 'differs from its inventory sha256'in cp.stderr,cp.stderr
            code=('import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import members\n'
                  'with members.mini_inputs(base=Path(sys.argv[2]))as d:print(d,(d/"manifest.json").exists())')
            cp=subprocess.run([sys.executable,'-B','-c',code,str(ROOT/'tools'),str(tmp)],capture_output=True,text=True,env=c8pkg.env(TMPDIR=tmp))
            assert cp.returncode==0 and cp.stdout.split()[1]=='True',cp.stderr
            keep=Path(cp.stdout.split()[0])
            assert not keep.exists() and not list(tmp.iterdir()),'inputs_mini left a temporary directory behind'
            print(f'PASS members.py on inputs_mini: materialized and verified, {n8} L8 members extracted byte for byte at their inventory and '
                  'MEMBERS_d3.sha256 hashes, a one-byte change of a mini pack member refused, mini_inputs() cleaned up');tests+=1
        else:print('SKIP inputs_mini: tests/fixtures/inputs_mini/ does not exist yet (Stage 2b makes it)')
        print(json.dumps({'status':'passed','tests':tests}));return 0
    finally:shutil.rmtree(td,ignore_errors=True)
if __name__=='__main__':sys.exit(main())
