from pathlib import Path
import subprocess,time,json,sys,hashlib
from fractions import Fraction as F
sys.path.insert(0,'/mnt/data/P8_final_run');import period_algebra as pa
R=Path('/mnt/data/P8_final_run/F3_six_kink_completion');folder=R/'P8_terminal_fibration';dest=R/'F3_final';dest.mkdir(exist_ok=True)
while len(list((folder/'terminal').glob('b*.report.json')))<256:time.sleep(3)
subprocess.run(['python','-u','/mnt/data/P8_final_run/finalize_terminal_target.py',str(folder),'P8','-1'],check=True)
p8=pa.parse_expr((folder/'P8.expr').read_text());assert p8.get(())==F(-757993),p8.get(())
known=Path('/mnt/data/F3_six_kink_completion/data/F3_known_with_six_kinks.expr')
if not known.exists():known=R/'data/F3_known_with_six_kinks.expr'
out=pa.parse_expr(known.read_text());assert out.get(())==F(-9017996,3);pa.add(out,p8,-4);assert out.get(())==F(77920,3)
fp=dest/'Kv.expr';fp.write_text(pa.dump(out));(dest/'P8.expr').write_text((folder/'P8.expr').read_text())
rep={'complete_full_period_expression':True,'P8_rational_projection':'-757993','Kv_rational_projection':'77920/3','P8_terms':len(p8),'Kv_terms':len(out),'P8_sha256':hashlib.sha256((folder/'P8.expr').read_bytes()).hexdigest(),'known_input':str(known),'known_sha256':hashlib.sha256(known.read_bytes()).hexdigest(),'Kv_sha256':hashlib.sha256(fp.read_bytes()).hexdigest(),'input_bins':256,'no_unknown_period_filled_from_rational_value':True};(dest/'assembly.json').write_text(json.dumps(rep,indent=2))
manifest={'P8':str(dest/'P8.expr'),'Kv':str(fp),'F3_known':str(known)};(dest/'manifest.json').write_text(json.dumps(manifest,indent=2));print('P8_KV_COMPLETE',rep,flush=True)
