# Retrieval evaluation

`python -m eval.run_retrieval` scores retrieval on `questions.jsonl` (40 questions with an expected article; 7 more that must be refused, corrected or answered with a limit). Full output: `results.txt`. Scores are at article level, top 5. `hit@5` is the share of questions with at least one expected article in the top 5; `MRR` uses the position of the first expected article. Every row also resolves explicit references ("artículo 9 del Decreto 1377") the same way.

## 1. Hybrid search did not beat vector search

First run (articles chunked by size only):

| Setting | hit@5 | MRR |
|---|---|---|
| Vector only | 0.95 | **0.87** |
| Text only (best normalization) | 0.88 | 0.63 |
| Hybrid 1:1, normalization 0 | 0.90 | 0.72 |
| Hybrid 1:1, normalization 4 | 0.95 | 0.85 |
| Hybrid 1:1, normalization 8 | **0.97** | 0.78 |

No hybrid setting beat vector search on MRR. The best hit@5 is one question ahead. The text ranker (Postgres `ts_rank_cd`) rewards long articles that repeat "datos", which is almost all of them. Default: vector only, text ranker at weight 0.

An early impression from 6 hand-picked questions ("the text ranker brings in what vectors miss") did not hold on 40.

## 2. One chunk per definition

The two worst questions asked for the definition of "Responsable" and "Encargado" (art. 3 of the law). Art. 3 is short (860 characters), so length was not the cause, but each definition is an independent unit. Chunking `Definiciones` articles one definition per chunk (intro kept in each) gave, for vector only:

| | hit@5 | coverage@5 | MRR |
|---|---|---|---|
| Before | 0.95 | 0.93 | 0.87 |
| After | **1.00** | **0.98** | **0.88** |

q02 went from 8th to 2nd and q03 from 20th to 2nd.

## 3. Rejection threshold: similarity alone is not enough

Cosine similarity of the best chunk:

| | n | min | median | max |
|---|---|---|---|---|
| Answerable | 30 | 0.865 | 0.892 | 0.924 |
| Must refuse | 6 | 0.787 | 0.834 | 0.884 |

The easy refusals (arepas 0.787, cookies 0.822, GDPR 0.828, prison 0.840) sit below every answerable question. Two do not: the Ley 1266 question (0.855, the law mentions it only to exclude it) and the cost of registering a database (0.884, the law defines the registry but says nothing about cost). A threshold near 0.86 would still accept the 0.884 one. Questions with an explicit article reference score lower (0.84) and must bypass the threshold. Hard cases need the checks after generation.

## 4. Questions written by a non-lawyer: retrieval fails

`blind.jsonl` has 23 questions written by a person who had not seen the corpus (verbatim: long, colloquial, often two questions in one). Labels were proposed by the model that built the system and have not been reviewed by a lawyer; 8 of them are marked `dudoso` because the corpus cannot fully answer. `esperados` are the articles that must be found; `opcionales` are also relevant. `util@5` counts a question as served if any expected or optional article is in the top 5. One question (b13, Datacrédito) must be refused, so 22 are scored. Full output: `results_blind.txt`.

| Setting | hit@5 | coverage@5 | MRR | util@5 |
|---|---|---|---|---|
| **Questions written by the model (40)**, vector only | 1.00 | 0.98 | 0.88 | - |
| **Non-lawyer questions (22)**, vector only | **0.55** | **0.23** | **0.30** | 0.77 |
| Non-lawyer, hybrid 1:1, normalization 0 | 0.59 | 0.25 | 0.36 | 0.86 |
| Non-lawyer, hybrid 1:1, normalization 4 | 0.41 | 0.17 | 0.29 | 0.64 |
| Non-lawyer, text only | 0.27 | 0.12 | 0.21 | 0.50 |

Coverage is the weak point: on average fewer than a quarter of the expected articles are in the top 5. Hybrid settings move between 0.41 and 0.59 and do not fix it.

