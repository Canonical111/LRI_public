"""Count quadrature nodes x terms for a cluster_engine run (same region logic as the engine).
usage: python m3_nodecount.py ENGINE_INPUT kmax nseg m nplain [plainR] [conj 0/1]"""
import sys
inp = sys.argv[1]; kmax = int(sys.argv[2]); nseg, m, nplain = map(int, sys.argv[3:6])
plainR = float(sys.argv[6]) if len(sys.argv) > 6 else 0.3
conj = int(sys.argv[7]) if len(sys.argv) > 7 else 1
tok = open(inp).read().split('\n')
nodes = nt = 0; nsec = 0; per = []
D = None
i = 0
while i < len(tok):
    line = tok[i].split()
    if line and line[0] == 'n': D = 2 * int(line[1]) - 2
    if line and line[0] == 'sector':
        p = line[1:]
        j0 = p.index('plain0'); j1 = p.index('plain1'); jr = p.index('R')
        pl0 = list(map(int, p[j0 + 1:j0 + 1 + D])); pl1 = list(map(int, p[j1 + 1:j1 + 1 + D]))
        R = list(map(float, p[jr + 1:jr + 1 + D]))
        plain = [(pl0[k] if kmax == 0 else pl1[k]) and R[k] >= plainR for k in range(D)]
        split = [k for k in range(D) if not plain[k]]
        tot = 0
        for reg in range(1 << len(split)):
            nn = 1; first = True
            ncirc = bin(reg).count('1')
            for k in range(D):
                if plain[k]: nn *= nplain
                else:
                    pos = split.index(k)
                    nn *= m if (reg >> pos) & 1 else nseg
            if conj and ncirc: nn //= 2
            tot += nn
        # terms
        while not tok[i].startswith('nterm'): i += 1
        ntm = int(tok[i].split()[1])
        nodes += tot; nt += tot * ntm; nsec += 1; per.append((tot, ntm))
    i += 1
print(f'sectors {nsec}  nodes {nodes:.3e}  node*terms {nt:.3e}')
