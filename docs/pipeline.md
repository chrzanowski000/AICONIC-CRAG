# How the agent works

The system answers a question from 20 internal documents. It never pretends to know more than
the documents say. There are three possible outcomes:

| outcome | when | what the user sees |
|---|---|---|
| **answered** | the documents give one current answer | the answer, each sentence cited `[Dxx]`, plus a note if an older version of the fact exists |
| **disputed** | two current documents give different answers and neither one officially replaces the other | both versions with document id, source and date, and *no* answer |
| **abstained** | no document answers the question | a short "I don't know" plus the closest documents it looked at |

The main rule: **only an explicit `supersedes` link in the document metadata can make one source
win.** A newer date, a more official-looking source, or the language model's opinion never does.

## The graph

The pipeline is a LangGraph state graph. Each box is a step that reads some fields of a shared
state and writes others. Diamonds are decisions about where to go next.

```mermaid
flowchart TD
    START([question]) --> R[retrieve<br/><i>Qdrant search + score cutoff<br/>+ add docs with same topic or supersedes link</i>]
    R --> R1{any doc above<br/>the score cutoff?}
    R1 -- no --> AB[abstain<br/><i>Python</i>]
    R1 -- yes --> EC[extract_claims<br/><i>LLM, structured output</i><br/>one sentence per document:<br/>what does it say about the question?]
    EC --> J[judge<br/><i>Jev decision model</i><br/>per doc: is it relevant? p<br/>per pair: agree / disagree / unrelated? p]
    J -. if the API fails .-> JL[judge fallback<br/><i>LLM, structured output</i>]
    JL --> RC
    J --> RC[reconcile<br/><i>Python rules</i><br/>apply supersedes links,<br/>keep only real disputes,<br/>number check, pick the route]
    RC --> R2{route}
    R2 -- no relevant doc --> AB
    R2 -- disputes left --> CR[conflict_report<br/><i>Python</i><br/>show both versions with dates]
    R2 -- one current answer --> AN[answer<br/><i>LLM, structured output</i><br/>cited answer + outdated note]
    AB --> END([FinalOutput])
    CR --> END
    AN --> END
```

Two different models are used, and each has one job:

- **The LLM** (`openai/gpt-6-luna` through OpenRouter) writes text. It pulls out claims and
  writes the final answer. It is never asked "which document is right?" and it never writes the
  dispute report. So it cannot blur a contradiction into a vague middle ground.
