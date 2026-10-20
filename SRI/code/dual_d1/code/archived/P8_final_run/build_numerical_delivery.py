from pathlib import Path
import shutil,json
root=Path('/mnt/data/P8_final_run/F3_six_kink_completion');dst=Path('/mnt/data/C8_full_numerical_completion')
for n in ['P8','Kv']:
 shutil.copy2(root/'F3_final'/f'{n}.expr',dst/'data'/f'{n}.expr')
for source,name in [
(root/'F4_data/J9.expr','J9.expr'),
(root/'F4_A9/A9_log.expr','A9_log.expr'),
(root/'F4_Z8/Z8_log.expr','Z8_log.expr'),
(root/'F4_EA7/EA7_full.expr','EA7_finite.expr'),
(root/'F4_EZ6/EZ6_full.expr','EZ6_finite.expr'),
(root/'F4_data/J9_lower_shift.expr','J9_lower_shift.expr'),
(root/'C8_assembly/B_old_full.expr','B_old_full.expr'),
(Path('/mnt/data/F3_six_kink_completion/data/F3_known_with_six_kinks.expr'),'F3_known.expr'),
(Path('/mnt/data/F1c_completion/data/Nd_known_part.expr'),'F1_known.expr'),
(Path('/mnt/data/F2_F3_delivery/F2/data/U.expr'),'U.expr')]:shutil.copy2(source,dst/'data'/name)
for folder,stem in [('F3_final','eval'),('F4_data','full')]:
 for dps in (70,100):
  source=root/folder/f'{stem}{dps}.json'
  shutil.copy2(source,dst/'data'/f'{folder}_{dps}.json')
  shutil.copy2(source.with_suffix('.periods.json'),dst/'data'/f'{folder}_{dps}.periods.json')
for source,name in [
('/mnt/data/F2_F3_delivery/F2/verification/run110dfs.json','U_record.json'),
('/mnt/data/C8_full_work/full_engine/final_evaluation_C8_six_second.json','six_new_inputs.json'),
('/mnt/data/C8_full_work/full_trace.json','full_trace.json'),
('/mnt/data/F1a_resume/mellin/data/gfull_n6_N32_s64_r.43_q0_quad.json','P6_N32_original.json'),
('/mnt/data/F1a_resume/mellin/data/gfull_n6_N36_s64_r.43_q0_quad.json','P6_N36_original.json'),
('/mnt/data/P8_final_run/mellin_inputs/F2_F3_delivery/F3/mellin/data/gfull_n6_N32_s64_r.43_q0_quad_kahan.json','P6_N32_kahan.json'),
('/mnt/data/C8_rational_completion/result.json','C8_rational_record.json')]:shutil.copy2(source,dst/'inherited'/name)
# Generalize the independent literal monomial implementation; remove rational-only guards.
s=Path('/mnt/data/C8_rational_work/verify_trace_fraction.py').read_text();s=s[:s.index("if __name__=='__main__':")]
s=s[:s.index(' expected=q[')]+''' return {'u':u,'z':z,'trace':fulltrace,'C8':8*fulltrace[4]}
'''
(dst/'code/full_jacobian.py').write_text(s)
