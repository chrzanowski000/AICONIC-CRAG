---
id: D14
title: Code Review Guidelines
source: Engineering wiki
date: 2025-05-05
topic: engineering
supersedes: null
---
# Code review guidelines

Code review keeps our code safe to change. These rules apply to every repository.

**Approvals.** Every pull request needs 2 approvals before it can be merged. At least one of the
approvers must be from the team that owns the code.

**Checks.** All automated checks must pass before merging. Do not merge around a failing check.

**Size.** Keep pull requests small and focused on one change. Large changes are easier to review
when split into several pull requests.

**Description.** Say what the change does, why it is needed and how you tested it. Link the ticket.

**Reviewing.** Reviewers should reply within one working day. Be kind and specific. Ask questions
instead of giving orders.

**Author's job.** Answer every comment. Resolve a thread only when the reviewer is happy.

**Merging.** The author merges once the rules above are met. Use squash merge so the history stays
clean.
