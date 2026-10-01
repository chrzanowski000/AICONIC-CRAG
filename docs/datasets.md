# Datasets

The same pipeline can run over different sets of documents. Each set is a **dataset**: one folder
in `data/` with its own documents and its own questions. There are three:

| name | company | documents | questions | list of documents and cases |
|---|---|---:|---:|---|
| `helios` (default) | Helios Dynamics, a drone maker in Tallinn | 40 | 34 | [`corpus.md`](corpus.md) |
| `brightwater` | Brightwater Ferries, a ferry company in Port Alder | 30 | 26 | below |
| `larkfield` | Larkfield Motors, a factory in Brennmoor that builds e-bike motors | 28 | 20 | below |

They never mix. Each dataset has its own folder, its own Qdrant collection and its own
LangSmith dataset:

| | `helios` | `brightwater` | `larkfield` |
|---|---|---|---|
| documents | `data/helios/corpus/` | `data/brightwater/corpus/` | `data/larkfield/corpus/` |
| questions | `data/helios/questions.json` | `data/brightwater/questions.json` | `data/larkfield/questions.json` |
| Qdrant collection | `helios_docs` | `brightwater_docs` | `larkfield_docs` |
| index hash | `qdrant_data/helios_docs.sha256` | `qdrant_data/brightwater_docs.sha256` | `qdrant_data/larkfield_docs.sha256` |
| LangSmith dataset | `rag-conflicts-helios-<fingerprint>` | `rag-conflicts-brightwater-<fingerprint>` | `rag-conflicts-larkfield-<fingerprint>` |
| LangSmith experiments | `rag-conflicts-helios-...` | `rag-conflicts-brightwater-...` | `rag-conflicts-larkfield-...` |

The prompts, the rules, the thresholds and the model are the same for every dataset. Nothing in
the code knows about a company.

## Switching

Switching can't mix the datasets up: each one has its own documents, questions, Qdrant
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
Brightwater and Larkfield; a new dataset may need a check with `search`.

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

## The Larkfield Motors documents

28 made-up documents about Larkfield Motors, a factory in Brennmoor that builds electric motors
for e-bikes. Here the system advises people on the production line: torque values, oven settings,
breaks, quality tests, forklifts, safety rules and what to do when a machine stops. 83 to 169
words each. They follow the same rules as the other datasets: the documents of a dispute never
mention each other and have no `supersedes` link, a replaced document is named in the text and in
`supersedes`, and apart from the planned disputes no two documents give different values for the
same thing.

