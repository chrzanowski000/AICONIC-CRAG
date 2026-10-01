# Setup

## What you need

- Python 3.12 (tested on WSL2 Ubuntu, CPU only, no GPU needed).
- An OpenRouter key with a little credit. A full demo run costs well under one cent.
- About 100 MB of disk: 65 MB for the embedding model, a few MB for the Qdrant data.
- Optional: a LangSmith key, if you want traces and the LangSmith eval (see below).
- Optional: Docker, if you want to run Qdrant as a server.

## Install

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # then put your OpenRouter key in LLM_API_OR
```

`requirements-dev.txt` holds tools you only need for development: `pytest` for the unit tests,
and `langgraph-cli[inmem]` for LangGraph Studio.

```bash
pip install -r requirements-dev.txt
python -m pytest                     # unit tests, no model calls, free
```

## First run

```bash
python main.py config                    # check the settings; the key is shown masked
python main.py index                     # downloads the embedding model once, builds the index
python main.py search "parental leave"   # retrieval test, no model calls, costs nothing
python main.py llm-test                  # one LLM call through OpenRouter, checks the key
python main.py ask "How many weeks of paid parental leave does Helios Dynamics offer?"
```

`ask` prints the result, then a short trace of every step (switch it off with
`SHOW_SCORES=false`), then the tokens, the cost of this run and the running total.

`index` prints `Rebuilt collection 'helios_docs' (embedded mode): 40 points. Reason: ...` the first
time, and `Reused ...` after that. It rebuilds by itself when a document changes. Use
`python main.py index --reindex` to force a rebuild.

## Choosing the dataset

There are three datasets: `helios` (the default), `brightwater` and `larkfield`. Pick one for one
command with the flag (in `main.py` it goes before the command), or for every command in `.env`:

```bash
python main.py --dataset brightwater ask "Can I bring my dog on the ferry?"
python eval.py --dataset brightwater
```

```
DATASET=brightwater
```

If both are set, the flag wins over `.env`. Only one program can use `qdrant_data/` at a time, so stop `langgraph dev` or a running eval
before you start another command. The full steps (stop, pick, check) are in
[`datasets.md`](datasets.md#switching).

## Where things are stored

| folder / file | what | safe to delete? |
|---|---|---|
| `models/` | the downloaded embedding model | yes, it is downloaded again |
| `qdrant_data/` | the Qdrant data (embedded mode): one collection per dataset, and `<name>_docs.sha256` | yes, run `index` again |
| `.spend.json` | running total of money spent by this app | yes, the total starts again at 0 |
| `.env` | your keys | no, and never commit it |

## Settings

Every setting of the app is in `config.py` and can be changed in `.env` or in the shell with the
same name, for example `SHOW_SCORES=false python main.py ask "..."`. `python main.py config`
prints them all. The main ones are listed in `architecture.md`.

## LangSmith (optional)

Tracing is **off** by default. To use it:

1. Put your key in `.env` under exactly this name: `LANGSMITH_API_KEY=lsv2_...`
   (`LANG_SMITH_API_KEY` or other spellings are not read).
2. Switch tracing on, for one command or for good:
   ```bash
   LANGSMITH_TRACING=true python main.py ask "How many weeks of paid parental leave does Helios Dynamics offer?"
   LANGSMITH_TRACING=true python eval.py      # also creates the dataset and runs an experiment
   ```
   or add `LANGSMITH_TRACING=true` to `.env`.
3. Traces go to the project `rag-conflicts` (change it with `LANGSMITH_PROJECT`). Each command
   ends with `Traces sent to LangSmith project 'rag-conflicts'.`

If `LANGSMITH_TRACING=true` is set but the key is missing, every command prints
`WARNING: LANGSMITH_TRACING=true but no LANGSMITH_API_KEY is set, so tracing is off.` and runs
without tracing.

Keys from the EU region also need `LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com` in
`.env`. The default is the US server.

## LangGraph Studio (optional)

Studio shows the graph, lets you type a question, and shows the state after every step.

```bash
pip install -r requirements-dev.txt     # once: langgraph-cli[inmem]
langgraph dev                           # from the repo root, with the venv active
```

Then open <https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024>, or in Studio's
"Configure Studio connection" dialog enter the base URL `http://127.0.0.1:2024` and press
Connect. Pick the graph `helios_rag`; the input form has one field, `question`.

