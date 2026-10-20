from pathlib import Path
import json,subprocess,sys,concurrent.futures
ROOT=Path(__file__).resolve().parent.parent
m=json.loads((ROOT/'XE_moving_chunks/manifest.json').read_text())
def work(rec):
 p=ROOT/rec['directory']
 with (ROOT/'logs'/('XE_fibrate_'+p.name+'.log')).open('w') as f:subprocess.run([sys.executable,str(ROOT/'engine/fibrate_XE_piece.py'),str(p)],stdout=f,stderr=subprocess.STDOUT,check=True)
 return p.name
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for f in concurrent.futures.as_completed([pool.submit(work,r) for r in m['chunks']]):print('FIBRATED',f.result(),flush=True)
print('ALL_FIBRATION_PIECES_DONE',flush=True)
