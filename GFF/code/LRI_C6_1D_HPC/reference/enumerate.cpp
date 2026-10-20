#include <bits/stdc++.h>
using namespace std;
int nv,ne,E; vector<pair<int,int>>edges; int degs[10]={},vals[32]={};int rems[33][10]; int fact[]={1,1,2,6,24};
uint64_t countg=0, countc=0;long double sumA=0,sumB=0,sumH=0;ofstream out;uint64_t by[8]={};
void rec(int k,int total){
 if(total>E)return;int cap=0;for(int i=0;i<nv;i++)cap+=4-degs[i];if(total+cap/2<E)return;
 if(k==ne){if(total!=E)return;for(int i=0;i<nv;i++)if(degs[i]<2)return;
 for(int mask=1;mask<(1<<(nv-1));mask++){int cross=0;for(int e=0;e<ne;e++){auto [i,j]=edges[e];if(((mask>>i)^(mask>>j))&1)cross+=vals[e];}if(cross<2)return;}
 int den=1,ss=0;for(int i=0;i<nv;i++){den*=fact[4-degs[i]];ss+=(4-degs[i])*(3-degs[i]);}for(int e=0;e<ne;e++)den*=fact[vals[e]];
 int scale=1728;int A=24*scale/den;if(24*scale%den){cerr<<"bad den "<<den<<endl;exit(3);}int B=A*ss/12;if(A*ss%12){cerr<<"bad ss";exit(4);}int H=3*B-A;
 countg++;if(H)countc++;sumA+=(long double)A/scale;sumB+=(long double)B/scale;sumH+=(long double)H/scale;by[ss]++;
 for(int e=0;e<ne;e++)out.write((char*)&vals[e],4);out.write((char*)&A,4);out.write((char*)&B,4);return;}
 auto [i,j]=edges[k];for(int v=0;v<=min({3,4-degs[i],4-degs[j],E-total});v++){vals[k]=v;degs[i]+=v;degs[j]+=v;bool ok=true;for(int z=0;z<nv;z++)if(degs[z]+3*rems[k+1][z]<2){ok=false;break;}if(ok)rec(k+1,total+v);degs[i]-=v;degs[j]-=v;}
}
int main(int argc,char**argv){nv=argc>1?atoi(argv[1]):7; E=2*nv-2;for(int i=0;i<nv;i++)for(int j=i+1;j<nv;j++)edges.push_back({i,j});ne=edges.size();for(int k=ne-1;k>=0;k--){for(int i=0;i<nv;i++)rems[k][i]=rems[k+1][i];rems[k][edges[k].first]++;rems[k][edges[k].second]++;}out.open(string(argv[2]),ios::binary);rec(0,0);cout<<"nv="<<nv<<" total="<<countg<<" nonzero="<<countc<<" sumA="<<setprecision(20)<<sumA<<" sumB="<<sumB<<" sumH="<<sumH<<endl;for(int i=0;i<8;i++)cout<<i<<":"<<by[i]<<" ";cout<<endl;}
