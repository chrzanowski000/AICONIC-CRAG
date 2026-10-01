# Datasets

The same pipeline can run over different sets of documents. Each set is a **dataset**: one folder
in `data/` with its own documents and its own questions. There are two:

| name | company | documents | questions | list of documents and cases |
|---|---|---:|---:|---|
| `helios` (default) | Helios Dynamics, a drone maker in Tallinn | 40 | 34 | [`corpus.md`](corpus.md) |
| `brightwater` | Brightwater Ferries, a ferry company in Port Alder | 30 | 26 | below |

The two never mix. Each dataset has its own folder, its own Qdrant collection and its own
LangSmith dataset:

| | `helios` | `brightwater` |
|---|---|---|
| documents | `data/helios/corpus/` | `data/brightwater/corpus/` |
| questions | `data/helios/questions.json` | `data/brightwater/questions.json` |
| Qdrant collection | `helios_docs` | `brightwater_docs` |
| index hash | `qdrant_data/helios_docs.sha256` | `qdrant_data/brightwater_docs.sha256` |
| LangSmith dataset | `rag-conflicts-helios-<fingerprint>` | `rag-conflicts-brightwater-<fingerprint>` |
| LangSmith experiments | `rag-conflicts-helios-...` | `rag-conflicts-brightwater-...` |

The prompts, the rules, the thresholds and the model are the same for every dataset. Nothing in
the code knows about a company.

## Switching

Switching can't mix the two datasets up: each one has its own documents, questions, Qdrant
collection and LangSmith dataset. The one thing to watch is that only one program can use
`qdrant_data/` at a time.

### 1. Stop anything that uses `qdrant_data/`

That means `langgraph dev`, `eval.py`, or another `main.py` command. Press Ctrl+C in its
terminal. To check that nothing is left:

```
ps aux | grep -E "langgraph dev|eval.py|main.py" | grep -v grep
```

No output means nothing is running. If a command still stops with `ERROR (LockedStorageError)`,
something is still running: find it with the line above and stop it. Don't delete
`qdrant_data/.lock`. The lock goes away by itself when the program stops; deleting the file only
lets two programs write to the same folder at once.

### 2. Pick the dataset

**For one command**, add the flag. In `main.py` it goes before the command:

```
python main.py --dataset brightwater ask "Can I bring my dog on the ferry?"
python main.py --dataset brightwater demo
python eval.py --dataset brightwater
```

**For every command, until you change it back**, set it in `.env`:

```
DATASET=brightwater
```

If both are set, the flag wins over `.env`.

**For LangGraph Studio**, the dataset is fixed when the server starts. Stop it and start it again
to switch:

```
DATASET=brightwater langgraph dev
```

### 3. Check which one is active

```
python main.py --dataset brightwater config | grep -E "DATASET|CORPUS|COLLECTION|EVAL_DATASET"
```

This shows the dataset (`DATASET`), the folder (`CORPUS_DIR`), the Qdrant collection
(`QDRANT_COLLECTION`, here `brightwater_docs`) and the LangSmith dataset name
(`EVAL_DATASET_NAME`). Leave out `--dataset` to see what `.env` picks. The eval also prints
`Local eval: dataset brightwater, ...` at the start.

### What happens by itself

- **Index.** The first time you use a dataset, its index is built (by `index`, `search`, `ask`,
  `demo`, `eval.py` or Studio, whichever runs first). It takes a few seconds and costs nothing. After that it is reused, and it is rebuilt only if one of that
  dataset's documents changes. Switching never rebuilds or touches the other dataset.
- **LangSmith.** `LANGSMITH_TRACING=true python eval.py --dataset brightwater` uses
  `rag-conflicts-brightwater-<fingerprint>`; without the flag it uses
  `rag-conflicts-helios-<fingerprint>`. The first run creates the LangSmith dataset from
  `data/<name>/questions.json`; later runs reuse it until the questions change. In the LangSmith
  UI, pick the dataset to see its experiments and compare them. Every trace carries `dataset` in
  its metadata, so traces of `ask` and `demo` can be filtered by dataset in the project
  `rag-conflicts`.

