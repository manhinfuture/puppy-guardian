# Meals Analytics Page — Design

**Date:** 2026-04-27
**Status:** Approved (pending implementation plan)
**Phase:** New phase, slots after Phase 6 (Training).

## Goal

Give the user a quick way to see meal-feeding **consistency** and **growth trend** for Ichi, using the `amount_grams` data already captured on `meal` events. No vet-recommended target exists yet, so no target line — that stays in BACKLOG (see `Daily meal grams vs. target`).

User priorities (in order):

- **B — Day-to-day consistency:** spot under/over-feeding days.
- **C — Growth trend:** confirm the amount is scaling up as Ichi grows.

Explicitly **not** the goal: hitting a vet-prescribed daily target (A), or "did I already feed her today" — the existing home-page status strip already answers that.

## Where it lives

New page: `pages/3_Meals.py`. Streamlit auto-discovers it and adds a sidebar entry after `1_Observations.py` and `2_Training.py`. The home page (`app.py`) is **not** modified.

## Page layout (top to bottom)

### 1. Two metric cards

Two `st.metric` widgets side by side (mirroring the 7-day potty-accuracy metric style on the home page).

| Metric | Definition | Delta |
|---|---|---|
| 7-day avg/day | sum of grams in last 7 days ÷ 7 | "+X g vs prior 7 days" (days 8–14 ago) |
| 7-day avg meal size | sum of grams in last 7 days ÷ count of qualifying meal events in last 7 days | vs prior 7 days |

Together they answer "is the recent shift coming from bigger meals, more meals, or both?" Meals/day is implicit — the user can derive it by eye from the per-meal scatter below.

### 2. Daily total grams — last 30 days (bar chart)

- X axis: date, last 30 calendar days, including zero-meal days as empty bars (using `.reindex(window_dates, fill_value=0)`, same pattern as the existing poop daily-count chart at `app.py:431`)
- Y axis: grams (sum of qualifying meal events that day)
- **7-day rolling-average line overlaid** on the bars (Altair `mark_line` layered on `mark_bar`)
- Rolling average uses `min_periods=1` so the line starts at day 1 (not day 7)
- Height: ~300px

This single visual answers both priorities: bars expose day-to-day variance (B), the line exposes the trend curve (C).

### 3. Per-meal scatter — last 14 days

- X axis: date, last 14 days (categorical, same axis style as the home-page poop time-of-day scatter at `app.py:401-425`)
- Y axis: grams
- Each dot = one qualifying meal event
- `mark_circle(size=100, opacity=0.7)` (matches the poop scatter visually for app-wide consistency)
- Tooltip on hover: date, time, grams, notes
- Height: ~320px

Same-day meals stack vertically — that's the point. You can see "morning was 12 g, afternoon was 18 g" at a glance.

## Data filtering

A "qualifying meal event" =

- `event_type == "meal"`, **AND**
- `pd.to_numeric(amount_grams, errors="coerce")` is a positive float

Zero-gram and blank-gram meals are excluded everywhere (metrics, both charts). This handles legacy events from before the `amount_grams` field existed — including them would skew avg meal size and put `0` dots on the scatter.

All time windows are anchored to "today" in `America/Los_Angeles`, using `TIMEZONE` from `config.py` (same convention as the home page).

## Empty / sparse-data states

| Situation | Behavior |
|---|---|
| No qualifying meal events at all | Single `st.info("No meals with grams logged yet. Log a meal with grams on the home page to see analytics here.")`. Page renders nothing else. |
| Meals exist but none in last 7 days | Metric values show `—`, no delta. Charts still render whatever falls in their windows. |
| Meals exist in last 7 days but not in prior 7-day window | Metric value renders. Delta text shows `"no prior-week data"` (matches the pattern at `app.py:362`). |
| Fewer than 7 days total of meal data | Rolling-average line uses `min_periods=1`, renders from day 1. Early points are noisier — acceptable. |

## Files changed

| File | Change |
|---|---|
| `pages/3_Meals.py` | **New file**, ~120 lines |
| `app.py` | None |
| `sheets.py` | None |
| `config.py` | None |
| `pages/1_Observations.py` | None |
| `pages/2_Training.py` | None |

**Google Sheet schema: unchanged.** No new tabs, no new columns.

## Code patterns reused

- `_load_events()` from `app.py:68-77` — **duplicated** into `pages/3_Meals.py`. Two consumers = Rule of Three says copy, don't extract.
- `_static_bar_chart()` style from `app.py:80-94` — adapted, then layered with an Altair rolling-average line.
- Poop scatter style from `app.py:401-425` — mirrored for the per-meal scatter (visual consistency across pages).

A single internal helper inside `pages/3_Meals.py`: `_meal_events(df) -> DataFrame` that returns only qualifying rows with `amount_grams` parsed to a positive float. Used by both metrics and charts.

No new dependencies. Altair, pandas, Streamlit are already in `requirements.txt`.

## Risk: existing functions are not affected

- The new file is **read-only**: it consumes `read_all_events()` from `sheets.py`. It does not write, edit, or delete any rows.
- `app.py`, `sheets.py`, `config.py`, `pages/1_Observations.py`, `pages/2_Training.py` are **not edited**.
- The duplicated `_load_events()` lives inside `pages/3_Meals.py` and does **not** import from `app.py`, so opening the new page does not re-execute any home-page side effects.
- Adding a new file to `pages/` only adds a sidebar entry; it cannot affect the home page or other pages' behavior.

## Verification (manual, before merging)

1. Open the Meals page locally with current data → 2 metrics render, daily-totals chart shows last 30 days with rolling-average line overlay, per-meal scatter shows each meal as a dot.
2. Hover the scatter → tooltip shows date, time, grams, notes.
3. Sanity-check the 7d avg by hand: pick a recent week, sum the grams in the Sheet, divide by 7, confirm the metric matches.
4. Confirm zero-gram historical meals are excluded from both metric calculations and the scatter (no dots at y=0).
5. Open on phone → metrics + both charts render readably.
6. Confirm home page (`app.py`) is unchanged — same status strip, log form, charts, recent events, export.
7. Confirm Observations and Training pages are unchanged.

## Out of scope (BACKLOG candidates)

- Target line on the daily-totals chart — waits for a vet-recommended grams/day per BACKLOG `Daily meal grams vs. target`.
- Home-page meal teaser/summary widget — Rule of Three; revisit if the user finds themselves opening the Meals page constantly.
- Per-meal time-of-day analysis (e.g. "did morning meal shift later?").
- Weekly grouped bars for longer-than-30-day comparison.
- Meal-time intervals — already partially answered by the home-page status-strip `avg: Xh Ym · 14d` caption on the Meal tile.
