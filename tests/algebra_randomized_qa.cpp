#include <bits/stdc++.h>
#include <boost/multiprecision/cpp_int.hpp>
using namespace std;
using boost::multiprecision::cpp_int;
using i128 = __int128_t;
using u128 = __uint128_t;

[[noreturn]] void die(const string& s){ cerr << "FAIL: " << s << '\n'; exit(1); }

// ---------- Big integer article snippets ----------
using lnum = vector<int>;
constexpr int BASE = 1'000'000'000;
void trim(lnum& a){ while(a.size()>1 && a.back()==0) a.pop_back(); if(a.empty()) a.push_back(0); }
bool is_zero(const lnum& a){ return a.size()==1 && a[0]==0; }
lnum multiply_lnum(const lnum& a,const lnum& b){
    if(is_zero(a)||is_zero(b)) return {0};
    lnum c(a.size()+b.size(),0);
    for(size_t i=0;i<a.size();++i){
        long long carry=0;
        for(size_t j=0;j<b.size()||carry;++j){
            i128 cur=c[i+j]+carry;
            if(j<b.size()) cur+=(i128)a[i]*b[j];
            c[i+j]=int(cur%BASE);
            carry=(long long)(cur/BASE);
        }
    }
    trim(c); return c;
}
cpp_int to_cpp(const lnum& a){ cpp_int x=0; for(int i=(int)a.size()-1;i>=0;--i){x*=BASE;x+=a[i];}return x; }

// ---------- Linear Diophantine article snippets ----------
long long extended_gcd_ld(long long a,long long b,long long& x,long long& y){
    if(b==0){x=1;y=0;return a;}
    long long x1,y1; long long g=extended_gcd_ld(b,a%b,x1,y1);
    x=y1; y=x1-y1*(a/b); return g;
}
bool find_any_solution(long long a,long long b,long long c,long long& x0,long long& y0,long long& g){
    g=extended_gcd_ld(llabs(a),llabs(b),x0,y0);
    if(g==0) return c==0;
    if(c%g!=0) return false;
    x0*=c/g; y0*=c/g; if(a<0)x0=-x0; if(b<0)y0=-y0; return true;
}
long long floor_div(long long a,long long b){assert(b!=0);long long q=a/b,r=a%b;if(r!=0&&((r>0)!=(b>0)))--q;return q;}
long long ceil_div(long long a,long long b){assert(b!=0);long long q=a/b,r=a%b;if(r!=0&&((r>0)==(b>0)))++q;return q;}
bool constrain(long long base,long long step,long long low,long long high,long long& kl,long long& kr){
    if(step==0) return low<=base&&base<=high;
    long long left,right;
    if(step>0){left=ceil_div(low-base,step);right=floor_div(high-base,step);}else{left=ceil_div(high-base,step);right=floor_div(low-base,step);}
    kl=max(kl,left);kr=min(kr,right);return kl<=kr;
}
long long count_solutions(long long a,long long b,long long c,long long minx,long long maxx,long long miny,long long maxy){
    long long x0,y0,g; if(!find_any_solution(a,b,c,x0,y0,g)) return 0;
    if(a==0&&b==0) return (maxx-minx+1)*(maxy-miny+1);
    long long dx=b/g,dy=-a/g; const long long INF=(1LL<<60); long long kl=-INF,kr=INF;
    if(!constrain(x0,dx,minx,maxx,kl,kr))return 0;
    if(!constrain(y0,dy,miny,maxy,kl,kr))return 0;
    return kr-kl+1;
}

