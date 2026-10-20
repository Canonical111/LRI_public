#!/usr/bin/env python3
"""Assemble fresh C2 outputs, with archived reference data kept separate."""
from pathlib import Path
import argparse,csv,json
import mpmath as mp
ROOT=Path(__file__).resolve().parents[1]

def load(p):return json.loads(p.read_text())
def num(x):return mp.mpf(str(x))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,default=ROOT/'inputs/calculation.json');a=p.parse_args()
 cfg=load(a.config);dps=cfg['working_dps'];adps=cfg['independent_working_dps'];mp.mp.dps=max(dps,adps)+20
 formula=load(ROOT/f'outputs/raw/three_4f3_{dps}dps.json');bounds=load(ROOT/'outputs/raw/certificate_boundaries.json')
 ren=load(ROOT/f'outputs/raw/renormalization_{dps}dps.json');contacts=load(ROOT/f'outputs/raw/source_contacts_{dps}dps.json')
 audit=load(ROOT/f'outputs/raw/independent_c2_{adps}dps.json');conv=load(ROOT/'outputs/raw/convergence.json')
 bridges=load(ROOT/'outputs/raw/analytic_bridges.json')
 reference=load(ROOT/'inputs/reference/three_4f3_100dps.json')
 assert bounds['all_exact_residuals_zero']
 assert all(r['residual']=='0' and r['H_at_zero']=='0' for r in formula['symbolic_certificates'].values())
 assert ren['symbolic']['Mobius_Jacobian_residual']=='0' and ren['symbolic']['Abel_linear_complex_determinant']=='2'
 assert audit['all_implemented_assertions_passed']
 bridge_exact=bridges['exact'];bridge_numeric=bridges['numerical']
 assert bridge_exact['boundary_differential_certificate_residuals']==['0','0','0']
 assert bridge_exact['Landen_numerator_residuals']==['0','0','0']
 assert all(bridge_exact[k]=='0' for k in ['symmetric_period_factorization_residual','D1_polynomial_residual','D0_IBP_residual'])
 assert bridge_exact['cut_jump_matrix_residual']=='Matrix([[0, 0, 0], [0, 0, 0], [0, 0, 0]])'
 boundary_max=max(num(bridge_numeric[k]) for k in ['upper_boundary_max_absolute_difference','lower_boundary_max_absolute_difference','negative_cut_max_absolute_difference'])
 interior_max=max(num(bridge_numeric[k]) for k in ['Landen_area_max_relative_difference','area_Wronskian_max_relative_difference','full_Landen_integrand_max_relative_difference'])
 assert boundary_max<100*num(bridge_numeric['boundary_displacement'])
 assert interior_max<mp.power(10,-int(bridge_numeric['working_digits'])+8)
 tol=mp.power(10,-min(dps-10,65))
 assert num(formula['checks']['max_absolute_discrepancy'])<tol
 assert num(ren['pointwise_cover_relative_error'])<tol and num(ren['B31_quadrature_residual'])<tol
 assert max(abs(num(r['error'])) for r in contacts['profiles'])<tol
 assert abs(num(audit['period_quadrature']['discrepancy']))<mp.mpf('1e-50')
 assert abs(num(conv['rows'][-1]['difference']))<tol
 c=num(formula['values']['C2']);refdiff=c-num(reference['values']['C2'])
 assert abs(refdiff)<mp.power(10,-min(dps-10,70))
 coef=ren['coefficient_values'];b=num(coef['b0']);I=num(coef['I']);rows=[]
 for name,key in [('Gamma_ratio','R'),('P','P'),('Q','Q'),('T','T'),('C2_delta_convention','C2')]:
  rows.append({'quantity':name,'value':formula['values'][key],'origin':'fresh three-4F3 evaluation'})
 for name,key in [('b0','b0'),('B31','B31'),('I_from_closed_expression','I'),('z41','z41')]:
  rows.append({'quantity':name,'value':coef[key],'origin':'fresh evaluation or algebraically derived quantity; see note'})
 rows.extend([
  {'quantity':'I_from_independent_Carlson_periods','value':audit['period_quadrature']['I_from_independent_periods'],'origin':'fresh endpoint-subtracted Carlson quadrature'},
  {'quantity':'C2_s_convention','value':mp.nstr(c/4,dps-8),'origin':'C2_delta_convention divided by four'},
  {'quantity':'period_contribution_to_C2','value':mp.nstr(-mp.pi*I/(4*b*b),dps-8),'origin':'fresh derived decomposition'},
  {'quantity':'contact_contribution_to_C2','value':mp.nstr(-mp.pi**2/(4*b),dps-8),'origin':'fresh derived decomposition'}])
 def table(name,records):
  with (ROOT/'outputs/tables'/name).open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=records[0]);w.writeheader();w.writerows(records)
 table('final_constants.csv',rows)
 validation=[
  {'check':'three rational telescoping identities','result':'PASS: exact residual 0','scope':'exact algebra'},
  {'check':'three infinite endpoint terms','result':'PASS: exact residual 0; nonzero boundary terms retained','scope':'exact gamma/rational algebra'},
  {'check':'analytic bridge differential, monodromy, Landen and IBP certificates','result':'PASS: exact residuals 0; contour reflection assertions passed','scope':'exact algebra; no global quartic integration'},
  {'check':'elliptic cut boundary values','result':mp.nstr(boundary_max,12),'scope':'maximum observed absolute discrepancy at stated finite boundary displacement'},
  {'check':'Landen area, Wronskian and complete transformed integrand','result':mp.nstr(interior_max,12),'scope':'maximum observed relative discrepancy at selected complex points'},
  {'check':'six-to-three and Frobenius agreement','result':formula['checks']['max_absolute_discrepancy'],'scope':'observed absolute numerical discrepancy'},
  {'check':'independent Carlson period agreement','result':audit['period_quadrature']['discrepancy'],'scope':'observed discrepancy; finite u cutoff, no rigorous quadrature bound'},
  {'check':'elliptic-cover pointwise identity','result':ren['pointwise_cover_relative_error'],'scope':'observed relative numerical discrepancy'},
  {'check':'Gaussian B31 quadrature','result':ren['B31_quadrature_residual'],'scope':'observed absolute numerical discrepancy'},
  {'check':'general source contacts','result':str(max(abs(num(r['error'])) for r in contacts['profiles'])),'scope':'maximum observed contact-identity residual'},
  {'check':'regulated map, local OPE, local two-energy corner','result':'PASS: inherited independent assertions','scope':'selected local checks, not a uniform global nested-sector proof'},
  {'check':'lower-order gamma reductions and C2 scheme covariance','result':'PASS: exact symbolic identities','scope':'exact algebra in specified analytic continuation'},
  {'check':'analytic series-tail inequalities','result':'PASS: exact polynomial sign certificates','scope':'analytic tail bounds evaluated with non-certified floating-point sums'},
  {'check':'archived final expression comparison','result':mp.nstr(refdiff,dps-8),'scope':'fresh result minus saved 100-dps reference; reference never used as a computational input'}]
 table('validation.csv',validation)
 result={'status':'Complete fresh reproduction of the final special-function expression and the implemented exact/local checks.',
  'physical_status':'Project formal C2 result in the specified critically tuned analytic-MS prescription. This package does not independently prove every global nested-sector subtraction or a uniform remainder bound.',
  'convention':{'delta':'(7/4-s)/2','energy_dimension':'Delta_epsilon=1+C2*delta^2+O(delta^3)','coefficient_of_(7/4-s)^2':'C2/4'},
  'working_dps':dps,'C2':formula['values']['C2'],'C2_in_s_convention':mp.nstr(c/4,dps-8),
  'constants':rows,'validation':validation,
  'analytic_bridges':{'file':'outputs/raw/analytic_bridges.json','scope':bridges['scope'],'exact_algebra_status':'passed','pointwise_assertions_status':'passed','working_digits':bridge_numeric['working_digits'],'finite_boundary_displacement':bridge_numeric['boundary_displacement'],'max_boundary_absolute_difference':mp.nstr(boundary_max,12),'max_interior_relative_difference':mp.nstr(interior_max,12)},
  'saved_reference_comparison':{'file':'inputs/reference/three_4f3_100dps.json','fresh_minus_reference':mp.nstr(refdiff,dps-8)},
  'independent_series_envelope':audit['C2_series_envelope'],
  'not_claimed':['elementary or gamma-only reduction','interval-certified rounding or physical derivation','new global renormalized integral evaluation']}
 (ROOT/'outputs/summary.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'C2':result['C2'],'C2_in_s_convention':result['C2_in_s_convention'],'status':result['status']},indent=2))
if __name__=='__main__':main()
