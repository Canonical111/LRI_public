from pathlib import Path
import mpmath as m,json,time
W=Path(__file__).parent;m.mp.dps=65;t=time.time();records=[]
def numerator(z):
 a=m.mpf('.5')+z/4;b=m.mpf('.5')+3*z/4
 F1=m.hyper([1,z/2,a],[1-z/2,a+m.mpf('.5')],m.mpf('.25'))
 F2=m.hyper([z,2*a,b],[1+z/2,b+m.mpf('.5')],m.mpf('.25'))
 w=m.gamma(1+z)*m.gamma(1-z/2)*m.gamma(b)**2/(m.gamma(a)**2*m.gamma(2*b))
 return 4*F1-2*w*F2
for rad,n in [('0.05',64),('0.08',80)]:
 r=m.mpf(rad);v=[numerator(r*m.exp(2j*m.pi*(j+m.mpf('.5'))/n))for j in range(n//2)]
 coeff=[]
 for k in range(1,6):
  val=2*m.fsum(m.re(v[j]*m.exp(-2j*m.pi*(j+m.mpf('.5'))*k/n))for j in range(n//2))/(n*r**k)
  coeff.append(-6*val)
 records.append({'radius':rad,'nodes':n,'b2_jets':[str(v)for v in coeff],'c2_jets':[str(v/6)for v in coeff]})
old=json.load(open(W/'lri_C6_d2_two_forest_update/analytic/verification/two_loop_extended_reference.json'))['dimensions']['2']['A2']
diff=max(abs(m.mpf(v)-(-2*m.mpf(old[str(j-1)])))for j,v in enumerate(records[-1]['b2_jets']))
(W/'fresh_two_loop_mom.json').write_text(json.dumps({'dps':65,'records':records,'largest_difference_vs_saved_input':str(diff),'largest_changed_Cauchy_contour_difference':str(max(abs(m.mpf(x)-m.mpf(y))for x,y in zip(records[0]['b2_jets'],records[1]['b2_jets']))),'seconds':time.time()-t},indent=2));print('done',diff,time.time()-t)
