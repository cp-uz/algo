#include <bits/stdc++.h>
#include <boost/multiprecision/cpp_int.hpp>
using namespace std;
using boost::multiprecision::cpp_int;

namespace primeqa {

using u64 = uint64_t;
using u128 = __uint128_t;

u64 mod_mul(u64 a, u64 b, u64 mod) {
    return (u128)a * b % mod;
}

u64 mod_pow(u64 a, u64 e, u64 mod) {
    u64 result = 1;
    while (e > 0) {
        if (e & 1) result = mod_mul(result, a, mod);
        a = mod_mul(a, a, mod);
        e >>= 1;
    }
    return result;
}

bool miller_witness(u64 n, u64 a, u64 d, int s) {
    if (a % n == 0) return true;
    u64 x = mod_pow(a % n, d, n);
    if (x == 1 || x == n - 1) return true;
    for (int r = 1; r < s; ++r) {
        x = mod_mul(x, x, n);
        if (x == n - 1) return true;
    }
    return false;
}

bool is_prime(u64 n) {
    if (n < 2) return false;
    for (u64 p : {2ULL, 3ULL, 5ULL, 7ULL, 11ULL, 13ULL, 17ULL,
                  19ULL, 23ULL, 29ULL, 31ULL, 37ULL}) {
        if (n % p == 0) return n == p;
    }

    u64 d = n - 1;
    int s = 0;
    while ((d & 1) == 0) {
        d >>= 1;
        ++s;
    }

    // Barcha 64-bit unsigned n uchun yetarli deterministik bazalar.
    for (u64 a : {2ULL, 325ULL, 9375ULL, 28178ULL,
                  450775ULL, 9780504ULL, 1795265022ULL}) {
        if (!miller_witness(n, a, d, s)) return false;
    }
    return true;
}

} // namespace primeqa

namespace factorqa {

using u64 = uint64_t;
using u128 = __uint128_t;

u64 mul_mod(u64 a, u64 b, u64 mod) {
    return (u128)a * b % mod;
}

u64 pow_mod(u64 a, u64 e, u64 mod) {
    u64 r = 1;
    while (e) {
        if (e & 1) r = mul_mod(r, a, mod);
        a = mul_mod(a, a, mod);
        e >>= 1;
    }
    return r;
}

bool is_prime64(u64 n) {
    if (n < 2) return false;
    for (u64 p : {2ULL,3ULL,5ULL,7ULL,11ULL,13ULL,17ULL,19ULL,23ULL,29ULL,31ULL,37ULL})
        if (n % p == 0) return n == p;

    int s = 0;
    u64 d = n - 1;
    while ((d & 1) == 0) d >>= 1, ++s;

    for (u64 a : {2ULL,325ULL,9375ULL,28178ULL,450775ULL,9780504ULL,1795265022ULL}) {
        if (a % n == 0) continue;
        u64 x = pow_mod(a % n, d, n);
        if (x == 1 || x == n - 1) continue;
        bool composite = true;
        for (int r = 1; r < s; ++r) {
            x = mul_mod(x, x, n);
            if (x == n - 1) {
                composite = false;
                break;
            }
        }
        if (composite) return false;
    }
    return true;
}

mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

u64 pollard_rho(u64 n) {
    if (n % 2 == 0) return 2;
    if (n % 3 == 0) return 3;

    while (true) {
        u64 c = uniform_int_distribution<u64>(1, n - 1)(rng);
        u64 x = uniform_int_distribution<u64>(0, n - 1)(rng);
        u64 y = x;
        u64 d = 1;

        auto f = [&](u64 v) {
            return (u64)(((u128)mul_mod(v, v, n) + c) % n);
        };

        while (d == 1) {
            x = f(x);
            y = f(f(y));
            u64 diff = x > y ? x - y : y - x;
            d = std::gcd(diff, n);
        }
        if (d != n) return d;
        // Omadsiz sikl: boshqa c va boshlang‘ich nuqta bilan qayta urinamiz.
    }
}

void factor_rec(u64 n, vector<u64>& out) {
    if (n == 1) return;
    if (is_prime64(n)) {
        out.push_back(n);
        return;
    }
    u64 d = pollard_rho(n);
    factor_rec(d, out);
    factor_rec(n / d, out);
}

vector<pair<u64,int>> factorize64(u64 n) {
    if (n == 0) throw invalid_argument("n must be positive");
    vector<u64> raw;
    factor_rec(n, raw);
    sort(raw.begin(), raw.end());

    vector<pair<u64,int>> result;
    for (u64 p : raw) {
        if (result.empty() || result.back().first != p)
            result.push_back({p, 1});
        else
            ++result.back().second;
    }
    return result;
}

} // namespace factorqa

