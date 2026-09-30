# The documents

40 short made-up documents about Helios Dynamics, a small drone maker in Tallinn. They live in
`data/corpus/`, one markdown file each, 137 to 167 words.

## Format

```markdown
---
id: D02
title: Remote Work Policy (v2)
source: HR Handbook
date: 2025-06-15
topic: remote-work
supersedes: D01
---
# Remote Work Policy (v2)

This replaces the 2024-03-01 version of the Remote Work Policy.
...
```

| field | meaning |
|---|---|
| `id` | `D01` ... `D40`. Unique. |
| `title`, `source` | shown next to every claim, so the user can tell a handbook from a chat digest |
| `date` | `YYYY-MM-DD`, the day the document was created. Shown as "created YYYY-MM-DD" wherever the document appears in an output: sources, both versions of a dispute, "What differs", the outdated note, and the closest documents of "I don't know". It never settles a conflict on its own. |
| `topic` | docs with the same topic are always fetched together, so both sides of a dispute are seen |
| `supersedes` | id of the document this one replaces, or `null`. The only thing that can settle a conflict. |

`src/load_docs.py` checks that ids are unique, that every date parses, that every `supersedes`
target exists, and that a document and the one it replaces share a topic (retrieval brings in
related documents by topic, so a link across topics could miss one end). It stops with a clear
error if not.

## The list

| id | title | source | date | topic | supersedes | key fact | role |
|---|---|---|---|---|---|---|---|
| D01 | Remote Work Policy (v1) | HR Handbook | 2024-03-01 | remote-work | – | up to 2 remote days a week | old |
| D02 | Remote Work Policy (v2) | HR Handbook | 2025-06-15 | remote-work | D01 | up to 3 remote days a week | replaces D01 |
| D03 | Parental Leave Policy | HR Handbook | 2025-01-10 | parental-leave | – | 16 weeks paid | dispute A |
| D04 | Benefits FAQ | People Ops wiki | 2025-02-20 | parental-leave | – | 12 weeks paid | dispute A |
| D05 | Travel & Expense Policy | Finance | 2025-04-01 | travel-expenses | – | meals $60 a day | dispute B |
| D06 | Travel Team Update | #travel Slack digest | 2025-05-12 | travel-expenses | – | meals $75 a day | dispute B |
| D07 | HQ Office Information | Facilities | 2024-09-01 | offices | – | HQ at 12 Harbor Street | old |
| D08 | HQ Relocation Notice | Facilities | 2025-08-01 | offices | D07 | HQ at 400 Meridian Avenue | replaces D07 |
| D09 | Kestrel X2 Datasheet v1 | Product | 2024-11-05 | kestrel-x2 | – | flight time 38 min | old |
| D10 | Kestrel X2 Datasheet v2 | Product | 2025-07-20 | kestrel-x2 | D09 | flight time 45 min | replaces D09 |
| D11 | Password Policy | IT Security | 2025-03-15 | security | – | change every 90 days | dispute C (spare) |
| D12 | IT Announcement: password rotation | #it-announcements | 2025-03-30 | security | – | no forced changes | dispute C (spare) |
| D13 | Onboarding Checklist | People Ops | 2025-02-01 | onboarding | – | laptop day 1, buddy week 1 | filler |
| D14 | Code Review Guidelines | Engineering wiki | 2025-05-05 | engineering | – | 2 approvals to merge | clean answer |
| D15 | Incident Response Process | Engineering wiki | 2025-01-20 | engineering | – | Sev1 ack within 15 min | filler |
| D16 | Holiday Calendar 2025 | HR Handbook | 2025-01-02 | holidays | – | 11 public holidays | filler |
| D17 | Company Overview | Comms | 2024-06-10 | company | – | founded 2019 in Tallinn | filler |
| D18 | Kestrel X2 Product Overview | Product | 2025-07-20 | kestrel-x2 | – | 1.2 kg, 300 g payload | filler |
| D19 | Customer Support SLA | Support | 2025-03-01 | support | – | first reply within 4 business hours | filler |
| D20 | On-call Rotation | Engineering wiki | 2025-04-10 | engineering | – | weekly rotation, one comp day | filler |
| D21 | IT Equipment Policy | IT | 2025-02-10 | equipment | – | laptops replaced every three years | agree E |
| D22 | Finance FAQ: Hardware | Finance wiki | 2025-04-22 | equipment | – | laptops on a 3-year cycle | agree E |
| D23 | Learning and Development Policy | HR Handbook | 2025-01-15 | learning-budget | – | €1,000 a year | dispute D (three docs) |
| D24 | Manager Guide: Team Budgets | People Ops wiki | 2025-03-05 | learning-budget | – | €1,200 a year | dispute D (three docs) |
| D25 | Learning Channel Digest | #learning Slack digest | 2025-06-02 | learning-budget | – | €1,500 a year | dispute D (three docs) |
| D26 | Sick Leave Policy | HR Handbook | 2025-01-20 | sick-leave | – | doctor's note after more than three days | one answer |
| D27 | Annual Leave Policy (2023) | HR Handbook | 2023-01-01 | annual-leave | – | 25 days | old (chain) |
| D28 | Annual Leave Policy (2024) | HR Handbook | 2024-01-01 | annual-leave | D27 | 28 days | replaces D27, replaced by D29 |
| D29 | Annual Leave Policy (2025) | HR Handbook | 2025-01-01 | annual-leave | D28 | 30 days | newest of the chain |
| D30 | Kestrel X2 Warranty Terms | Support | 2025-07-25 | kestrel-x2 | – | warranty 12 months | agree F (with D18, D31) |
| D31 | Reseller FAQ | Sales | 2025-08-12 | kestrel-x2 | – | one-year warranty | agree F (with D18, D30) |
| D32 | Release Process | Engineering wiki | 2025-02-18 | releases | – | release every two weeks, on Tuesday | dispute G |
| D33 | Engineering Channel Digest | #engineering Slack digest | 2025-06-20 | releases | – | ship once a week, every Thursday | dispute G |
| D34 | Data Retention Policy | Legal | 2025-02-01 | data-retention | – | tickets kept 24 months | dispute H |
| D35 | Privacy FAQ | Customer Support wiki | 2025-05-15 | data-retention | – | tickets kept 36 months | dispute H |
| D36 | Commuting Benefit | People Ops | 2025-03-20 | commuting | – | public transport pass paid 100% | one answer |
| D37 | Summer Party 2025 | Comms | 2025-05-02 | company-events | – | 20 June 2025, Pirita beach | one answer |
| D38 | Expense Claims Policy | Finance | 2025-03-10 | expense-claims | – | claim within 30 days | agree I |
| D39 | Expenses App Help | IT help centre | 2025-05-30 | expense-claims | – | app accepts claims up to 30 days | agree I |
| D40 | Phishing Awareness Training | IT Security | 2025-04-15 | security-training | – | yearly 30-minute course | filler |

