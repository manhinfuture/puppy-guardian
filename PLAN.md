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

**Status as of 2026-04-20:** Phases 1–4 complete. Phase 4 soak ran long enough to surface real follow-on needs (see Phases 5–7 below). Phases 5 and 6 are locked and ready to build; Phase 7 (Medical) is intentionally deferred pending a fresh design discussion.

- Repo is live on GitHub (public): `manhinfuture/puppy-guardian` — no secrets in code, service-account key and `secrets.toml` are gitignored.
- App is deployed on Streamlit Community Cloud and auto-deploys from `main` on push.
- Google service-account key is stored in Streamlit Cloud secrets as `gcp_service_account_json`.
- Wife has tested logging from her phone — works.
- Timezone fix shipped (`TIMEZONE = "America/Los_Angeles"` in `config.py`, used in `app.py` date/time defaults).
- Historical data was rewritten once via a one-time `replace_history.py` script on 2026-04-19 (backup saved locally to `sheet_backup_20260419_011113.csv`). The script is spent — the Sheet is now the source of truth.
- Auth deliberately deferred — tracked in BACKLOG.md.

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
- **Auth deliberately deferred** — URL is obscure, data is non-sensitive, worst case is a fake "poop" row that's deleted from the Sheet. Rule of Three: add auth only when it's actually needed. Tracked in BACKLOG.md.

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
- **Profile card at top of page.** Replaces the `Tracking Ichi` caption. Circle photo on the left, name / breed / sex / DOB (with computed age in years+months) / current weight on the right. Profile metadata lives in `config.py` under `PUPPY` (Rule of Three — promote to a Sheet tab only if editing-from-phone becomes a real need). Photo committed at `assets/ichi.jpg` because Streamlit Cloud's filesystem is ephemeral — an in-app uploader would lose the file on redeploy. Current weight reads the latest `weight` event from the Sheet so it stays live.
- **Average daytime interval per type** in the status strip. Each pee/poop/meal tile shows a small caption underneath: `avg: Xh Ym · 14d`. Window is the last 14 days. Overnight gaps are excluded by only pairing consecutive same-type events at/after 06:00 on the same calendar day (any gap crossing midnight is dropped). Meal avg is included as a sanity check even though it mostly reflects the feeding schedule. Intended to answer "is Ichi overdue?" at a glance by comparing time-since-last against the average.

---

### Shared structural change for Phases 5 and 6

Both new phases live as separate pages under Streamlit's multipage layout:

```
app.py                  ← stays as the home page (status strip, log, charts)
pages/
  1_Observations.py     ← Phase 5
  2_Training.py         ← Phase 6
```

Streamlit auto-discovers files in `pages/` and renders a sidebar nav. The home page is unchanged — no new buttons or event types added to the existing log form.

**Phase 5 — Observations** ✅ done

Free-text "note to self" log for things to revisit later (e.g., "Ichi is jumpy and biting everything — look into this"). Subjective by design — kept structurally separate from factual event logging at both the data layer and the UI layer.

- **New Sheet tab `Observations`** (sibling to `Events`). Columns: `observation_id` (UUID), `date` (no time), `notes`, `resolved` (`yes` / blank).
- **No changes to `Events`.** No new event_type. No new columns.
- **New page `pages/1_Observations.py`:**
  - Add form at the top (date defaulting to today, notes text area).
  - **Open** section (default expanded): each row shows date, notes, a resolved checkbox, Edit, Delete.
  - **Resolved** section (collapsed by default): same row shape.
  - Edit opens an inline form with Save / Cancel. Delete requires a confirmation step.
- **`sheets.py`** gains: `read_observations()`, `add_observation()`, `update_observation()`, `delete_observation()`.
- **`config.py`** gains: `OBSERVATIONS_TAB` and column constants. No changes to event-type lists.
- **One-time Sheet migration:** create the `Observations` tab manually (or via auto-create on first read).
- Verification: add → row in Sheet, appears under Open. Tick resolved → moves to Resolved. Edit → persists. Delete → row removed. Home page log form unchanged.

**Phase 6 — Training** ⏳ planned

A structured curriculum checklist with per-item state (status, session count, last practiced, notes). Answers "what should I train next?" without trying to be smart about it.

