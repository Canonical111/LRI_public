import numpy as np
from mb_check_np import J_mb, J_d1
for h in (0.08, 0.05, 0.035):
    print('h', h, 'd=2 tau=0.3', '%.15g' % J_mb(2.0, 0.6, c1=-0.15, c2=-0.25, h=h).real, ' exact 47.790785413226103671')
for h in (0.05, 0.035):
    print('h', h, 'd=1 t=0.3', '%.15g' % J_mb(1.0, 0.3, c1=-0.075, c2=-0.125, h=h).real, ' exact %.15g' % J_d1(0.3))
