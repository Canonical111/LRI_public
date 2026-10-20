import sys; sys.dont_write_bytecode=True
from ht5 import Engine
for L in (8, 12):
    for caps in ((10, 11), (12, 13), (16, 17)):
        e = Engine(L, *caps)
        R = {v: e.run(v) for v in ('raw', 'Dconn')}
        print(L, caps, (e.Se.dim, e.So.dim), '%.15f %.15f %.15f' % (R['raw']['C'][5], R['Dconn']['C'][5] - R['raw']['C'][5], R['Dconn']['C'][4] - R['raw']['C'][4]))