// ---------- FFT article snippets ----------
using cd=complex<double>; const double PI=acos(-1.0);
void fft(vector<cd>& a,bool invert){
    int n=(int)a.size();
    for(int i=1,j=0;i<n;++i){int bit=n>>1;for(;j&bit;bit>>=1)j^=bit;j^=bit;if(i<j)swap(a[i],a[j]);}
    for(int len=2;len<=n;len<<=1){double angle=2*PI/len*(invert?-1:1);cd wlen(cos(angle),sin(angle));
        for(int block=0;block<n;block+=len){cd w(1);for(int j=0;j<len/2;++j){cd u=a[block+j],v=a[block+j+len/2]*w;a[block+j]=u+v;a[block+j+len/2]=u-v;w*=wlen;}}}
    if(invert)for(cd&x:a)x/=n;
}
vector<long long> convolution_ll(const vector<int>& a,const vector<int>& b){
    if(a.empty()||b.empty())return{};int need=a.size()+b.size()-1,n=1;while(n<need)n<<=1;
    vector<cd> fa(a.begin(),a.end()),fb(b.begin(),b.end());fa.resize(n);fb.resize(n);fft(fa,false);fft(fb,false);for(int i=0;i<n;++i)fa[i]*=fb[i];fft(fa,true);
    vector<long long> c(need);for(int i=0;i<need;++i)c[i]=llround(fa[i].real());return c;
}
const int NMOD=7'340'033,NROOT=5,NROOT_INV=4'404'020,NROOT_PW=1<<20;
int nmod_pow(int a,long long e){long long r=1;while(e){if(e&1)r=r*a%NMOD;a=(long long)a*a%NMOD;e>>=1;}return(int)r;}
void ntt(vector<int>& a,bool invert){
    int n=a.size();for(int i=1,j=0;i<n;++i){int bit=n>>1;for(;j&bit;bit>>=1)j^=bit;j^=bit;if(i<j)swap(a[i],a[j]);}
    for(int len=2;len<=n;len<<=1){int wlen=invert?NROOT_INV:NROOT;for(int i=len;i<NROOT_PW;i<<=1)wlen=(long long)wlen*wlen%NMOD;
        for(int block=0;block<n;block+=len){int w=1;for(int j=0;j<len/2;++j){int u=a[block+j],v=(long long)a[block+j+len/2]*w%NMOD;a[block+j]=u+v<NMOD?u+v:u+v-NMOD;a[block+j+len/2]=u-v>=0?u-v:u-v+NMOD;w=(long long)w*wlen%NMOD;}}}
    if(invert){int inv_n=nmod_pow(n,NMOD-2);for(int&x:a)x=(long long)x*inv_n%NMOD;}
}

// ---------- Continued fractions floor-sum/sqrt ----------
long long floor_sum_alg(long long n,long long m,long long a,long long b){
    i128 ans=0;while(true){if(a>=m){ans+=(i128)(n-1)*n*(a/m)/2;a%=m;}if(b>=m){ans+=(i128)n*(b/m);b%=m;}i128 y=(i128)a*n+b;if(y<m)break;n=(long long)(y/m);b=(long long)(y%m);swap(m,a);}if(ans>LLONG_MAX)throw overflow_error("overflow");return(long long)ans;
}
vector<long long> sqrt_cf(long long D){
    long long a0=sqrtl((long double)D);while((i128)(a0+1)*(a0+1)<=D)++a0;while((i128)a0*a0>D)--a0;if((i128)a0*a0==D)return{a0};
    vector<long long>a{a0};long long m=0,d=1,x=a0;do{m=d*x-m;d=(D-m*m)/d;x=(a0+m)/d;a.push_back(x);}while(x!=2*a0);return a;
}

// ---------- Factoring exponentiation ----------
const uint32_t mbin_table[32]={
0x00000000,0x00000000,0xd3cfd984,0x9ee62e18,0xe83d9070,0xb59e81e0,0xa17407c0,0xce601f80,
0xf4807f00,0xe701fe00,0xbe07fc00,0xfc1ff800,0xf87ff000,0xf1ffe000,0xe7ffc000,0xdfff8000,
0xffff0000,0xfffe0000,0xfffc0000,0xfff80000,0xfff00000,0xffe00000,0xffc00000,0xff800000,
0xff000000,0xfe000000,0xfc000000,0xf8000000,0xf0000000,0xe0000000,0xc0000000,0x80000000};
uint32_t mbin_log(uint32_t r,uint32_t x){for(unsigned n=2;n<32;++n){uint32_t bit=uint32_t(1)<<n;if(x&bit){x=x+(x<<n);r-=mbin_table[n];}}return r;}
uint32_t mbin_exp(uint32_t r,uint32_t z){for(unsigned n=2;n<32;++n){uint32_t bit=uint32_t(1)<<n;if(z&bit){r=r+(r<<n);z-=mbin_table[n];}}return r;}
uint32_t mbin_power(uint32_t rem,uint32_t base,uint32_t exp){if(base&2u){base=-base;if(exp&1u)rem=-rem;}uint32_t l=mbin_log(0,base);return mbin_exp(rem,l*exp);}
uint32_t mbin_log_fast(uint32_t r,uint32_t x){for(unsigned n=2;n<16;++n){uint32_t bit=uint32_t(1)<<n;if(x&bit){x=x+(x<<n);r-=mbin_table[n];}}r-=x&0xFFFF0000u;return r;}
uint32_t mbin_exp_fast(uint32_t r,uint32_t z){for(unsigned n=2;n<16;++n){uint32_t bit=uint32_t(1)<<n;if(z&bit){r=r+(r<<n);z-=mbin_table[n];}}r*=1u-(z&0xFFFF0000u);return r;}
uint32_t pow_wrap(uint32_t a,uint32_t e){uint32_t r=1;while(e){if(e&1)r*=a;a*=a;e>>=1;}return r;}

