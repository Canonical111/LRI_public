from assemble6 import *
def predict(cut,n=28):
 d=inputs(cut,n);a=assemble(d);G=a['G'];Z=a['Z'];b=a['beta'];c=a['gamma']
 gp={};zp={}
 for i in range(1,6):
  gp=la_add(gp,G[7-i],b[i-1]*(7-i)/6)
  zp=la_add(zp,Z[6-i],((6-i)*b[i-1]+c[i-1])/6)
 gp={k-1:v for k,v in gp.items()};zp={k-1:v for k,v in zp.items()}
 expect=la_add(la_add(Z[6],G[7],-mp.mpf(1)/3),la_add(zp,gp,-mp.mpf(1)/3),-1)
 expect={k:3*v for k,v in expect.items()if k<-1}
 return expect
if __name__=='__main__':
 out={cut:predict(cut)for cut in ['maxgap','span']};(R/'H6_predicted_higher_poles.json').write_text(json.dumps(serial(out),indent=2));print(json.dumps(serial(out),indent=2))
