"""Independent invariant assembly and provenance-aware report generation.
No guessed critical-exponent value is an input to this program.
"""
from pathlib import Path
import json,re,mpmath as m,subprocess,sys,inspect
m.mp.dps=65
ROOT=Path(__file__).resolve().parent;D=ROOT/'data';NOTE=ROOT/'note'
z2=m.zeta(2);z3=m.zeta(3);z4=m.zeta(4);L=m.log(2);li=m.polylog(2,-m.mpf('.5'))
a=-4*z2;c=-16;p=8-2*z2-7*z3-8*L
b=-18-6*z2+m.mpf(28)/3*z3+32*L-12*m.log(3)-4*L*L-8*li
f=32-m.mpf(136)/3*z3-64*L+48*m.log(3)+16*L*L+32*li
P=4*z2+m.mpf(8)/3*z3-2+3*m.log(3)+L*L+2*li
T2=2-2*z2-4*z3;D2=m.mpf(5)/2+2*z2
A=-8-4*z2-2*z3+16*L
I3=m.quad(lambda t:m.log1p(-t)**3/(t*t*(1-t)**2),[0,m.mpf('.25'),m.mpf('.5')])
I12=m.quad(lambda t:m.log(t)*m.log1p(-t)**2/(t*t*(1-t)**2),[0,m.mpf('.25'),m.mpf('.5')])
E=p-4*I3+8*I12
three=json.loads((D/'three_derivatives.json').read_text())
assert abs(A+m.mpf(three['vv']['-2'])/2)<m.mpf('1e-40')
assert abs(E-(4-m.mpf(three['vd']['-2'])))<m.mpf('1e-40')
C30=3-2*z2;C30v=18-14*z2-15*z3-8*L;C30vv=8+m.mpf(three['vv']['-1'])
A3vp=-m.mpf(three['v_at_minus1']['-2'])
K40=P+4*z2-10;L2=10-4*z2;L2d=-60+12*z2+12*z3+8*z4

def moment(name):
 d=json.loads((D/name).read_text())
 return {j-1:(-1)**(j-1)*m.mpf(d['coeff'][str(-j)][0])/m.factorial(j-1) for j in range(1,9)}

def endpoint(n,N):
 for mode in ('e2','analytice'):
  fn=f'm{n}_{int(n%2==0)}_e1_{mode}_N{N}_c0.json'
  if (D/fn).exists():return moment(fn),fn
 raise FileNotFoundError((n,N))

def calculate(n6,ne4,n5,ne3):
 Q4=moment('m4_1_e0_base_N16_c0.json');Q4v=moment('m4_1_e0_v2_N16_c0.json')
 Q4p=moment('m4_1_e0_base_N16_c-1.json');Z4=moment('m4_0_e0_base_N16_c0.json')
 Z4v=moment('m4_0_e0_v2_N16_c0.json');Z4m=moment('m4_0_e0_base_N16_c1.json')
 A5v=moment(f'm5_0_e0_v_N{n5}_c0.json');Q6=moment(f'm6_1_e0_base_N{n6}_c0.json')
 E3v=moment(f'm3_0_e1_ve_N{ne3}_c0.json');E3,e3file=endpoint(3,ne3);EQ4,eqfile=endpoint(4,ne4)
 Q4d={j:m.mpf(0) for j in range(8)}
 for pair,w in [('01',m.mpf('-.5')),('02',m.mpf('.5')),('03',m.mpf('-.25')),('12',m.mpf('-.25'))]:
  mm=moment(f'm4_1_e0_vv_N16_c0_p{pair}.json')
  for j in Q4d:Q4d[j]+=w*mm[j]
 C51v=A5v[1]-Z4v[1]-C30v-14-4*z2-A3vp
 K61=Q6[1]+Z4[0]-P+7-6*z2-Q4p[1]-Z4m[1]
 J3=-2*C30v-26+8*z2;J3v=-2*C30vv+E3v[0]+4*z2-4*z3
 L4=-2*K40-4*Q4v[0]+2*(EQ4[0]-6)
 G=C51v-3*C30v-3*C30*a+16-f+2*J3+2*J3v
 q=-4*(Q4d[1]-4+2*p+L2d)
 k=-4*(K61+2*b-4*K40-4*L2+L4)
 D3=(16*A-32*E-8*G+8*b+c*c+4*f-4*k+32*p-8*q)/64
 C5=2*D3-T2/2+(D2-m.mpf(1)/16)**2/4
 checks={'three_endpoint':E3[0]-(-26+10*z2),'four_current_finite':Q4[0]-(P+4*z2-8),
         'four_current_log':Q4[1]-(-8+4*z2),'four_vacuum_log':Z4[1]-(4-6*z2)}
 assert max(abs(t) for t in checks.values())<m.mpf('1e-7'),checks
 return {'resolution':{'n6':n6,'ne4':ne4,'n5':n5,'ne3':ne3,'n4':16},
 'A':A,'E':E,'G':G,'q_delta':q,'k':k,'D2':D2,'T2':T2,'D3':D3,'C5':C5,
 'Q61':Q6[1],'EQ40':EQ4[0],'E30v':E3v[0],'Q41delta':Q4d[1],'K40v':Q4v[0],'C51v':C51v,'K61':K61,
 'checks':checks,'endpoint_files':[e3file,eqfile]}