namespace crtqa {

struct CRTResult {
    bool ok;
    long long r;   // 0 <= r < mod
    long long mod;
};

long long ext_gcd(long long a, long long b,
                  long long& x, long long& y) {
    if (b == 0) {
        x = (a >= 0 ? 1 : -1);
        y = 0;
        return llabs(a);
    }
    long long x1, y1;
    long long g = ext_gcd(b, a % b, x1, y1);
    x = y1;
    y = x1 - (a / b) * y1;
    return g;
}

long long norm(long long x, long long m) {
    x %= m;
    if (x < 0) x += m;
    return x;
}

CRTResult crt_merge(long long a1, long long m1,
                    long long a2, long long m2) {
    if (m1 <= 0 || m2 <= 0)
        throw invalid_argument("moduli must be positive");

    a1 = norm(a1, m1);
    a2 = norm(a2, m2);

    long long x, y;
    long long g = ext_gcd(m1, m2, x, y);
    long long diff = a2 - a1;
    if (diff % g != 0) return {false, 0, 0};

    long long m2g = m2 / g;
    // x — (m1/g) ning m2/g modul bo‘yicha teskarisi.
    long long t = (long long)((__int128)(diff / g)
                              * norm(x, m2g) % m2g);
    t = norm(t, m2g);

    __int128 lcm128 = (__int128)(m1 / g) * m2;
    if (lcm128 > numeric_limits<long long>::max())
        throw overflow_error("combined modulus does not fit in int64");
    long long lcm = (long long)lcm128;

    long long r = (long long)(((__int128)a1 + (__int128)m1 * t) % lcm);
    if (r < 0) r += lcm;
    return {true, r, lcm};
}


CRTResult crt_system(const vector<long long>& a,
                     const vector<long long>& m) {
    if (a.size() != m.size())
        throw invalid_argument("size mismatch");

    CRTResult cur{true, 0, 1};
    for (size_t i = 0; i < a.size() && cur.ok; ++i)
        cur = crt_merge(cur.r, cur.mod, a[i], m[i]);
    return cur;
}


long long crt_pairwise_coprime(const vector<long long>& a,
                               const vector<long long>& m) {
    __int128 product = 1;
    for (long long mod : m) product *= mod;
    if (product > numeric_limits<long long>::max())
        throw overflow_error("product does not fit in int64");
    long long M = (long long)product;

    __int128 ans = 0;
    for (size_t i = 0; i < m.size(); ++i) {
        long long Mi = M / m[i];
        long long inv, y;
        long long g = ext_gcd(Mi, m[i], inv, y);
        if (g != 1) throw invalid_argument("moduli are not pairwise coprime");
        inv = norm(inv, m[i]);
        ans = (ans + (__int128)norm(a[i], m[i]) * Mi % M * inv) % M;
    }
    return (long long)ans;
}

} // namespace crtqa

namespace garnerqa {

long long norm(long long x, long long m) {
    x %= m;
    if (x < 0) x += m;
    return x;
}

long long ext_gcd(long long a, long long b,
                  long long& x, long long& y) {
    if (b == 0) {
        x = 1;
        y = 0;
        return a;
    }
    long long x1, y1;
    long long g = ext_gcd(b, a % b, x1, y1);
    x = y1;
    y = x1 - (a / b) * y1;
    return g;
}

long long inv_mod(long long a, long long m) {
    long long x, y;
    long long g = ext_gcd(norm(a, m), m, x, y);
    if (g != 1) throw invalid_argument("inverse does not exist");
    return norm(x, m);
}

vector<long long> garner_digits(vector<long long> a,
                                const vector<long long>& m) {
    int n = (int)m.size();
    if ((int)a.size() != n) throw invalid_argument("size mismatch");

    vector<long long> c(n);
    for (int i = 0; i < n; ++i) {
        a[i] = norm(a[i], m[i]);
        long long value = a[i];
        for (int j = 0; j < i; ++j) {
            value = norm(value - c[j], m[i]);
            value = (long long)((__int128)value
                                * inv_mod(m[j], m[i]) % m[i]);
        }
        c[i] = value;
    }
    return c;
}


long long mul_mod(long long a, long long b, long long mod) {
    return (long long)((__int128)a * b % mod);
}

long long garner_mod(vector<long long> a,
                     vector<long long> m,
                     long long target_mod) {
    if (a.size() != m.size() || target_mod <= 0)
        throw invalid_argument("bad Garner input");

    int n = (int)a.size();
    m.push_back(target_mod);

    vector<long long> coefficient(n + 1, 1);
    vector<long long> constant(n + 1, 0);

    for (int k = 0; k < n; ++k) {
        a[k] = norm(a[k], m[k]);
        long long t = norm(a[k] - constant[k], m[k]);
        t = mul_mod(t, inv_mod(coefficient[k], m[k]), m[k]);

        for (int i = k + 1; i <= n; ++i) {
            constant[i] = (long long)(((__int128)constant[i]
                               + mul_mod(coefficient[i], t, m[i])) % m[i]);
            coefficient[i] = mul_mod(coefficient[i], m[k], m[i]);
        }
    }
    return constant[n];
}


__int128 restore_exact(const vector<long long>& c,
                       const vector<long long>& m) {
    __int128 x = 0;
    for (int i = (int)c.size() - 1; i >= 0; --i)
        x = x * m[i] + c[i];
    return x;
}

} // namespace garnerqa

namespace factqa {

long long factorial_without_p(long long n, int p) {
    if (n < 0 || p < 2)
        throw invalid_argument("need n >= 0 and prime p");

    vector<long long> fact(p);
    fact[0] = 1;
    for (int i = 1; i < p; ++i)
        fact[i] = fact[i - 1] * i % p;

    long long result = 1;
    while (n > 1) {
        long long full_blocks = n / p;
        if (full_blocks & 1)
            result = (p - result) % p; // Wilson: (p-1)! = -1
        result = result * fact[n % p] % p;
        n /= p;
    }
    return result;
}


long long exponent_in_factorial(long long n, long long p) {
    long long e = 0;
    while (n > 0) {
        n /= p;
        e += n;
    }
    return e;
}

} // namespace factqa

namespace linqa {

long long ext_gcd(long long a, long long b,
                  long long& x, long long& y) {
    if (b == 0) {
        x = (a >= 0 ? 1 : -1);
        y = 0;
        return llabs(a);
    }
    long long x1, y1;
    long long g = ext_gcd(b, a % b, x1, y1);
    x = y1;
    y = x1 - (a / b) * y1;
    return g;
}

long long normalize(long long x, long long mod) {
    x %= mod;
    if (x < 0) x += mod;
    return x;
}

vector<long long> solve_linear_congruence(
        long long a, long long b, long long m) {
    if (m <= 0) throw invalid_argument("modulus must be positive");

    long long g = std::gcd(llabs(a), m);
    if (b % g != 0) return {};

    long long aa = a / g;
    long long bb = b / g;
    long long mm = m / g;

    long long inv, y;
    long long got = ext_gcd(aa, mm, inv, y);
    // gcd(aa, mm) = 1
    assert(got == 1);
    inv = normalize(inv, mm);

    long long x0 = (long long)((__int128)normalize(bb, mm)
                               * inv % mm);

    vector<long long> ans;
    ans.reserve((size_t)g);
    for (long long k = 0; k < g; ++k)
        ans.push_back(x0 + k * mm);
    return ans;
}

} // namespace linqa

