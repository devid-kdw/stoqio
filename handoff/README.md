# Handoff Protocol

`handoff/` is the shared coordination area for all project agents.

## Purpose

Use this folder to leave a durable trace of work completed in each implementation phase.
Agents do not communicate through chat summaries alone. They must record what they did, what they changed, what they verified, and what remains open.

## Folder Layout

```text
handoff/
  README.md
  decisions/
    README.md
    decision-log.md
  templates/
    agent-handoff-template.md
    orchestrator-handoff-template.md
  phase-01-project-setup/
    orchestrator.md
    backend.md
    frontend.md
    testing.md
```

New phase folders must follow this pattern:
- `phase-01-project-setup`
- `phase-02-database-models`
- `phase-03-authentication`

Use lowercase kebab-case after the numeric prefix.

## Responsibilities

### Orchestrator

Before delegation:
- create the phase folder if it does not exist
- create or update `orchestrator.md`
- state scope, source docs, constraints, and success criteria
- list which agent is expected to act next

After agent responses are reviewed:
- append a validation note to `orchestrator.md`
- record accepted work, rejected work, missing items, and next action

### Backend / Frontend / Testing Agents

Each agent writes only to its own file:
- `backend.md`
- `frontend.md`
- `testing.md`

Rules:
- append-only; do not delete previous entries
- include timestamp in local project time if available
- keep entries factual and short
- mention blockers immediately, not at the end of a long entry
- if you make an assumption not backed by docs, log it explicitly
- if you discover a spec gap, add it to `handoff/decisions/decision-log.md` and reference it in your entry

## Required Entry Shape

Every agent entry must contain these sections:
- `Status`
- `Scope`
- `Docs Read`
- `Files Changed`
- `Commands Run`
- `Tests`
- `Open Issues / Risks`
- `Next Recommended Step`

If a section is not applicable, write `None`.

## Decision Logging

Use `handoff/decisions/decision-log.md` for:
- product clarifications from the user that are not yet in `stoqio_docs`
- implementation choices with cross-agent impact
- temporary assumptions that need later confirmation

Decision log entries should include:
- date
- phase
- source of decision
- decision text
- impact
- whether the main docs need updating

## Non-Negotiable Rules

- Do not overwrite another agent's file.
- Do not silently change scope.
- Do not mark work as done without listing the files changed and tests run.
- Do not treat `handoff/` as optional. Every delegated task must leave a trace here.