Where it fails (position of the expected article, vector only):
- Vocabulary gap: "huella" does not find the biometric-data articles (Ley 5 at 28th, 2.2.2.25.2.3 and Ley 6 not in the top 30); "borrar mi cuenta" does not find the erasure article 2.2.2.25.2.6 (not in the top 30); "vende las bases de datos" finds none of Ley 23, Ley 9 or Ley 13 in the top 30.
- Easy ones work: "tarjeta de puntos" and "fotos de mis hijos" put an expected article 1st or 2nd; the registry question puts Ley 25 first.

Similarity does not help to reject. The best chunk scores 0.83 to 0.90 on all 23 questions, including b13, which must be refused (0.867). Answering from the wrong articles is the failure mode this project must prevent.

**The numbers in sections 1 and 2 measure the easy case (questions that reuse the corpus vocabulary) and should not be read as the system's real accuracy.**

Which fixes help was measured afterwards: a larger embedding model (`bge-m3`) in sections 5 and 6, a reranker in section 5. Not tried: rewriting the question in legal vocabulary with the LLM before searching, and splitting a two-part question. Any change must be judged on questions it was not designed from; 23 is small and these were already used to diagnose, which is why section 5 also uses a held-out set.

## Limits of the numbers in sections 1 to 4
- 40 questions: one question is 0.025 of hit@5. Differences of 0.02 are noise.
- The questions were written after reading the corpus, so they are easier than real users' questions.
- The chunking change in section 2 was designed after seeing which questions failed in this same set. The gain is in-sample. It needs questions written independently to confirm it.
- The settings in section 1 were compared on the same set they were judged on.
- The 7 other questions (refusals, false premises, partial answer) are only used for the similarity table here. They are scored in sections 7 and 8, once there is an answer layer.

## 5. Embedding models and reranker

Compared in memory with `python -m eval.experiments` (no database, no reference resolution, so the 40 model-written questions score below the 1.00 of section 2). Vector only, article level, top 5. Labels as in section 4.

| Model | Model-written (40) hit / MRR | Non-lawyer dev (22) hit / cov / MRR | Held-out (20) hit / cov / MRR |
|---|---|---|---|
| `e5-small` (384 dim) | 0.93 / 0.79 | 0.55 / 0.23 / 0.30 | 0.60 / 0.29 / 0.48 |
| `e5-base` | 0.85 / 0.79 | 0.68 / 0.42 / 0.50 | not run |
| `bge-m3` (1024 dim) | 0.88 / 0.80 | 0.77 / 0.49 / 0.67 | 0.60 / 0.35 / 0.56 |

- The held-out set was scored once per model, after choosing the candidates on the development sets. Output: `results_heldout_models.txt`.
- The development gain of `bge-m3` (MRR 0.30 to 0.67) shrank on held-out (0.48 to 0.56). Hit@5 did not move (0.60). With 20 questions, one question is 0.05 of hit@5, so only the coverage and MRR differences point the same way; none is conclusive. The dev gain was partly selection on a small set.
- `e5-base` was not run on held-out: it lost to `bge-m3` on dev.

Reranker `BAAI/bge-reranker-v2-m3` over the top 10 of `bge-m3`, non-lawyer dev set (22):

| | hit@5 | coverage@5 | MRR |
|---|---|---|---|
| `bge-m3` | 0.77 | 0.49 | 0.67 |
| `bge-m3` + reranker | 0.77 | 0.48 | 0.51 |

It brings nothing into the top 5 and lowers MRR. It also took about 40 s per question on this CPU, measured while about 30 unrelated Docker containers were running, so that time is inflated and was not re-measured. Discarded for quality, not for speed. A pool of 20 was started on the model-written set and stopped before finishing, so it is not reported.

Cost on this laptop (i5-1235U, 12 threads, no GPU), measured with `python -m eval.latency`, one run, 3 containers active. Peak memory is the whole process (torch plus corpus):

| Model | Load | Embed 82 chunks | Query, median / p95 | Peak memory |
|---|---|---|---|---|
| `e5-small` | 9.3 s | 34 s | 0.18 s / 0.37 s | 2.0 GB |
| `bge-m3` | 6.3 s | 174 s | 0.50 s / 0.82 s | 2.9 GB |