// ---------- Montgomery ----------
struct Montgomery64{using u64=uint64_t;using u128=__uint128_t;u64 mod,nprime,r2;explicit Montgomery64(u64 modulus):mod(modulus){if(mod<=1||(mod&1)==0||mod>=(1ULL<<63))throw invalid_argument("bad");u64 inv=1;for(int i=0;i<6;++i)inv*=2-mod*inv;nprime=0-inv;u64 rmod=(u64)((u128(1)<<64)%mod);r2=(u64)((u128)rmod*rmod%mod);}u64 reduce(u128 t)const{u64 q=(u64)t*nprime;u128 u=(t+(u128)q*mod)>>64;u64 result=(u64)u;if(result>=mod)result-=mod;return result;}u64 to_mont(u64 x)const{return reduce((u128)(x%mod)*r2);}u64 from_mont(u64 x)const{return reduce(x);}u64 one()const{return to_mont(1);}u64 multiply(u64 a,u64 b)const{return reduce((u128)a*b);}u64 power(u64 base,u64 e)const{u64 a=to_mont(base),r=one();while(e){if(e&1)r=multiply(r,a);a=multiply(a,a);e>>=1;}return from_mont(r);}};
uint64_t pow_mod_u64(uint64_t a,uint64_t e,uint64_t m){uint64_t r=1%m;a%=m;while(e){if(e&1)r=(u128)r*a%m;a=(u128)a*a%m;e>>=1;}return r;}

// ---------- Discrete logarithm ----------
using int64=long long;
int64 dl_mul(int64 a,int64 b,int64 mod){return(int64)((i128)a*b%mod);}int64 dl_pow(int64 a,int64 e,int64 mod){int64 r=1%mod;a%=mod;if(a<0)a+=mod;while(e){if(e&1)r=dl_mul(r,a,mod);a=dl_mul(a,a,mod);e>>=1;}return r;}
int64 dl_egcd(int64 a,int64 b,int64&x,int64&y){if(b==0){x=1;y=0;return a;}int64 x1,y1,g=dl_egcd(b,a%b,x1,y1);x=y1;y=x1-(a/b)*y1;return g;}
int64 dl_inv(int64 a,int64 mod){int64 x,y,g=dl_egcd(a,mod,x,y);if(g!=1)return-1;x%=mod;if(x<0)x+=mod;return x;}
int64 bsgs_coprime(int64 a,int64 b,int64 mod){if(mod==1)return 0;a%=mod;b%=mod;if(a<0)a+=mod;if(b<0)b+=mod;int64 n=(int64)sqrtl((long double)mod)+1;unordered_map<int64,int64>baby;baby.reserve((size_t)n*2+1);int64 cur=1%mod;for(int64 j=0;j<n;++j){if(!baby.count(cur))baby[cur]=j;cur=dl_mul(cur,a,mod);}int64 an=dl_pow(a,n,mod),factor=dl_inv(an,mod);if(factor==-1)die("BSGS inverse");cur=b;for(int64 i=0;i<=n;++i){auto it=baby.find(cur);if(it!=baby.end())return i*n+it->second;cur=dl_mul(cur,factor,mod);}return-1;}
int64 discrete_log_alg(int64 a,int64 b,int64 mod){if(mod<=0)throw invalid_argument("mod");if(mod==1)return 0;a%=mod;b%=mod;if(a<0)a+=mod;if(b<0)b+=mod;int64 k=1%mod,add=0;while(true){int64 g=gcd(a,mod);if(g==1)break;if(b==k)return add;if(b%g!=0)return-1;b/=g;mod/=g;++add;k=dl_mul(k,a/g,mod);}int64 ik=dl_inv(k,mod);if(ik==-1)return-1;int64 target=dl_mul(b,ik,mod);int64 y=bsgs_coprime(a%mod,target,mod);return y==-1?-1:y+add;}
long long brute_dlog(long long a,long long b,long long m){a%=m;if(a<0)a+=m;b%=m;if(b<0)b+=m;long long cur=1%m;map<long long,int>seen;for(int x=0;;++x){if(cur==b)return x;if(seen.count(cur))return-1;seen[cur]=x;cur=(i128)cur*a%m;}}

