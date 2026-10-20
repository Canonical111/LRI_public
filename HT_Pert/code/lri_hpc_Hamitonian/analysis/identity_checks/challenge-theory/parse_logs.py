import re, json, glob
HERE='<TMP>/scratchpad/identity/challenge-theory/'
def parse(ph):
    rows={}
    for line in open(HERE+f'log_ph{ph}.txt'):
        m=re.search(r'Lam=\s*([\d.]+).*raw C2..C4=\[([^\]]*)\] corr C2..C4=\[([^\]]*)\] v_dphi raw/corr e2..e4=\[([^\]]*)\] \[([^\]]*)\]',line)
        if m:
            f=lambda s:[float(x) for x in s.split(',')]
            rows[float(m.group(1))]=dict(rawC=f(m.group(2)),corrC=f(m.group(3)),rawv=f(m.group(4)),corrv=f(m.group(5)))
    return rows
