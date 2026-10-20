# validation at d=2,3 (low precision, local): b-circle (L, Z) and tau-circle (K)
for d in 3 2; do python3 hp_general_d.py val_b_$d.json $d 25 24 26 32 b 0.1 > val_b_$d.log 2>&1; python3 hp_general_d.py val_t_$d.json $d 25 24 26 32 t 0.1 > val_t_$d.log 2>&1; done
