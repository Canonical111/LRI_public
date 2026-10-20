from pathlib import Path
import json,time
R=Path('/mnt/data/P8_final_run/F3_six_kink_completion');mf=R/'F3_final/manifest.json'
while not mf.exists():time.sleep(2)
d=json.loads(mf.read_text());base=Path('/mnt/data/P8_final_run/old_C7/C7_completion/engine')
mp={'a':'a_check','p':'p_check','A':'A_check','E':'E_check','c':'c_check','f':'f_check','q':'q_check','b':'b_check','G':'G_check','k':'k_check','Q':'Qnew','P':'Pnew','K':'Knew'}
for a in ['a','p','A','E','c','f','q','b','G','k','V','R','J','L','M','N','alpha','beta','gamma','Phi','Psi','Omega','Q','P','K']:
 d['beta_'+a]=str(base/(mp.get(a,a)+'_symbolic.expr'))
d['F1_known']=str(Path('/mnt/data/F1c_completion/data/Nd_known_part.expr'))
(R/'F3_final/full_manifest.json').write_text(json.dumps(d,indent=2))
