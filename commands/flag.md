---
description: Log a tool-facing gap, limitation, or ambiguous situation to hunt-memory/tool_notes.jsonl — the counterpart to /remember, which only logs target-facing findings. Usage: /flag
---

# /flag

Save a note about the *tool*, not the target — something the agent itself
hit a limit on, an ambiguous call it had to make, or a gap worth fixing
later. `journal.jsonl` and `patterns.jsonl` only capture what was found
on a target; this is the place a tooling gap doesn't just disappear
because nobody happened to mention it afterward.

## What This Does

1. Prompts for the fields below (auto-fills `target`/`engagement_id`/
   `phase`/`session_id` from session context where available)
2. Writes one entry to `hunt-memory/tool_notes.jsonl` via `memory.tool_notes.ToolNotesLog`
3. Does **not** touch `journal.jsonl`, `patterns.jsonl`, or the target
   profile — this is a separate log type on the same plumbing, not a
   replacement for `/remember`

## Usage

```
/flag                         # prompts for all fields
```

## Interactive Flow

```
FLAG — Log a tool-facing gap to hunt-memory

Target/Engagement: target.com (auto-detected)
Phase:             [scope / recon / hunt / validate / report / autopilot / swarm / other]?
Observation:       ___?
Classification:    [known_limitation / newly_discovered]?
Action taken:      ___ (leave blank if nothing was done in the moment)?
Needs follow-up:   [y/n]?

Save to tool_notes.jsonl? [y/n]
```

## Minimum Required Fields

- `target` — engagement or target this was observed on (use the
  engagement id if it isn't target-specific)
- `phase` — one of `scope`, `recon`, `hunt`, `validate`, `report`,
  `autopilot`, `swarm`, `other`
- `observation` — what was actually observed, in enough detail that
  someone with no session context can act on it later
- `classification` — `known_limitation` (already understood, just
  recording another instance) or `newly_discovered` (first time this
  came up)
- `needs_followup` — `true`/`false`

## Optional Fields

- `engagement_id` — set this alongside `target` when the note is
  engagement-level rather than target-specific
- `action_taken` — what, if anything, was done in the moment (a
  workaround, a skip, an escalation) — leave unset if nothing was
  done
- `session_id` — auto-filled from `BBHUNT_SESSION_ID` when set, same as
  every other memory write

## Why This Matters

- `journal.jsonl` answers "what did we find." `tool_notes.jsonl` answers
  "what did the tooling itself get wrong, or not know how to handle."
  Different question, same plumbing.
- `ToolNotesLog.read_needs_followup()` is the queue the next round of
  fixes reads from — a flagged gap from this run is exactly the kind of
  finding that fed the fix spec this command itself came out of.
- Rotated and reported by `/memory-gc` the same as `audit.jsonl` /
  `patterns.jsonl` / `journal.jsonl` — nothing extra to remember to run.
