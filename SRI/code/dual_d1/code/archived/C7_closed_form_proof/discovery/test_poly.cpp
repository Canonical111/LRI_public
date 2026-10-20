#include "word_core.hpp"
int main(){mt19937 rng(19);PolyWord p;Primitive pr;
for(int t=0;t<4000;t++){int n=2+rng()%5,k=1+rng()%(n-1);vector<int>a(k),b(n-k);for(int&x:a)x=rng()%5;for(int&x:b)x=rng()%5;W wa=makew(a),wb=makew(b);map<U,Z>left,right;
for(auto[w,c]:shwords(wa,wb))for(auto[m,d]:p.get(w))left[m]+=c*d;
for(auto[m,c]:p.get(wa))for(auto[n,d]:p.get(wb)){auto[k,f]=monmul(m,n);right[k]+=c*d*f;}
for(auto it=left.begin();it!=left.end();)if(!it->second)it=left.erase(it);else++it;for(auto it=right.begin();it!=right.end();)if(!it->second)it=right.erase(it);else++it;if(left!=right)throw runtime_error("shuffle homomorphism");
a.insert(a.end(),b.begin(),b.end());W w=makew(a);map<W,Z>ind;for(auto[m,c]:p.get(w)){auto fac=monvec(m);if(fac.size()==1)ind[fac[0]]=c;}IV v(ind.begin(),ind.end());if(v!=pr.get(w))throw runtime_error("primitive projection differs");}
cout<<"PASS 4000 exact shuffle and primitive-projection checks\n";}