namespace dlogqa {

using int64 = long long;
using i128 = __int128_t;

int64 mul_mod(int64 a, int64 b, int64 mod) {
    return (int64)((i128)a * b % mod);
}

int64 mod_pow(int64 a, int64 e, int64 mod) {
    int64 r = 1 % mod;
    a %= mod;
    if (a < 0) a += mod;
    while (e > 0) {
        if (e & 1) r = mul_mod(r, a, mod);
        a = mul_mod(a, a, mod);
        e >>= 1;
    }
    return r;
}

int64 ext_gcd(int64 a, int64 b, int64& x, int64& y) {
    if (b == 0) {
        x = 1;
        y = 0;
        return a;
    }
    int64 x1, y1;
    int64 g = ext_gcd(b, a % b, x1, y1);
    x = y1;
    y = x1 - (a / b) * y1;
    return g;
}

int64 inverse_mod(int64 a, int64 mod) {
    int64 x, y;
    int64 g = ext_gcd(a, mod, x, y);
    if (g != 1) return -1;
    x %= mod;
    if (x < 0) x += mod;
    return x;
}

// gcd(a, mod) = 1 bo‘lishi shart. Yechim bo‘lmasa -1.
int64 bsgs_coprime(int64 a, int64 b, int64 mod) {
    if (mod == 1) return 0;
    a %= mod;
    b %= mod;
    if (a < 0) a += mod;
    if (b < 0) b += mod;

    int64 n = (int64)sqrtl((long double)mod) + 1;

    unordered_map<int64, int64> baby;
    baby.reserve((size_t)n * 2 + 1);
    int64 cur = 1 % mod;
    for (int64 j = 0; j < n; ++j) {
        if (!baby.count(cur)) baby[cur] = j;
        cur = mul_mod(cur, a, mod);
    }

    int64 a_n = mod_pow(a, n, mod);
    int64 factor = inverse_mod(a_n, mod);
    assert(factor != -1);

    cur = b;
    for (int64 i = 0; i <= n; ++i) {
        auto it = baby.find(cur);
        if (it != baby.end()) return i * n + it->second;
        cur = mul_mod(cur, factor, mod);
    }
    return -1;
}


// Eng kichik x >= 0; yechim bo‘lmasa -1.
int64 discrete_log(int64 a, int64 b, int64 mod) {
    if (mod <= 0) throw invalid_argument("modulus must be positive");
    if (mod == 1) return 0;

    a %= mod;
    b %= mod;
    if (a < 0) a += mod;
    if (b < 0) b += mod;

    int64 k = 1 % mod;
    int64 add = 0;

    while (true) {
        int64 g = std::gcd(a, mod);
        if (g == 1) break;
        if (b == k) return add;
        if (b % g != 0) return -1;

        b /= g;
        mod /= g;
        ++add;
        k = mul_mod(k, a / g, mod);
    }

    // k * a^y = b (mod mod), y = x - add
    int64 inv_k = inverse_mod(k, mod);
    if (inv_k == -1) return -1;
    int64 target = mul_mod(b, inv_k, mod);
    int64 y = bsgs_coprime(a % mod, target, mod);
    return y == -1 ? -1 : y + add;
}

} // namespace dlogqa

namespace primrootqa {

long long mod_pow(long long a, long long e, long long mod) {
    long long r = 1 % mod;
    while (e > 0) {
        if (e & 1) r = (long long)((__int128)r * a % mod);
        a = (long long)((__int128)a * a % mod);
        e >>= 1;
    }
    return r;
}

vector<long long> distinct_prime_factors(long long n) {
    vector<long long> factors;
    for (long long p = 2; p <= n / p; ++p) {
        if (n % p != 0) continue;
        factors.push_back(p);
        while (n % p == 0) n /= p;
    }
    if (n > 1) factors.push_back(n);
    return factors;
}

// p tub bo‘lishi shart.
long long primitive_root_prime(long long p) {
    if (p == 2) return 1;
    long long phi = p - 1;
    vector<long long> factors = distinct_prime_factors(phi);

    for (long long g = 2; g < p; ++g) {
        bool ok = true;
        for (long long q : factors) {
            if (mod_pow(g, phi / q, p) == 1) {
                ok = false;
                break;
            }
        }
        if (ok) return g;
    }
    return -1; // tub p uchun bu sodir bo‘lmaydi
}


long long multiplicative_order(long long a, long long mod,
                               long long phi,
                               const vector<long long>& prime_factors) {
    if (std::gcd(a, mod) != 1) return -1;
    long long order = phi;
    for (long long q : prime_factors) {
        while (order % q == 0 &&
               mod_pow(a, order / q, mod) == 1)
            order /= q;
    }
    return order;
}

} // namespace primrootqa

