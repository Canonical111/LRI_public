import sys,json,random,time
sys.path.insert(0,'/mnt/data/P8_final_run')
import fast_fibration as fast
from full_runner import *
source=Path('/mnt/data/F3_P8_checkpoint/B8_moving4_total/moving.jsonl')
rows=[json.loads(x) for x in source.open()];random.seed(35768);chosen=random.sample(rows,120)
t=time.time();nw=0
for i,(w,tail,ll,c) in enumerate(chosen):
 ww=tuple(rm.parseK(a) for a in w);reference=endpoint_fibrate(ww,5)
 fv=fast.fibrate(tuple(map(fast.letter,w)))
 conv={tuple(K(ar)*GEN[6]+b for ar,b in key):K(mu) for key,mu in fv.items()}
 assert reference==conv,(w,reference,conv)
 nw+=len(conv)
print('PASS 120 actual source words',nw,'fixedword coefficients',time.time()-t,flush=True)
(ROOT/'fast_fibration_check.json').write_text(json.dumps({'actual_source_words':120,'fixed_word_coefficients':nw,'all_exact_equal':True,'seconds':time.time()-t},indent=2))
