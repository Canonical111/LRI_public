from pathlib import Path
import json,sys,subprocess,time
W=Path(__file__).resolve().parents[1]
OLD=W.parent/'LRI_C7_d2_progress'
L=int(sys.argv[1]);points=int(sys.argv[2]);rep=int(sys.argv[3]);tag=sys.argv[4]if len(sys.argv)>4 else'pilot'
inventory=json.load(open(W/f'inputs/L{L}/inventory.json'))
sel=[g for g in inventory if g['status']=='finite-kernel' and (L<7 or g['mass_numerator']!=4)]
f=W/f'records/{tag}_L{L}.tasks'
with f.open('w')as out:
 out.write(f'C7D2TASKS1 {L} {len(sel)*rep}\n');uid=0
 for r in range(rep):
  for g in sel:out.write(f'{uid} {r} {g["id"]} 0 {points} {points}\n');uid+=1
cmd=[str(W/'code/integrate'),str(W/'inputs'),str(OLD/'inputs/gamma_d2_7.txt'),str(OLD/f'inputs/a_L{L}.net'),str(f),str(W/f'records/{tag}_L{L}.json'),'19421725','0','.8','4','compensated','-']
with open(W/f'records/{tag}_L{L}.log','w') as log:
 p=subprocess.Popen(cmd,stdout=log,stderr=log,start_new_session=True)
 (W/f'records/{tag}_L{L}.pid').write_text(str(p.pid));print(p.pid, 'graphs',len(sel),'points',points*rep*len(sel),flush=True)