namespace rootsqa {
using dlogqa::discrete_log;
using primrootqa::primitive_root_prime;
long long norm(long long x, long long m) {
    x %= m;
    if (x < 0) x += m;
    return x;
}

long long ext_gcd(long long a, long long b,
                  long long& x, long long& y) {
    if (b == 0) {
        x = 1;
        y = 0;
        return a;
    }
    long long x1, y1;
    long long g = ext_gcd(b, a % b, x1, y1);
    x = y1;
    y = x1 - (a / b) * y1;
    return g;
}

long long inverse_mod(long long a, long long m) {
    long long x, y;
    long long g = ext_gcd(norm(a, m), m, x, y);
    if (g != 1) return -1;
    return norm(x, m);
}

long long mod_pow(long long a, long long e, long long mod) {
    long long r = 1 % mod;
    while (e > 0) {
        if (e & 1) r = (long long)((__int128)r * a % mod);
        a = (long long)((__int128)a * a % mod);
        e >>= 1;
    }
    return r;
}

vector<long long> discrete_roots_prime(long long k,
                                       long long a,
                                       long long p) {
    if (p < 2 || k <= 0)
        throw invalid_argument("p must be prime and k positive");
    a = norm(a, p);

    if (a == 0) return {0};
    if (p == 2) return {1};

    long long g = primitive_root_prime(p);
    long long A = discrete_log(g, a, p);
    if (A == -1) return {}; // primitiv g uchun a != 0 da sodir bo‘lmaydi

    long long order = p - 1;
    long long d = std::gcd(k, order);
    if (A % d != 0) return {};

    long long kk = k / d;
    long long AA = A / d;
    long long mod = order / d;
    long long inv = inverse_mod(norm(kk, mod), mod);
    assert(inv != -1);

    long long y0 = (long long)((__int128)norm(AA, mod) * inv % mod);
    vector<long long> roots;
    roots.reserve((size_t)d);
    for (long long t = 0; t < d; ++t) {
        long long y = y0 + t * mod;
        roots.push_back(mod_pow(g, y, p));
    }
    sort(roots.begin(), roots.end());
    roots.erase(unique(roots.begin(), roots.end()), roots.end());
    return roots;
}

} // namespace rootsqa

namespace montqa {

struct Montgomery64 {
    using u64 = uint64_t;
    using u128 = __uint128_t;

    u64 mod;
    u64 nprime; // -mod^{-1} (mod 2^64)
    u64 r2;     // R^2 (mod mod)

    explicit Montgomery64(u64 modulus) : mod(modulus) {
        if (mod <= 1 || (mod & 1) == 0 || mod >= (1ULL << 63))
            throw invalid_argument("need odd 1 < modulus < 2^63");

        // Newton iteratsiyasi: x <- x(2-mod*x).
        // x avval mod 2 bo‘yicha to‘g‘ri; har qadam aniqlik bitlarini ikki baravar qiladi.
        u64 inv = 1;
        for (int i = 0; i < 6; ++i)
            inv *= 2 - mod * inv;
        nprime = 0 - inv;

        u64 r_mod = (u64)((u128(1) << 64) % mod);
        r2 = (u64)((u128)r_mod * r_mod % mod);
    }

    // 0 <= t < mod*R bo‘lgan holat uchun.
    u64 reduce(u128 t) const {
        u64 q = (u64)t * nprime; // avtomatik mod 2^64
        u128 u = (t + (u128)q * mod) >> 64;
        u64 result = (u64)u;
        if (result >= mod) result -= mod;
        return result;
    }

    u64 to_mont(u64 x) const {
        return reduce((u128)(x % mod) * r2);
    }

    u64 from_mont(u64 x) const {
        return reduce(x);
    }

    u64 one() const {
        return to_mont(1);
    }

    u64 multiply(u64 a_mont, u64 b_mont) const {
        return reduce((u128)a_mont * b_mont);
    }

    u64 power(u64 base, uint64_t exponent) const {
        u64 a = to_mont(base);
        u64 r = one();
        while (exponent > 0) {
            if (exponent & 1) r = multiply(r, a);
            a = multiply(a, a);
            exponent >>= 1;
        }
        return from_mont(r);
    }
};

} // namespace montqa

namespace btqa {

// Raqamlar eng kichik darajadan boshlab qaytariladi.
vector<int> to_balanced_ternary_unsigned(uint64_t n) {
    vector<int> digits;
    while (n > 0) {
        int r = (int)(n % 3);
        n /= 3;
        if (r == 2) {
            digits.push_back(-1);
            ++n;
        } else {
            digits.push_back(r);
        }
    }
    if (digits.empty()) digits.push_back(0);
    return digits;
}


vector<int> to_balanced_ternary(long long value) {
    // LLONG_MIN ni ham xavfsiz unsigned modulga o‘tkazamiz.
    uint64_t magnitude;
    if (value >= 0)
        magnitude = (uint64_t)value;
    else
        magnitude = uint64_t(-(value + 1)) + 1;

    vector<int> d = to_balanced_ternary_unsigned(magnitude);
    if (value < 0)
        for (int& x : d) x = -x;
    return d;
}

string balanced_ternary_string(long long value) {
    vector<int> d = to_balanced_ternary(value);
    string s;
    for (auto it = d.rbegin(); it != d.rend(); ++it) {
        if (*it == -1) s += 'T';
        else s += char('0' + *it);
    }
    return s;
}


long long from_balanced_ternary(const string& s) {
    __int128 value = 0;
    for (char c : s) {
        int digit;
        if (c == '0') digit = 0;
        else if (c == '1') digit = 1;
        else if (c == 'T' || c == '-') digit = -1;
        else throw invalid_argument("bad balanced ternary digit");

        value = value * 3 + digit;
        if (value < numeric_limits<long long>::min() ||
            value > numeric_limits<long long>::max())
            throw overflow_error("value does not fit in int64");
    }
    return (long long)value;
}


string ordinary_to_balanced_ternary(string s) {
    vector<int> a;
    for (auto it = s.rbegin(); it != s.rend(); ++it) {
        if (*it < '0' || *it > '2')
            throw invalid_argument("not a ternary string");
        a.push_back(*it - '0');
    }

    int carry = 0;
    string out;
    for (size_t i = 0; i < a.size() || carry; ++i) {
        int x = carry + (i < a.size() ? a[i] : 0);
        carry = 0;
        if (x == 0 || x == 1) out += char('0' + x);
        else if (x == 2) out += 'T', carry = 1;
        else if (x == 3) out += '0', carry = 1;
    }
    while (out.size() > 1 && out.back() == '0') out.pop_back();
    reverse(out.begin(), out.end());
    return out;
}

} // namespace btqa

