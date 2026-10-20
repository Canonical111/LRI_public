"""Reassemble C6 using freshly recomputed separate five-loop poles."""
from assemble6 import *
read=lambda f:json.loads((R/f).read_text(),parse_float=str)
h=read('full_H_L5_N16_0_10000.json')['values'];j=read('full_J_L5_N16_0_10000.json')['values'];out={}
for ix,cut in enumerate(['maxgap','span']):
 data=inputs(cut,28);ref=assemble(data)
 for k in range(5):
  H=mp.mpf(h[5*ix+k]);J=mp.mpf(j[6*ix+k]);power=str(k-5)
  data['5'][0][power]=mp.nstr(8*H-3*J,70);data['5'][1][power]=mp.nstr(3*H-J,70)
 new=assemble(data)
 out[cut]={'change_in_C6_lower':mp.nstr(new['C'][-1]-ref['C'][-1],40),'change_in_C5':mp.nstr(new['C'][-2]-ref['C'][-2],40),'scope':'New N16 five-loop integrals are a degree control, not inputs to the main final estimate.'}
(R/'five_loop_input_control.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
