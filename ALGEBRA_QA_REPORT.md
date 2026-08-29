# Algebra randomized va differential QA hisoboti

**Run date:** 2026-08-18  
**Compiler:** GNU C++20  
**Result:** PASS

Quyidagi test harnesslar kompilyatsiya qilindi va ishga tushirildi:

```bash
g++ -std=gnu++20 -O2 -pipe tests/algebra_randomized_qa.cpp -o qa-bin/algebra_randomized_qa
./qa-bin/algebra_randomized_qa

g++ -std=gnu++20 -O2 -pipe tests/algebra_randomized_qa_extended.cpp -o qa-bin/algebra_randomized_qa_extended
./qa-bin/algebra_randomized_qa_extended
```

Birinchi harness chiqishi:

```text
big_integer OK
linear_diophantine OK
fft OK
ntt OK
continued_fractions OK
factoring_exponentiation OK
montgomery OK
discrete_log OK
primitive_and_discrete_roots OK
crt_garner OK
factorial_mod_p OK
ALL ALGEBRA QA TESTS PASSED
```

Ikkinchi harness chiqishi:

```text
ALGEBRA_QA_OK
```

## Qamrov

Harnesslar katta sonlar arifmetikasi, chiziqli Diofant tenglamalari, FFT/NTT, uzluksiz kasrlar, factoring exponentiation, Montgomery ko‘paytirishi, diskret logarifm/ildiz, primitiv ildiz, CRT/Garner va faktorial modul `p` implementatsiyalarini brute-force yoki mustaqil reference natijalar bilan solishtiradi.

## Muhim cheklov

Bu testlar maqolalarning tarjima to‘liqligini, barcha formula va isbotlarni yoki har bir code blockni tasdiqlamaydi. Ular repositorydagi mustaqil reference implementatsiyalar uchun texnik regressiya testi xolos. Inson texnik reviewi hamon `pending`.
## Joriy CI komandasi

Kundalik CI va `make check`dan tashqari ishlatiladigan tezkor C++ tekshiruv:

```bash
make qa-algebra
```

Bu komanda `tests/algebra_smoke_qa.cpp` faylini kompilyatsiya qilib, ikkilik darajaga oshirish, kengaytirilgan Evklid algoritmi, Eratosfen elagi va Xitoy qoldiqlar teoremasi uchun deterministik smoke-testlarni bajaradi. Yuqoridagi ancha uzun randomized/differential harnesslarni qayta ishlatish uchun:

```bash
make qa-algebra-full
```

Tezkor va to‘liq rejimlarning ajratilishi CI vaqtini barqaror saqlaydi, eski chuqur regression testlarini esa yo‘qotmaydi.

