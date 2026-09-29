# Setup

## What you need

- Python 3.12 (tested on WSL2 Ubuntu, CPU only, no GPU needed).
- An OpenRouter key with a little credit. A full demo run costs well under one cent.
- About 100 MB of disk: 65 MB for the embedding model, a few MB for the Qdrant data.
- Optional: a LangSmith key, if you want traces and the LangSmith eval.
- Optional: Docker, if you want to run Qdrant as a server.

## Install

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # then put your OpenRouter key in LLM_API_OR
```

`requirements-dev.txt` holds tools that are only needed to redraw the chart in `docs/models.md`.

## First run

```bash
python main.py config                    # check the settings; the key is shown masked
python main.py index                     # downloads the embedding model once, builds the index
python main.py search "parental leave"   # retrieval test, no model calls, costs nothing
```

`index` prints `Rebuilt collection 'helios_docs' (embedded mode): 20 points.` the first time, and
`Reused ...` after that. It rebuilds by itself when a document changes. Use
`python main.py index --reindex` to force a rebuild.

## Where things are stored

| folder / file | what | safe to delete? |
|---|---|---|
| `models/` | the downloaded embedding model | yes, it is downloaded again |
| `qdrant_data/` | the Qdrant data (embedded mode) and `corpus.sha256` | yes, run `index` again |
| `.spend.json` | running total of money spent by this app | yes, the total starts again at 0 |
| `.env` | your keys | no, and never commit it |

## Settings

Every setting is in `config.py` and can be changed in `.env` or in the shell with the same name,
for example `JUDGE=llm python main.py ask "..."`. `python main.py config` prints them all.

## Qdrant server mode (optional)

```bash
docker pull qdrant/qdrant:latest
docker run -p 6333:6333 qdrant/qdrant:latest
QDRANT_MODE=server python main.py index
QDRANT_MODE=server python main.py demo
```

Use a recent server. The client is `qdrant-client` 1.19.1; an old server (tested: 1.16.3) still
works but prints a version warning. `latest` was 1.19.1 on 2026-09-29 and gave the same demo
results as embedded mode. In server mode the keyword indexes on `metadata.topic` and
`metadata.id` are created too (embedded mode ignores them).

## Problems

**"The Qdrant folder ... is in use by another process."** Embedded Qdrant allows only one process
at a time. Close the other `main.py` or `eval.py` run. If none is running, delete
`qdrant_data/.lock`. Or use server mode.

**A command stops with `ERROR (JevError)`.** Jev failed and `JUDGE_FALLBACK=none` is set. With
the default `JUDGE_FALLBACK=llm` the LLM judges instead and a warning is logged.

**The embedding model does not download.** FastEmbed needs to reach Hugging Face once. If ONNX
does not work on your machine, install `langchain-huggingface sentence-transformers` and set
`EMBEDDING_BACKEND=huggingface` (same model, same 384 numbers), then run
`python main.py index --reindex`.
