# Algebra source-fidelity auditi

**Audit date:** 2026-08-18  
**Pinned source:** `85a94001d46b9f34d3b2cf26aca6bd0f7a7e8681`  
**Result:** PASS  
**Articles:** 29/29

## Avtomatik tekshiruvlar

| Tekshiruv | Natija |
|---|---|
| navigation inventory matches | PASS |
| utf8 and control char scan | PASS |
| frontmatter and status | PASS |
| markdown fences balanced | PASS |
| local targets exist | PASS |
| generated routes exist | PASS |

Qo‘shimcha ravishda `scripts/validate.py` 163 route, 167 generated `index.html`, lokal havolalar, rasm assetlari, manifest/front matter mosligi va Algebra full-translation inventarini tekshiradi.

## Maqolalar bo‘yicha metrikalar

| № | Sarlavha | Yo‘l | Body satri | Heading | Code fence | SHA-256 |
|---:|---|---|---:|---:|---:|---|
| 1 | Ikkilik darajaga oshirish | `algebra/binary-exp.md` | 226 | 12 | 4 | `bb29adc39f18…` |
| 2 | EKUBni hisoblash uchun Evklid algoritmi | `algebra/euclid-algorithm.md` | 114 | 8 | 5 | `f67e50daf2e8…` |
| 3 | Kengaytirilgan Evklid algoritmi | `algebra/extended-euclid-algorithm.md` | 119 | 6 | 2 | `eb8e6ca4faa1…` |
| 4 | Chiziqli Diofant tenglamalari | `algebra/linear-diophantine-equation.md` | 207 | 9 | 2 | `e40958d1bcf9…` |
| 5 | Fibonacci sonlari | `algebra/fibonacci-numbers.md` | 289 | 11 | 3 | `9a65e3a75b66…` |
| 6 | Eratosthen elagi | `algebra/sieve-of-eratosthenes.md` | 262 | 12 | 5 | `fa0b2c1f16d2…` |
| 7 | Chiziqli elak | `algebra/prime-sieve-linear.md` | 92 | 7 | 1 | `53acbc846e2d…` |
| 8 | Tub sonlikni tekshirish usullari | `algebra/primality_tests.md` | 207 | 7 | 4 | `1ddc5a8e3f99…` |
| 9 | Butun sonni ko‘paytuvchilarga ajratish | `algebra/factorization.md` | 410 | 13 | 11 | `b4247311be09…` |
| 10 | Eulerning φ funksiyasi | `algebra/phi-function.md` | 229 | 12 | 4 | `09f6b7313587…` |
| 11 | Bo‘luvchilar soni va bo‘luvchilar yig‘indisi | `algebra/divisors.md` | 124 | 6 | 2 | `a3569d94ba8b…` |
| 12 | Modul bo‘yicha teskari element | `algebra/module-inverse.md` | 145 | 8 | 4 | `e7c0299d0a19…` |
| 13 | Chiziqli kongruensiya tenglamasi | `algebra/linear_congruence_equation.md` | 53 | 4 | 0 | `0c5fd62f7cab…` |
| 14 | Xitoy qoldiqlar teoremasi | `algebra/chinese-remainder-theorem.md` | 205 | 12 | 1 | `ea8e6e906b4d…` |
| 15 | Garner algoritmi | `algebra/garners-algorithm.md` | 150 | 5 | 2 | `a6c3e9b2f691…` |
| 16 | p modul bo‘yicha faktorial | `algebra/factorial-modulo.md` | 96 | 5 | 2 | `7c7e1c99004a…` |
| 17 | Diskret logarifm | `algebra/discrete-log.md` | 209 | 10 | 4 | `9d0d82c5ca7d…` |
| 18 | Primitiv ildiz | `algebra/primitive-root.md` | 88 | 7 | 1 | `03010bf013d1…` |
| 19 | Diskret ildiz | `algebra/discrete-root.md` | 138 | 6 | 1 | `08050e007fca…` |
| 20 | Montgomery ko‘paytirishi | `algebra/montgomery_multiplication.md` | 200 | 7 | 4 | `0320d83ee65a…` |
| 21 | Muvozanatlangan uchlik sanoq tizimi | `algebra/balanced-ternary.md` | 72 | 4 | 2 | `537f4d766692…` |
| 22 | Gray kodi | `algebra/gray-code.md` | 64 | 6 | 2 | `95ab277fff0e…` |
| 23 | Bitlar bilan amallar | `algebra/bit-manipulation.md` | 230 | 17 | 12 | `0aeb5a1dcb2a…` |
| 24 | Bitmask submaskalarini sanash | `algebra/all-submasks.md` | 70 | 5 | 4 | `abf4becc48ed…` |
| 25 | Ixtiyoriy aniqlikdagi arifmetika | `algebra/big-integer.md` | 182 | 17 | 11 | `32d37999f67e…` |
| 26 | Tez Fourier almashtirishi (FFT) | `algebra/fft.md` | 614 | 17 | 6 | `7449bd4111a3…` |
| 27 | Ko‘phadlar va qatorlar ustida amallar | `algebra/polynomial.md` | 438 | 29 | 2 | `8aa9e7ca85c7…` |
| 28 | Uzluksiz kasrlar | `algebra/continued-fractions.md` | 1140 | 15 | 19 | `7f5fcd5a0290…` |
| 29 | Faktorlash orqali ikkilik darajaga oshirish | `algebra/factoring-exp.md` | 207 | 7 | 5 | `b62fcdad74bf…` |

## Chegaralar

- The archive does not bundle all 29 English upstream Markdown snapshots, so this audit does not claim a byte-for-byte English/Uzbek line diff.
- Source-order and sentence coverage were checked during translation construction against the pinned raw articles; technical and language review remain pending.
- Code QA exercises independent implementations in tests/ and does not prove every prose statement or every code block in the articles.

Shuning uchun `sentence_preserving_full_copy` metadata tarjimaning qurilish ko‘lamini bildiradi, lekin inson tomonidan tasdiqlangan sertifikat emas. Barcha sahifalarda `technical_review: pending` va `language_review: pending` saqlanadi.
