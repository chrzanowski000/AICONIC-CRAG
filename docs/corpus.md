# The documents

20 short made-up documents about Helios Dynamics, a small drone maker in Tallinn. They live in
`data/corpus/`, one markdown file each, 150 to 190 words.

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
| `id` | `D01` ... `D20`. Unique. |
| `title`, `source` | shown next to every claim, so the user can tell a handbook from a chat digest |
| `date` | `YYYY-MM-DD`, the day the document was created. Shown as "created YYYY-MM-DD" wherever the document appears in an output: sources, both versions of a dispute, "What differs", the outdated note, and the closest documents of "I don't know". It never settles a conflict on its own. |
| `topic` | docs with the same topic are always fetched together, so both sides of a dispute are seen |
| `supersedes` | id of the document this one replaces, or `null`. The only thing that can settle a conflict. |

`src/load_docs.py` checks that ids are unique, that every `supersedes` target exists, and that
every date parses. It stops with a clear error if not.

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

## Rules the documents follow

- **Disputes.** The two documents of a dispute never mention each other and neither has a
  `supersedes` link. In disputes A and B the newer document is on purpose not the "official" one
  (a FAQ against the handbook, a chat digest against the Finance policy). A system that trusts the
  newest date would get these wrong.
- **Replaced documents.** A document that replaces another says "This replaces the {date}
  version ..." in its text, and has `supersedes` in its metadata. Only the metadata is used by the
  rules; the sentence is there so a human reader sees it too.
- **No side clashes.** Apart from the planned disputes, documents never give different values for
  the same thing. For example, D10 and D18 give the same weight and payload, D07 and D08 give the
  same opening hours, and D18 does not state a flight time at all.
- **No answer on purpose.** No document says anything about pets or animals. That is the
  "I don't know" question.

## Editing the documents

Change a file and run any command. The corpus hash in `qdrant_data/corpus.sha256` no longer
matches, so the index is rebuilt on the next run. Keep the rules above, or the demo questions in
`questions.json` may no longer give the expected results.
