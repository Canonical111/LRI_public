#!/usr/bin/env python3
"""Build the immutable Expanse release tarball for one git commit (run locally, in the repo).

The tarball holds `git archive <commit>` plus two generated members:
  GIT_SHA         the full commit id
  RELEASE.sha256  sha256 of every other member ("<hex>  <path>", sorted), excluding itself
Jobs verify RELEASE.sha256 after node-local extraction; its own sha256 is the release
fingerprint bound into receipts and lane manifests. Output: <out>/<commit12>.tar and
<commit12>.tar.sha256. Deterministic: same commit, same bytes.
"""
import argparse,hashlib,io,subprocess,sys,tarfile
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--commit',default='HEAD');p.add_argument('--out',required=True)
    a=p.parse_args()
    repo=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],text=True).strip())
    sha=subprocess.check_output(['git','-C',str(repo),'rev-parse',a.commit],text=True).strip()
    when=int(subprocess.check_output(['git','-C',str(repo),'show','-s','--format=%ct',sha],text=True))
    raw=subprocess.check_output(['git','-C',str(repo),'archive','--format=tar',sha])
    src=tarfile.open(fileobj=io.BytesIO(raw))
    members=[];listing=[]
    for m in src.getmembers():
        if m.name in ('GIT_SHA','RELEASE.sha256'):sys.exit(f'{m.name} must not be tracked')
        data=src.extractfile(m).read() if m.isfile() else None
        if data is not None:listing.append(f'{hashlib.sha256(data).hexdigest()}  {m.name}')
        members.append((m,data))
    gitsha=(sha+'\n').encode()
    listing.append(f'{hashlib.sha256(gitsha).hexdigest()}  GIT_SHA')
    release=('\n'.join(sorted(listing,key=lambda s:s.split('  ',1)[1]))+'\n').encode()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    tar=out/f'{sha[:12]}.tar';buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w',format=tarfile.PAX_FORMAT) as t:
        for m,data in members:
            m.mtime=when;m.uid=m.gid=0;m.uname=m.gname=''
            t.addfile(m,io.BytesIO(data) if data is not None else None)
        for name,data in (('GIT_SHA',gitsha),('RELEASE.sha256',release)):
            ti=tarfile.TarInfo(name);ti.size=len(data);ti.mtime=when;ti.mode=0o644
            t.addfile(ti,io.BytesIO(data))
    tar.write_bytes(buf.getvalue())
    h=hashlib.sha256(buf.getvalue()).hexdigest()
    (out/f'{sha[:12]}.tar.sha256').write_text(f'{h}  {tar.name}\n')
    print(f'{tar}  sha256 {h}  release fingerprint {hashlib.sha256(release).hexdigest()}  ({len(listing)} files)')

if __name__=='__main__':main()
