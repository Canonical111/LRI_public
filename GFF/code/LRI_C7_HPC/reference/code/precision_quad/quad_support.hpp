#pragma once
#include <bits/stdc++.h>
#include <quadmath.h>
using LD=__float128;
inline LD abs(LD v){return fabsq(v);}
inline std::ostream& operator<<(std::ostream&o,LD v){char b[180];quadmath_snprintf(b,sizeof b,"%.*Qg",(int)o.precision(),v);o<<b;return o;}
inline std::istream& operator>>(std::istream&i,LD&v){std::string s;i>>s;v=strtoflt128(s.c_str(),nullptr);return i;}