### Studio and the CLI at the same time

Run Qdrant as a server, which allows many programs at once:

```
docker run -p 6333:6333 qdrant/qdrant
```

Then set `QDRANT_MODE=server` in `.env`. The first command on each dataset builds its collection
on the server. More in [`setup.md`](setup.md#qdrant-server-mode-optional).

## Adding a dataset

1. Make `data/<name>/corpus/` with one markdown file per document, in the same format as the
   others (`id, title, source, date, topic, supersedes`, see [`corpus.md`](corpus.md)). A
   document and the document it replaces must share a `topic`.
2. Write `data/<name>/questions.json` in the same format (see [`evaluation.md`](evaluation.md)).
   Mark a few questions `"demo": true` for `main.py demo`.
3. Run `python -m pytest`: one test loads every dataset and checks that its questions only name
   documents that exist.
4. Run `python main.py --dataset <name> search "<q>"` on a few questions to see the scores, then
   `python eval.py --dataset <name>` twice.

The score cutoff (0.58) and margin (0.10) were chosen on Helios. They worked unchanged for
Brightwater; a new dataset may need a check with `search`.

## The Brightwater Ferries documents

30 made-up documents about Brightwater Ferries, which runs four car and passenger ferries from
Port Alder to the islands of Skerra and Holm. 107 to 145 words each. They follow the same rules as
the Helios documents: the documents of a dispute never mention each other and have no
`supersedes` link, a replaced document is named in the text and in `supersedes`, and apart from
the planned disputes no two documents give different values for the same thing.

| id | title | source | date | topic | supersedes | key fact | role |
|---|---|---|---|---|---|---|---|
| D01 | Baggage Allowance (2024) | Passenger Guide | 2024-02-01 | luggage | – | 20 kg free | old |
| D02 | Baggage Allowance (2025) | Passenger Guide | 2025-03-01 | luggage | D01 | 23 kg free | replaces D01 |
| D03 | Staff Travel Discount (2023) | HR Handbook | 2023-01-01 | staff-travel | – | 30% off | old (chain) |
| D04 | Staff Travel Discount (2024) | HR Handbook | 2024-01-01 | staff-travel | D03 | 40% off | replaces D03, replaced by D05 |
| D05 | Staff Travel Discount (2025) | HR Handbook | 2025-01-01 | staff-travel | D04 | 50% off | newest of the chain |
| D06 | MV Kittiwake Specification v1 | Fleet Engineering | 2023-05-10 | vessel-kittiwake | – | 280 passengers, 60 cars | old |
| D07 | MV Kittiwake Specification v2 | Fleet Engineering | 2025-04-15 | vessel-kittiwake | D06 | 320 passengers, 60 cars, 18 knots | replaces D06 |
| D08 | MV Kittiwake at a Glance | Marketing | 2025-05-20 | vessel-kittiwake | – | top speed 18 knots | agree (with D07) |
| D09 | Crew Pay Handbook | HR Handbook | 2025-01-20 | overtime | – | overtime 1.5×, shift captain approves | dispute A |
| D10 | Crew Council FAQ | Crew Council wiki | 2025-04-08 | overtime | – | overtime 1.75×, shift captain approves | dispute A |
| D11 | Passenger Terms: Cancellations and Refunds | Passenger Terms | 2025-02-01 | refunds | – | full refund up to 24 h before; back to the card | dispute B |
| D12 | Booking Desk Wiki: Refunds | Customer Service wiki | 2025-06-10 | refunds | – | full refund up to 48 h before; back to the card | dispute B |
| D13 | Port Alder Terminal Guide | Operations | 2025-01-15 | check-in | – | car check-in closes 30 min before | dispute C (three docs) |
| D14 | Website FAQ: Travelling by Car | Website | 2025-03-12 | check-in | – | 45 min before | dispute C (three docs) |
| D15 | Terminal Ops Channel Digest | #terminal-ops Slack digest | 2025-07-01 | check-in | – | 20 min before | dispute C (three docs) |
| D16 | Safety Manual: Drills | Marine Safety | 2025-02-05 | safety-drills | – | a drill every week | dispute D (in words) |
| D17 | Crew Bulletin, May 2025 | Crew Bulletin | 2025-05-30 | safety-drills | – | a drill once a month | dispute D (in words) |
| D18 | Crew Working Hours | HR Handbook | 2025-01-20 | crew-rest | – | at least 10 h rest in 24 h | agree |
| D19 | Compliance Note: Hours of Rest | Compliance | 2025-03-18 | crew-rest | – | minimum 10 h rest in 24 h | agree |
| D20 | Fare Table 2025 | Ticket Office | 2025-01-02 | fares | – | child aged 0 to 3: free | agree (three docs, different words) |
| D21 | Family Travel FAQ | Website | 2025-04-02 | fares | – | kids under 4 go free | agree (three docs, different words) |
| D22 | Ticket Office Handbook | Ticket Office | 2024-11-20 | fares | – | younger than four: free | agree (three docs, different words) |
| D23 | Onboard Services | Passenger Guide | 2025-02-15 | onboard-services | – | free wifi, café, shop | one answer |
| D24 | Reporting Sickness | HR Handbook | 2025-01-20 | crew-sickness | – | call the duty officer 4 h before | one answer |
| D25 | Uniform for New Crew | Operations | 2024-09-01 | uniform | – | three sets of uniform | one answer |
| D26 | Travelling with Pets | Passenger Guide | 2025-03-01 | pets | – | dogs and cats welcome, free | one answer |
| D27 | Winter Dinner 2025 | Comms | 2025-10-01 | company-events | – | 5 December 2025, Harbour Hall | one answer |
| D28 | Company Overview | Comms | 2024-06-01 | company | – | founded 2011, four ferries | filler |
| D29 | Accessibility on Board | Passenger Guide | 2025-02-15 | accessibility | – | a wheelchair user's companion travels free | one answer |
| D30 | How to Pay | Passenger Guide | 2025-01-10 | payments | – | card and mobile only, no cash | filler |

### The cases

| case | documents | questions | expected outcome |
|---|---|---|---|
| documents agree | D07 + D08 (top speed); D18 + D19 (rest); D20 + D21 + D22 (children free, in different words); D09 + D10 (who approves overtime); D11 + D12 (where refunds go) | Q9, Q12, Q13, Q14, Q15 | answered, citing every agreeing document |
| documents disagree | D09 vs D10; D11 vs D12; D13 vs D14 vs D15 (three documents); D16 vs D17 (in words) | Q3, Q4, Q10, Q11, Q20 (reworded) | disputed: every version with its date, what differs, no answer |
| one document answers | D23, D24, D25, D26, D27, D29 | Q1, Q16, Q17, Q18, Q19, Q21 (reworded), Q26 | answered from that document |
| no document answers | nothing about a casino, a pension, the CEO, sourdough bread, or a number of paid sick days | Q5, Q22, Q23, Q24, Q25 | abstained; Q24 is stopped at the search |
| a document replaced by a newer one | D01 → D02; D06 → D07 (also with the same value, Q8); D03 → D04 → D05 (a chain of three) | Q2, Q6, Q7, Q8 | answered from the newest, with an "outdated" note for each older one |

As in Helios, the two sides of a dispute agree on other points: D09 and D10 disagree on the
overtime rate (Q4) and agree that the shift captain approves overtime (Q13); D11 and D12 disagree
on the refund deadline (Q3, Q20) and agree that refunds go back to the card (Q12). In disputes A
and B the newer document is on purpose not the "official" one (a council FAQ against the HR
Handbook, a desk wiki against the Passenger Terms).