// ---------- Primitive/discrete roots ----------
long long pr_pow(long long a,long long e,long long mod){long long r=1%mod;while(e){if(e&1)r=(i128)r*a%mod;a=(i128)a*a%mod;e>>=1;}return r;}
vector<long long> distinct_pf(long long n){vector<long long>f;for(long long p=2;p<=n/p;++p)if(n%p==0){f.push_back(p);while(n%p==0)n/=p;}if(n>1)f.push_back(n);return f;}
long long primitive_root_prime(long long p){if(p==2)return 1;long long phi=p-1;auto f=distinct_pf(phi);for(long long g=2;g<p;++g){bool ok=1;for(long long q:f)if(pr_pow(g,phi/q,p)==1){ok=0;break;}if(ok)return g;}return-1;}
long long normll(long long x,long long m){x%=m;if(x<0)x+=m;return x;}long long root_egcd(long long a,long long b,long long&x,long long&y){if(b==0){x=1;y=0;return a;}long long x1,y1,g=root_egcd(b,a%b,x1,y1);x=y1;y=x1-(a/b)*y1;return g;}long long root_inv(long long a,long long m){long long x,y,g=root_egcd(normll(a,m),m,x,y);if(g!=1)return-1;return normll(x,m);}
vector<long long> discrete_roots(long long k,long long a,long long p){if(p<2||k<=0)throw invalid_argument("bad");a=normll(a,p);if(a==0)return{0};if(p==2)return{1};long long g=primitive_root_prime(p),A=discrete_log_alg(g,a,p);if(A==-1)return{};long long order=p-1,d=gcd(k,order);if(A%d!=0)return{};long long kk=k/d,AA=A/d,mod=order/d,inv=root_inv(normll(kk,mod),mod);if(inv==-1)die("root inv");long long y0=(i128)normll(AA,mod)*inv%mod;vector<long long>r;for(long long t=0;t<d;++t)r.push_back(pr_pow(g,y0+t*mod,p));sort(r.begin(),r.end());r.erase(unique(r.begin(),r.end()),r.end());return r;}

// ---------- CRT/Garner ----------
long long crt_egcd(long long a,long long b,long long&x,long long&y){if(b==0){x=(a>=0?1:-1);y=0;return llabs(a);}long long x1,y1,g=crt_egcd(b,a%b,x1,y1);x=y1;y=x1-(a/b)*y1;return g;}long long cnorm(long long x,long long m){x%=m;if(x<0)x+=m;return x;}
struct CRTResult{bool ok;long long r,mod;};
CRTResult crt_merge(long long a1,long long m1,long long a2,long long m2){a1=cnorm(a1,m1);a2=cnorm(a2,m2);long long x,y,g=crt_egcd(m1,m2,x,y),diff=a2-a1;if(diff%g)return{false,0,0};long long m2g=m2/g,t=(i128)(diff/g)*cnorm(x,m2g)%m2g;t=cnorm(t,m2g);i128 l=(i128)(m1/g)*m2;if(l>LLONG_MAX)throw overflow_error("lcm");long long lm=(long long)l;long long r=(long long)(((i128)a1+(i128)m1*t)%lm);if(r<0)r+=lm;return{true,r,lm};}
long long g_egcd(long long a,long long b,long long&x,long long&y){if(b==0){x=1;y=0;return a;}long long x1,y1,g=g_egcd(b,a%b,x1,y1);x=y1;y=x1-(a/b)*y1;return g;}long long ginv(long long a,long long m){long long x,y,g=g_egcd(cnorm(a,m),m,x,y);if(g!=1)throw invalid_argument("inv");return cnorm(x,m);}vector<long long> garner_digits(vector<long long>a,const vector<long long>&m){int n=m.size();vector<long long>c(n);for(int i=0;i<n;++i){a[i]=cnorm(a[i],m[i]);long long v=a[i];for(int j=0;j<i;++j){v=cnorm(v-c[j],m[i]);v=(i128)v*ginv(m[j],m[i])%m[i];}c[i]=v;}return c;}i128 restore_exact(const vector<long long>&c,const vector<long long>&m){i128 x=0;for(int i=(int)c.size()-1;i>=0;--i)x=x*m[i]+c[i];return x;}

