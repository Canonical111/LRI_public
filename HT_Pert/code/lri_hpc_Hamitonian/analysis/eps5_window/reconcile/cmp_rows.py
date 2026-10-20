import json, numpy as np
S='<TMP>/scratchpad/eps5'
A={r['L']:r for r in json.load(open(S+'/A/final_tables.json'))}
B={r['L']:r for r in json.load(open(S+'/B/dC5_table.json'))}
print(' L  meas |  A W8_5+W6_5 - B B5 | A W8_5 - B A5 | A F_X5 - B rows5 | A F_feed - B rows4 | W8_4 - A4 | W8_4+W6_4 - B4 | dC4 shift: A(Dconn-g2D) - B shift4')
mx={}
for L in sorted(set(A)&set(B)):
    a=A[L]; b=B[L]
    vals=[a['W8_5']+a['W6_5']-b['B5'], a['W8_5']-b['A5'], a['F_X5']-b['dC5_rows5'], a['F_feed']-b['dC5_rows4'],
          a['W8_4']-b['A4'], a['W8_4']+a['W6_4']-b['B4'], (a['dC4_Dconn']-a['dC4_g2D'])-b['shift4']]
    m=a['measured_window']
    for i,v in enumerate(vals): mx[(i,m)]=max(mx.get((i,m),0),abs(v))
    print(f"{L:4d} {int(m)} | "+' | '.join(f'{v:+.2e}' for v in vals))
print(mx)
