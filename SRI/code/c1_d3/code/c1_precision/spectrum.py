"""Load published selected-spectrum data and coherent precision replacements.
The raw table and updated snapshot are both included under data/inputs.
This is not a certified complete spectrum. f-normalization is used internally.
"""
import os, json, math, copy
from pathlib import Path
INPUT=Path(os.environ.get('C1_INPUT_DIR',Path(__file__).resolve().parents[2]/'data/inputs'))
LOW={k:(v['value'],v['quoted_error']) for k,v in json.loads((INPUT/'low_inputs.json').read_text())['values'].items()}
S=LOW['S'][0];E=LOW['E'][0]
def get_rows(updated=True):
    rows=json.loads((INPUT/'published_spectrum.json').read_text())
    if updated:
        for p in rows:
            if p['ell']==0 and p['Delta']<1:
                p.update(source='arXiv:2411.15300v2 Table 1 (shared leading inputs)',Delta=S,Delta_error=LOW['S'][1],f=LOW['sse'][0],f_error=LOW['sse'][1])
            if p['ell']==0 and 1<p['Delta']<2:
                p.update(source='arXiv:2411.15300v2 Table 1 (shared leading inputs)',Delta=E,Delta_error=LOW['E'][1],f=LOW['sse'][0],f_error=LOW['sse'][1],h=LOW['eee'][0],h_error=LOW['eee'][1])
            if p['ell']==2 and p['Delta']==3:
                ct=LOW['ct'][0]
                # In Simmons-Duffin convention f_ssT=Delta_s*sqrt(3/(8ct)).
                p.update(source='arXiv:2411.15300v2 Table 1 + stress-tensor Ward identity',f=S*math.sqrt(3/(8*ct)),h=E*math.sqrt(3/(8*ct)),f_error=0.,h_error=0.)
    return rows

def as_upstream(rows):
    even=[];odd=[]
    for p in rows:
        fac=2**(p['ell']/2)
        tup=(p['name'],p['Delta'],p['ell'],p['f']*fac)
        if p['sector']=='even':even.append(tup+(p['h']*fac,))
        else:odd.append(tup)
    return even,odd
