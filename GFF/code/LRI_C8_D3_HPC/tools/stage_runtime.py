#!/usr/bin/env python3
"""Stage one planned job index's runtime on node-local scratch (optional; slurm/run_array.sh with C8_STAGE=1; PLAN D.15).

  stage_runtime.py RUN DEST --index I [--whole-pack]

Copies the pinned tools, the planned executable and the small inputs, each verified against the plan and the inputs
manifest, and ONLY the pack members of the index's frozen blocks (each read exactly with common.read_member, os.pread
and no Python buffer, F12; each verified against its inventory sha256), written
at their offsets into a sparse copy of the pack, so `production.py run` from DEST reads them exactly as from the shared
pack. --whole-pack copies the whole pack instead and refuses a pack above 1 GB (an L8 pack is far larger). vendor/
and reference/ are not staged: run never opens them. The staged tools are re-verified by `production.py run`.
"""
from pathlib import Path
import argparse,hashlib,os,shutil,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT,checked,read_member
import production as prod
WHOLE_PACK_LIMIT=10**9

def stage(run:Path,out:Path,index:int,whole_pack:bool=False)->dict:
    run=Path(run).resolve();m,I,mh,_=prod.verify_base(run);j=m['jobs'][index];_,cfg=prod.group_of(run,m,j['group']);out=Path(out).resolve()
    if out.exists()and any(out.iterdir()):raise FileExistsError('Use a new or empty staging directory')
    (out/'tools').mkdir(parents=True,exist_ok=True);(out/'bin').mkdir(exist_ok=True)
    for f in (ROOT/'tools').iterdir():
        if f.is_file()and f.suffix in('.py','.json'):shutil.copy2(f,out/'tools'/f.name)
    for n,h in m['tool_sha256'].items():checked(out/'tools'/n,h)
    exe=ROOT/'bin'/m['executable'];shutil.copy2(exe,out/'bin'/exe.name);checked(out/'bin'/exe.name,m['executable_sha256'])
    try:rel=I.dir.resolve().relative_to(ROOT.resolve())
    except ValueError:raise ValueError(f'the campaign\'s inputs {I.dir} are outside the package: staging needs the package inputs')
    dest=out/rel;dest.mkdir(parents=True,exist_ok=True);shutil.copy2(I.dir/'manifest.json',dest/'manifest.json');checked(dest/'manifest.json',m['inputs_manifest_sha256'])
    for name in prod.SMALL_INPUTS:
        (dest/name).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(I.where(name),dest/name);checked(dest/name,I.sha(name))
    pack=f'packs/{cfg["sector"]}_L{cfg["L"]}.pack';src=I.where(pack);dst=dest/pack;dst.parent.mkdir(parents=True,exist_ok=True);size=src.stat().st_size
    rows=prod.job_rows(run,j);graphs=sorted({r[2]for r in rows});inv={r['id']:r for r in prod.load_inventory(I)[cfg['sector']][str(cfg['L'])]}
    if whole_pack:
        if size>WHOLE_PACK_LIMIT:raise ValueError(f'{pack} is {size:,} bytes > 1 GB: a whole-pack copy is refused (D.15); stage the members (default)')
        shutil.copy2(src,dst);checked(dst,I.sha(pack));members=len(inv)
    else:
        fd=os.open(src,os.O_RDONLY)
        try:
            with dst.open('wb')as fo:
                fo.truncate(size)
                for g in graphs:
                    r=inv[g];data=read_member(fd,r['offset'],r['length'])
                    if len(data)!=r['length']or hashlib.sha256(data).hexdigest()!=r['sha256']:raise ValueError(f'{pack} member G{g} does not match its inventory sha256')
                    fo.seek(r['offset']);fo.write(data)
        finally:os.close(fd)
        members=len(graphs)
    return {'destination':str(out),'index':index,'pack':pack,'pack_bytes':size,'members_staged':members,'whole_pack':whole_pack}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);p.add_argument('run',type=Path);p.add_argument('destination',type=Path)
    p.add_argument('--index',type=int,required=True);p.add_argument('--whole-pack',action='store_true');a=p.parse_args()
    try:r=stage(a.run,a.destination,a.index,a.whole_pack)
    except (ValueError,FileExistsError,OSError)as e:print(f'stage_runtime: {e}',file=sys.stderr);sys.exit(1)
    print(r['destination'])
