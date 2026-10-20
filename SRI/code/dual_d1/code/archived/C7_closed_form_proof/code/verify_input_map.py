#!/usr/bin/env python3
"""Independent, exact lift of all archived beta inputs to the C7 word target.

Restricted-AST parser; no eval, no numerical periods, no guessed reduction.
This checks the input map, not the underlying raw kink integration.
"""
from pathlib import Path
import ast,sys,time,json,hashlib,argparse
from collections import defaultdict,Counter
from fractions import Fraction as Q
sys.setrecursionlimit(100000)
import verify_C6_input_map as core
root=Path(__file__).resolve().parent
src=root.parent/'data/input_expressions'
oldlift=core.lift

def terms(node):
 stack=[(node,Q(1))]
 while stack:
  n,c=stack.pop()
  if isinstance(n,ast.BinOp) and isinstance(n.op,(ast.Add,ast.Sub)):
   stack.append((n.right,-c if isinstance(n.op,ast.Sub) else c));stack.append((n.left,c))
  elif isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):
   stack.append((n.operand,-c if isinstance(n.op,ast.USub) else c))
  else:yield n,c

def lift(node):
 if isinstance(node,ast.BinOp) and isinstance(node.op,(ast.Add,ast.Sub)):
  out=defaultdict(Q)
  for n,c in terms(node):
   for w,d in lift(n).items():out[w]+=c*d
  return {w:c for w,c in out.items() if c}
 return oldlift(node)
core.lift=lift

def read(name):
 data=(src/name).read_text();depth=0;start=0;pieces=[]
 for i,ch in enumerate(data):
  if ch=='(':depth+=1
  elif ch==')':depth-=1
  elif ch in '+-' and depth==0 and i>start and data[:i].rstrip()[-1] not in '*/':
   pieces.append(data[start:i]);start=i
 pieces.append(data[start:]);assert depth==0
 out=defaultdict(Q)
 for term in pieces:
  for w,c in lift(ast.parse(term.strip(),mode='eval').body).items():out[w]+=c
 return {w:c for w,c in out.items() if c}

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--report',type=Path,default=root.parent/'verification/input_map_report.json');args=parser.parse_args()
 if not __debug__:raise RuntimeError('Do not run with Python -O')
 start=time.time();co={}
 oldnames='a p A E c f q b G k'.split();newnames='V R J L M N alpha beta gamma Phi Psi Omega'.split()
 files={n:n+'_check_symbolic.expr' for n in oldnames};files.update({n:n+'_symbolic.expr' for n in newnames});files.update(Q='Qnew_symbolic.expr',P='Pnew_symbolic.expr',K='Knew_symbolic.expr')
 for n,file in files.items():
  co[n]=read(file);print('INPUT',n,len(co[n]),'seconds',time.time()-start,flush=True)
 def assemble(node):
  if isinstance(node,ast.Name):return co[node.id]
  if isinstance(node,ast.Constant):return {():core.rational(node)}
  if isinstance(node,ast.UnaryOp):return core.scale(assemble(node.operand),Q(-1) if isinstance(node.op,ast.USub) else Q(1))
  if isinstance(node,ast.BinOp):
   if isinstance(node.op,(ast.Add,ast.Sub)):
    out=defaultdict(Q)
    for n,c in terms(node):
     for w,d in assemble(n).items():out[w]+=c*d
    return {w:c for w,c in out.items() if c}
   if isinstance(node.op,ast.Mult):return core.mul(assemble(node.left),assemble(node.right))
   if isinstance(node.op,ast.Div):return core.scale(assemble(node.left),1/core.rational(node.right))
   if isinstance(node.op,ast.Pow):return core.power(assemble(node.left),int(core.rational(node.right)))
  raise ValueError(ast.dump(node))
 D4=assemble(ast.parse((src/'D4_symbolic.expr').read_text(),mode='eval').body)
 assert D4==read('D4_value_symbolic.expr'),'D4 archive differs from its beta inputs'
 known=read('C7_known_additive_symbolic.expr')
 c7=core.add(core.scale(D4,Q(4)),known)
 assert c7==read('C7_symbolic.expr'),'Thermal conversion differs'
 candidate='1798583/32768-90637*Z2/1024+453*Z3/4-16835*Z4/64+1224*Z5-540*Z2*Z3+4335*Z6/8-320*Z3**2'
 candidate=lift(ast.parse(candidate,mode='eval').body)
 diff=core.add(c7,candidate,Q(-1))
 target_path=root.parent/'proof/C7_linear_words.json'
 target={tuple(w):Q(c) for w,c in json.loads(target_path.read_text())}
 assert diff==target,('Word target differs',len(diff),len(target),list(core.add(diff,target,Q(-1)).items())[:3])
 report={'status':'PASS','inputs':len(files),'target_words':len(target),'weight_counts':dict(sorted(Counter(map(len,target)).items())),
 'method':'restricted AST, exact rational shuffle algebra, beta assembly and target comparison',
 'numerical_periods_used':False,'raw_kink_integrals_reintegrated':False,'seconds':time.time()-start,
 'input_sha256':{f:hashlib.sha256((src/f).read_bytes()).hexdigest() for f in list(files.values())+['D4_symbolic.expr','D4_value_symbolic.expr','C7_symbolic.expr','C7_known_additive_symbolic.expr']},
 'target_sha256':hashlib.sha256(target_path.read_bytes()).hexdigest()}
 args.report.write_text(json.dumps(report,indent=2))
 print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
