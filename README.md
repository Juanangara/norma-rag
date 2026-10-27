# Norma — local RAG over Colombian personal-data law

Ask a question in plain Spanish ("me pidieron la cédula para un descuento, ¿es legal?") and get the **articles of the law that answer it, verbatim, with their source**. Everything runs on a laptop: no cloud, no API keys, no GPU.

Corpus: **Ley 1581 de 2012** (30 articles) and **Decreto 1074 de 2015, capítulo 25** (35 articles, which compiles the old Decreto 1377 de 2013). Provenance and checks: [`corpus/SOURCES.md`](corpus/SOURCES.md).

This is a study of how far a small local model can be trusted in a legal domain, and the answer it measured is "not far": the project is built around that result. Read [`eval/REPORT.md`](eval/REPORT.md) for the numbers.

## What it does

```
question ─▶ retrieve (bge-m3 + pgvector, reference resolution) ─▶ articles, verbatim  ◀── main result
                  │
                  └─ too far from every article? ─▶ "I found nothing about this"      (defense 1)
                  │
                  └─ --resumen: local LLM (JSON only) ─▶ checks ─▶ labelled summary    (defenses 2 and 3)
```

- **Retrieval** is the result. Vector search over article-sized chunks (long articles are split by paragraph, "Definiciones" one definition per chunk), plus explicit references: "artículo 9 del Decreto 1377" resolves to the article that replaced it (2.2.2.25.2.6).
- **A summary is optional and labelled automatic.** The local LLM (Llama 3.2 1B by default, swappable) answers in bounded JSON; the system then looks for the paragraphs that support it, rejects figures that appear nowhere in what it was shown, and rejects answers the retrieved text does not cover.
- **It says when it does not know**: out-of-scope questions get a refusal, never an invented answer.

## What was measured (and what it means)

| | Result |
|---|---|
| Retrieval, questions I wrote after reading the corpus (40) | an expected article in the top 4: **0.97** |
| Retrieval, 22 questions from a non-lawyer (development) | **0.77** (any relevant article: 0.86) |
| Retrieval, 20 questions from a non-lawyer (held out, scored once) | **0.60** (any relevant article: 0.75) |
| `bge-m3` vs `multilingual-e5-small`, non-lawyer MRR (dev / held-out) | 0.67 vs 0.30 / 0.55 vs 0.48 |
| Reranker `bge-reranker-v2-m3` | no gain, lower MRR (0.51 vs 0.67), ~40 s per question on CPU: discarded |
| Hybrid (Spanish full-text + vector) | did not beat vector alone |
| **1B model, summaries that passed all checks, held-out** | **0 of 5 correct** |

The last row is why the main output is the law and not generated text. On held-out questions every summary that passed the checks was wrong: it reversed the meaning ("answering every health field is obligatory") or asserted what the corpus does not cover. The checks do stop obvious fabrications (a recipe, a prison sentence, an invented figure): 20 of 25 wrong answers blocked on the development sample. They cannot see a reversed meaning. Details, failure cases and the method (thresholds were tuned on development answers only): `eval/REPORT.md`, sections 7 and 8.

## Limits you should know

- **Not legal advice.** Every result says so. The labels of the evaluation sets were proposed by the model that built the system and are **not reviewed by a lawyer**; 8 are flagged `dudoso`. The answers were also graded by that model.
- The evaluation sets are small (20 to 47 questions): one question moves a score by 0.02 to 0.05.
- The texts are digital copies (SUIN, Función Pública), compared with each other but not with the Diario Oficial. A reform bill (Proyecto de Ley Estatutaria 282 de 2026 Cámara) was pending when the corpus was fetched; check its status before relying on the text.
- Decreto 1377 de 2013 is reachable only through the equivalences to the Decreto 1074 chapter. Other norms (e.g. Ley 1266, habeas data financiero) are out of scope and refused.
- On CPU a summary takes 30 to 95 s; search alone takes well under a second once the model is loaded.

## Run it

Needs Docker, Python 3.11 and about 4 GB of free RAM (6 GB with the summary).

```bash
cp .env.example .env                  # set POSTGRES_PASSWORD; MODELS_DIR for the summary (below)
docker compose up -d db
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # .venv/bin/pip on Linux/macOS
.venv/Scripts/python -m ingest.build  # corpus/raw -> corpus/articles/*.jsonl (already included)
.venv/Scripts/python -m ingest.load   # chunk, embed with bge-m3 (first run downloads ~2.3 GB), load pgvector
.venv/Scripts/python -m app.cli "Mi vecino subió una foto mía a internet sin permiso, ¿es un tema de datos personales?"
```

Or open the local web page (standard library only, bound to `127.0.0.1`):

```bash
.venv/Scripts/python -m app.web       # then open http://127.0.0.1:8765
```

It shows the closest articles as cards (first paragraph visible, the rest folded), with example questions, and an optional checkbox for the automatic summary.

For the summary, point `MODELS_DIR` at a folder with a GGUF file (default `Llama-3.2-1B-Instruct-Q4_K_M.gguf`, ~0.8 GB, from `bartowski/Llama-3.2-1B-Instruct-GGUF` on Hugging Face), then:

```bash
docker compose up -d llama
.venv/Scripts/python -m app.cli --resumen "¿Qué es un dato sensible?"
```

Any other GGUF works by changing `MODEL_FILE`. Any other embedding model works by changing `EMBEDDING_MODEL` and re-running `ingest.load` (the table is recreated with the model's vector size).

## Reproduce the evaluation

```bash
python -m eval.run_retrieval eval/blind.jsonl     # retrieval on a set (questions, blind, heldout)
python -m eval.experiments bge-m3 e5-base         # compare embedding models in memory (--rerank for the reranker)
python -m eval.latency e5-small                   # load / index / query time and memory of a model
python -m eval.run_answers questions blind        # generate with the local LLM (~1 min per question)
python -m eval.score_answers --detail             # defenses on the cached answers
python -m pytest                                  # 54 tests (retrieval tests need the database)
```

`eval/heldout.jsonl` is reserved for final confirmation: look at it once, after choosing.

## Layout

```
corpus/   raw texts, parsed articles (JSONL, the source of truth), SOURCES.md
ingest/   parse → chunk → embed → load into pgvector
app/      retrieve (vector, full-text, reference resolution), generate (bounded JSON), verify, answer, cli, web (+ static/)
eval/     question sets, retrieval and answer scoring, model/reranker experiments, REPORT.md
db/       schema template      tests/    unit and integration tests
```

## License

Code: MIT, see `LICENSE`. The laws in `corpus/` are public legal texts; their provenance is in `corpus/SOURCES.md`.
