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
| `event_type` | enum | Yes | `pee` / `poop` / `meal` / `medicine` / `weight` |
| `amount_grams` | number (optional) | Yes — meal and weight | `16` (meal grams) · `5216` (weight in grams → displayed as lbs in app) |
| `location_correct` | `yes` / `no` / blank | Yes — pee/poop only | `yes` |
| `notes` | string (optional) | Yes | `soft stool, slightly green` |

**Design notes:**
- `event_id` is a UUID generated at write time. Not shown anywhere in the UI. Exists so the app can target a specific row for edit/delete even after rows shift.
- `timestamp` is one column in the Sheet but split into date and time columns for display.
- `event_type` has five values (`pee`, `poop`, `meal`, `medicine`, `weight`). `medicine` covers any dosing (albon, future meds). `weight` records body weight as a timestamped measurement. Vomit and other rare events live in `notes` until they prove themselves by the Rule of Three.
- `amount_grams` is filled for `meal` (food grams) and `weight` (body weight in grams). Blank for everything else. The app accepts lbs for weight input and converts to grams on save. **If editing the Sheet directly for weight rows, always enter grams (multiply lbs × 453.6).**
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

**Status as of 2026-04-19:** Phases 1, 2, and 3 are complete. Next session should start on Phase 4.

- Repo is live on GitHub (public): `manhinfuture/puppy-guardian` — no secrets in code, service-account key and `secrets.toml` are gitignored.
- App is deployed on Streamlit Community Cloud and auto-deploys from `main` on push.
- Google service-account key is stored in Streamlit Cloud secrets as `gcp_service_account_json`.
- Wife has tested logging from her phone — works.
- Timezone fix shipped (`TIMEZONE = "America/Los_Angeles"` in `config.py`, used in `app.py` date/time defaults).
- Historical data was rewritten once via a one-time `replace_history.py` script on 2026-04-19 (backup saved locally to `sheet_backup_20260419_011113.csv`). The script is spent — the Sheet is now the source of truth.
- Auth deliberately deferred to Phase 5 (see below).

**Phase 1 — Local logger (run on Mac only)** ✅ done
- Python + Streamlit installed
- `app.py` with a form: event type dropdown (poop / pee / meal), optional notes, submit button
- Date and time default to "now" but are editable (in case you log after the fact)
- `sheets.py` writes the event to a Google Sheet via `gspread`
- "Recent events" table shows the last 20 rows (date, time, event type, notes) from the Sheet
- Verification: fill out the form, hit submit, confirm the row appears in the Google Sheet, confirm the recent-events table updates

**Phase 2 — Cloud deploy + wife access** ✅ done
- Push project to a GitHub repo (public; no secrets in code, all gitignored)
- Connect to Streamlit Community Cloud, deploy to `puppy-guardian.streamlit.app`
- Share the URL with wife, confirm she can log events from her phone
- Verification: wife logs an event from her phone while user's Mac is off; event appears in Sheet and in the app
- **Auth deliberately deferred to Phase 5** — URL is obscure, data is non-sensitive, worst case is a fake "poop" row that's deleted from the Sheet. Rule of Three: add auth only when it's actually needed.

**Phase 3 — Status strip, targeted charts, CSV export** ✅ done

Revised after Phase 3 planning discussion. Goal: every view answers a real question; no decorative charts.

1. **Status strip** (top of page, above the log form) — one line per event type showing *time since last* and *today's count*. Answers "did she already eat / pee / poop?" at a glance. Not a chart, just computed text.
2. **Potty training accuracy %** — `location_correct = yes` rate for pee+poop, this week vs. last week. Small number / tiny bar.
3. **Poop charts (two, side by side):**
   - Time-of-day distribution (x: hour, y: count across window) — spots schedule drift
   - Daily count, last 14 days (x: date, y: count that day) — spots trend changes
4. **Pee chart:** daily count only, last 14 days. Time-of-day for pee is not informative (puppies pee whenever awake), so skipped.
5. **"Download CSV" button** — exports the Sheet as CSV on demand.

Explicitly dropped from earlier plan: generic "events per day" bar chart (redundant with the per-type daily counts and the status strip).

**Added mid-phase (2026-04-19):**
- **Potty accuracy weekly trend line** (last 8 calendar weeks) under the 7-day accuracy metric, to visualize training progression.
- **Weight tracking** — `weight` event_type, form accepts lbs, stored as grams in `amount_grams`. New Weight section shows current weight + full-history line chart. Originally a BACKLOG item ("weight tracking if a smart scale is added") — manual version promoted because the user had real data to log.
- **Recent events table** formats `amount_grams` as "11.50 lbs" (weight) or "16 g" (meal) for readability; Sheet storage unchanged.
- **CSV export** uses UTF-8 BOM (`utf-8-sig`) so Chinese characters render correctly in Numbers/Excel.

- Verification: log 10+ events across 3 days → status strip updates, all 3 charts render, accuracy % computes, CSV downloads and opens in Numbers/Excel.

**Phase 4 — Polish and use it**
- Edit/delete button for individual events (in case of mis-log)
- Filter by date range and category
- **Use it daily for at least 2 weeks before adding anything else.** Let real usage tell us what to build next.

**Added mid-phase (2026-04-19):**
- **Average daytime interval per type** in the status strip. Each pee/poop/meal tile shows a small caption underneath: `avg: Xh Ym · 14d`. Window is the last 14 days. Overnight gaps are excluded by only pairing consecutive same-type events at/after 06:00 on the same calendar day (any gap crossing midnight is dropped). Meal avg is included as a sanity check even though it mostly reflects the feeding schedule. Intended to answer "is Ichi overdue?" at a glance by comparing time-since-last against the average.

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