namespace grayqa {

uint64_t gray(uint64_t x) {
    return x ^ (x >> 1);
}


uint64_t inverse_gray(uint64_t g) {
    uint64_t x = 0;
    for (; g != 0; g >>= 1)
        x ^= g;
    return x;
}


uint64_t inverse_gray_fast(uint64_t g) {
    g ^= g >> 1;
    g ^= g >> 2;
    g ^= g >> 4;
    g ^= g >> 8;
    g ^= g >> 16;
    g ^= g >> 32;
    return g;
}


vector<unsigned> gray_sequence(int n) {
    if (n < 0 || n > 31) throw invalid_argument("bad n");
    vector<unsigned> result(1u << n);
    for (unsigned i = 0; i < result.size(); ++i)
        result[i] = i ^ (i >> 1);
    return result;
}

} // namespace grayqa

namespace bigqa {

using lnum = vector<int>;
constexpr int BASE = 1'000'000'000;
constexpr int BASE_DIGITS = 9;


void trim(lnum& a) {
    while (a.size() > 1 && a.back() == 0) a.pop_back();
    if (a.empty()) a.push_back(0);
}

bool is_zero(const lnum& a) {
    return a.size() == 1 && a[0] == 0;
}


lnum read_lnum(const string& s) {
    if (s.empty()) throw invalid_argument("empty integer");
    lnum a;
    for (int r = (int)s.size(); r > 0; r -= BASE_DIGITS) {
        int l = max(0, r - BASE_DIGITS);
        for (int i = l; i < r; ++i)
            if (!isdigit((unsigned char)s[i]))
                throw invalid_argument("non-decimal digit");
        a.push_back(stoi(s.substr(l, r - l)));
    }
    trim(a);
    return a;
}


ostream& print_lnum(ostream& out, const lnum& a) {
    out << (a.empty() ? 0 : a.back());
    char old = out.fill('0');
    for (int i = (int)a.size() - 2; i >= 0; --i)
        out << setw(BASE_DIGITS) << a[i];
    out.fill(old);
    return out;
}


int compare(const lnum& a, const lnum& b) {
    if (a.size() != b.size()) return a.size() < b.size() ? -1 : 1;
    for (int i = (int)a.size() - 1; i >= 0; --i) {
        if (a[i] != b[i]) return a[i] < b[i] ? -1 : 1;
    }
    return 0;
}


void add_to(lnum& a, const lnum& b) {
    int carry = 0;
    for (size_t i = 0; i < max(a.size(), b.size()) || carry; ++i) {
        if (i == a.size()) a.push_back(0);
        long long cur = (long long)a[i] + carry;
        if (i < b.size()) cur += b[i];
        a[i] = int(cur % BASE);
        carry = int(cur / BASE);
    }
}


void subtract_from(lnum& a, const lnum& b) {
    if (compare(a, b) < 0) throw invalid_argument("a must be >= b");
    int borrow = 0;
    for (size_t i = 0; i < b.size() || borrow; ++i) {
        long long cur = (long long)a[i] - borrow;
        if (i < b.size()) cur -= b[i];
        borrow = cur < 0;
        if (borrow) cur += BASE;
        a[i] = (int)cur;
    }
    trim(a);
}


void multiply_short(lnum& a, int b) {
    if (b < 0 || b >= BASE) throw invalid_argument("short multiplier out of range");
    long long carry = 0;
    for (size_t i = 0; i < a.size() || carry; ++i) {
        if (i == a.size()) a.push_back(0);
        long long cur = carry + 1LL * a[i] * b;
        a[i] = int(cur % BASE);
        carry = cur / BASE;
    }
    trim(a);
}


lnum multiply(const lnum& a, const lnum& b) {
    if (is_zero(a) || is_zero(b)) return {0};

    lnum c(a.size() + b.size(), 0);
    for (size_t i = 0; i < a.size(); ++i) {
        long long carry = 0;
        for (size_t j = 0; j < b.size() || carry; ++j) {
            __int128 cur = c[i + j] + carry;
            if (j < b.size()) cur += (__int128)a[i] * b[j];
            c[i + j] = int(cur % BASE);
            carry = (long long)(cur / BASE);
        }
    }
    trim(c);
    return c;
}


pair<lnum, int> divide_short(lnum a, int b) {
    if (b <= 0 || b >= BASE) throw invalid_argument("bad divisor");
    long long rem = 0;
    for (int i = (int)a.size() - 1; i >= 0; --i) {
        long long cur = a[i] + rem * BASE;
        a[i] = int(cur / b);
        rem = cur % b;
    }
    trim(a);
    return {a, (int)rem};
}

} // namespace bigqa

namespace fftqa {

using cd = complex<double>;
const double PI = acos(-1.0);

void fft(vector<cd>& a, bool invert) {
    int n = (int)a.size();

    for (int i = 1, j = 0; i < n; ++i) {
        int bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) swap(a[i], a[j]);
    }

    for (int len = 2; len <= n; len <<= 1) {
        double angle = 2 * PI / len * (invert ? -1 : 1);
        cd wlen(cos(angle), sin(angle));
        for (int block = 0; block < n; block += len) {
            cd w(1);
            for (int j = 0; j < len / 2; ++j) {
                cd u = a[block + j];
                cd v = a[block + j + len / 2] * w;
                a[block + j] = u + v;
                a[block + j + len / 2] = u - v;
                w *= wlen;
            }
        }
    }

    if (invert)
        for (cd& x : a) x /= n;
}


