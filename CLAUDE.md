# Puppy Guardian — Claude Code Instructions

## What this project is
A simple Streamlit web app where the user and his wife log their puppy's events (pee, poop, meals, medical notes) from any device. Data lives in a shared Google Sheet. Deployed on Streamlit Community Cloud so both users can access it from anywhere.

This is one module of a planned "Life Dashboard." The FinBoard finance app at `/Users/jethrotsa/Personal Dashboard Project/` is the other module — **do not touch FinBoard code from this project**. The two projects use different stacks on purpose and will remain independent until a future unification phase.

## Start every session by reading these three files

1. **`PLAN.md`** — what we're currently building. Read first.
2. **`BACKLOG.md`** — future ideas deliberately not in the current plan. Read before any structural decision so you don't write code that *unnecessarily* blocks a listed idea. **Do not pre-build flexibility for backlog items** — just avoid painting into a corner.
3. This file (`CLAUDE.md`) — project-specific conventions.

## Tech stack (locked for MVP)

- **Framework:** Streamlit (Python) — handles both frontend and backend in one process
- **Data store:** Google Sheets via `gspread`, single source of truth
- **Hosting:** Streamlit Community Cloud (free), auto-deploys from GitHub
- **Auth:** Streamlit's built-in Google login, restricted to allow-listed emails
- **Language:** Python only. No JavaScript, no separate backend, no Docker — the MVP deliberately avoids all of that.

If a change would require adding a second language, a separate backend service, or moving off Streamlit Cloud, stop and discuss with the user first. Those are not MVP decisions.

## Core conventions

- **Simple code over clever code.** The user is a non-coder learning as we go. Every file should be readable by a beginner. Use obvious names, short functions, and plain patterns. Avoid abstractions, design patterns, or "clever" tricks unless the code genuinely needs them.
- **Rule of Three.** First time you need something, hardcode it. Second time, copy-paste is fine. Only extract an abstraction the third time, when the real pattern is visible. Never design interfaces for imagined futures — this is the single most common way beginner projects get over-engineered.
- **One feature per session.** Keep sessions scoped to one item from `PLAN.md`.
- **Discuss before structural changes.** For anything touching the data schema, hosting, auth, or stack, explain the approach and wait for approval before coding.
- **Read before editing.** Always read the relevant file before modifying it.
- **Never edit FinBoard code.** Different project, different folder, different stack.

## Event schema (single table, Google Sheet tab: `Events`)

```
event_id    string (UUID)  — internal, not shown in UI
timestamp   ISO8601        — displayed as separate date + time in UI
event_type  enum           — poop | pee | meal
notes       string         — optional free text
```

**UI shows:** date, time, event type, notes — nothing else.

This schema is the contract between the app and the Sheet. Don't add columns without updating `PLAN.md`. If a new field is tempting, check BACKLOG.md first — it probably belongs there until a real use case appears (Rule of Three).

## Easy to get wrong

Project-specific traps a competent developer would still hit cold:

- **The Google Sheet is the only source of truth.** Do not treat a local CSV or an in-memory cache as authoritative. CSV exists only as an on-demand export. If the two disagree, the Sheet wins.
- **No two-way sync.** The app writes to the Sheet; the Sheet is read back for display. If the user edits the Sheet directly, those edits show up in the app on refresh. Never build sync logic that tries to reconcile "local first" with "Sheet first" — we intentionally avoided that complexity.
- **The allow-list of emails lives in one place** (Streamlit Cloud secrets or `config.py`). Both the OAuth check and any Sheet-sharing logic must read from the same list. Don't hardcode emails in two places.
- **The service-account key (`secrets.toml`) must never be committed.** It's in `.gitignore` — confirm before any `git add`.
- **Don't copy patterns from FinBoard.** FinBoard's rules ("no framework, no build step, vanilla JS only") do not apply here. Different stack, different constraints.
- **Cloud-first, not Mac-first.** The app runs on Streamlit Community Cloud; the Mac is only for local development. Don't write code that depends on local files, absolute paths, or anything Mac-specific. Everything the app reads must come from the Sheet or Streamlit secrets.

## Standard for this file
This file exists to prevent mistakes specific to this project — the traps a competent developer would still hit without knowing the context. Generic rules are wasted space.