| id | title | source | date | topic | supersedes | key fact | role |
|---|---|---|---|---|---|---|---|
| D01 | Torque Settings for the Motor Housing (v1) | Engineering Work Instructions | 2024-03-04 | housing-torque | – | M6 housing bolts 9 Nm | old |
| D02 | Torque Settings for the Motor Housing (v2) | Engineering Work Instructions | 2025-02-10 | housing-torque | D01 | M6 housing bolts 10 Nm | replaces D01 |
| D03 | Line 2 Output Targets (2023) | Production Planning | 2023-01-09 | line2-output | – | 40 motors per hour | old (chain) |
| D04 | Line 2 Output Targets (2024) | Production Planning | 2024-01-08 | line2-output | D03 | 45 motors per hour | replaces D03, replaced by D05 |
| D05 | Line 2 Output Targets (2025) | Production Planning | 2025-01-06 | line2-output | D04 | 48 motors per hour | newest of the chain |
| D06 | Curing Oven Settings (v1) | Engineering Work Instructions | 2024-05-06 | curing-oven | – | 160 °C, 30 minutes | old |
| D07 | Curing Oven Settings (v2) | Engineering Work Instructions | 2025-04-14 | curing-oven | D06 | 160 °C, 25 minutes | replaces D06 |
| D08 | Curing Oven Quick Card | Line notice board | 2025-05-02 | curing-oven | – | 160 °C, 25 minutes | agree (with D07) |
| D09 | Shift Rules | HR Handbook | 2025-01-15 | breaks | – | 30-minute meal break; the team leader sets the break rota | dispute A |
| D10 | Works Council FAQ: Breaks | Works Council wiki | 2025-04-02 | breaks | – | 45-minute meal break; the team leader sets the break rota | dispute A |
| D11 | Quality Plan: Final Test | Quality Manual | 2025-02-03 | final-test | – | full test on 1 motor in 50; a failed motor gets a red tag and goes to the quarantine cage | dispute B |
| D12 | Test Bench Wiki: Full Test | Test team wiki | 2025-06-20 | final-test | – | full test on 1 motor in 100; red tag, quarantine cage | dispute B |
| D13 | Site Traffic Rules | EHS Manual | 2025-01-10 | forklifts | – | forklifts at most 10 km/h in the hall | dispute C (three docs) |
| D14 | Forklift Driver Card | Logistics | 2025-03-05 | forklifts | – | 8 km/h | dispute C (three docs) |
| D15 | Logistics Channel Digest | #logistics Slack digest | 2025-06-30 | forklifts | – | 6 km/h | dispute C (three docs) |
| D16 | PPE Rules | EHS Manual | 2025-02-01 | safety-glasses | – | safety glasses at all times, at every station | dispute D (in words) |
| D17 | Line 1 Team Brief, May 2025 | Line 1 team brief | 2025-05-12 | safety-glasses | – | glasses only at the press and grinding stations; optional at the assembly benches | dispute D (in words) |
| D18 | Lockout Procedure | EHS Manual | 2025-01-20 | lockout | – | emergency stop, own red padlock on the main switch, test that it does not start | agree |
| D19 | Press Station Work Instruction | Engineering Work Instructions | 2025-03-03 | lockout | – | the same steps before clearing a jam in the press | agree |
| D20 | Noise Map 2025 | EHS | 2025-02-20 | hearing | – | Hall B, the stamping hall: hearing protection required | agree (three docs, different words) |
| D21 | Safety Card for New Starters | EHS | 2025-03-10 | hearing | – | ear protection in the stamping hall | agree (three docs, different words) |
| D22 | Induction Checklist | HR Onboarding | 2024-11-18 | hearing | – | Hall B (stamping): ear protection is a must | agree (three docs, different words) |
| D23 | Reporting a Machine Breakdown | Maintenance | 2025-01-08 | breakdowns | – | andon button, call maintenance on 4400 | one answer |
| D24 | Fire Alarm and Muster Point | EHS | 2024-10-01 | fire | – | muster point in Car Park C | one answer |
| D25 | Scrap Reporting | Quality Manual | 2025-03-20 | scrap | – | scrap log, coloured bins; nothing about a bonus | near a "no answer" question |
| D26 | Calling in Sick | HR Handbook | 2025-01-15 | sickness | – | call the supervisor 1 h before; no number of sick days | near a "no answer" question |
| D27 | Company Overview | Comms | 2024-06-01 | company | – | founded 2006, about 350 people | filler |
| D28 | Canteen and Lockers | Facilities | 2025-02-25 | facilities | – | canteen, lockers, showers; no gym | near a "no answer" question |

### The cases

| case | documents | questions | expected outcome |
|---|---|---|---|
| documents agree | D07 + D08 (time in the oven); D18 + D19 (lockout); D20 + D21 + D22 (hearing protection, in different words); D09 + D10 (who sets the breaks); D11 + D12 (what happens to a failed motor) | Q7, Q11, Q12, Q13, Q14 | answered, citing every agreeing document |
| documents disagree | D09 vs D10; D11 vs D12; D13 vs D14 vs D15 (three documents); D16 vs D17 (in words, a safety rule) | Q3, Q4, Q9, Q10, Q17 (reworded) | disputed: every version with its date, what differs, no answer |
| one document answers | D23, D24 | Q1, Q15, Q16 (reworded) | answered from that document |
| no document answers | nothing about a gym, a number of paid sick days, a scrap bonus, or football | Q5, Q18, Q19, Q20 | abstained; Q20 is stopped at the search |
| a document replaced by a newer one | D01 → D02; D06 → D07 (also with the same value, Q8); D03 → D04 → D05 (a chain of three) | Q2, Q6, Q7, Q8 | answered from the newest, with an "outdated" note for each older one |

The split by outcome (the LangSmith split): 11 `one_answer`, 5 `dispute`, 4 `no_answer`.

As in the other datasets, the two sides of a dispute agree on other points: D09 and D10 disagree
on the length of the meal break (Q3) and agree that the team leader sets the break rota (Q11);
D11 and D12 disagree on how often a motor gets the full test (Q9) and agree on what happens to a
motor that fails it (Q12). In disputes A and B the newer document is on purpose not the
"official" one (a works council FAQ against the HR Handbook, a team wiki against the Quality
Manual). Dispute D is about a safety rule, where picking one side quietly would be most harmful.
