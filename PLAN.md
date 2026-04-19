# Puppy Guardian — MVP Plan

## Context

Puppy Guardian is a simple web app that lets the user and his wife log their puppy's events (pee, poop, meals, medical notes) from any device, store the data in a Google Sheet, and see basic charts and recent history.

This is the **MVP** — intentionally small. AI detection from a camera feed, drag-drop widget dashboards, Bristol stool scoring, and many other features are valuable but deferred. See [BACKLOG.md](./BACKLOG.md) for the full list of future ideas.

### Why MVP-first
Before building automation, we prove the product is useful by using it manually. A week of manual logging teaches us:
- What data we actually want to capture (vs. what we imagine wanting)
- Which events are annoying to log (those become automation candidates)
- Which charts are actually useful (vs. decorative)

Automation built on those real insights is dramatically more valuable than automation built on guesses.

## What the MVP does

1. User or wife opens a URL on any device (phone, laptop, tablet)
2. They click a button to log an event: pee / poop / meal / medical / general note
3. The event is saved to a shared Google Sheet with a timestamp
4. The app shows recent events and a few simple charts (events per day, time-of-day distribution)
5. CSV export is available on demand (button click → download)

That's it. No camera, no AI, no drag-drop widgets.

## Tech stack (locked)

- **Framework:** [Streamlit](https://streamlit.io/) (Python)
  - One language, one process — simplest web app stack that fits the job
  - Handles both frontend (buttons, forms, charts) and backend (writes to Sheet) in one file
- **Data store:** Google Sheet (single source of truth)
  - Accessed via the `gspread` Python library
  - Both users see the same data from any device
  - CSV export is generated on-demand from the Sheet
- **Hosting:** [Streamlit Community Cloud](https://streamlit.io/cloud) (free tier)
  - Push code to GitHub → Streamlit Cloud auto-deploys → public URL
  - No servers to manage
- **Auth:** Streamlit's built-in Google login, restricted to the user's and wife's Google accounts
  - Ensures only they can access the app and the Sheet

## Data model (single table)

One Google Sheet with one tab: `Events`. Columns:

| Column | Type | Shown in UI? | Example |
|---|---|---|---|
| `event_id` | string (UUID) | No — internal | `a3f1…` |
| `timestamp` | ISO8601 | Yes — displayed as separate date + time | `2026-04-18T14:30:00` |
| `event_type` | enum | Yes | `pee` / `poop` / `meal` / `medicine` |
| `amount_grams` | number (optional) | Yes — meal only | `16` |
| `location_correct` | `yes` / `no` / blank | Yes — pee/poop only | `yes` |
| `notes` | string (optional) | Yes | `soft stool, slightly green` |

**Design notes:**
- `event_id` is a UUID generated at write time. Not shown anywhere in the UI. Exists so the app can target a specific row for edit/delete even after rows shift.
- `timestamp` is one column in the Sheet but split into date and time columns for display.
- `event_type` has four values (`pee`, `poop`, `meal`, `medicine`). `medicine` covers any dosing (albon, future meds). Weight, vomit, and other rare events live in `notes` until they prove themselves by the Rule of Three.
- `amount_grams` is only filled for `meal` events. Blank for everything else.
- `location_correct` tracks potty training accuracy for `pee`/`poop` only. `yes` = on pee pad, `no` = elsewhere, blank = not noted. Added because 3 weeks of historical data showed this is tracked on every single poop.
- No `size`, `consistency`, `dose_ml`, or old-vs-new-food columns. Those go in `notes`. Promote to columns only if they persist and prove needed.

## Project layout

```
Puppy Guardian Project/
├── PLAN.md                  ← this file (current work only)
├── BACKLOG.md               ← future ideas parking lot
├── CLAUDE.md                ← project rules for AI sessions
├── app.py                   ← the entire Streamlit app (start here)
├── sheets.py                ← Google Sheets read/write helpers
├── config.py                ← Sheet ID, column names, category list
├── requirements.txt         ← Python dependencies
├── .streamlit/
│   └── secrets.toml         ← Google service-account key (gitignored)
└── .gitignore
```

Small project, flat structure. If the app grows, we'll split further — but not before.

## Build phases

**Phase 1 — Local logger (run on Mac only)**
- Python + Streamlit installed
- `app.py` with a form: event type dropdown (poop / pee / meal), optional notes, submit button
- Date and time default to "now" but are editable (in case you log after the fact)
- `sheets.py` writes the event to a Google Sheet via `gspread`
- "Recent events" table shows the last 20 rows (date, time, event type, notes) from the Sheet
- Verification: fill out the form, hit submit, confirm the row appears in the Google Sheet, confirm the recent-events table updates

**Phase 2 — Cloud deploy + wife access**
- Push project to a GitHub repo (public; no secrets in code, all gitignored)
- Connect to Streamlit Community Cloud, deploy to `puppy-guardian.streamlit.app`
- Share the URL with wife, confirm she can log events from her phone
- Verification: wife logs an event from her phone while user's Mac is off; event appears in Sheet and in the app
- **Auth deliberately deferred to Phase 5** — URL is obscure, data is non-sensitive, worst case is a fake "poop" row that's deleted from the Sheet. Rule of Three: add auth only when it's actually needed.

**Phase 3 — Basic charts + CSV export**
- Chart 1: events per day (bar chart, last 14 days)
- Chart 2: time-of-day distribution for poop events (helps spot routine changes)
- "Download CSV" button that exports the Sheet as CSV
- Verification: charts render and update after new events; CSV downloads and opens correctly in Numbers/Excel

**Phase 4 — Polish and use it**
- Edit/delete button for individual events (in case of mis-log)
- Filter by date range and category
- **Use it daily for at least 2 weeks before adding anything else.** Let real usage tell us what to build next.

**Phase 5 — Revisit auth (decide after Phase 4)**
- After 2+ weeks of real daily use, decide whether to add Google OAuth login restricted to an email allow-list.
- Decide based on actual evidence: has the URL leaked? Has the Sheet been spammed? Does sharing with family require finer permissions?
- If no → stay unauthenticated, done.
- If yes → wire up `st.login()` with Google, allow-list emails in `config.py` or secrets.

## What "done" looks like

- Both user and wife can log events from their phones
- The Google Sheet fills up with real data
- Charts show something useful
- The app has been used for 2+ weeks without either person wanting to stop using it
- A list of real, concrete pain points and feature requests has emerged from that usage — those feed the next round of planning

## Verification plan

- **Phase 1:** Submit a form entry → row appears in Sheet within 2 seconds
- **Phase 2:** Wife opens URL on phone from outside the home WiFi → can log an event → it appears in the Sheet
- **Phase 3:** Log 10 events across 3 days → charts render correctly → CSV downloads and opens
- **Phase 4:** Daily usage for 14 days with both users → collect feedback
- **Phase 5:** Review whether auth is needed; if yes, wife can still log in with one tap on her phone after setup

## Open questions

- Whether to use a single Sheet with one tab, or anticipate multiple tabs (one per puppy) if a second dog arrives
  - **Default assumption:** single tab for now. If a second puppy joins, we add a `puppy_name` column rather than a second tab.

## Out of scope (tracked in BACKLOG.md)

Anything not listed in the build phases above. Resist scope creep — the MVP's job is to prove the product is useful before we invest in automation.
