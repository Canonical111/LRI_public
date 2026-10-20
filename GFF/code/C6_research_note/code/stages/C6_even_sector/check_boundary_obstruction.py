"""Narrow exact obstruction: no universal rational-row boundary primitive
in the full inherited nine-dimensional differential module.
This says nothing about more general finite special-value evaluations of Pa.
"""
from pathlib import Path
import json
import sympy as sp
from sympy.polys.matrices import DomainMatrix
ROOT=Path(__file__).resolve().parent
def main():
    inp=json.loads((ROOT/'inputs/expression.json').read_text())
    obj=inp['single_index_recurrence_series_terms'][0]
    A=sp.Matrix(obj['A_matrix']);C=sp.Matrix(obj['C_matrix']);eye=sp.eye(9)
    x=sp.symbols('x');co=sp.symbols('c0:36')
    R=((1+x*x)*(A+eye/2)+x*C)/(x*(1-x*x))
    row=sp.Matrix(1,9,[co[i]*x+co[i+9]+co[i+18]/x+co[i+27]/(x+1) for i in range(9)])
    eq=[]
    for f in ((row.diff(x)+row*R-sp.Matrix([[4/x]+[0]*8]))*x*x*(1-x*x)*(x+1)):
        eq.extend(sp.Poly(sp.cancel(f),x).all_coeffs())
    M,b=sp.linear_eq_to_matrix(eq,co)
    DM=DomainMatrix.from_Matrix(M).to_field()
    DA=DomainMatrix.from_Matrix(M.row_join(b)).to_field()
    rank=len(DM.rref()[1]);aug=len(DA.rref()[1])
    assert rank==36 and aug==37
    null=DomainMatrix.from_Matrix(M.T).to_field().nullspace().to_Matrix()
    cert=None
    for i in range(null.rows):
        u=null.row(i);v=(u*b)[0]
        if v:
            cert=u/v;break
    assert cert is not None and cert*M==sp.zeros(1,36) and (cert*b)[0]==1
    def eigs(M):return {str(k):v for k,v in M.eigenvals().items()}
    res={'scope':'No rational row r(x) solves r prime+r R=4 e0/x for the full nine-dimensional system. Not a theorem excluding a finite evaluation of Pa by another method.',
      'rank':rank,'augmented_rank':aug,'shape':list(M.shape),
      'rational_ansatz':'r(x)=a*x+b+c/x+d/(x+1), each a,b,c,d has 9 entries',
      'left_null_certificate':list(map(str,cert)),
      'certificate_identities':['lambda*M=0','lambda*b=1'],
      'residue_0_eigenvalues':eigs(A+eye/2),
      'residue_plus1_eigenvalues':eigs(-(2*A+C+eye)/2),
      'residue_minus1_eigenvalues':eigs(-(2*A-C+eye)/2),
      'minus_infinity_coefficient_eigenvalues':eigs(A+eye/2)}
    (ROOT/'results/boundary_obstruction.json').write_text(json.dumps(res,indent=2)+'\n')
    return res
if __name__=='__main__':print(json.dumps(main(),indent=2))
