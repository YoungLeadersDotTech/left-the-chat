# Placeholder

Target for the uncommitted Cowork work.

## Why this file exists

There is existing exploratory work in a Cowork session that was never committed. This branch
gives it somewhere to land so it stops being a single point of failure sitting in one session.

## Before anything from Cowork lands here

Two gates, both because this repo becomes public on the day. They are separate questions and
only one of them is the event's.

### 1. Eligibility - the event's rule

The published rule permits existing templates, reusable components, libraries, prompts and
starter code. What must be built during the event is the project being submitted and its core
functionality, and a pre-existing project cannot be extended and entered as a new one.

A check corpus ported freshly on the day satisfies this, on one condition: **the core
functionality is the agent** - deterministic auditing running offline, where no model can
reach - and the checks are a library it consumes. Framed the other way round, as an existing
validator now running in a browser, it falls under the extension clause instead.

Teams are asked to explain which parts were created during the hackathon. The working test is
whether that can be answered in one sentence without hedging.

### 2. Provenance - not the event's rule, and not resolved by it

The existing falsification engine lives on Toast's GitHub Enterprise. The event has no view on
that either way, so nothing in the eligibility rule settles it.

The approach that satisfies both gates at once: **port from understanding, not from the files.**
Writing the checks fresh is barely slower than translating them, and it removes the derivative
question and the eligibility question together. What travels is what is known. What does not
travel is a file.

## Open decisions

Tracked in `consultancy/builder-plans/consultancy-launch--2026-09-03/` under T-27, with the
idea shortlist and its reasoning in `consultancy/events/ai-tinkerers-idea-shortlist.md`.

- Three approaches run in parallel on the day and the strongest is submitted. Nothing is locked
  in advance, including the cut-line.
- Target user deliberately not aimed yet - let the tracks diverge first.
- Repo goes public on 12 September, not before.
