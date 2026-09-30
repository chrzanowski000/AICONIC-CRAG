---
id: D32
title: Release Process
source: Engineering wiki
date: 2025-02-18
topic: releases
supersedes: null
---
# Release process

This page describes how we ship new versions of the flight-planning software and the cloud
service.

**How often we release.** We release every two weeks, on Tuesday.

**Release branch.** On the Friday before a release, the release manager cuts a release branch.
Only bug fixes go into the branch after that.

**Testing.** The release branch is tested on the staging system over the weekend and on Monday.
Every release needs a green test run before it can go out.

**Release notes.** The release manager writes short release notes for customers and posts them in
the product channel.

**Who is release manager.** The role moves between the senior engineers. The rota is in the team
calendar.

**Rollback.** If something goes wrong after a release, roll back first and investigate later.
The on-call engineer can start a rollback without asking anyone.

Questions about releases go to the release manager.
