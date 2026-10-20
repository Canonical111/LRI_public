import json, glob, math
base='<TMP>/scratchpad/identity/'
# A raw-Dfull shift (-B/3), c6, c8
Ash={}
for f in glob.glob(base+'A/c4shift_*.json'):
    for k,v in json.load(open(f)).items(): Ash[int(k)]=v
# B topshell
Bts={}
for f in glob.glob(base+'B/topshell_*.json'):
    d=json.load(open(f)); d=d if isinstance(d,list) else [d]
    for r in d: Bts[r['L']]=r
Bsh=json.load(open(base+'B/shift_all.json')); Bconn=dict(zip([int(x) for x in Bsh['L']],Bsh['shift']))
A=json.load(open(base+'A/analysis_table.json'))
print('L   A:-B/3(raw)        B:shift_raw        diff     | A:c6*81 vs B:Z diff | A Dconn-g2D C4 vs B shift_conn diff')
for L in sorted(set(Ash)|set(Bts)|set(Bconn)):
    s=f'{L:3d} '
    if L in Ash and L in Bts:
        s+=f"{Ash[L]['dC4']:.15f} {Bts[L]['shift_raw']:.15f} {Ash[L]['dC4']-Bts[L]['shift_raw']:+.1e} | {Ash[L]['c6']*81-Bts[L]['Z']:+.1e} | "
    else: s+=' '*58+'| '
    if str(L) in A and L in Bconn:
        aconn=A[str(L)]['Dconn']['C'][4]-A[str(L)]['g2D']['C'][4]
        s+=f"{aconn:.13f} {Bconn[L]:.13f} {aconn-Bconn[L]:+.1e}"
    print(s)
print('A Dshift keys example', {k:(v if not isinstance(v,list) else v[:5]) for k,v in A['64']['Dshift'].items() if k in ('r4','g4','C')})
