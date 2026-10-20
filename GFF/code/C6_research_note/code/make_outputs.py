#!/usr/bin/env python3
"""Generate project-level tables and audit the assembled formulas.

Uses freshly rerun certificates and separately rerun polylogarithmic/Barnes tests.
It never estimates an unknown block by subtracting it from the target C6 value.
Bivariate values are obtained by documented exact transformations; this is not
an independent double-Barnes certificate.
"""
from __future__ import annotations
from fractions import Fraction
from pathlib import Path
import csv,json,sys,platform
import mpmath as mp
import sympy as sp
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs';R=OUT/'rerun'
mp.mp.dps=110

def read(path):return json.loads(path.read_text())
def interval(rec):
 if 'denominator_power_of_two' in rec:
  den=1<<rec['denominator_power_of_two'];return Fraction(int(rec['lower_numerator']),den),Fraction(int(rec['upper_numerator']),den)
 return tuple(Fraction(int(rec[k]['numerator']),int(rec[k]['denominator'])) for k in ('lower','upper'))
def mf(x):return mp.mpf(x.numerator)/x.denominator
def mid(rec):a,b=interval(rec);return mf((a+b)/2)
def num(x,n=65):return mp.nstr(x,n)
def csvwrite(name,fields,rows):
 p=OUT/'tables'/name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def main():
 # Re-create the canonical representations from their rerun/source records.
 canonical=ROOT/'inputs/canonical';canonical.mkdir(parents=True,exist_ok=True)
 combined=read(R/'real_build/generated/results/all_real_representations.json')
 for key,name in [('recommended_nine','recommended_real_nine.json'),('single_family_ten','optional_all_logsine_ten.json')]:
  (canonical/name).write_text(json.dumps(combined[key],indent=2)+'\n')
 for src,dst in [('C6_seventh_unit_slopes_expression.json','complex_nine_reference.json'),('C6_eight_value_alternative_expression.json','optional_complex_eight.json')]:
  (canonical/dst).write_bytes((ROOT/'inputs/source_snapshots'/src).read_bytes())
 cp=read(R/'complete_refined/generated/results/complete_refined.json')
 rp=read(R/'residual_intervals/generated/results.json')
 pl=read(R/'real_checks_90/generated/results/checks_90.json')
 v={k:mid(x) for k,x in cp['values'].items()};res={k:mid(x) for k,x in rp['values'].items()}
 pi=mp.pi;ell=mp.log(2);A=pi+4*ell;Q=mp.gamma(mp.mpf(1)/4)**4/pi;G=mp.catalan
 z3=mp.zeta(3);z5=mp.zeta(5)
 env=dict(pi=pi,ell=ell,A=A,Q=Q,G=G,z3=z3,z5=z5)
 original=read(ROOT/'inputs/source_snapshots/C6_seventh_unit_slopes_expression.json')
 syms={k:sp.Symbol(k) for k in env}
 def ev(s):
  q=sp.sympify(s,locals=syms);return mp.mpf(str(q.evalf(110,subs={syms[k]:sp.Float(str(x),110) for k,x in env.items()})))
 E=ev(original['known_polynomial']);shift=-mp.mpf(476)/3*pi**3*(32*G+9*pi**2);Er=E+shift
 L=mp.mpf(pl['values']['Ls3_pi2']);C=mp.mpf(pl['values']['Cl212_pi2']);D3=mp.mpf(pl['values']['old_D3']);D5=mp.mpf(pl['values']['old_D5'])
 pol=-2176*((32*G+9*pi*pi)*L+128*C)
 oldpol=4352*((32*G+9*pi*pi)*D3-64*D5)
 Cd=96*Q-42*A*A-18*A*pi-1227*pi*pi
 Cs=60*Q-mp.mpf(105)/4*A*A-9*A*pi-mp.mpf(2469)/4*pi*pi
 low=Cd*(v['Bminus']-v['Bplus'])+Cs*(v['Bminus']+v['Bplus'])
 B6=24*v['PB6'];B8=24*v['PZ6']+v['PK6']/3
 W=res['Wzero_n_ge_0'];M7=res['M7'];Pa=res['Pa']
 wheel=-393*pi**3*W;sev=24*pi**3*M7;primitive=96*Pa
 series_result=(E+oldpol+low+B6+B8+wheel+sev+primitive)/2187
 ref=mid(cp['C6_representation'])
 blocks={'known_real':Er,'log_sine_and_Clausen':pol,'lower':low,'sixth':B6,'eighth':B8,'wheel':wheel,'seventh':sev,'primitive':primitive}
 real_result=mp.fsum(blocks.values())/2187
 discrepancies={'real_vs_HPL_polylog_compensation':abs(E+oldpol-Er-pol),'full_series_vs_refined_interval_midpoint':abs(series_result-ref),'real_form_via_series_conversions_vs_refined_midpoint':abs(real_result-ref)}
 rho4=mp.sqrt(Cd*Cd+Cs*Cs);rho8=mp.sqrt(2177203-1028322*mp.sqrt(2))
 fixed={'Ls3_pi_over_2':L,'Cl212_pi_over_2':C,'G4':-low/(4*pi*pi*rho4),'G6':B6/(192*pi*mp.sqrt(290)),'G8':B8/(16*pi**3*rho8),'H_W':pi*pi*W/mp.sqrt(89),'H_star':Pa/(80*pi**3)}
 paths=list((R/'seventh_barnes/generated/results').glob('numerical_40.json'))
 if paths:
  b=read(paths[0]);G7=mp.mpf(b['G7']);H7=mp.mpf(b['H7_unit']);a7=259*A-49*pi;b7=481*A-539*pi;c7=407*A-1127*pi;rho7=mp.sqrt((a7-c7)**2+b7*b7)
  sev_b=24*pi**mp.mpf('1.5')*(rho7*G7+196*pi*mp.sqrt(185)*H7)
  fixed.update(G7=G7,H7_unit=H7)
  barnes_result=(mp.fsum(blocks.values())-sev+sev_b)/2187
  discrepancies['seventh_Barnes_vs_certified_series_r6']=abs(sev_b-sev)
  discrepancies['real_form_with_fresh_Barnes_seventh_vs_refined_midpoint']=abs(barnes_result-ref)
 else: barnes_result=None
 # Exact polynomial audit of the adopted real form.
 p,g,aa,qq,zz3,zz5=sp.symbols('pi G A Q z3 z5');local=dict(pi=p,G=g,A=aa,Q=qq,z3=zz3,z5=zz5)
 Es=sp.sympify(original['known_polynomial'],locals=local)
 Ers=sp.expand(Es-sp.Rational(476,3)*p**3*(32*g+9*p*p))
 exact={'recommended_known_polynomial_has_18_monomials':len(sp.Add.make_args(Ers))==18,'G_pi_cubed_coefficient':Ers.coeff(g,1).coeff(p,3)==-sp.Rational(15776,3),'pi_fifth_coefficient':Ers.coeff(p,5)==-sp.Rational(145153,128)}
 assert all(exact.values())
 out={'scope':'Fresh assembly of supplied analytic identities; no independent upstream graph/RG proof. Real values computed in separate reruns. Bivariate values evaluated via their proved univariate/series equivalents.','precision_digits_for_assembly':110,'source_files':{'complete':'outputs/rerun/complete_refined/generated/results/complete_refined.json','residuals':'outputs/rerun/residual_intervals/generated/results.json','real_basis':'outputs/rerun/real_checks_90/generated/results/checks_90.json'},'known_polynomial_real':str(Ers),'blocks_r6':{k:num(x,90) for k,x in blocks.items()},'fixed_values':{k:num(x,65 if k not in ('G7','H7_unit') else 40) for k,x in fixed.items()},'C6_reassembled_from_series':num(series_result,100),'C6_reassembled_real_form':num(real_result,100),'C6_reassembled_with_Barnes_seventh':num(barnes_result,40) if barnes_result else None,'reference_interval_midpoint':num(ref,110),'absolute_discrepancies':{k:num(x,12) for k,x in discrepancies.items()},'exact_checks':exact,'full_physical_certificate':False}
 (OUT/'reassembly.json').write_text(json.dumps(out,indent=2)+'\n')
 csvwrite('block_contributions.csv',['block','r6_contribution','C6_contribution'],[{'block':k,'r6_contribution':num(x,55),'C6_contribution':num(x/2187,55)} for k,x in blocks.items()])
 csvwrite('fixed_values.csv',['symbol','value','method'],[{'symbol':k,'value':num(x,35),'method':'fresh outer Barnes quadrature' if k in ('G7','H7_unit') else 'fresh log-sine/cosine evaluation' if k in ('Ls3_pi_over_2','Cl212_pi_over_2') else 'exact conversion of freshly rerun interval inputs'} for k,x in fixed.items()])
 cert=[]
 for name in ['smoke','release','refined']:
  d=read(R/f'complete_{name}/generated/results/complete_{name}.json');lo,hi=interval(d['C6_representation'])
  cert.append({'profile':name,'bits':d['parameters']['bits'],'interval_width':num(mf(hi-lo),12),'decimal_lower':d['C6_representation']['decimal_lower'],'decimal_upper':d['C6_representation']['decimal_upper']})
 csvwrite('full_intervals.csv',list(cert[0]),cert)
 # Literal wheel terms and rigorous direct-tail bound, not accelerated values.
 a=mp.mpf(1);delta=pi*pi/3;partial=mp.mpf(0);rows=[];Ns={16,32,64,128,256,512,1024}
 for n in range(1024):
  if n in Ns:
   err=res['Wcentral_n_ge_1']-partial;bd=(8+20*pi/3)/(54*(mp.mpf(n)-mp.mpf(3)/4)**3)
   rows.append({'N':n,'partial_n_ge_1':num(partial,50),'observed_remaining_tail':num(err,18),'proved_direct_tail_bound':num(bd,18)})
  if n: partial+=a**4*(8+5*pi*(4*n+1)*a*a)*delta
  a*=mp.mpf(2*n+1)/(2*n+2);delta-=mp.mpf(4)/(2*n+1)**2-mp.mpf(1)/(n+1)**2
 n=1024;err=res['Wcentral_n_ge_1']-partial;bd=(8+20*pi/3)/(54*(mp.mpf(n)-mp.mpf(3)/4)**3);rows.append({'N':n,'partial_n_ge_1':num(partial,50),'observed_remaining_tail':num(err,18),'proved_direct_tail_bound':num(bd,18)})
 csvwrite('wheel_convergence.csv',list(rows[0]),rows)
 print(json.dumps({'C6':out['C6_reassembled_real_form'],'discrepancies':out['absolute_discrepancies'],'exact_checks':exact},indent=2))
if __name__=='__main__':main()