Read the result in the **`output`** field of the last step (`answer`, `conflict_report` or
`abstain`): it is the same text the CLI prints (`STATUS: ...`, the answer or both versions, the
sources). The same data is also in `result` as an object, but Studio's step view may show only
part of a nested object.

- `langgraph.json` tells the server where the graph is (`src/studio.py:graph`) and loads `.env`.
  `src/studio.py` builds the index if needed, then builds the graph.
- The dataset is fixed when the server starts. To use Brightwater, start it with
  `DATASET=brightwater langgraph dev` (or set `DATASET` in `.env`); to switch, stop it and start
  it again.
- While the server runs it holds `qdrant_data/`, so `main.py` and `eval.py` stop with
  `ERROR (LockedStorageError)`. Stop the server (Ctrl+C) first, or use `QDRANT_MODE=server` for
  both.
- WSL: the Windows browser reaches `127.0.0.1:2024` in WSL (tested). Brave and Safari block a
  secure page from calling plain `http://` on localhost; use `langgraph dev --tunnel` there.
- Studio shows each step itself; runs are **not** sent to LangSmith unless you start the server
  with `LANGSMITH_TRACING=true langgraph dev`.
- Runs through Studio are not added to `.spend.json` and their cost is not printed.
- The server reloads when a `.py` file changes. Its local threads live in `.langgraph_api/`
  (not committed).

## Qdrant server mode (optional)

Embedded mode lets only one program use `qdrant_data/` at a time. A Qdrant server allows many at
once, for example Studio and the CLI together.

```bash
docker pull qdrant/qdrant:latest
docker run -p 6333:6333 qdrant/qdrant:latest
```

Then set `QDRANT_MODE=server` in `.env` (the server is at `QDRANT_URL`, default
`http://localhost:6333`), or set it for one command:

```bash
QDRANT_MODE=server python main.py index
QDRANT_MODE=server python main.py demo
```

The first command on each dataset builds its collection on the server. The hash files that tell
when a rebuild is needed stay in `qdrant_data/`.

Use a recent server. The client is `qdrant-client` 1.19.1; an old server (tested: 1.16.3) still
works but prints a version warning. `latest` was 1.19.1 on 2026-09-29 and gave the same demo
results as embedded mode.

## Problems

**A command stops with `ERROR (LockedStorageError)`: "The Qdrant folder ... is in use by another
process."** Embedded Qdrant allows only one program at a time, and another one is still running:
`langgraph dev`, `eval.py` or another `main.py`. Find it and stop it (Ctrl+C in its terminal):

```bash
ps aux | grep -E "langgraph dev|eval.py|main.py" | grep -v grep
```

Don't delete `qdrant_data/.lock`. The lock goes away by itself when the program stops; deleting
the file only lets two programs write to the same folder at once. To run several programs at
once, use server mode.

**The embedding model does not download.** FastEmbed needs to reach Hugging Face once. After
that the model is read from `./models`.

**A command stops with `ERROR (StructuredOutputError)` or an OpenRouter error.** The LLM reply
could not be read, or the call failed (bad key, no credit, unknown model id, network). The
message says which. Check the key with `python main.py llm-test`.

**A command stops with `ERROR (CorpusError)`.** A document in `data/<name>/corpus/` has missing or bad
frontmatter, a duplicate id, a `supersedes` target that does not exist, or a `supersedes` link
between two different topics. The message names the file.
