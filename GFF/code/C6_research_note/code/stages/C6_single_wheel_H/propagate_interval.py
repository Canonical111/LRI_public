"""Propagate an inherited rational wheel enclosure to the newly identified H.
This is not certification of a two-dimensional numerical Barnes integration.
"""
from pathlib import Path
from fractions import Fraction as F
from math import isqrt
import json, decimal, hashlib
ROOT=Path(__file__).resolve().parent
source=ROOT/'inputs/C6_central_binomial_wheel_intervals.json'
x=json.loads(source.read_text())
def frac(d): return F(int(d['numerator']),int(d['denominator']))
lo_p,hi_p=map(frac,[x['pi']['lower'],x['pi']['upper']])
wc=x['enclosures'][-1]['Wcentral']
lo_w,hi_w=map(frac,[wc['lower'],wc['upper']])
B=700; scale=2**B; root=isqrt(89*scale**2)
rootlo,roothi=F(root,scale),F(root+1,scale)
assert rootlo**2 < 89 < roothi**2
# H = pi**2/sqrt(89) * (Wc+(8+5*pi)*pi**2/3), all positive.
lower=lo_p**2*(lo_w+(8+5*lo_p)*lo_p**2/3)/roothi
upper=hi_p**2*(hi_w+(8+5*hi_p)*hi_p**2/3)/rootlo
lower=F((lower.numerator*scale)//lower.denominator,scale)
upper=F(-((-upper.numerator*scale)//upper.denominator),scale)
assert lower<upper
assert upper-lower < F(2223,10**149) # 2.223e-146
# Directed rounding was handled exactly above. Decimals below are informative.
decimal.getcontext().prec=180
def dec(q): return decimal.Decimal(q.numerator)/decimal.Decimal(q.denominator)
def record(q): return {'numerator':str(q.numerator),'denominator':str(q.denominator)}
result={
 'scope':'PROPAGATION of the inherited rigorous wheel interval using the proved identity Hwheel=pi**2*W0/sqrt(89). Not a new independent numerical Barnes certificate or a full physical-C6 certificate.',
 'source':source.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
 'formula':'Hwheel=pi**2*(Wcentral+(8+5*pi)*pi**2/3)/sqrt(89)',
 'Hwheel':{'lower':record(lower),'upper':record(upper),'width':record(upper-lower),
           'width_decimal':str(dec(upper-lower)),
           'lower_decimal':str(dec(lower)),'upper_decimal':str(dec(upper))},
 'arithmetic':'exact Fraction; square root bracket via integer isqrt; outward rounding to denominator 2**700',
 'new_all_sector_evaluation':False}
(ROOT/'results/propagated_interval.json').write_text(json.dumps(result,indent=2)+'\n')
print('Propagated width:',result['Hwheel']['width_decimal'])
print('Hwheel:',f'{dec(lower):.60f}')