- **Jev** (`typesafe/jev-1.13` through OpenRouter's Decisions API) makes decisions. It only
  answers yes/no and multiple-choice questions ("is this document relevant?", "do these two claims
  agree, disagree, or is one unrelated?") and returns a probability for each. It cannot write
  text at all.

Everything that turns those decisions into an outcome is plain Python with fixed rules.

## The state

One dictionary flows through the graph. Each step adds to it.

```python
class RAGState(TypedDict):
    question: str
    retrieved: list[RetrievedDoc]      # docs in context: id, title, source, date, topic, supersedes, text, score
    best_score: float                  # best similarity score among the first hits
    closest: list[dict]                # top search hits before the cutoff: {doc_id, score}, for "I don't know"
    claims: dict[str, str | None]      # doc_id -> one-sentence claim, or None if the doc says nothing
    judge_used: Literal["jev", "llm"]  # which judge actually ran
    relevance: dict[str, float]        # doc_id -> probability the doc answers the question
    pairs: list[dict]                  # {doc_a, doc_b, relation, p_disagree} for each compared pair
    relevant_ids: list[str]            # after reconcile
    outdated: list[dict]               # {old_id, old_date, old_claim, new_id, new_date}
    disputes: list[dict]               # {doc_a, doc_b, description}
    route: Literal["answer", "conflict", "abstain"]
    result: dict | None                # FinalOutput
```

## Step by step

### 1. `retrieve`

1. Turn the question into a vector locally (`BAAI/bge-small-en-v1.5`, 384 numbers, cosine).
2. Ask Qdrant for the 6 closest documents with scores. Keep a hit only if its score is at least
   `SCORE_THRESHOLD` (0.58) **and** at most `SCORE_MARGIN` (0.10) below the best hit. If nothing
   is left, go straight to `abstain`. No LLM call is spent.
3. **Add related docs.** This is the step that makes sure both sides of a conflict are present:
   - every document with the same `topic` as a hit is added (found by a metadata filter, not by
     similarity), and
   - every document linked to a hit by `supersedes`, in either direction, is added.
4. Remove duplicates, keep at most 10 (hits first, then the added ones, newest first).

Why add related docs: the two documents of a dispute (say "16 weeks" vs "12 weeks" of parental
leave) look almost the same to the search, so it usually finds both. But "usually" is not good
enough for a system whose whole point is to notice the second one. The topic filter makes it
certain. It really happens: for the parental leave question D03 scores 0.888 and D04 0.788, just
under the margin. D04 is dropped by the search and added back by the topic filter.

How the two numbers were chosen (`python main.py search "<q>"` prints the scores): the embedding
model gives even unrelated documents a cosine score of about 0.50 to 0.65, so no single cutoff
separates good from bad documents. The best hit of every answerable test question (including
paraphrases like "Who needs to approve my PR?") scored 0.62 or more; clearly unanswerable
questions (stock price, salary, dental cover) topped out at about 0.54. So the cutoff is 0.58.
It only throws out questions that are clearly off. The margin keeps the context small: for the
demo questions it leaves just the documents about the question (2 or 3), not ten loosely related
ones. The judge's relevance check, not the score, is the real gate.

### 2. `extract_claims` (LLM)

One structured-output call. Input: the question and every retrieved document with its metadata.
Output, checked by Pydantic:

```json
{"claims": [
  {"doc_id": "D03", "claim": "Helios offers 16 weeks of fully paid parental leave."},
  {"doc_id": "D04", "claim": "Employees receive 12 weeks of paid parental leave."},
  {"doc_id": "D13", "claim": null}
]}
```

The prompt tells the model not to answer the question and not to judge which document is right.
It only asks for a short, literal restatement per document, with numbers copied as written.
These sentences are what the user sees in a dispute report, so they must be short and exact.

### 3. `judge` (Jev)

One HTTP call to `POST https://openrouter.ai/api/alpha/decisions`. We send the question plus the
list of `{id, source, date, claim}` and a set of questions built from it:

- for every document with a claim: `rel_D03` — type `noul` (yes/no) —
  "Does document D03 directly answer the question?"
- for every pair of such documents that is **not** linked by `supersedes`:
  `pair_D03_D04` — type `choice` with options `agree` / `disagree` / `unrelated` —
  "Compare the claims of D03 and D04 as answers to the question. Different dates or sources do
  NOT make claims agree or disagree; only their content does."

Response (shortened):

```json
{"answers": {
   "rel_D03": {"type": "noul", "noul": 0.96},
   "rel_D04": {"type": "noul", "noul": 0.93},
   "pair_D03_D04": {"type": "choice", "choice": "disagree",
                    "probabilities": {"agree": 0.05, "disagree": 0.88, "unrelated": 0.07}}},
 "usage": {"cost": 0.00002}}
```

The step writes `relevance = {"D03": 0.96, "D04": 0.93}` and
`pairs = [{"doc_a": "D03", "doc_b": "D04", "relation": "disagree", "p_disagree": 0.88}]`.

What we actually saw (`python main.py jev-test`, 2026-09-29): the reply comes from
`typesafe/jev-1.13-20260917`, provider `TypeSafe`, in about 0.4 seconds. The format is exactly the
one above. `noul` is the probability of "yes". Each `choice` answer has `choice`, `confidence` and
`probabilities` over the three options. On clear cases the probabilities are 0.00 or 1.00, and
relevance is above 0.9 or below 0.05, so the 0.6 thresholds are not sensitive. A call with 4
documents and 6 pairs (10 questions) used 1,377 input and 343 output tokens and cost $0.0000578.
`src/jev.py` checks that every question we asked has an answer; if not, it counts as a failure.

If the call fails for any reason (timeout, HTTP error, unexpected format), the step runs again
with the LLM as judge: a structured-output prompt that returns `relevant: true/false` per document
and a list of pairs that disagree. The result is mapped onto the same two fields with
probabilities 1.0 / 0.0. `judge_used` records which one ran, so traces and the eval show it.

### 4. `reconcile` (Python rules)

This is where "outdated" and "disputed" are told apart. On purpose, this is not a model:

1. `relevant` = documents with `relevance ≥ JEV_RELEVANT_P` (0.6).
2. Build the "replaces" chains from metadata (`D02 supersedes D01`, and so on down a chain).
   Any relevant document that is replaced by another document in the corpus moves to
   `outdated`. The newest document in its chain is forced into `relevant` (the retrieve step
   already fetched it).
3. `disputes` = pairs with `p_disagree ≥ JEV_DISAGREE_P` (0.6) where both documents are relevant,
   neither is outdated, and they are not in the same "replaces" chain.
4. Number check: if two relevant, current documents on the same topic have claims with different
   numbers and no dispute was recorded, add one anyway ("numeric mismatch (backstop)"). This
   catches a judge that is too soft.
5. Route: no relevant document → `abstain`; any dispute → `conflict`; otherwise `answer`.

### 5a. `answer` (LLM)

Structured call with only the relevant, current documents. Output `{answer, citations}`.
Python then checks that every citation is one of the allowed ids (drops unknown ones, asks once
more if none are left, abstains if that still fails). Python also adds the outdated note itself
from the `outdated` list. The model is not trusted to mention it.

### 5b. `conflict_report` (Python)

No model. For each dispute it prints both claims with id, source and date, and the sentence
"Neither document is marked as replacing the other; a newer date alone does not settle it."
`answer` stays `None`.

### 5c. `abstain` (Python)

No model. Says the documents do not cover the question and lists the closest documents with their
scores, so a badly tuned cutoff is easy to spot.

## Three worked examples

### "How many days per week can employees work remotely?" → answered, with outdated note

```
retrieve        hits: D02 (0.71), D01 (0.69), D13 (0.48)   related docs added: none new (same topic)
extract_claims  D01 -> "up to two days per week"   D02 -> "up to three days per week"   D13 -> null
judge (jev)     rel_D01 0.91  rel_D02 0.95        pair: not asked (D02 replaces D01)
reconcile       D01 is replaced by D02  ->  outdated=[D01->D02]   relevant=[D02]   route=answer
answer          "Employees may work remotely up to three days per week [D02]."
                Outdated: D01 (2024-03-01) said "up to two days per week"; replaced by D02 (2025-06-15).
```

### "How many weeks of paid parental leave does Helios Dynamics offer?" → disputed

```
retrieve        hits: D03 (0.74), D04 (0.72), D16 (0.41 -> dropped)   related docs added: none new
extract_claims  D03 -> "16 weeks of fully paid parental leave"   D04 -> "12 weeks of paid parental leave"
judge (jev)     rel_D03 0.96  rel_D04 0.93   pair_D03_D04: disagree 0.88
reconcile       no supersedes link between D03 and D04  ->  disputes=[D03 vs D04]   route=conflict
conflict_report STATUS: DISPUTED
                  - [D03] HR Handbook (2025-01-10): 16 weeks of fully paid parental leave.
                  - [D04] Benefits FAQ (2025-02-20): 12 weeks of paid parental leave.
                Neither document is marked as replacing the other; a newer date alone does not settle it.
```

Note that D04 is newer. The system still refuses to pick it, because nothing in the corpus says
D04 replaces D03.

### "What is the policy on bringing pets to the office?" → abstained

```
retrieve        hits: D07 (0.43), D13 (0.41), D16 (0.39)  -> all below the cutoff 0.45
                (with a lower cutoff: extract_claims returns null for all, judge marks none relevant,
                 reconcile routes to abstain. Same outcome, one LLM call later.)
abstain         STATUS: ABSTAINED. The documents do not cover this. Closest: D07 (0.43), D13 (0.41), D16 (0.39).
```

## Why it "admits it doesn't know"

- Two gates before any answer is written: the score cutoff and the judge's per-document
  relevance. If either one fails, the system abstains.
- Disagreement is decided by a model that can only output a probability over
  `agree / disagree / unrelated`. The report is built from the extracted claims by code.
  There is no step where a model could write "roughly 12 to 16 weeks".
- Newer is not the same as right. Only an explicit `supersedes` link settles a conflict, and even
  then the old value is still shown with its date.
- Every claim in every outcome carries `[doc_id] source (date)`, so each statement can be checked
  against the corpus.

## Tracing and cost

Every step, both LLM calls and the Jev call are sent to LangSmith when `LANGSMITH_TRACING=true`.
With tracing off, nothing changes. A full run of the five demo questions costs about $0.006
(two LLM calls per answered question, one per disputed question, none for a question that is
dropped at retrieval, plus about $0.00002 per Jev call).
