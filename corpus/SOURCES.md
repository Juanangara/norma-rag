# Corpus sources

| File | Source | Retrieved | Status |
|---|---|---|---|
| `raw/ley_1581_2012.suin.txt` | [SUIN-Juriscol, Ley 1581 de 2012](https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Leyes/1684507) | 2024-11-06 (print date) | Vigente according to SUIN |
| `raw/decreto_1074_2015_cap25.funcionpublica.txt` | [Función Pública, Decreto 1074 de 2015](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=76608), chapter 25 | 2026-10-26 | Función Pública does not guarantee vigencia |

`raw/ley_1581_2012.suin.txt` is the first 625 lines of the SUIN print. The rest of that 204-page print is the court ruling C-748/11 and the legislative history, which is not law text.

Decreto 1377 de 2013 is **not** indexed. SUIN lists it as "Compilado": its articles now live in chapter 25 of Decreto 1074, and each article there records its origin as `(Decreto 1377 de 2013, art. N)`. Chapter 25 includes section 7, added by Decreto 255 de 2022.

## What was checked
- The 30 articles of the law were compared one by one (normalized text hash) against the [Función Pública copy](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=49981): 28 identical. Article 25 differs by an editorial note ("Reglamentado por el Decreto Nacional 886 de 2014") that is not law text. Article 30 differs by a corrupted character in the signature block of the Función Pública copy.
- The SUIN print swaps the order of articles 4/5 and 9/10. The parser sorts by article number.

## Second check of chapter 25 (2026-10-26)
Articles 2.2.2.25.1.1 to 2.2.2.25.6.2 are the compiled text of Decreto 1377 de 2013, so each was compared with the SUIN print of that decree (independent source). All 27 match in substance. The differences are:
- Editorial changes made by the compilation: "presente decreto" became "presente capítulo", article cross-references were renumbered, and "antes de la expedición del presente decreto" became "antes del 27 de junio de 2013".
- Transcription slips in the Función Pública copy that are not in the SUIN text: "cómo" for "como", "cuál" for "cual", "analogas", "paginas", "esta prohibido", "obrán". They are left as they are in `raw/`, so the corpus is a faithful copy of its source. Do not "fix" them by hand without recording it here.

## Vigencia (2026-10-26)
- Chapter 25: in the Función Pública copy of Decreto 1074, 345 articles elsewhere carry an inline note such as "(Modificado por…)" or "(Derogado por…)". Chapter 25 has only one: "(Adicionada por el Art.1, Decreto 255 de 2022)" for section 7. So no article of chapter 25 is recorded as modified or repealed. The page cites decrees up to 2025. Función Pública says it does not guarantee vigencia, and this is a single source.
- Ley 1581: Función Pública lists three "Reglamentado por" entries (Decretos 1377/2013, 886/2014, 1081/2015) and no modification or repeal.
- Pending reform: Proyecto de Ley Estatutaria 282 de 2026 Cámara (Gaceta 1217 de 2026, filed August 2026) would modify Ley 1581. No source found shows it approved. Earlier bills (274 and 214 de 2025) did not become law. If it passes, this corpus is out of date.
  - Re-checked 2026-10-27 with a web search: the bill exists ([vLex copy of the Gaceta](https://vlex.com.co/vid/proyecto-ley-estatutaria-numero-1134555141), [Uniandes analysis](https://algoritmos.uniandes.edu.co/proyecto-de-ley-estatutaria-por-la-cual-se-modifica-parcialmente-la-ley-1581-de-2012-y-se-dictan-otras-disposiciones-relativas-al-derecho-fundamental-a-la-proteccion-de-datos-personales-2/)); a news source ([CiberLATAM](https://ciberlatam.com/en/news/colombia-updates-data-law-bill)) says it was under review by the Primera Comisión. The sources disagree on the Gaceta publication date, and none is official, so its current procedural status is **not confirmed**. Check SILEG or the Gaceta del Congreso.

## Not checked
- The text of Ley 1581 against the printed Diario Oficial (only two digital copies were compared).
- Decreto 886 de 2014 (Registro Nacional de Bases de Datos, chapter 26 of Decreto 1074) and Decreto 1081 de 2015 are not in the corpus.