vector<long long> convolution_ll(const vector<int>& a,
                                 const vector<int>& b) {
    if (a.empty() || b.empty()) return {};
    int need = (int)a.size() + (int)b.size() - 1;
    int n = 1;
    while (n < need) n <<= 1;

    vector<cd> fa(a.begin(), a.end()), fb(b.begin(), b.end());
    fa.resize(n);
    fb.resize(n);

    fft(fa, false);
    fft(fb, false);
    for (int i = 0; i < n; ++i) fa[i] *= fb[i];
    fft(fa, true);

    vector<long long> c(need);
    for (int i = 0; i < need; ++i)
        c[i] = llround(fa[i].real());
    return c;
}


const int MOD = 7'340'033;
const int ROOT = 5;
const int ROOT_INV = 4'404'020;
const int ROOT_PW = 1 << 20;


int mod_pow(int a, long long e) {
    long long r = 1;
    while (e) {
        if (e & 1) r = r * a % MOD;
        a = (long long)a * a % MOD;
        e >>= 1;
    }
    return (int)r;
}

void ntt(vector<int>& a, bool invert) {
    int n = (int)a.size();
    for (int i = 1, j = 0; i < n; ++i) {
        int bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) swap(a[i], a[j]);
    }

    for (int len = 2; len <= n; len <<= 1) {
        int wlen = invert ? ROOT_INV : ROOT;
        for (int i = len; i < ROOT_PW; i <<= 1)
            wlen = (long long)wlen * wlen % MOD;

        for (int block = 0; block < n; block += len) {
            int w = 1;
            for (int j = 0; j < len / 2; ++j) {
                int u = a[block + j];
                int v = (long long)a[block + j + len / 2] * w % MOD;
                a[block + j] = u + v < MOD ? u + v : u + v - MOD;
                a[block + j + len / 2] = u - v >= 0 ? u - v : u - v + MOD;
                w = (long long)w * wlen % MOD;
            }
        }
    }

    if (invert) {
        int inv_n = mod_pow(n, MOD - 2);
        for (int& x : a) x = (long long)x * inv_n % MOD;
    }
}

} // namespace fftqa

namespace fexpqa {

const uint32_t mbin_log_32_table[32] = {
    0x00000000, 0x00000000, 0xd3cfd984, 0x9ee62e18,
    0xe83d9070, 0xb59e81e0, 0xa17407c0, 0xce601f80,
    0xf4807f00, 0xe701fe00, 0xbe07fc00, 0xfc1ff800,
    0xf87ff000, 0xf1ffe000, 0xe7ffc000, 0xdfff8000,
    0xffff0000, 0xfffe0000, 0xfffc0000, 0xfff80000,
    0xfff00000, 0xffe00000, 0xffc00000, 0xff800000,
    0xff000000, 0xfe000000, 0xfc000000, 0xf8000000,
    0xf0000000, 0xe0000000, 0xc0000000, 0x80000000,
};


uint32_t mbin_log_32(uint32_t r, uint32_t x) {
    // Precondition: x odd va x ≡ 1 (mod 4).
    for (unsigned n = 2; n < 32; ++n) {
        uint32_t bit = uint32_t(1) << n;
        if (x & bit) {
            x = x + (x << n);
            r -= mbin_log_32_table[n];
        }
    }
    return r;
}


uint32_t mbin_exp_32(uint32_t r, uint32_t z) {
    for (unsigned n = 2; n < 32; ++n) {
        uint32_t bit = uint32_t(1) << n;
        if (z & bit) {
            r = r + (r << n); // r *= 2^n + 1
            z -= mbin_log_32_table[n];
        }
    }
    return r;
}


uint32_t mbin_log_32_fast(uint32_t r, uint32_t x) {
    for (unsigned n = 2; n < 16; ++n) {
        uint32_t bit = uint32_t(1) << n;
        if (x & bit) {
            x = x + (x << n);
            r -= mbin_log_32_table[n];
        }
    }
    r -= x & 0xFFFF0000u;
    return r;
}

uint32_t mbin_exp_32_fast(uint32_t r, uint32_t z) {
    for (unsigned n = 2; n < 16; ++n) {
        uint32_t bit = uint32_t(1) << n;
        if (z & bit) {
            r = r + (r << n);
            z -= mbin_log_32_table[n];
        }
    }
    r *= 1u - (z & 0xFFFF0000u);
    return r;
}


uint32_t mbin_power_odd_32(uint32_t rem,
                           uint32_t base,
                           uint32_t exp) {
    // base ≡ 3 (mod 4) bo‘lsa -base ≡ 1 (mod 4).
    if (base & 2u) {
        base = -base;
        if (exp & 1u) rem = -rem;
    }
    uint32_t logarithm4 = mbin_log_32(0, base);
    return mbin_exp_32(rem, logarithm4 * exp);
}

} // namespace fexpqa


static void require(bool cond, const string& msg) {
    if (!cond) throw runtime_error(msg);
}

static bool trial_prime_u64(uint64_t n) {
    if (n < 2) return false;
    for (uint64_t d=2; d<=n/d; ++d) if(n%d==0) return false;
    return true;
}

static uint64_t powmod_u64(uint64_t a, uint64_t e, uint64_t m) {
    __uint128_t r=1%m;
    while(e){ if(e&1) r=r*a%m; a=(__uint128_t)a*a%m; e>>=1; }
    return (uint64_t)r;
}

static uint32_t pow32(uint32_t a, uint32_t e) {
    uint32_t r=1;
    while(e){ if(e&1u) r*=a; a*=a; e>>=1; }
    return r;
}

static cpp_int parse_cppint(const string& s) {
    cpp_int x=0;
    for(char c:s) x=x*10+(c-'0');
    return x;
}

static string cppint_string(cpp_int x) {
    return x.convert_to<string>();
}

static string lnum_string(const bigqa::lnum& a) {
    ostringstream os; bigqa::print_lnum(os,a); return os.str();
}

