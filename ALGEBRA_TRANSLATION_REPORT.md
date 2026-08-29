# Algebra tarjimasi hisoboti

**Release:** 2026-08-18  
**Pinned upstream commit:** `85a94001d46b9f34d3b2cf26aca6bd0f7a7e8681`  
**Holat:** `ai_full_translation_draft`  
**Qamrov:** Algebra navigatsiyasi 29/29

## Tuzatish

Oldingi Algebra paketi cp-algorithms matnining to‘liq tarjimasi emas, qayta yozilgan texnik moslashtirish edi. Ushbu release’da 29 maqola pinned upstream maqolalarning bo‘limlari va mazmuni asl ketma-ketlikda saqlangan holda qayta qurildi. Oldingi Algebra fayllari bilan ushbu fayllarni almashtirish kerak.

Qolgan 134 route bu release’da source-faithful to‘liq tarjima sifatida belgilanmaydi. Ularning metadata holati `ai_synopsis_draft`, `full_prose_translated: false` va `translation_fidelity: not_source_faithful` ga tushirildi.

## Tarjima inventari

| № | O‘zbekcha sarlavha | Repository yo‘li | Body satrlari | Kod bloklari |
|---:|---|---|---:|---:|
| 1 | Ikkilik darajaga oshirish | `algebra/binary-exp.md` | 226 | 4 |
| 2 | EKUBni hisoblash uchun Evklid algoritmi | `algebra/euclid-algorithm.md` | 114 | 5 |
| 3 | Kengaytirilgan Evklid algoritmi | `algebra/extended-euclid-algorithm.md` | 119 | 2 |
| 4 | Chiziqli Diofant tenglamalari | `algebra/linear-diophantine-equation.md` | 207 | 2 |
| 5 | Fibonacci sonlari | `algebra/fibonacci-numbers.md` | 289 | 3 |
| 6 | Eratosthen elagi | `algebra/sieve-of-eratosthenes.md` | 262 | 5 |
| 7 | Chiziqli elak | `algebra/prime-sieve-linear.md` | 92 | 1 |
| 8 | Tub sonlikni tekshirish usullari | `algebra/primality_tests.md` | 207 | 4 |
| 9 | Butun sonni ko‘paytuvchilarga ajratish | `algebra/factorization.md` | 410 | 11 |
| 10 | Eulerning φ funksiyasi | `algebra/phi-function.md` | 229 | 4 |
| 11 | Bo‘luvchilar soni va bo‘luvchilar yig‘indisi | `algebra/divisors.md` | 124 | 2 |
| 12 | Modul bo‘yicha teskari element | `algebra/module-inverse.md` | 145 | 4 |
| 13 | Chiziqli kongruensiya tenglamasi | `algebra/linear_congruence_equation.md` | 53 | 0 |
| 14 | Xitoy qoldiqlar teoremasi | `algebra/chinese-remainder-theorem.md` | 205 | 1 |
| 15 | Garner algoritmi | `algebra/garners-algorithm.md` | 150 | 2 |
| 16 | p modul bo‘yicha faktorial | `algebra/factorial-modulo.md` | 96 | 2 |
| 17 | Diskret logarifm | `algebra/discrete-log.md` | 209 | 4 |
| 18 | Primitiv ildiz | `algebra/primitive-root.md` | 88 | 1 |
| 19 | Diskret ildiz | `algebra/discrete-root.md` | 138 | 1 |
| 20 | Montgomery ko‘paytirishi | `algebra/montgomery_multiplication.md` | 200 | 4 |
| 21 | Muvozanatlangan uchlik sanoq tizimi | `algebra/balanced-ternary.md` | 72 | 2 |
| 22 | Gray kodi | `algebra/gray-code.md` | 64 | 2 |
| 23 | Bitlar bilan amallar | `algebra/bit-manipulation.md` | 230 | 12 |
| 24 | Bitmask submaskalarini sanash | `algebra/all-submasks.md` | 70 | 4 |
| 25 | Ixtiyoriy aniqlikdagi arifmetika | `algebra/big-integer.md` | 182 | 11 |
| 26 | Tez Fourier almashtirishi (FFT) | `algebra/fft.md` | 614 | 6 |
| 27 | Ko‘phadlar va qatorlar ustida amallar | `algebra/polynomial.md` | 438 | 2 |
| 28 | Uzluksiz kasrlar | `algebra/continued-fractions.md` | 1140 | 19 |
| 29 | Faktorlash orqali ikkilik darajaga oshirish | `algebra/factoring-exp.md` | 207 | 5 |

## Jami metrikalar

- Tarjima qilingan body satrlari: **6580**
- Body belgilar soni: **347635**
- Sarlavhalar: **284**
- Fenced code bloklari: **125**
- Display-math bloklari: **316**
- Markdown/HTML havola va rasm targetlari: **335**

## Metadata

Barcha 29 sahifada:

```yaml
translation_status: ai_full_translation_draft
translation_scope: full_upstream_article
translation_fidelity: sentence_preserving_full_copy
full_prose_translated: true
technical_review: pending
language_review: pending
```

Bu sahifalar `published` emas. Texnik aniqlik, formulalar, algoritm preconditionlari, kod va o‘zbekcha til inson reviewidan o‘tishi kerak.

## Audit va QA

- Source-inventory, front matter, UTF-8, Markdown fence, lokal target va generated route auditi: [`ALGEBRA_SOURCE_FIDELITY_AUDIT.md`](ALGEBRA_SOURCE_FIDELITY_AUDIT.md)
- Machine-readable audit: [`reports/algebra-source-fidelity-audit.json`](reports/algebra-source-fidelity-audit.json)
- Randomized/differential code QA: [`ALGEBRA_QA_REPORT.md`](ALGEBRA_QA_REPORT.md)

Audit byte-for-byte English/Uzbek line diff deb da’vo qilmaydi, chunki repository ichiga barcha 29 English source snapshot kiritilmagan. Tarjimalar pinned raw maqolalar bo‘yicha qurilgan; texnik va til reviewi baribir `pending`.
