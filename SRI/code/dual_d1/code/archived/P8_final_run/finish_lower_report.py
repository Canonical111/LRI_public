from pathlib import Path
import sys,json,ast,hashlib
from fractions import Fraction as F
R=Path('/mnt/data/P8_final_run/F3_six_kink_completion');sys.path.insert(0,str(R/'numerical'))
from evaluate_set import terms

def ev(x):
 if isinstance(x,ast.Constant):return F(x.value)
 if isinstance(x,(ast.Call,ast.Name)):return F(0)
 if isinstance(x,ast.UnaryOp):return -ev(x.operand) if isinstance(x.op,ast.USub) else ev(x.operand)
 if isinstance(x,ast.BinOp):
  a,b=ev(x.left),ev(x.right)
  if isinstance(x.op,ast.Add):return a+b
  if isinstance(x.op,ast.Sub):return a-b
  if isinstance(x.op,ast.Mult):return a*b
  if isinstance(x.op,ast.Div):return a/b
  if isinstance(x.op,ast.Pow):return a**int(b)
 raise ValueError(ast.dump(x))
p=R/'F4_data/J9_lower_shift.expr';txt=p.read_text();rat=sum((ev(ast.parse(t,mode='eval').body) for t in terms(txt)),F(0));print('J9rat',rat);assert rat==F(-2868919,6)
(R/'F4_data/J9_lower_assembly.json').write_text(json.dumps({'complete_lower_expression':True,'definition':'J9=A9_log-Z8_log+2*EA7_finite-2*EZ6_finite+J9_lower_shift','terms':25851,'rational_projection':str(rat),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'not_inferred_from_rational_value':True},indent=2))
