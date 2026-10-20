from pathlib import Path
import copy, json, hashlib
import sympy as s
ROOT=Path(__file__).resolve().parent
old=json.loads((ROOT/'inputs/C6_seventh_unit_slopes_expression.json').read_text())
p,g,A,Q,z3,z5=s.symbols('pi G A Q z3 z5',real=True)
L,C,U,V=s.symbols('Ls3_pi2 Cl212_pi2 Ls23_pi2 Ls41_pi2',real=True)
d3,d5=s.symbols('D3 D5')
loc={'pi':p,'G':g,'A':A,'Q':Q,'z3':z3,'z5':z5,'D3':d3,'D5':d5}
expr=s.sympify(old['formula_C6'],locals=loc,rational=True)
E=s.sympify(old['known_polynomial'],locals=loc,rational=True)
D3=-L/2-7*p**3/192
Cexpr=-g*L+s.Rational(3,2)*U+V/2-s.Rational(13,192)*g*p**3+s.Rational(451,3072)*p*p*z3+s.Rational(7635,2048)*z5
shiftR=-s.Rational(476,3)*p**3*(32*g+9*p*p)
shiftL=s.Rational(41344,3)*g*p**3-1428*p**5-s.Rational(122672,3)*p*p*z3-1038360*z5
unaffected=['univariate_meijer_g_terms','bivariate_fox_H_terms','source_correction_unchanged','lower_parameters','eighth_parameters','primitive_compression_parameters','wheel_reduction','seventh_reduction']
outputs={}
checks={}
for mode, newexpr, newE, shift in [
 ('recommended_nine',expr.subs({d3:D3,d5:C}),E+shiftR,shiftR),
 ('single_family_ten',expr.subs({d3:D3,d5:Cexpr}),E+shiftL,shiftL),
]:
 out=copy.deepcopy(old)
 out['title']='C6(1): '+('nine fixed real-valued values, no Re/Im in coefficient' if mode=='recommended_nine' else 'ten fixed real-valued values, polylog sector expressed only in log-sine functions')
 out['scope']='A real-valued rewrite, not an arithmetic-independence or minimality theorem. The nine-value option uses a standard multiple Clausen function: its replacement of D5 is a change of real-valued function convention, not a new evaluation. The ten-value option expresses that Clausen value in two depth-two iterated log-sine values plus Ls3 and known constants. Neither replaces a residual by a fitted constant. The seven other fixed values, wheel zero-index convention and source correction are unchanged; all upstream graph/RG identifications are inherited.'
 out['formula_C6']=str(s.expand(newexpr))
 out['known_polynomial']=str(s.expand(newE))
 out['known_polynomial_change_this_assembly']=str(s.expand(shift))
 out['polylogarithm_values']=[]
 names=[('Ls3_pi2','log-sine',[3],[0])]
 if mode=='recommended_nine': names += [('Cl212_pi2','multiple Clausen',[2,1,2],None)]
 else:names += [('Ls23_pi2','iterated log-sine',[2,3],[0,0]),('Ls41_pi2','iterated log-sine',[4,1],[0,0])]
 out['real_special_values']=[{'id':n,'family':f,'indices':k,'log_sine_superscripts':l,'argument':'pi/2','convention':'Borwein-Straub descending MPL indices for Cl; Umezawa increasing integration variables for iterated Ls'} for n,f,k,l in names]
 out['counts']['polylogarithm_values']=0
 out['counts']['real_log_sine_values']=1 if mode=='recommended_nine' else 3
 out['counts']['multiple_Clausen_values']=1 if mode=='recommended_nine' else 0
 out['counts']['total_fixed_function_values']=9 if mode=='recommended_nine' else 10
 out['counts']['explicit_Re_Im_operations']=0
 out['counts']['known_polynomial_monomials']=len(s.Add.make_args(s.expand(newE)))
 out['counts']['arithmetic_independence_claimed']=False
 out['formula_r6_block']=('E_real-2176*((32*G+9*pi**2)*Ls3_pi2+128*Cl212_pi2)' if mode=='recommended_nine' else 'E_logsine-6528*(3*pi**2-32*G)*Ls3_pi2-139264*(3*Ls23_pi2+Ls41_pi2)')+'+Blow+B6+B8-393*pi*sqrt(89)*Hw+24*pi**(3/2)*(rho7*G7+196*pi*sqrt(185)*H7unit)+7680*pi**3*Hstar'
 out['provenance_this_step']={'input':'C6_seventh_unit_slopes_expression.json','input_sha256':hashlib.sha256((ROOT/'inputs/C6_seventh_unit_slopes_expression.json').read_bytes()).hexdigest(),'new_all_sector_evaluation':False,'new_interval_certificate':False,'definition_sources':['https://arxiv.org/abs/1103.4298','https://arxiv.org/abs/1912.07201']}
 out['new_all_sector_evaluation']=False;out['new_interval_certificate']=False
 for key in unaffected:checks[mode+': preserved '+key]=old[key]==out[key]
 checks[mode+': no old projections or values']=not ({d3,d5}&s.expand(newexpr).free_symbols)
 checks[mode+': polynomial 18 monomials']=out['counts']['known_polynomial_monomials']==18
 (ROOT/'results'/f'{mode}_expression.json').write_text(json.dumps(out,indent=2)+'\n')
 outputs[mode]=out
assert all(checks.values()),checks
(ROOT/'results'/'preservation_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
(ROOT/'results'/'all_real_representations.json').write_text(json.dumps(outputs,indent=2)+'\n')
print('Preservation checks:',len(checks), 'all passed')