`e5-small` ran faster in a first run (0.05 s median query, 10 s for the chunks), so these timings vary by a factor of 3 between runs; read them as orders of magnitude. `bge-m3` is about 3 times slower per query and about 5 times slower to index, still half a second per query.

## 6. Switch to `bge-m3` in the database pipeline

Sections 1 to 4 were measured with `e5-small`. The default is now `BAAI/bge-m3` (1024 dim); `ingest.load` recreates the table with the model's vector size, so changing `EMBEDDING_MODEL` only needs a reload (E5 prefixes are added only when the name contains `e5`). Same measurement as section 4, vector only, with reference resolution; outputs in `results_bge-m3_*.txt`.

| Set | `e5-small` hit / cov / MRR | `bge-m3` hit / cov / MRR |
|---|---|---|
| Model-written (40) | 1.00 / 0.98 / 0.88 | 0.97 / 0.95 / 0.89 |
| Non-lawyer dev (22) | 0.55 / 0.23 / 0.30 | 0.77 / 0.49 / 0.67 |
| Held-out (20) | 0.60 / 0.29 / 0.48 | 0.60 / 0.35 / 0.55 |

The held-out row was already looked at once in section 5 (in-memory); this is the same configuration run through the database, not a new choice. The results agree with section 5 (0.56 in memory, 0.55 here: reference resolution changes one ranking). The 22 development questions favoured `bge-m3` more than the held-out ones; the honest summary is a modest gain in coverage and MRR, none in hit@5.

Similarity of the best chunk changes scale with the model (cosine of `bge-m3` is lower), but the rejection problem remains: on the model-written set the highest score among questions that must be refused (0.627) is above the lowest answerable one (0.475). A threshold on similarity still cannot decide whether to answer.

The 38 tests pass (72 s) with the new model.

## 7. Answer layer: do the defenses stop hallucinations?

`python -m eval.run_answers` generates one answer per question with the local LLM (Llama 3.2 1B Instruct, Q4_K_M, 4 retrieved articles, temperature 0) and caches it; `python -m eval.score_answers` applies each combination of defenses to the cached answers. Sample: development sets only, 39 questions (all 23 that must be refused, corrected or answered with a limit, plus one in three of the plain ones). The held-out set has not been used here. Output: `results_answers_dev.txt`. Each answer was read against its `respuesta_clave` (`grades_answers.json`); **the reader is the model that built the system, not a lawyer**, and the sample is deliberately rich in hard questions, so the share of wrong answers is not what a real user would see.

First trial, before the fixes below (5 articles, the model asked to copy quotes): 0 of 8 quotes were literal in the article (it returned article headings), it answered "Sí es legal" to a question about Datacrédito that the corpus cannot answer, and the 700-token limit was reached without closing the JSON in 2 of 3 questions (88 to 193 s each).

Defects found in my own first design, fixed before the numbers below:
- The prompt contained the example citation "2.1" and the model copied it into almost every answer.
- Numeric paragraph labels made it answer "2.1.5" or start the answer with the label. Labels are now `S2P1`, and codes written in the answer are not counted as figures.
- It answered a bare "Sí" or "No". The schema now requires 80 to 450 characters.
- The model's own citations were unreliable (it copied from one article and cited another), so they are not used: the system finds the paragraphs that cover the answer (`app/verify.py: attribute`) and shows those, verbatim.

| Defenses | Shown | Correct | Wrong | Empty | Correct blocked | Wrong blocked |
|---|---|---|---|---|---|---|
| None | 39 | 13 | 25 | 1 | 0 | 0 |
| Layer 1 only (similarity floor 0.45) | 36 | 13 | 22 | 1 | 0 | 3 |
| Layer 3 only (verification) | 18 | 11 | 6 | 1 | 2 | 19 |
| Layers 1 and 3 | 17 | 11 | 5 | 1 | 2 | 20 |

