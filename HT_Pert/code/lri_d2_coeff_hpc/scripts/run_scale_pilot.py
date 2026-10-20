"""A resource-bounded L22 pilot. Does not fit any continuum coefficients."""
from pathlib import Path
import os,subprocess,sys,json,time
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    dest=ROOT/'results/scale_pilot';dest.mkdir(exist_ok=True)
    env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'src')
    env.setdefault('LRI_COEFF_NATIVE_CACHE',str(Path.home()/'.cache/lri_coeff'))
    cache=Path(os.environ.get('LRI_COEFF_PILOT_CACHE',str(ROOT.parent/'lri_coeff_pilot_cache')))
    for degree,scheme in [(8,'consistent'),(7,'consistent'),(8,'raw')]:
        output=dest/f'{scheme}_L22_d{degree}.json'
        cmd=[sys.executable,'-m','lri_coeff','run','--cutoff','22','--degree',str(degree),'--scheme',scheme,'--threads','4','--max-states','6500000','--memory-gib','3.9','--cache',str(cache),'--checkpoint',str(cache/'checkpoints'),'--resume','--output',str(output)]
        print('START',output.name,flush=True)
        p=subprocess.run(cmd,env=env,timeout=500)
        if p.returncode:raise SystemExit(p.returncode)
        print('FINISHED',output.name,flush=True)
