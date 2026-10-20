import json
R='<TMP>/scratchpad/eps5/reconcile'
EX5=-731.13947662454; EX4=45.42488010356
rows=json.load(open(R+'/refit_rc.json'))['rows']
for lo in (16,40,50,60,70):
    sel={r['variant']:r for r in rows if r['lo']==lo}
    s=f'lo={lo}: '+' '.join(f"{b}={sel[b]['Dconn_full']['C5']:.3f}" for b in 'ABCDEF')
    s+=' | MS: '+' '.join(f"{b}={sel[b]['Dconn_MS']['C5']:.3f}" for b in 'ABCDEF')
    print(s)
    print('      raw: '+' '.join(f"{b}={sel[b]['raw']['C5']:.3f}" for b in 'ABCDEF')+ ' | C4 full: '+' '.join(f"{b}={sel[b]['Dconn_full']['C4']:.4f}" for b in 'ABCDEF'))
    post=[r for r in sel.values() if r['cls']=='post']; ex=[r for r in sel.values() if r['cls']=='extra']
    fe=[r for r in post if 'free' in r['variant']]
    nf=[r for r in post if 'free' not in r['variant'] and 'gap' not in r['variant']]
    print(f"      post-hoc towers/L^-0.75: {min(r['Dconn_full']['C5'] for r in nf)-EX5:+.3f}..{max(r['Dconn_full']['C5'] for r in nf)-EX5:+.3f}; free-exp: {min(r['Dconn_full']['C5'] for r in fe)-EX5:+.3f}..{max(r['Dconn_full']['C5'] for r in fe)-EX5:+.3f}; extra E+L^-.5(,zL^-.5): " + ', '.join(f"{r['Dconn_full']['C5']-EX5:+.3f}" for r in ex))
    # fraction of miss removed
    for b in ('A','E'):
        rm=sel[b]['raw']['C5']-EX5; dm=sel[b]['Dconn_full']['C5']-EX5
        r4=sel[b]['raw']['C4']-EX4; d4=sel[b]['Dconn_full']['C4']-EX4
        print(f"      {b}: C5 miss raw {rm:+.3f} -> {dm:+.3f} ({100*(1-dm/rm):.0f}% removed); C4 miss raw {r4:+.4f} -> {d4:+.4f} ({100*(1-d4/r4):.0f}% removed)")
