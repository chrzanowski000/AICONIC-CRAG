---
id: D15
title: Incident Response Process
source: Engineering wiki
date: 2025-01-20
topic: engineering
supersedes: null
---
# Incident response process

An incident is any problem that stops customers from using our products or puts their data at
risk.

**Severity levels.**
- Sev1: a product is down for many customers, or data may be exposed.
- Sev2: a product is slow or partly broken for many customers.
- Sev3: a small problem with a workaround.

**Response times.** The on-call engineer must acknowledge a Sev1 alert within 15 minutes and a
Sev2 alert within 30 minutes. Sev3 issues are handled in working hours.

**Roles.** Every Sev1 has an incident lead, who makes decisions, and a communications lead, who
updates the status page and the support team.

**During the incident.** Work in the incident channel so everything is written down. Fix the
customer impact first; find the root cause later.

**After the incident.** Write a blameless review for every Sev1 and Sev2 and share what we learned.
