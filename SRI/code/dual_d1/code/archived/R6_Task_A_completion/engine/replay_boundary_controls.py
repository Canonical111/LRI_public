"""Re-evaluate complete saved control boundary sources with exact Fractions.
This does not read their recorded face sums as numerical inputs.
"""
from pathlib import Path
from fractions import Fraction as Q
import json,hashlib,time
import boundary_residue as br
import terminal_projection as tp
from hyperlog_core import K,e
ROOT=Path(__file__).resolve().parent.parent

def main():
    answers=[];start=time.time()
    for n,deriv,expected in [(4,'vd',Q(712)),(6,'base',Q(-829,2)),(6,'v',Q(-5140)),(6,'d',Q(20303,2))]:
        face_sums=[];nvar=n-2
        for face in range(1,n//2+1):
            source=ROOT/'boundary'/f'B{n}_{deriv}_f{face}_stage{nvar-1}.jsonl'
            items=br.rr.load(source);total=Q(0)
            for (words,logs),co in items:
                assert not logs and not any(words[:-1])
                word=tuple(tp.field_letter(a,nvar,e) for a in words[-1])
                total+=tp.apply_field(co,word,0,n-1,((0,0),),qindex=nvar)[0]
            face_sums.append(total);br.rr.clear();tp.clear_caches()
        answer=-sum(a*(1 if i==len(face_sums)-1 else 2) for i,a in enumerate(face_sums))
        assert answer==expected,(n,deriv,answer,expected)
        answers.append({'n':n,'derivative':deriv,'face_constants':list(map(str,face_sums)),'residue':str(answer),'archived_control_residue':str(expected),'exact_equal':True})
        print('CONTROL',n,deriv,answer,flush=True)
    result={'method':'fresh endpoint evaluation of every saved complete control boundary','checks':answers,'seconds':time.time()-start}
    (ROOT/'replayed_boundary_controls.json').write_text(json.dumps(result,indent=2))
if __name__=='__main__':main()