int main() {
    mt19937_64 gen(0xC0FFEE123456789ULL);

    // Miller-Rabin versus trial division on a dense prefix.
    for (uint64_t n=0;n<=200000;++n)
        require(primeqa::is_prime(n)==trial_prime_u64(n), "Miller-Rabin mismatch "+to_string(n));
    require(primeqa::is_prime(2305843009213693951ULL), "2^61-1 should be prime");
    require(!primeqa::is_prime(2305843009213693951ULL*3ULL), "large composite accepted");

    // Pollard-Rho factorization: factors prime and product exact.
    vector<uint64_t> factor_cases={1,2,3,4,6,97,9999999967ULL,
        1000000007ULL*1000000009ULL, 4294967291ULL*1000003ULL};
    for(int t=0;t<120;++t) factor_cases.push_back(2 + gen()%1000000000000ULL);
    for(uint64_t n: factor_cases){
        auto f=factorqa::factorize64(n);
        __uint128_t prod=1;
        for(auto [p,e]:f){
            require(primeqa::is_prime(p),"nonprime factor");
            for(int i=0;i<e;++i) prod*=p;
        }
        require(prod==n,"factor product mismatch "+to_string(n));
    }

    // General CRT versus exhaustive search for small moduli.
    for(int m1=1;m1<=18;++m1) for(int m2=1;m2<=18;++m2)
    for(int a1=-2*m1;a1<=2*m1;++a1) for(int a2=-2*m2;a2<=2*m2;++a2){
        auto r=crtqa::crt_merge(a1,m1,a2,m2);
        long long L=std::lcm(m1,m2), brute=-1;
        for(long long x=0;x<L;++x) if((x-a1)%m1==0 && (x-a2)%m2==0){ brute=x; break; }
        require(r.ok==(brute!=-1),"CRT existence mismatch");
        if(r.ok){ require(r.mod==L && r.r==brute,"CRT value mismatch"); }
    }

    // Garner exact and target-mod reconstruction.
    vector<long long> mods={3,5,7,11,13};
    long long product=1; for(auto m:mods) product*=m;
    for(int t=0;t<2000;++t){
        long long x=(long long)(gen()%product);
        vector<long long>a; for(auto m:mods)a.push_back(x%m);
        auto c=garnerqa::garner_digits(a,mods);
        require((long long)garnerqa::restore_exact(c,mods)==x,"Garner exact mismatch");
        long long target = (t&1)?1000000007LL:9000000000000000001LL;
        require(garnerqa::garner_mod(a,mods,target)==x%target,"Garner mod mismatch");
    }

    // Factorial with p-factors removed.
    for(int p: {2,3,5,7,11,13,17,19}) for(int n=0;n<=400;++n){
        long long b=1;
        for(int i=1;i<=n;++i){ int x=i; while(x%p==0)x/=p; b=b*(x%p)%p; }
        require(factqa::factorial_without_p(n,p)==b,"factorial_without_p mismatch");
        long long e=0,q=n; while(q){q/=p;e+=q;}
        require(factqa::exponent_in_factorial(n,p)==e,"factorial exponent mismatch");
    }

    // Linear congruences versus all residues.
    for(int m=1;m<=60;++m) for(int a=-40;a<=40;++a) for(int b=-40;b<=40;++b){
        auto got=linqa::solve_linear_congruence(a,b,m);
        vector<long long> brute;
        for(int x=0;x<m;++x) if(((long long)a*x-b)%m==0) brute.push_back(x);
        sort(got.begin(),got.end());
        require(got==brute,"linear congruence mismatch");
    }

    // Discrete logarithm versus first occurrence before the sequence repeats.
    for(int mod=1;mod<=160;++mod) for(int a=0;a<mod;++a) for(int b=0;b<mod;++b){
        long long brute=-1,cur=1%mod;
        vector<char> seen(mod,0);
        for(int x=0;;++x){
            if(cur==b){brute=x;break;}
            if(seen[cur]) break;
            seen[cur]=1;
            cur=(long long)((__int128)cur*a%mod);
        }
        long long got=dlogqa::discrete_log(a,b,mod);
        require(got==brute,"discrete log mismatch m="+to_string(mod)+" a="+to_string(a)+" b="+to_string(b)+" got="+to_string(got)+" exp="+to_string(brute));
    }

    // Primitive roots and discrete roots over small prime fields.
    vector<int> small_primes;
    for(int p=2;p<=211;++p) if(trial_prime_u64(p)) small_primes.push_back(p);
    for(int p:small_primes){
        long long g=primrootqa::primitive_root_prime(p);
        require(g>=1 && g<p,"bad primitive root range");
        set<long long> seen;
        long long cur=1%p;
        for(int i=0;i<p-1;++i){seen.insert(cur);cur=cur*g%p;}
        require((int)seen.size()==p-1,"primitive root lacks full order");
        for(int k=1;k<=30;++k) for(int a=0;a<p;++a){
            auto got=rootsqa::discrete_roots_prime(k,a,p);
            vector<long long> brute;
            for(int x=0;x<p;++x) if(powmod_u64(x,k,p)==(uint64_t)a) brute.push_back(x);
            require(got==brute,"discrete roots mismatch");
        }
    }

    // Montgomery multiplication/power against __int128 reference.
    vector<uint64_t> montmods={3,5,17,1000000007ULL,2305843009213693951ULL,9223372036854775783ULL};
    for(int t=0;t<3000;++t){
        uint64_t m = t<(int)montmods.size()?montmods[t]:(3+(gen()%4000000000000000000ULL));
        m|=1ULL; if(m>=(1ULL<<63))m>>=1; if(m<=1)m=3;
        montqa::Montgomery64 M(m);
        uint64_t a=gen(),e=gen();
        require(M.power(a,e)==powmod_u64(a%m,e,m),"Montgomery power mismatch");
        uint64_t x=gen()%m,y=gen()%m;
        auto xm=M.to_mont(x),ym=M.to_mont(y);
        require(M.from_mont(M.multiply(xm,ym))==(uint64_t)((__uint128_t)x*y%m),"Montgomery multiply mismatch");
    }

    // Balanced ternary roundtrips, including int64 endpoints.
    vector<long long> vals={0,1,-1,2,-2,3,-3,LLONG_MAX,LLONG_MIN};
    for(int t=0;t<10000;++t) vals.push_back((long long)gen());
    for(long long x:vals){
        string s=btqa::balanced_ternary_string(x);
        require(btqa::from_balanced_ternary(s)==x,"balanced ternary roundtrip");
    }
    for(int t=0;t<10000;++t){
        uint64_t x=gen()%1000000000000ULL, q=x; string s;
        do{s.push_back(char('0'+q%3));q/=3;}while(q); reverse(s.begin(),s.end());
        string bs=btqa::ordinary_to_balanced_ternary(s);
        require(btqa::from_balanced_ternary(bs)==(long long)x,"ordinary ternary conversion");
    }

    // Gray conversion and Hamiltonian-cycle property.
    for(int t=0;t<100000;++t){
        uint64_t x=gen(),g=grayqa::gray(x);
        require(grayqa::inverse_gray(g)==x && grayqa::inverse_gray_fast(g)==x,"Gray inverse mismatch");
    }
    for(int n=0;n<=16;++n){
        auto seq=grayqa::gray_sequence(n);
        set<unsigned> s(seq.begin(),seq.end()); require(s.size()==seq.size(),"Gray duplicate");
        if(seq.size()>1){
            for(size_t i=1;i<seq.size();++i) require(popcount(seq[i]^seq[i-1])==1,"Gray adjacency");
            require(popcount(seq.front()^seq.back())==1,"Gray cyclicity");
        }
    }

    // Base-1e9 arbitrary-precision arithmetic against boost::cpp_int.
    for(int t=0;t<1200;++t){
        int na=1+gen()%80, nb=1+gen()%80;
        string sa,sb; sa.reserve(na); sb.reserve(nb);
        sa.push_back(char('1'+gen()%9)); sb.push_back(char('1'+gen()%9));
        for(int i=1;i<na;++i)sa.push_back(char('0'+gen()%10));
        for(int i=1;i<nb;++i)sb.push_back(char('0'+gen()%10));
        auto A=bigqa::read_lnum(sa), B=bigqa::read_lnum(sb);
        cpp_int aa=parse_cppint(sa),bb=parse_cppint(sb);
        auto sum=A; bigqa::add_to(sum,B); require(lnum_string(sum)==cppint_string(aa+bb),"big add");
        auto prod=bigqa::multiply(A,B); require(lnum_string(prod)==cppint_string(aa*bb),"big multiply");
        if(bigqa::compare(A,B)>=0){ auto d=A; bigqa::subtract_from(d,B); require(lnum_string(d)==cppint_string(aa-bb),"big subtract"); }
        int sh=1+gen()%999999999; auto sm=A; bigqa::multiply_short(sm,sh); require(lnum_string(sm)==cppint_string(aa*sh),"big short multiply");
        auto [quot,rem]=bigqa::divide_short(A,sh); require(lnum_string(quot)==cppint_string(aa/sh) && rem==(aa%sh).convert_to<int>(),"big short divide");
    }

    // Floating FFT convolution versus naive integer convolution.
    for(int t=0;t<1500;++t){
        int n=1+gen()%35,m=1+gen()%35; vector<int>a(n),b(m);
        for(int&x:a)x=(int)(gen()%2001)-1000; for(int&x:b)x=(int)(gen()%2001)-1000;
        auto got=fftqa::convolution_ll(a,b); vector<long long> brute(n+m-1);
        for(int i=0;i<n;++i)for(int j=0;j<m;++j)brute[i+j]+=(long long)a[i]*b[j];
        require(got==brute,"FFT convolution mismatch");
    }
    // NTT roundtrip and convolution modulo 7,340,033.
    for(int t=0;t<300;++t){
        int n=1<<(1+gen()%9); vector<int>a(n); for(int&x:a)x=gen()%fftqa::MOD;
        auto orig=a; fftqa::ntt(a,false); fftqa::ntt(a,true); require(a==orig,"NTT roundtrip");
    }
    for(int t=0;t<500;++t){
        int n=1+gen()%80,m=1+gen()%80,sz=1; while(sz<n+m-1)sz<<=1;
        vector<int>a(sz),b(sz); for(int i=0;i<n;++i)a[i]=gen()%fftqa::MOD; for(int i=0;i<m;++i)b[i]=gen()%fftqa::MOD;
        vector<int> brute(n+m-1); for(int i=0;i<n;++i)for(int j=0;j<m;++j)brute[i+j]=(brute[i+j]+(long long)a[i]*b[j])%fftqa::MOD;
        fftqa::ntt(a,false);fftqa::ntt(b,false);for(int i=0;i<sz;++i)a[i]=(long long)a[i]*b[i]%fftqa::MOD;fftqa::ntt(a,true);a.resize(n+m-1);
        require(a==brute,"NTT convolution mismatch");
    }

    // Factoring exponentiation versus ordinary uint32 modular exponentiation.
    for(int t=0;t<300000;++t){
        uint32_t rem=(uint32_t)gen(), base=((uint32_t)gen())|1u, e=(uint32_t)gen();
        uint32_t expected=rem*pow32(base,e);
        uint32_t got=fexpqa::mbin_power_odd_32(rem,base,e);
        require(got==expected,"factoring exponentiation mismatch");
        uint32_t x=((uint32_t)gen())|1u; if(x&2u)x=-x;
        uint32_t z=fexpqa::mbin_log_32(0,x);
        require(fexpqa::mbin_exp_32(1,z)==x,"mbin log/exp inverse");
        require(fexpqa::mbin_log_32_fast(0,x)==z,"fast log mismatch");
        require(fexpqa::mbin_exp_32_fast(1,z)==x,"fast exp mismatch");
    }

    cout << "ALGEBRA_QA_OK" << '\n';
}
