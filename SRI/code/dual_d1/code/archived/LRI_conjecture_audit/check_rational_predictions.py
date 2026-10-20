#!/usr/bin/env python3
"""Check fixed trial predictions against the archived weight-zero C8 = 88.

Only rational algebra is performed. This does not repeat the kink integrations
or assume numerical independence of real zeta values. The projection is the
formal weight-zero map specified by the archived perturbative calculation.

Optional: --archive PATH verifies the previously generated model data too.
"""
from fractions import Fraction as F
from math import factorial
from pathlib import Path
import argparse
import ast
import json
import zipfile


def constant_term(expr: str) -> F:
    """Evaluate the weight-zero component of an archived rational expression."""
    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) is int:
            return F(node.value)
        if isinstance(node, ast.Name) and node.id.startswith('Z') and node.id[1:].isdigit():
            return F(0)
        if isinstance(node, ast.UnaryOp):
            val = visit(node.operand)
            if isinstance(node.op, ast.USub): return -val
            if isinstance(node.op, ast.UAdd): return val
        if isinstance(node, ast.BinOp):
            a, b = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add): return a+b
            if isinstance(node.op, ast.Sub): return a-b
            if isinstance(node.op, ast.Mult): return a*b
            if isinstance(node.op, ast.Div): return a/b
            if isinstance(node.op, ast.Pow) and b.denominator == 1:
                return a**int(b)
        raise ValueError(f'Unsupported expression node: {ast.dump(node)}')
    return visit(ast.parse(expr, mode='eval'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    c = {1:F(-2), 2:F(1,2), 3:F(39,16), 4:F(4),
         5:F(11249,1024), 6:F(26), 7:F(1798583,32768), 8:F(88)}
    # H=(1-f)/(2t). Derive log H through t^6 only from C1,...,C7.
    h = [F(1)]+[-c[n+1]/2 for n in range(1,7)]
    ell = [F(0)]*7
    for n in range(1,7):
        ell[n] = h[n]-sum(F(k,n)*ell[k]*h[n-k] for k in range(1,n))
    assert ell[1:] == list(map(F, ['-1/4','-5/4','-887/384','-109/16',
                                    '-709683/40960','-2003/48']))
    # In both fixed Gamma models the rational logarithm stops at degree six.
    hp = [F(1)]
    for n in range(1,8):
        hp.append(sum(F(k,n)*ell[k]*hp[n-k] for k in range(1,min(n,6)+1)))
    gamma_prediction = -2*hp[7]
    assert gamma_prediction == F(-78669187,917504)
    assert all(-2*hp[n-1] == c[n] for n in range(2,8))
    guesses = {
        'geometric_rational_trace': F(6**4-2**4,8),
        'unmodified_implicit_Gamma': F(-55777,64),
        'quadratic_log_Gamma_A': gamma_prediction,
        'Borel_Gamma_B': gamma_prediction,
        'rational_invariant_Pade': c[6]**2/c[4],
    }
    archive_checked = False
    if args.archive:
        with zipfile.ZipFile(args.archive) as z:
            data = json.loads(z.read('LRI_alternative_models/data/results.json'))
        for model in ['quadratic_log_gamma','borel_log_gamma','rational_rg']:
            predicted = constant_term(data['models'][model]['coefficients']['8']['exact'])
            assert predicted == (c[6]**2/c[4] if model=='rational_rg' else gamma_prediction)
        for model in ['quadratic_log_gamma','borel_log_gamma']:
            poly = list(map(F, data['models'][model]['rational_polynomial']))
            if model == 'borel_log_gamma':
                poly = [val*factorial(n) for n,val in enumerate(poly)]
            assert poly == ell
        archive_checked = True
    result = {
        'scope':'conditional on the archived matched perturbative inputs; formal rational projection only',
        'physical_C8_weight_zero_input': str(c[8]),
        'new_integration_performed':False,
        'log_H_weight_zero_through_degree_6':list(map(str,ell)),
        'predictions':{key:{'C8_weight_zero':str(val),
                            'difference_from_88':str(val-c[8]),
                            'matches':val==c[8]} for key,val in guesses.items()},
        'Pade_identity_after_clearing_denominator':{
            'C4_C8_weight_zero':str(c[4]*c[8]),
            'C6_squared_weight_zero':str(c[6]**2)},
        'archived_model_coefficients_independently_checked':archive_checked,
        'full_C8_not_evaluated':True,
        'all_order_MZV_statement_not_tested_by_rational_part':True,
    }
    text=json.dumps(result,indent=2)
    if args.output: args.output.write_text(text+'\n')
    print(text)

if __name__ == '__main__':
    main()
