import json
S='<TMP>/scratchpad/eps5'
P={int(k):v['delta_C'] for k,v in json.load(open('<PROJECT>/lri_hpc_Hamitonian/analysis/eh_addon_review/physics-impact/d5_all.json')).items()}
A={int(k):v for k,v in json.load(open(S+'/A/dC_table.json'))['table'].items()}
B={r['L']:r for r in json.load(open(S+'/B/dC5_table.json'))}
print('package Ls', min(P), max(P), len(P))
ma=mb=ma4=mb4=0; mbw=0; maw=0
for L in sorted(P):
    if L in A:
        ma=max(ma,abs(A[L]['g2D']['dC5']-P[L][5])); ma4=max(ma4,abs(A[L]['g2D']['dC4']-P[L][4]))
        maw=max(maw,abs((A[L]['g2D3W']['dC5']-A[L]['g2D']['dC5'])+2*P[L][4]))
    if L in B:
        mb=max(mb,abs(B[L]['dC5_g2D']-P[L][5])); mb4=max(mb4,abs(B[L]['dC4_g2D']-P[L][4]))
        mbw=max(mbw,abs(B[L]['dC5_g3W']+2*P[L][4]))
print(f'A g2D dC5 vs pkg {ma:.2e} dC4 {ma4:.2e} ; A g3W vs -2dC4pkg {maw:.2e}')
print(f'B g2D dC5 vs pkg {mb:.2e} dC4 {mb4:.2e} ; B g3W vs -2dC4pkg {mbw:.2e}')
