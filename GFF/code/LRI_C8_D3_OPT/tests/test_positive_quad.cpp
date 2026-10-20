#include <algorithm>
#include "../src/positive_quad.hpp"
#include <iostream>
#include <random>
#include <limits>
#include <quadmath.h>
#include <iomanip>
static unsigned long long count=0,nans=0;
__float128 number(u128 u){__float128 x;std::memcpy(&x,&u,16);return x;}
u128 raw(__float128 x){u128 u;std::memcpy(&u,&x,16);return u;}
void check(u128 ua,u128 ub){auto a=number(ua),b=number(ub);volatile __float128 va=a,vb=b;auto want=va+vb;auto got=positive_quad_add(a,b);++count;
 if(isnanq(want)&&isnanq(got)){++nans;return;}
 if(raw(want)!=raw(got)){std::cerr<<"mismatch at "<<count<<"\n";std::exit(2);}}
int main(){if(std::fegetround()!=FE_TONEAREST)return 3;std::mt19937_64 rng(62714597);constexpr u128 h=u128(1)<<112,mask=h-1;
 for(unsigned long long i=0;i<4000000;++i){u128 a=(u128(rng())<<64)|rng(),b=(u128(rng())<<64)|rng();check(a,b);a&=~(u128(1)<<127);b&=~(u128(1)<<127);check(a,b);unsigned e=1+rng()%32766;unsigned delta=rng()%120;u128 fa=(u128(rng())<<64|rng())&mask,fb=(u128(rng())<<64|rng())&mask;check((u128(e)<<112)|fa,(u128(std::max(1,int(e)-int(delta)))<<112)|fb);}
 for(unsigned e: {1u,2u,100u,16383u,32765u,32766u})for(unsigned delta=0;delta<120;++delta)for(u128 ma:{u128(0),u128(1),h/2-1,h/2,mask-1,mask})for(u128 mb:{u128(0),u128(1),h/2-1,h/2,mask-1,mask}){u128 a=(u128(e)<<112)|ma,b=(u128(std::max(1,int(e)-int(delta)))<<112)|mb;check(a,b);check(b,a);}
 std::cout<<"{\"status\":\"passed\",\"test_cases\":"<<count<<",\"bitwise_checks\":"<<(count-nans)<<",\"nan_result_cases\":"<<nans<<",\"seed\":62714597,\"rounding\":\"FE_TONEAREST\"}\n";}