## The cases

Every case the system must handle is in the corpus at least twice, and each has questions in
`questions.json`:

| case | documents | questions | expected outcome |
|---|---|---|---|
| documents agree | D11 + D12 (multi-factor sign-in); D10 + D18 (weight, payload); D21 + D22 (laptops); D38 + D39 (expense deadline); D18 + D30 + D31 (warranty, in different words: "one-year", "12 months") | Q9, Q10, Q12, Q19, Q23, Q28 | answered, citing the agreeing documents |
| documents disagree | D03 vs D04; D05 vs D06; D11 vs D12 (in words); D23 vs D24 vs D25 (three documents); D32 vs D33 (in words); D34 vs D35 | Q3, Q4, Q8, Q20, Q24, Q25 | disputed: every version with its date, what differs, no answer |
| one document answers | D14, D04, D11, D26, D36, D37 | Q1, Q16, Q17, Q21, Q26, Q27 | answered from that document |
| no document answers | nothing about pets, a gym, or a number of paid sick days | Q5, Q29, Q30 | abstained ("I don't know") |
| a document replaced by a newer one | D01 → D02; D07 → D08; D09 → D10; D27 → D28 → D29 (a chain of three) | Q2, Q6, Q7, Q18, Q22 | answered from the newest, with an "outdated" note for each older one |

The same two documents can agree on one question and disagree on another: D11 and D12 agree that
multi-factor sign-in is required (Q12) and disagree on password changes (Q8). D03 and D04 agree
on adoption, splitting and pay (Q11, Q13, Q14) and disagree on the number of weeks (Q3).

## Rules the documents follow

- **Disputes.** The documents of a dispute never mention each other and none has a
  `supersedes` link. Dispute D has three sides. In disputes A and B the newer document is on purpose not the "official" one
  (a FAQ against the handbook, a chat digest against the Finance policy). A system that trusts the
  newest date would get these wrong.
- **Replaced documents.** A document that replaces another says "This replaces the {date}
  version ..." in its text, and has `supersedes` in its metadata. D27 → D28 → D29 is a chain:
  a question about it is answered from D29, and both D27 and D28 get an "outdated" note. Only the metadata is used by the
  rules; the sentence is there so a human reader sees it too.
- **No side clashes.** Apart from the planned disputes, documents never give different values for
  the same thing. For example, D10 and D18 give the same weight and payload, D07 and D08 give the
  same opening hours, D18 does not state a flight time at all, and D30, D31 and D18 give the same
  warranty in different words.
- **No answer on purpose.** No document says anything about pets or animals, a gym, or how many
  paid sick days there are. Those are the "I don't know" questions (Q5, Q29, Q30). Q29 and Q30
  are close to real topics (the commuting benefit, the sick leave policy), so the search finds
  documents, but none answers.

## Editing the documents

Change a file, then run `index`, `search`, `ask`, `demo` or `eval.py`. The corpus hash in
`qdrant_data/corpus.sha256` no longer matches, so the index is rebuilt first. Keep the rules
above, or the questions in `questions.json` may no longer give the expected results. Run
`python eval.py` twice after any change to a document.
