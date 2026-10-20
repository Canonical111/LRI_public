"""Static checks only. This is not Wolfram-kernel execution or parsing."""
from pathlib import Path
import re,json
R=Path(__file__).resolve().parent
s=(R/'C6_sixth_MeijerG_patch.wl').read_text()
stack=[]; pairs={']':'[','}':'{',')':'('}; i=0; comment=0; string=False; clean=[]
while i<len(s):
    c=s[i]; nxt=s[i:i+2]
    if comment:
        if nxt=='(*':comment+=1;i+=2;continue
        if nxt=='*)':comment-=1;i+=2;continue
        i+=1;continue
    if string:
        if c=='\\':i+=2;continue
        if c=='"':string=False
        i+=1;continue
    if nxt=='(*':comment=1;i+=2;continue
    if c=='"':string=True;i+=1;continue
    clean.append(c)
    if c in '[{(':stack.append(c)
    if c in ']})':
        if not stack or stack.pop()!=pairs[c]:raise AssertionError('delimiter mismatch')
    i+=1
assert not stack and not string and not comment
body=''.join(clean)
for head in ['Integrate','NIntegrate','Sum','NSum','Derivative','Inactive','FoxH','HarmonicPolyLog','MultiplePolyLog']:
    assert not re.search(r'\b'+head+r'\s*\[',body), head
report={'delimiters_balanced':True,'no_integral_sum_or_derivative_heads':True,
 'requires_new_HPL_builtins':False,'wolfram_kernel_executed':False,
 'limitation':'Static source checks only, not a Wolfram parser or numerical execution.'}
(R/'results/wolfram_static_checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