- Without defenses the model never refuses: 0 of 7 questions that must be refused (arepa recipe, prison sentence, cookie banner, Ley 1266, GDPR, cost of the registry) are refused, and it accepts the false premises of 3 of 4 correction questions.
- Layer 1 alone blocks 3 wrong answers and no correct one. It is cheap but weak, as section 3 predicted.
- Layer 3 does most of the work: 19 of 25 wrong answers blocked. It also blocks 2 of 13 correct ones (`b17`, `b22`: right in substance but with little overlap with the cited text).
- Together: 20 of 25 wrong answers blocked, 11 of 13 correct answers kept. 5 of 17 shown answers are still wrong (29%, against 64% with no defenses on this sample).

What still gets through (`b03`, `b07`, `b19`, `q25`, `q39`): answers that flip the meaning ("No, you have no right to deletion", "the law applies to domestic databases") or invent a source ("the GDPR establishes ..." built from words of the Colombian text). The check compares vocabulary, not meaning, so it cannot see a negation or a wrong attribution. This is the main open problem. Candidate next step: an entailment model (the answer must follow from the cited paragraph), which needs a model download.

Thresholds (0.6 minimum support, 0.45 floor) were chosen on these same 39 answers after looking at them, so the table is in-sample and optimistic. Sweeping the support from 0.3 to 0.8: refusals correct 4 to 7 of 7, plain questions answered 13 to 8 of 16; 0.6 is the knee (6 of 7, 12 of 16). Floor 0.48 blocks 4 of 7 refusals but also 1 plain and 4 limited/corrected questions, so 0.45 was kept. The held-out set is the confirmation still to do.

Latency: 30 to 95 s per answer on this CPU (prompt reading about 26 to 40 tokens/s, generation 3 to 9 tokens/s, varying by run). Thread count (4, 6, 10) changed less than run-to-run noise.

## 8. Held-out confirmation: the defenses do not hold on non-lawyer questions

The 20 held-out questions were run whole, with the thresholds frozen from section 7 (0.6 support, 0.45 floor). Each answer was graded after seeing which defenses blocked it, without changing anything (`grades_heldout.json`; same limits as section 7: the reader is not a lawyer, and h06, h15 and h18 are debatable). Output: `results_answers_heldout.txt`.

| Defenses | Shown | Correct | Wrong | Empty | Correct blocked | Wrong blocked |
|---|---|---|---|---|---|---|
| None | 20 | 5 | 10 | 5 | 0 | 0 |
| Layer 1 only | 17 | 4 | 10 | 3 | 1 | 0 |
| Layers 1 and 3 | 5 | 0 | 5 | 0 | 5 | 5 |

- **All 5 answers that passed verification are wrong** (h04, h08, h09, h19, h20), and all 5 correct answers were blocked. On this set the verification chose by vocabulary overlap, and overlap does not separate right from wrong.
- Half of the wrong answers were blocked (5 of 10) and the other half passed or was not reached. Without defenses, 10 of 20 are wrong; with them, everything shown is wrong. Blocking is not worthless (5 fabrications stopped, plus 5 empty answers), but nothing that remains can be trusted.
- The failures that pass are the ones section 7 predicted: confident answers that go beyond the corpus (h20: "yes, the data of a deceased person can be deleted", when the corpus does not cover it; h08: "yes, answering every health field is obligatory", the opposite of the law), answers built on an irrelevant article (h04 cites the binding corporate rules), and answers that mix in another law (h19).
- One answer was cut off and one is a bare refusal; the model refuses by itself only when the question is very far from the text (h03, h10).

Why section 7 looked better: on non-lawyer development questions the same pattern was already there (4 shown, 1 correct: b03, b07, b19 wrong; b20 right). The development sample was mostly model-written questions that reuse the corpus vocabulary, where the model copies the right article and verification passes it. Combining both non-lawyer sets, 1 of 9 shown answers is correct.

Conclusion for this system, as it stands: retrieval is the reliable part (an expected or relevant article is among the 4 shown for 0.86 of the non-lawyer development questions and 0.75 of the held-out ones, section 6); the 1B generator is not. The checks block obvious inventions (recipe, prison sentence, wrong figures) but cannot see a reversed meaning or an irrelevant source. Presenting generated text as the answer would be misleading. Options measured or to be measured: show the retrieved paragraphs verbatim as the primary result and the generated text only as a labelled summary; an entailment check on the answer; the 3B model (about 3 times slower, so not interactive on this CPU).