// ---------- factorial without p ----------
long long factorial_without_p(long long n,int p){vector<long long>fact(p);fact[0]=1;for(int i=1;i<p;++i)fact[i]=fact[i-1]*i%p;long long r=1;while(n>1){long long blocks=n/p;if(blocks&1)r=(p-r)%p;r=r*fact[n%p]%p;n/=p;}return r;}

bool is_prime_small(int n){if(n<2)return false;for(int d=2;d*d<=n;++d)if(n%d==0)return false;return true;}

int main(){
    mt19937_64 rng(0xC0FFEE123456789ULL);

    // Big integer multiplication.
    for(int tc=0;tc<3000;++tc){int n=rng()%80+1,m=rng()%80+1;lnum a(n),b(m);for(int&x:a)x=rng()%BASE;for(int&x:b)x=rng()%BASE;trim(a);trim(b);auto c=multiply_lnum(a,b);if(to_cpp(c)!=to_cpp(a)*to_cpp(b))die("big integer multiplication");}
    cout<<"big_integer OK\n";

    // Floor/ceil division and bounded Diophantine counts.
    for(long long a=-50;a<=50;++a)for(long long b=-20;b<=20;++b)if(b){long double z=(long double)a/b;if(floor_div(a,b)!=(long long)floor(z)||ceil_div(a,b)!=(long long)ceil(z))die("floor/ceil division");}
    for(int tc=0;tc<200000;++tc){long long a=(int)(rng()%21)-10,b=(int)(rng()%21)-10,c=(int)(rng()%41)-20;long long lx=(int)(rng()%11)-5,hx=lx+rng()%11,ly=(int)(rng()%11)-5,hy=ly+rng()%11;long long brute=0;for(long long x=lx;x<=hx;++x)for(long long y=ly;y<=hy;++y)brute+=a*x+b*y==c;long long got=count_solutions(a,b,c,lx,hx,ly,hy);if(got!=brute){cerr<<a<<' '<<b<<' '<<c<<' '<<lx<<' '<<hx<<' '<<ly<<' '<<hy<<" got "<<got<<" brute "<<brute<<'\n';die("diophantine count");}}
    cout<<"linear_diophantine OK\n";

    // FFT convolution.
    for(int tc=0;tc<5000;++tc){int n=rng()%70,m=rng()%70;vector<int>a(n),b(m);for(int&x:a)x=(int)(rng()%2001)-1000;for(int&x:b)x=(int)(rng()%2001)-1000;auto got=convolution_ll(a,b);vector<long long>want(n&&m?n+m-1:0);for(int i=0;i<n;++i)for(int j=0;j<m;++j)want[i+j]+=(long long)a[i]*b[j];if(got!=want)die("FFT convolution");}
    cout<<"fft OK\n";

    // NTT convolution.
    for(int tc=0;tc<5000;++tc){int na=rng()%100,nb=rng()%100;if(!na||!nb)continue;vector<int>a(na),b(nb);for(int&x:a)x=rng()%NMOD;for(int&x:b)x=rng()%NMOD;int need=na+nb-1,n=1;while(n<need)n<<=1;vector<int>fa=a,fb=b;fa.resize(n);fb.resize(n);ntt(fa,false);ntt(fb,false);for(int i=0;i<n;++i)fa[i]=(long long)fa[i]*fb[i]%NMOD;ntt(fa,true);for(int k=0;k<need;++k){long long want=0;for(int i=max(0,k-nb+1);i<na&&i<=k;++i)want=(want+(long long)a[i]*b[k-i])%NMOD;if(fa[k]!=want)die("NTT convolution");}}
    cout<<"ntt OK\n";

    // floor_sum.
    for(int tc=0;tc<300000;++tc){long long n=rng()%80,m=rng()%80+1,a=rng()%250,b=rng()%250;long long want=0;for(long long i=0;i<n;++i)want+=(a*i+b)/m;long long got=floor_sum_alg(n,m,a,b);if(got!=want){cerr<<n<<' '<<m<<' '<<a<<' '<<b<<' '<<got<<' '<<want<<'\n';die("floor_sum");}}
    vector<pair<int,vector<long long>>> known={{2,{1,2}},{3,{1,1,2}},{5,{2,4}},{6,{2,2,4}},{7,{2,1,1,1,4}},{13,{3,1,1,1,1,6}},{23,{4,1,3,1,8}}};for(auto&[D,v]:known)if(sqrt_cf(D)!=v)die("sqrt continued fraction");
    cout<<"continued_fractions OK\n";

    // Factoring exponentiation.
    for(int tc=0;tc<500000;++tc){uint32_t rem=rng(),base=(uint32_t)rng()|1u,exp=rng();uint32_t want=rem*pow_wrap(base,exp),got=mbin_power(rem,base,exp);if(got!=want){cerr<<rem<<' '<<base<<' '<<exp<<' '<<got<<' '<<want<<'\n';die("factoring exponentiation");}uint32_t normalized=(base&2u)?-base:base;if(mbin_log(0,normalized)!=mbin_log_fast(0,normalized))die("fast log");uint32_t z=mbin_log(0,normalized)*(uint32_t)exp;if(mbin_exp(rem,z)!=mbin_exp_fast(rem,z))die("fast exp");}
    cout<<"factoring_exponentiation OK\n";

    // Montgomery multiplication and power.
    for(int tc=0;tc<20000;++tc){uint64_t mod=(rng()&((1ULL<<63)-1))|1ULL;if(mod<=1)mod=3;Montgomery64 M(mod);uint64_t a=rng()%mod,b=rng()%mod;uint64_t am=M.to_mont(a),bm=M.to_mont(b);uint64_t got=M.from_mont(M.multiply(am,bm)),want=(u128)a*b%mod;if(got!=want)die("Montgomery multiply");uint64_t e=rng();if(M.power(a,e)!=pow_mod_u64(a,e,mod))die("Montgomery power");}
    cout<<"montgomery OK\n";

    // Discrete logarithm for all small moduli.
    for(int m=1;m<=220;++m)for(int a=0;a<m;++a)for(int b=0;b<m;++b){long long got=discrete_log_alg(a,b,m),want=brute_dlog(a,b,m);if(got!=want){cerr<<"m="<<m<<" a="<<a<<" b="<<b<<" got="<<got<<" want="<<want<<'\n';die("discrete log");}}
    cout<<"discrete_log OK\n";

    // Primitive roots and all discrete roots over small primes.
    for(int p=2;p<=300;++p)if(is_prime_small(p)){long long g=primitive_root_prime(p);set<long long>s;for(int e=0;e<p-1;++e)s.insert(pr_pow(g,e,p));if((int)s.size()!=p-1)die("primitive root");for(int k=1;k<=30;++k)for(int a=0;a<p;++a){auto got=discrete_roots(k,a,p);vector<long long>want;for(int x=0;x<p;++x)if(pr_pow(x,k,p)==a)want.push_back(x);if(got!=want){cerr<<"p="<<p<<" k="<<k<<" a="<<a<<'\n';die("discrete roots");}}}
    cout<<"primitive_and_discrete_roots OK\n";

    // CRT and Garner.
    for(int tc=0;tc<100000;++tc){long long m1=rng()%30+1,m2=rng()%30+1,a1=(int)(rng()%101)-50,a2=(int)(rng()%101)-50;auto got=crt_merge(a1,m1,a2,m2);long long l=lcm(m1,m2),w=-1;for(long long x=0;x<l;++x)if(x%m1==cnorm(a1,m1)&&x%m2==cnorm(a2,m2)){w=x;break;}if((w!=-1)!=got.ok||(got.ok&&(got.r!=w||got.mod!=l)))die("CRT merge");}
    vector<long long> primes={2,3,5,7,11,13,17,19};for(int tc=0;tc<50000;++tc){shuffle(primes.begin(),primes.end(),rng);int n=rng()%6+1;vector<long long>m(primes.begin(),primes.begin()+n),a(n);i128 product=1;for(auto x:m)product*=x;long long X=(long long)(rng()%(uint64_t)product);for(int i=0;i<n;++i)a[i]=X%m[i];auto c=garner_digits(a,m);if(restore_exact(c,m)!=X)die("Garner exact");}
    cout<<"crt_garner OK\n";

    // Factorial with p-factors removed.
    vector<int> ps={2,3,5,7,11,13,17,19,23,29,31};for(int p:ps)for(int n=0;n<=500;++n){long long want=1;for(int i=1;i<=n;++i){int x=i;while(x%p==0)x/=p;want=want*(x%p)%p;}if(factorial_without_p(n,p)!=want){cerr<<p<<' '<<n<<'\n';die("factorial without p");}}
    cout<<"factorial_mod_p OK\n";

    cout<<"ALL ALGEBRA QA TESTS PASSED\n";
}
