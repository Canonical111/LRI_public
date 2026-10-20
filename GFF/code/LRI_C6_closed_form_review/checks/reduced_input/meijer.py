import mpmath as mp, json, time
r=json.load(open('ordinary.json'))
for dps in [20, 30]:
    mp.mp.dps = dps
    t=time.time()
    h=mp.mpf(1)/2
    U4=mp.mpf(r['U4']['EM']); U6=mp.mpf(r['U6']['EM'])
    try:
        g13 = mp.meijerg([[h,h,h],[h]], [[0],[0,0,0]], 1)
        print(dps, 'g13', mp.nstr(g13, dps), ' U4 - g13/pi =', mp.nstr(U4-g13/mp.pi,3), ' t=%.1f'%(time.time()-t))
    except Exception as e:
        print('g13 failed', e)
    t=time.time()
    try:
        g22 = mp.meijerg([[h,h],[h,h]], [[0,0],[0,0]], 1)
        print(dps, 'g22', mp.nstr(g22, dps), ' U6 - 2 g22/pi^2 =', mp.nstr(U6-2*g22/mp.pi**2,3), ' t=%.1f'%(time.time()-t))
    except Exception as e:
        print('g22 failed', e)
