#include "../src/point.hpp"
// Compares the optimized expression with a literal transcription of the original.
// Stress configurations deliberately include tiny cluster ratios; the production
// promotion logic is tested separately by executable replays.
template<class T>pair<LD,LD> compare(const Graph&g,int L,const TreeSample&s,PointScratch<T>&sc){LD r1,r2;auto a=point_oracle<T>(g,L,7-L,s,&r1);auto b=point_fast<T>(g,L,7-L,s,&r2,sc);LD mx=0;
 for(int k=0;k<=7-L;k++){T da=a[k]-b[k];T ab=a[k]<0?-a[k]:a[k];T scale=ab>T(1)?ab:T(1);LD diff=abs((LD)(da/scale));require(isfinite(diff),"nonfinite test difference");mx=max(mx,diff);}return{mx,abs(r1-r2)};}
int main(int argc,char**argv){try{
 require(argc==3,"test_points INPUTS OUTPUT");string inputs=argv[1];uint64_t checks=0;LD ml=0,mq=0,mm=0,ratio=0;mt19937_64 rng(76541829);
 for(int L=3;L<=7;L++){
  Options o;o.inputs=inputs;o.L=L;o.mode="qmc";ifstream f(inputs+"/L"+to_string(L)+"_coord.txt");int ll,ng;f>>ll>>ng;vector<int>ids;string rest;getline(f,rest);
  for(int i=0;i<ng;i++){int gi,p,pr,nt;LD wa,wb;f>>gi>>wa>>wb>>p>>pr>>nt;getline(f,rest);if(!p&&nt&&nt<200&&!pr)ids.push_back(i);for(int j=0;j<nt;j++)getline(f,rest);}
  require(!ids.empty(),"no test graphs");vector<Work>w;for(int j=0;j<8;j++){int gi=ids[size_t(j)*(ids.size()-1)/7];w.push_back({uint64_t(j),0,gi,0,1,1});}
  vector<int>slot;auto gs=load_graphs(o,w,ng,slot);PointScratch<LD>sl;PointScratch<__float128>sq;PointScratch<MP>sm;
  for(auto&g:gs){auto p=prep_tree(g,L,.8L,false);for(int j=0;j<6;j++){
   LD u[16];for(int k=0;k<2*L-1;k++)u[k]=((LD)(rng()>>12)+.5L)/4503599627370496.L;auto s=draw_tree(p,u);
   if(j==4)for(int k=1;k<L;k++)s.lt[k]=-LD(40+k*15);
   if(j==5)for(int k=1;k<L;k++)s.lt[k]=-LD(350+k*30);
   auto q=compare<__float128>(g,L,s,sq);mq=max(mq,q.first);ratio=max(ratio,q.second);checks++;
   auto m=compare<MP>(g,L,s,sm);mm=max(mm,m.first);checks++;
   if(j<4){auto l=compare<LD>(g,L,s,sl);ml=max(ml,l.first);checks++;}
  }}
 }
 ofstream f(argv[2]);f<<setprecision(24)<<"{\"comparisons\":"<<checks<<",\"max_long_double_normalized\":"<<ml<<",\"max_binary128_normalized\":"<<mq<<",\"max_mp100_normalized\":"<<mm<<",\"max_ratio_difference\":"<<ratio<<"}\n";
 require(ml<1e-12L&&mq<1e-25L&&mm<1e-45L,"point comparison failed");return 0;
}catch(exception&e){cerr<<e.what()<<'\n';return 2;}}
