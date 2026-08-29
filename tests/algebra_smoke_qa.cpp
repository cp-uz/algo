#include <algorithm>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <numeric>
#include <random>
#include <tuple>
#include <vector>

using i64 = long long;
using i128 = __int128_t;

[[noreturn]] static void fail(const char* message) {
    std::cerr << "ALGEBRA SMOKE TEST FAILED: " << message << '\n';
    std::exit(1);
}

static i64 binary_power_mod(i64 base, i64 exponent, i64 modulus) {
    i64 result = 1 % modulus;
    base %= modulus;
    while (exponent > 0) {
        if (exponent & 1) result = static_cast<i64>((i128)result * base % modulus);
        base = static_cast<i64>((i128)base * base % modulus);
        exponent >>= 1;
    }
    return result;
}

static i64 extended_gcd(i64 a, i64 b, i64& x, i64& y) {
    if (b == 0) {
        x = 1;
        y = 0;
        return a;
    }
    i64 x1 = 0, y1 = 0;
    i64 g = extended_gcd(b, a % b, x1, y1);
    x = y1;
    y = x1 - (a / b) * y1;
    return g;
}

static std::vector<bool> sieve(int n) {
    std::vector<bool> prime(n + 1, true);
    if (n >= 0) prime[0] = false;
    if (n >= 1) prime[1] = false;
    for (int p = 2; p <= n / p; ++p) {
        if (!prime[p]) continue;
        for (int multiple = p * p; multiple <= n; multiple += p) {
            prime[multiple] = false;
        }
    }
    return prime;
}

static bool trial_prime(int n) {
    if (n < 2) return false;
    for (int d = 2; d <= n / d; ++d) {
        if (n % d == 0) return false;
    }
    return true;
}

struct CRTResult {
    bool ok;
    i64 value;
    i64 modulus;
};

static i64 normalize(i64 value, i64 modulus) {
    value %= modulus;
    return value < 0 ? value + modulus : value;
}

static CRTResult merge_crt(i64 a1, i64 m1, i64 a2, i64 m2) {
    i64 x = 0, y = 0;
    i64 g = extended_gcd(m1, m2, x, y);
    i64 difference = a2 - a1;
    if (difference % g != 0) return {false, 0, 0};
    i64 reduced = m2 / g;
    i64 multiplier = normalize(
        static_cast<i64>((i128)(difference / g) * x % reduced), reduced
    );
    i64 lcm = m1 / g * m2;
    i64 answer = normalize(
        static_cast<i64>(((i128)a1 + (i128)m1 * multiplier) % lcm), lcm
    );
    return {true, answer, lcm};
}

int main() {
    std::mt19937_64 random(0x4350555AULL);

    for (int test = 0; test < 5000; ++test) {
        i64 modulus = static_cast<i64>(random() % 100000) + 1;
        i64 base = static_cast<i64>(random() % 200001) - 100000;
        i64 exponent = static_cast<i64>(random() % 40);
        i64 expected = 1 % modulus;
        i64 normalized_base = normalize(base, modulus);
        for (i64 i = 0; i < exponent; ++i) {
            expected = static_cast<i64>((i128)expected * normalized_base % modulus);
        }
        if (binary_power_mod(normalized_base, exponent, modulus) != expected) {
            fail("binary exponentiation");
        }
    }

    for (int test = 0; test < 5000; ++test) {
        i64 a = static_cast<i64>(random() % 1000000) + 1;
        i64 b = static_cast<i64>(random() % 1000000) + 1;
        i64 x = 0, y = 0;
        i64 g = extended_gcd(a, b, x, y);
        if (g != std::gcd(a, b) || (i128)a * x + (i128)b * y != g) {
            fail("extended Euclidean algorithm");
        }
    }

    const auto prime = sieve(20000);
    for (int value = 0; value <= 20000; ++value) {
        if (prime[value] != trial_prime(value)) fail("sieve of Eratosthenes");
    }

    for (int test = 0; test < 5000; ++test) {
        i64 m1 = static_cast<i64>(random() % 40) + 1;
        i64 m2 = static_cast<i64>(random() % 40) + 1;
        i64 a1 = static_cast<i64>(random() % 101) - 50;
        i64 a2 = static_cast<i64>(random() % 101) - 50;
        CRTResult result = merge_crt(a1, m1, a2, m2);
        i64 lcm = std::lcm(m1, m2);
        i64 brute = -1;
        for (i64 value = 0; value < lcm; ++value) {
            if (value % m1 == normalize(a1, m1) && value % m2 == normalize(a2, m2)) {
                brute = value;
                break;
            }
        }
        if ((brute >= 0) != result.ok) fail("CRT solvability");
        if (result.ok && (result.value != brute || result.modulus != lcm)) {
            fail("CRT result");
        }
    }

    std::cout << "ALGEBRA SMOKE TESTS PASSED\n";
    return 0;
}
