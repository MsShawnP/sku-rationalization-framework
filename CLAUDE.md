# SKU Rationalization Framework — Project Context for Claude

## What this project is

A multi-dimensional SKU rationalization framework for specialty food brands at
$10M–$30M revenue. Scores every SKU across five dimensions — velocity,
contribution margin, shelf-space cost, production complexity, and cannibalization
risk — to produce a four-quadrant classification: double down, maintain,
fix or kill, or kill. V1 deliverables: polished demo/visualization tool
(Cinderhaven 90-SKU data), SQL diagnostic queries, and scoring methodology doc.
Excel financial model and case study HTML+PDF are deferred.

**Business question this project answers:** Which SKUs should this brand kill,
fix, maintain, or double down on — and what does each decision cost or save
per year?

## Tier

Heavy — full 11-step workflow. This is a maintained portfolio piece with a
consulting foot-in-the-door offer ($15K–$25K SKU Portfolio Audit engagement).

## Stack and tools

- Stack TBD — determined during /clarify
- Project brief: portfolio_project_brief_sku_rationalization.md

## Project files

- CLAUDE.md (this file) — permanent rules and facts
- DECISIONS.md — durable choices and reasoning
- HANDOFF.md — current session state
- PLAN.md — current work arc
- FAILURES.md — things tried that didn't work

Read PLAN.md and HANDOFF.md at session start. DECISIONS.md and
FAILURES.md as relevant.

## Voice and standards

- Economist style: sober, declarative, data-forward
- No marketing voice ("leverage," "synergy," "best-in-class," "unlock")
- No hedging that softens a real finding
- Charts must be readable by non-data-scientist audiences
- Plain English that tells the truth as the data presents it

## Rules

### Honesty and judgment

- Say "I don't know" or "I can't verify this" instead of guessing.
  This applies to industry context, technical claims, what code did,
  and anything else.
- Tell me what I need to hear, not what I want to hear. If a decision
  looks wrong, say so. If code I wrote has problems, say so.
- If a rule in this file is too vague to verify whether you're
  following it, flag it for revision rather than guessing at compliance.

### Building and proposing

- No speculative abstractions. If something isn't needed right now,
  don't build it.
- When proposing a tool, library, or approach, present at least two
  alternatives with tradeoffs, even if one is clearly preferred.
- Tie proposals back to the business question this project is
  answering.

### How to work the project

- Work in vertical slices, not horizontal phases.
- When a feature is working, suggest a simple test to verify it stays
  working.
- Do not start tasks outside the current PLAN.md arc without flagging
  it to the user first.
- Do not refactor unrelated code unprompted.
- Do not rename things unless asked.

### Git branching

- Before risky or experimental changes, suggest creating a branch.
- What counts as "risky": changing how the project is structured,
  trying a new library, rewriting a working feature.

### Scope creep detection

- Periodically check whether the current work matches PLAN.md.
- Flag drift within ~15 minutes of it starting.

## Working with PLAN.md

PLAN.md defines the current arc of work. Read it at session start.

- Mark tasks complete as they're finished, in the same commit as the work
- If a task is wrong-sized or no longer relevant, flag it
- "Out of scope" items are decisions — don't pull them in without approval

## Session reminders

### Reminding the user to /log

Prompt when a meaningful change lands or a natural pause point is reached.
One suggestion per trigger. Don't nag.

### Reminding the user to /wrap

Prompt when context crosses 65%, user signals stopping, or 90+ minutes
have passed. Don't nag.

### Session start protocol

1. Read CLAUDE.md, PLAN.md, and HANDOFF.md
2. If HANDOFF.md's most recent entry is > 24h old AND there are uncommitted
   changes, flag this
3. Briefly state the starting point from HANDOFF.md
4. Confirm the current PLAN.md arc is still active
5. Check improvement history in PLAN.md for overdue audits

## Defaults

- Default to flagging gaps rather than filling with plausible-sounding content
- Default to short responses unless the task is substantive
- Default to answering, not offering to answer
