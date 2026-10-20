#!/usr/bin/env python3
"""Stage one planned job index's runtime on node-local scratch (optional; slurm/run_array.sh with C8_STAGE=1).

  stage_runtime.py RUN DEST --index I [--whole-pack]

Copies the pinned tools, the planned executable and the small inputs, each verified against the plan and the inputs
manifest, and ONLY the pack members of the index's blocks (each read exactly with production.read_member, os.pread and
no Python buffer, so nothing of the shared pack beyond the members is read, F12; each verified against its inventory
sha256), written at their offsets into a sparse copy of the pack, so `production.py run` from DEST reads them exactly
as from the shared pack. --whole-pack copies the whole pack instead and refuses a pack above 1 GB. vendor/ and
reference/ are not staged (run never opens them). The staged tools are re-verified by `production.py run`.
The index's task file is streamed one block at a time (production.iter_job_blocks; Stage-6 fix round 4, W9): staging
holds one block of rows and the index's graph set, whatever the index's size.
"""
from pathlib import Path
import argparse,hashlib,os,shutil,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT,checked,digest
import production as prod
WHOLE_PACK_LIMIT=10**9

def stage(run:Path,out:Path,index:int,whole_pack:bool=False)->dict:
    run=run.resolve();m,I,mh,_=prod.verify_base(run);j=m['jobs'][index];_,cfg=prod.group_of(run,m,j['group']);out=out.resolve()
    if out.exists()and any(out.iterdir()):raise FileExistsError('Use a new or empty staging directory')
    (out/'tools').mkdir(parents=True,exist_ok=True);(out/'bin').mkdir(exist_ok=True)
    for f in (ROOT/'tools').iterdir():
        if f.is_file()and f.suffix in('.py','.json'):shutil.copy2(f,out/'tools'/f.name)
    for n,h in m['tool_sha256'].items():checked(out/'tools'/n,h)
    exe=ROOT/'bin'/m['executable'];shutil.copy2(exe,out/'bin'/exe.name);checked(out/'bin'/exe.name,m['executable_sha256'])
    dest_inputs=out/m['inputs'];dest_inputs.mkdir(parents=True,exist_ok=True);shutil.copy2(I.dir/'manifest.json',dest_inputs/'manifest.json')
    checked(dest_inputs/'manifest.json',m['inputs_manifest_sha256'])
    def staged(name):
        src=I.where(name);rel=src.relative_to(ROOT);dst=out/rel;dst.parent.mkdir(parents=True,exist_ok=True);return src,dst
    for name in prod.SMALL_INPUTS:
        src,dst=staged(name);shutil.copy2(src,dst);checked(dst,I.sha(name))
    pack=f'packs/{cfg["sector"]}_L{cfg["L"]}.pack';src,dst=staged(pack);size=src.stat().st_size
    # W9 (S6-C-R4-03): the index's graphs from its task file streamed block by block (production.iter_job_blocks: checked
    # against the manifest pin before the first block and hashed again while parsed, raising before the iteration
    # ends), so staging holds one block of rows and the graph set, never the index's rows; nothing is copied before the
    # whole file has verified
    graphs=set()
    for block in prod.iter_job_blocks(run,j,m['checkpoint_tasks']):graphs.update(r[2]for r in block)
    graphs=sorted(graphs);inv={r['id']:r for r in prod.read_verified(I.where('inventory.json'),I.sha('inventory.json'))[cfg['sector']][str(cfg['L'])]}  # verified bytes
    if whole_pack:
        if size>WHOLE_PACK_LIMIT:raise ValueError(f'{pack} is {size:,} bytes > 1 GB: a whole-pack copy is refused; stage the members (default)')
        shutil.copy2(src,dst);checked(dst,I.sha(pack));members=len(inv)
    else:
        fd=os.open(src,os.O_RDONLY)
        try:
            with dst.open('wb')as fo:
                fo.truncate(size)
                for g in graphs:
                    r=inv[g];data=prod.read_member(fd,r['offset'],r['length'])
                    if len(data)!=r['length']or hashlib.sha256(data).hexdigest()!=r['sha256']:raise ValueError(f'{pack} member G{g} does not match its inventory sha256')
                    fo.seek(r['offset']);fo.write(data)
        finally:os.close(fd)
        members=len(graphs)
    return {'destination':str(out),'index':index,'pack':pack,'pack_bytes':size,'members_staged':members,'whole_pack':whole_pack}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);p.add_argument('run',type=Path);p.add_argument('destination',type=Path)
    p.add_argument('--index',type=int,required=True);p.add_argument('--whole-pack',action='store_true');a=p.parse_args()
    r=stage(a.run,a.destination,a.index,a.whole_pack);print(r['destination'])