def serial(x):
 if isinstance(x,dict):return {k:serial(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [serial(v) for v in x]
 if isinstance(x,m.mpf):return m.nstr(x,40)
 return x
rows=[]
for cfg in [(10,10,12,12),(12,16,16,16),(14,16,16,16),(16,16,16,16)]:
 try:rows.append(calculate(*cfg))
 except FileNotFoundError:pass
if not rows:raise RuntimeError('No complete integral set is available; no coefficient is certified.')
last=dict(rows[-1])
assert len(rows)>=2,'A second complete integration resolution is required.'
assert abs(rows[-1]['C5']-rows[-2]['C5'])<m.mpf('0.0001'),'Resolution change exceeds the reporting tolerance.'
# New independent log checks. Their scripts recompute the coefficients from responses.
for script,out,args in [
 ('verify_algebra.py','final_algebra_checks.txt',[]),
 ('check_three_convergent.py','final_three_checks.txt',[]),
 ('check_new_logs.py','final_tail_log_checks.txt',[]),
 ('check_six_logs.py','final_six_log_checks.txt',['--n6',str(last['resolution']['n6']),'--ne4',str(last['resolution']['ne4'])])]:
 run=subprocess.run([sys.executable,str(ROOT/script),*args],cwd=ROOT,capture_output=True,text=True)
 (ROOT/out).write_text(run.stdout+'\n'+run.stderr)
 if run.returncode:raise RuntimeError(f'{script} failed; see {out}')
rfile=D/f"six_log_check_{last['resolution']['n6']}_{last['resolution']['ne4']}.json"
six=json.loads(rfile.read_text());sixmax=max(abs(m.mpf(v)) for v in six.values())
assert sixmax<m.mpf('0.00001'),six
last['six_log_max_residual']=sixmax;last['convergence']=rows;last['status']='numerically_evaluated_and_internal_checks_passed'
(ROOT/'final_result.json').write_text(json.dumps(serial(last),indent=2))
mac={'MainC':format(float(last['C5']),'.4f'),'MainD':format(float(last['D3']),'.5f')}
for macro,key in [('ValueE','E'),('ValueG','G'),('ValueQ','q_delta'),('ValueK','k'),('ValueQsix','Q61'),('ValueEQfour','EQ40'),('ValueEthreeV','E30v'),('ValueQfourD','Q41delta'),('ValueKfourV','K40v'),('ValueCfiveV','C51v'),('ValueKsix','K61')]:mac[macro]=format(float(last[key]),'.10f')
(NOTE/'results.tex').write_text('\n'.join('\\newcommand{\\'+k+'}{'+v+'}' for k,v in mac.items())+'\n')
lines=[r'\begin{table}[htbp]',r'\centering',r'\caption{Complete invariant assemblies at increasing resolutions. $N_6$ is the six-kink Gaussian order, $N_e$ the four-kink endpoint order, and $N_5$ the five-kink derivative order.}',r'\begin{tabular}{@{}rrrll@{}}\toprule',r'$N_6$ & $N_e$ & $N_5$ & $D_3$ & $C_{5/2}$\\\midrule']
for rr in rows:
 cfg=rr['resolution'];lines.append(f"{cfg['n6']} & {cfg['ne4']} & {cfg['n5']} & {float(rr['D3']):.12f} & {float(rr['C5']):.12f}"+' '+chr(92)*2)
lines += [r'\bottomrule\end{tabular}',r'\end{table}',r'The finest reported six-insertion higher-logarithm check has maximum residual $'+m.nstr(sixmax,5).replace('e-',r'\times10^{-')+(r'}$.' if 'e-' in m.nstr(sixmax,5) else '$.')]
(NOTE/'convergence.tex').write_text('\n'.join(lines)+'\n')
report=['FIVE-HALVES THERMAL COEFFICIENT: VERIFICATION RECORD','', 'This is a numerical result, not a claimed analytic closed form.',
'No expected value of the new exponent is used in the invariant assembly.','']
for rr in rows:report.append('Resolution '+str(rr['resolution'])+'\n D3='+m.nstr(rr['D3'],20)+'\n C5='+m.nstr(rr['C5'],20))
report += ['', 'Final beta coefficients:']+[k+' = '+m.nstr(last[k],24) for k in ['A','E','G','q_delta','k','D3','C5']]
report += ['','Maximum new six-order high-log residual: '+m.nstr(sixmax,12),'','No rigorous interval enclosure or independent bootstrap check is claimed.']
(ROOT/'verification_report.txt').write_text('\n'.join(report)+'\n')
print(json.dumps(serial(last),indent=2))