- **New Sheet tab `Trainings`.** Columns: `training_id` (UUID), `name`, `category`, `status` (`not_started` / `practicing` / `reliable`), `session_count` (int), `last_practiced` (ISO date, blank initially), `notes` (single editable field, not a log).
- **`Events` tab unchanged.** No `training` event_type — `session_count` + `last_practiced` carry enough state for MVP. Promote to per-session events only if the history of individual sessions becomes something we wish we had.
- **Starter curriculum** (10 items, 3 categories — seeded once via `seed_trainings.py`, then the script is spent):

  | # | Name | Category |
  |---|---|---|
  | 1 | Name recognition (look at me) | Foundation |
  | 2 | Sit | Obedience |
  | 3 | Down | Obedience |
  | 4 | Stay | Obedience |
  | 5 | Come (recall) | Obedience |
  | 6 | Leave it | Manners |
  | 7 | Drop it | Manners |
  | 8 | Loose-leash walking | Manners |
  | 9 | Crate / place / settle | Manners |
  | 10 | Bite inhibition (no nipping) | Manners |

- **New page `pages/2_Training.py`:**
  - Items grouped by category, sorted within each category by status (`practicing` → `not_started` → `reliable`). No recommendation logic beyond this sort.
  - **Stale flag:** if an item is `practicing` and `last_practiced` was 5+ days ago, show a small "haven't practiced in N days" hint.
  - Each row: name, status dropdown, session count, last-practiced date, notes preview, **"I trained this today"** button (increments count + sets last_practiced to today), Edit, Delete (with confirmation).
  - Add training item expander at the bottom: name + category (free text or pick from existing) + optional notes. New item starts at `not_started`.
- **`sheets.py`** gains: `read_trainings()`, `add_training()`, `update_training()`, `delete_training()`.
- **`config.py`** gains: `STARTER_CURRICULUM` (list of dicts) and `TRAINING_STATUSES`.
- **`seed_trainings.py`** is a one-shot script analogous to `replace_history.py` — creates the `Trainings` tab if missing, writes headers, inserts the starter rows.
- Verification: seed runs once → 10 rows in Sheet. Page renders grouped by category. Status change reorders. "I trained this today" increments + dates. Stale hint appears at 5+ days idle. Add / edit / delete works. Home page unchanged.

**Phase 7 — Medical** ⛔ DEFERRED — DO NOT START WITHOUT RE-DISCUSSION

> **STOP.** This phase is intentionally deferred. The user explicitly decided that the medical record feature is too complex to lock in alongside Observations and Training, and needs more thinking time.
>
> **Required before any Phase 7 work begins:**
> 1. The AI agent **must re-open a deep design discussion with the user** — covering layout, schema, storage, what counts as a "medical record" vs. an observation, file attachments, vet-visit fields, body-condition tracking, etc.
> 2. The AI agent **must obtain explicit double confirmation** from the user before writing any code, creating any new Sheet tabs, modifying any existing files for Phase 7, or even updating this plan to lock in a Phase 7 design.
> 3. **No assumptions, no shortcuts.** Even if the user says "go ahead with medical," surface what you intend to do, get agreement on each major decision, then ask once more for confirmation before execution.

Starting points from the initial discussion (context only — **not** locked decisions, must be re-opened):

- Tentative direction: text-only medical records at MVP, no in-app PDF/photo upload; user maintains a personal Drive folder on the side; revisit only after 3+ vet visits prove the friction.
- Possible architecture: keep `medicine` and `weight` on `Events` (don't break the existing weight chart and profile card); introduce a new `VetVisits` tab for consultations (different shape than events); have a Medical page that aggregates from both tabs into one chronological timeline.
- Possible vet-visit fields: date, vet name, reason, summary, follow-up.
- Open: where do "body condition" notes live (e.g., ear redness, limping)? Options were (a) existing Observations tab, (b) Observations tab with a new `category` column, (c) a separate `HealthNotes` tab. No decision.
- Possible Medical page contents: header summary (latest visit, current weight, recent medicines), combined timeline, filter by type, scoped CSV export.

**Again: none of the above is locked. Re-discuss everything when this phase is unblocked.**

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

## Open questions

- Whether to use a single Sheet with one tab, or anticipate multiple tabs (one per puppy) if a second dog arrives
  - **Default assumption:** single tab for now. If a second puppy joins, we add a `puppy_name` column rather than a second tab.

## Out of scope (tracked in BACKLOG.md)

Anything not listed in the build phases above. Resist scope creep — the MVP's job is to prove the product is useful before we invest in automation.
