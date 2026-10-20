"""Run tests on the actual compute node, then issue a checksummed receipt."""
from pathlib import Path
import argparse,json,os,subprocess,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from lri_spin import Config
from lri_spin.io import identity,source_hash,write_record
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
from lri_spin.campaign import refuse_campaign_destination
refuse_campaign_destination(a.output)
env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1')
r=subprocess.run([sys.executable,'-m','pytest','-q',str(root/'tests')],cwd=root,env=env)
if r.returncode:raise SystemExit(r.returncode)
idn=identity(Config(),None,'receipt')
write_record(a.output,idn,{'passed':True,'source_sha256':source_hash(),'runtime':idn['runtime'],
    'meaning':'local numerical/integrity regression suite passed; not physical continuum validation'})
print('Validation receipt:',a.output)
