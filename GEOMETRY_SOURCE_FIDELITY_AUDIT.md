# Geometry source-fidelity va release auditi

**Release:** 2026-08-21  
**Pinned upstream commit:** `85a94001d46b9f34d3b2cf26aca6bd0f7a7e8681`

## Qamrov

* Geometry navigatsiya inventari: **26 maqola**.
* Targetdagi to‘liq source-ordered tarjima qoralamalari: **26/26**.
* Bundle qilingan exact pinned English Markdown snapshotlari: **0**.
* Exact commitga bog‘langan raw-source reference: **26/26**.
* Inson texnik reviewi: **0**; inson til reviewi: **0**.

## Nima tekshirildi

Release validator va packaging tekshiruvlari quyidagilarni tasdiqlaydi:

1. 26 maqolaning manifest, front matter, review queue va route yozuvlari o‘zaro mos;
2. barcha sahifalar `full_upstream_article` va `source_ordered_full_translation` sifatida belgilangan;
3. har bir maqolada to‘liq-qoralama ogohlantirishi hamda manba/litsenziya bo‘limi mavjud;
4. Markdown code fence lar muvozanatlangan, article body lar minimal hajm talabidan katta;
5. barcha generated route lar, lokal havolalar va lokal assetlar mavjud;
6. cumulative 163-route repository va 167 ta statik `index.html` sahifasi muvaffaqiyatli validatsiyadan o‘tadi;
7. final repository, static-site va overlay ZIP lar CRC, duplicate-entry va unsafe-path tekshiruvlaridan o‘tkaziladi.

## Da’vo qilinmaydigan tekshiruvlar

Geometry uchun exact pinned Markdown snapshotlari ushbu release ichida bundle qilinmagani sababli quyidagilar avtomatik tasdiqlangan deb ko‘rsatilmaydi:

* inglizcha va o‘zbekcha matnning jumlama-jumla to‘liq semantik mosligi;
* code block, formula, inline-code va link targetlarning byte-for-byte tengligi;
* har bir proof, edge case, sonli aniqlik chegarasi va implementatsiyaning inson tomonidan texnik tasdig‘i;
* o‘zbekcha til va terminologiyaning tahririy tasdig‘i.

Har bir pinned raw URL `upstream/geometry-source-index.json` da, maqolama-maqola target metrikalari esa `reports/geometry-fidelity/article-map.tsv` va `reports/geometry-source-fidelity-audit.json` da saqlangan.
