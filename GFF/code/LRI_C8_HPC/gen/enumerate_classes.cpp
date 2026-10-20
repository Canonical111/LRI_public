// Generalization of reference/code/enumerate_classes.cpp from n<=8 to n<=9 vertices (L<=8 loops).
// Same algorithm, ordering and output format; the packed multiplicity key (2 bits per vertex pair,
// 36 pairs for n=9) is an unsigned __int128 written and read in decimal, so for n<=8 the output is
// byte-identical to the reference program. Usage: enumerate_classes <n=L+1> <output classesL.txt>
#include <bits/stdc++.h>
using namespace std;
using U=unsigned __int128;
static string u128s(U x){if(!x)return "0";char b[48];int p=47;b[p]=0;while(x){b[--p]=char('0'+int(x%10));x/=10;}return string(b+p);}
struct UH{size_t operator()(U x)const noexcept{uint64_t a=uint64_t(x),b=uint64_t(x>>64);uint64_t h=a*0x9E3779B97F4A7C15ULL^(b+0x632BE59BD9B4E019ULL+(a<<6)+(a>>2));h^=h>>31;h*=0xBF58476D1CE4E5B9ULL;h^=h>>29;return size_t(h);}};
int n,L,E,ne,target[9],deg[9],v[36],idx[9][9],rem[37][9]; vector<pair<int,int>> edges; vector<vector<int>> maps; unordered_set<U,UH> seen;
struct Row {U key; int orbit_group; int aut;}; vector<Row> rows; uint64_t leaves=0;
void rec(int k,int total){
 if(k==ne){
  if(total!=E)return;for(int i=0;i<n;i++)if(deg[i]!=target[i])return;leaves++;
  U key=0;for(int e=0;e<ne;e++)key|=U(v[e])<<(2*e);if(seen.count(key))return;
  for(int mask=1;mask<(1<<(n-1));mask++){int cross=0;for(int e=0;e<ne;e++){auto [i,j]=edges[e];if(((mask>>i)^(mask>>j))&1)cross+=v[e];}if(cross<2)return;}
  U best=key;int count=0;for(auto &mp:maps){U h=0;for(int e=0;e<ne;e++)h|=U(v[mp[e]])<<(2*e);best=min(best,h);count+=seen.insert(h).second;}
  rows.push_back({best,count,int(maps.size()/count)});return;
 }
 auto [i,j]=edges[k];int mx=min({3,target[i]-deg[i],target[j]-deg[j],E-total});
 for(int z=0;z<=mx;z++){v[k]=z;deg[i]+=z;deg[j]+=z;bool ok=true;for(int t=0;t<n;t++)if(deg[t]>target[t]||deg[t]+3*rem[k+1][t]<target[t]){ok=false;break;}if(ok)rec(k+1,total+z);deg[i]-=z;deg[j]-=z;}
}
void run(vector<int>d){
 for(int i=0;i<n;i++)target[i]=d[i];maps.clear();vector<int>p(n);iota(p.begin(),p.end(),0);
 do{bool good=true;for(int i=0;i<n;i++)if(d[i]!=d[p[i]]){good=false;break;}if(!good)continue;vector<int>m(ne);for(int e=0;e<ne;e++)m[e]=idx[p[edges[e].first]][p[edges[e].second]];maps.push_back(m);}while(next_permutation(p.begin(),p.end()));
 rec(0,0);cerr<<"pattern ";for(int a:d)cerr<<a;cerr<<" classes="<<rows.size()<<" sorted_leaves="<<leaves<<" seen="<<seen.size()<<"\n";
}
int main(int argc,char**argv){
 n=argc>1?atoi(argv[1]):8;if(n<1||n>9||argc<3){cerr<<"usage: enumerate_classes n(<=9) output\n";return 2;}L=n-1;E=2*L;for(int i=0;i<n;i++)for(int j=i+1;j<n;j++){idx[i][j]=idx[j][i]=edges.size();edges.push_back({i,j});}ne=edges.size();
 for(int k=ne-1;k>=0;k--){for(int i=0;i<n;i++)rem[k][i]=rem[k+1][i];rem[k][edges[k].first]++;rem[k][edges[k].second]++;}seen.reserve(n>=9?160000000:5000000);
 if(n>=2){vector<int>d(n,4);d[0]=d[1]=2;run(d);}if(n>=3){vector<int>d(n,4);d[0]=2;d[1]=d[2]=3;run(d);}if(n>=4){vector<int>d(n,4);fill(d.begin(),d.begin()+4,3);run(d);}
 sort(rows.begin(),rows.end(),[](auto a,auto b){return a.key<b.key;});ofstream out(argv[2]);out<<n<<' '<<rows.size()<<'\n';long long lab=0,fn=1;for(int i=2;i<=n;i++)fn*=i;for(auto r:rows){out<<u128s(r.key)<<' '<<r.aut<<' '<<(fn/r.aut)<<'\n';lab+=fn/r.aut;}cerr<<"FINAL "<<rows.size()<<" labelled "<<lab<<"\n";
 out.close();if(!out){cerr<<"write failed\n";return 1;}
}
