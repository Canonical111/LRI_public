from fractions import Fraction
from pathlib import Path
import json
import mpmath as realmp
import laurent_assembly as a
class RationalArithmetic:
 mpf=Fraction
 @staticmethod
 def fsum(xs):return sum(xs,Fraction(0))
a.mp=RationalArithmetic
R=Path(__file__).parent
raw=json.load(open(a.SOURCE),parse_float=str)
out=[]
for rec in raw[-2:]:
 v=a.assemble(rec['amplitudes']);c=v['C'][-1]
 data=json.loads(json.dumps(rec['amplitudes']));data['5'][0]['-1']=str(Fraction(data['5'][0]['-1'])+1)
 da=a.assemble(data)['C'][-1]-c
 data=json.loads(json.dumps(rec['amplitudes']));data['5'][1]['-1']=str(Fraction(data['5'][1]['-1'])+1)
 db=a.assemble(data)['C'][-1]-c
 assert da==Fraction(-5,729) and db==Fraction(5,243)
 realmp.mp.dps=90
 out.append({'cutoff':rec['cutoff'],'C5_exact_rational':str(c),'C5_decimal':realmp.nstr(realmp.mpf(c.numerator)/c.denominator,85),'dC5_dA5_simple':str(da),'dC5_dB5_simple':str(db),'rational_identity_checks_passed':True})
(R/'records/exact_decimal_audit.json').write_text(json.dumps(out,indent=2))
for v in out:print(v['cutoff'],v['C5_decimal'])
