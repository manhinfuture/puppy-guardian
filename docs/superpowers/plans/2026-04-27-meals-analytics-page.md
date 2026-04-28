# Meals Analytics Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated `pages/3_Meals.py` page that visualizes meal-feeding **consistency** (day-to-day variance) and **growth trend** (whether daily grams are scaling up as Ichi grows). No existing files are modified.

**Architecture:** A single new Streamlit page file. Read-only consumer of `read_all_events()` from `sheets.py`. Two `st.metric` cards followed by two layered Altair charts (daily-totals bar + 7-day rolling average overlay; per-meal scatter). The small `_load_events()` helper is duplicated from `app.py` per the project's Rule of Three convention (two consumers = copy, don't extract).

**Tech Stack:** Python, Streamlit (multipage), pandas, Altair. No new dependencies — all already in `requirements.txt`.

**Verification convention:** This project does not have a Python test suite — every prior phase used **manual browser-based verification** (see PLAN.md "Verification" subsections). Each task in this plan ends with manual verification steps run against `streamlit run app.py` locally. **Do not introduce a pytest framework.** That would be a structural change requiring discussion per CLAUDE.md.

**Spec:** [docs/superpowers/specs/2026-04-27-meals-analytics-page-design.md](../specs/2026-04-27-meals-analytics-page-design.md)

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `pages/3_Meals.py` | **New, ~120 lines** | The entire Meals page: data load, filter, metrics, two charts, empty states. Self-contained. |
| `app.py` | **Unchanged** | Home page must remain identical. |
| `sheets.py` | **Unchanged** | `read_all_events()` is reused as-is. |
| `config.py` | **Unchanged** | `meal` is already in `EVENT_TYPES`. |
| `pages/1_Observations.py` | **Unchanged** | |
| `pages/2_Training.py` | **Unchanged** | |

**Google Sheet schema: unchanged.** No new tabs, no new columns.

`pages/3_Meals.py` internal structure (single file, top-down):

1. Imports (`zoneinfo`, `datetime`, `altair`, `pandas`, `streamlit`, plus `TIMEZONE` from `config` and `read_all_events` from `sheets`)
2. Module-level constants: `TZ = ZoneInfo(TIMEZONE)`
3. `st.set_page_config(...)` and `st.title("🍽 Meals")`
4. Two helpers: `_load_events()` (duplicated from `app.py:68-77`) and `_meal_events(df)` (filter to qualifying meals)
5. Body: load → empty-state guard → metrics row → daily-totals chart → per-meal scatter

---

## Task 1: Scaffold the Meals page

**Files:**
- Create: `pages/3_Meals.py`

- [ ] **Step 1: Create the file with imports, page config, and title**

Create `pages/3_Meals.py` with the following exact content:

```python
from datetime import timedelta
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st

from config import TIMEZONE
from sheets import read_all_events

TZ = ZoneInfo(TIMEZONE)

st.set_page_config(page_title="Meals · Puppy Guardian", page_icon="🍽")
st.title("🍽 Meals")
st.caption("Daily total grams and per-meal detail for Ichi.")
```

- [ ] **Step 2: Run the app**

In a terminal at the project root:

```bash
streamlit run app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`).

- [ ] **Step 3: Manual verification**

Confirm all of:
- The sidebar shows three pages in this order: **Observations**, **Training**, **Meals**.
- Click **Meals** → page renders with the title `🍽 Meals` and the caption "Daily total grams and per-meal detail for Ichi."
- No errors visible in the Streamlit browser tab or in the terminal where Streamlit is running.
- Click **Home** (or the app name) → home page still loads unchanged (status strip, log form, charts, recent events all visible).
- Click **Observations** → page still loads unchanged.
- Click **Training** → page still loads unchanged.

If anything breaks: stop, investigate, do not proceed.

- [ ] **Step 4: Commit**

```bash
git add pages/3_Meals.py
git commit -m "Meals page: scaffold"
```

---

## Task 2: Load events and filter to qualifying meals

**Files:**
- Modify: `pages/3_Meals.py`

- [ ] **Step 1: Add the two helper functions and the empty-state guard**

Replace the entire contents of `pages/3_Meals.py` with:

```python
from datetime import timedelta
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st

from config import TIMEZONE
from sheets import read_all_events

TZ = ZoneInfo(TIMEZONE)

st.set_page_config(page_title="Meals · Puppy Guardian", page_icon="🍽")
st.title("🍽 Meals")
st.caption("Daily total grams and per-meal detail for Ichi.")


def _load_events() -> pd.DataFrame:
    df = read_all_events()
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    if df["timestamp"].dt.tz is None:
        df["timestamp"] = df["timestamp"].dt.tz_localize(TZ)
    else:
        df["timestamp"] = df["timestamp"].dt.tz_convert(TZ)
    return df


def _meal_events(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    meals = df[df["event_type"] == "meal"].copy()
    if meals.empty:
        return meals
    meals["grams"] = pd.to_numeric(meals["amount_grams"], errors="coerce")
    meals = meals[meals["grams"] > 0]
    return meals


df = _load_events()
meals = _meal_events(df)

if meals.empty:
    st.info(
        "No meals with grams logged yet. Log a meal with grams on the home page "
        "to see analytics here."
    )
    st.stop()

now_local = pd.Timestamp.now(tz=TZ)
today = now_local.date()
```

- [ ] **Step 2: Run the app**

```bash
streamlit run app.py
```

(If Streamlit is already running from Task 1, it auto-reloads on file save — just refresh the browser.)

- [ ] **Step 3: Manual verification**

Click the **Meals** sidebar entry. Two scenarios — confirm whichever applies:

- **If your Sheet has at least one meal event with `amount_grams > 0`:** the page renders the title and caption with no error. Nothing visible below the caption (next tasks add content).
- **If your Sheet has zero qualifying meals:** the page shows the info box `No meals with grams logged yet. Log a meal with grams on the home page to see analytics here.`

In either case:
- No tracebacks in the browser or terminal.
- Home / Observations / Training pages still work.

- [ ] **Step 4: Commit**

```bash
git add pages/3_Meals.py
git commit -m "Meals page: data loading and empty state"
```

---

## Task 3: Add the two metric cards

**Files:**
- Modify: `pages/3_Meals.py`

- [ ] **Step 1: Append the metrics row to the page**

Add the following block to `pages/3_Meals.py`, immediately after the `today = now_local.date()` line at the end of the file:

```python
# --- Metric cards ---
this_week_start = pd.Timestamp(today - timedelta(days=6), tz=TZ)
prior_week_start = pd.Timestamp(today - timedelta(days=13), tz=TZ)
prior_week_end = pd.Timestamp(today - timedelta(days=7), tz=TZ)

this_week = meals[meals["timestamp"] >= this_week_start]
prior_week = meals[
    (meals["timestamp"] >= prior_week_start) & (meals["timestamp"] < this_week_start)
]


def _avg_per_day(subset: pd.DataFrame) -> float | None:
    if subset.empty:
        return None
    return subset["grams"].sum() / 7.0


def _avg_meal_size(subset: pd.DataFrame) -> float | None:
    if subset.empty:
        return None
    return subset["grams"].mean()


tw_avg_day = _avg_per_day(this_week)
pw_avg_day = _avg_per_day(prior_week)
tw_meal_size = _avg_meal_size(this_week)
pw_meal_size = _avg_meal_size(prior_week)

m1, m2 = st.columns(2)
with m1:
    if tw_avg_day is None:
        st.metric("7-day avg/day", "—", "no data this week", delta_color="off")
    elif pw_avg_day is None:
        st.metric("7-day avg/day", f"{tw_avg_day:.0f} g", "no prior-week data", delta_color="off")
    else:
        st.metric(
            "7-day avg/day",
            f"{tw_avg_day:.0f} g",
            f"{tw_avg_day - pw_avg_day:+.0f} g vs prior 7d",
        )
with m2:
    if tw_meal_size is None:
        st.metric("7-day avg meal size", "—", "no data this week", delta_color="off")
    elif pw_meal_size is None:
        st.metric(
            "7-day avg meal size",
            f"{tw_meal_size:.1f} g",
            "no prior-week data",
            delta_color="off",
        )
    else:
        st.metric(
            "7-day avg meal size",
            f"{tw_meal_size:.1f} g",
            f"{tw_meal_size - pw_meal_size:+.1f} g vs prior 7d",
        )
```

- [ ] **Step 2: Refresh the browser**

The Streamlit dev server auto-reloads on file save.

- [ ] **Step 3: Manual verification**

On the **Meals** page, confirm:
- Two metric cards appear side by side under the caption: **7-day avg/day** and **7-day avg meal size**.
- Each shows a number followed by a `g` unit (or `—` if you have no data this week / no prior-week data).
- Each shows a colored delta (green = up, red = down) with the form `+X g vs prior 7d`, or a greyed-out "no prior-week data" if the prior 7-day window has zero qualifying meals.
- **Sanity check by hand:** open your Google Sheet, sum `amount_grams` for the last 7 days of `meal` events, divide by 7. Confirm the displayed number matches (rounded to a whole gram).
- No tracebacks. Home / Observations / Training pages still work.

- [ ] **Step 4: Commit**

```bash
git add pages/3_Meals.py
git commit -m "Meals page: 7-day metric cards"
```

---

## Task 4: Add the daily-totals chart with 7-day rolling average

**Files:**
- Modify: `pages/3_Meals.py`

- [ ] **Step 1: Append the daily-totals chart block**

Add the following to `pages/3_Meals.py`, immediately after the `with m2:` block from Task 3:

```python
# --- Daily total grams chart (last 30 days) ---
st.subheader("Daily total grams (last 30 days)")
st.caption("Bars = grams that day · line = 7-day rolling average")

window_days = 30
window_dates = pd.date_range(today - timedelta(days=window_days - 1), today, freq="D").date

meals_local = meals.copy()
meals_local["date"] = meals_local["timestamp"].dt.date

daily = (
    meals_local.groupby("date")["grams"]
    .sum()
    .reindex(window_dates, fill_value=0.0)
    .rename("grams")
    .reset_index()
    .rename(columns={"index": "date"})
)
daily["rolling7"] = daily["grams"].rolling(window=7, min_periods=1).mean()
daily["date_label"] = daily["date"].apply(lambda d: f"{d.month}/{d.day}")

bars = (
    alt.Chart(daily)
    .mark_bar()
    .encode(
        x=alt.X(
            "date_label:O",
            title="date",
            sort=None,
            axis=alt.Axis(labelAngle=0, labelOverlap=True),
        ),
        y=alt.Y("grams:Q", title="grams"),
        tooltip=[
            alt.Tooltip("date_label:O", title="date"),
            alt.Tooltip("grams:Q", title="grams", format=".0f"),
            alt.Tooltip("rolling7:Q", title="7d avg", format=".1f"),
        ],
    )
)

line = (
    alt.Chart(daily)
    .mark_line(point=False, strokeWidth=2)
    .encode(
        x=alt.X("date_label:O", sort=None),
        y=alt.Y("rolling7:Q"),
        color=alt.value("#e15759"),
    )
)

daily_chart = (bars + line).properties(height=300).configure_view(strokeWidth=0)
st.altair_chart(daily_chart, use_container_width=True)
```

- [ ] **Step 2: Refresh the browser**

Streamlit auto-reloads.

- [ ] **Step 3: Manual verification**

On the **Meals** page, confirm:
- Below the metrics, a new section titled **Daily total grams (last 30 days)** with the caption `Bars = grams that day · line = 7-day rolling average`.
- A bar chart renders, ~300px tall, with 30 x-axis ticks (one per day, formatted like `4/12`).
- Days where you logged no meals show as empty space (height-0 bars).
- A red line overlays the bars, smoothing through them — the 7-day rolling average.
- Hover a bar → tooltip shows `date`, `grams`, and `7d avg`.
- **Sanity check:** the bar for *today* should match the sum of today's meal grams in your Sheet.
- No tracebacks. Home / Observations / Training still work.

- [ ] **Step 4: Commit**

```bash
git add pages/3_Meals.py
git commit -m "Meals page: 30-day daily-totals chart with rolling average"
```

---

## Task 5: Add the per-meal scatter and final cross-page verification

**Files:**
- Modify: `pages/3_Meals.py`

- [ ] **Step 1: Append the per-meal scatter block**

Add the following to `pages/3_Meals.py`, immediately after the daily-totals chart block from Task 4:

```python
# --- Per-meal scatter (last 14 days) ---
st.subheader("Per-meal grams (last 14 days)")
st.caption("Each dot is one meal. Same-day meals stack vertically.")

scatter_window = pd.Timestamp(today - timedelta(days=13), tz=TZ)
scatter_meals = meals[meals["timestamp"] >= scatter_window].copy()

if scatter_meals.empty:
    st.info("No meals in the last 14 days.")
else:
    scatter_meals["date_label"] = scatter_meals["timestamp"].apply(
        lambda t: f"{t.month}/{t.day}"
    )
    scatter_meals["time_label"] = scatter_meals["timestamp"].dt.strftime("%H:%M")
    scatter_meals["notes_display"] = scatter_meals["notes"].fillna("").astype(str)

    scatter_chart = (
        alt.Chart(scatter_meals)
        .mark_circle(size=100, opacity=0.7)
        .encode(
            x=alt.X(
                "date_label:O",
                title="date",
                sort=None,
                axis=alt.Axis(labelAngle=0, labelOverlap=True),
            ),
            y=alt.Y("grams:Q", title="grams"),
            tooltip=[
                alt.Tooltip("date_label:O", title="date"),
                alt.Tooltip("time_label:N", title="time"),
                alt.Tooltip("grams:Q", title="grams", format=".1f"),
                alt.Tooltip("notes_display:N", title="notes"),
            ],
        )
        .properties(height=320)
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(scatter_chart, use_container_width=True)
```

- [ ] **Step 2: Refresh the browser**

Streamlit auto-reloads.

- [ ] **Step 3: Manual verification — Meals page**

On the **Meals** page, confirm:
- Below the daily-totals chart, a new section titled **Per-meal grams (last 14 days)** with the caption `Each dot is one meal. Same-day meals stack vertically.`
- A scatter chart renders, ~320px tall, with x = dates (last 14 days, format `4/26`) and y = grams.
- Each meal in the last 14 days appears as a single circle dot.
- Same-day meals stack vertically at slightly different y values (their gram amounts).
- Hover a dot → tooltip shows date, time (HH:MM), grams (one decimal), and notes (or empty if no notes).
- **Sanity check:** the dots on *today's* x-axis column should match the times and grams of the meals you logged today.
- No dots appear at y = 0 (zero-gram and blank-gram meals are correctly excluded).

- [ ] **Step 4: Manual verification — cross-page integrity**

Now confirm none of the existing pages broke:

- **Home page (`/`)**: status strip shows pee/poop/meal tiles with their `time since · today's count · avg: Xh Ym · 14d` captions. Log form is interactive. Existing charts (potty accuracy, poop, pee, weight) all render. Recent events table loads. CSV export button works.
- **Observations page**: add-form works, open and resolved sections render.
- **Training page**: items grouped by category, "I trained this today" button increments correctly.

- [ ] **Step 5: Manual verification — mobile viewport**

In Chrome / Safari devtools, switch to a phone viewport (e.g. iPhone 13 width). On the Meals page, confirm:
- Both metric cards remain readable (may stack vertically on narrow widths — Streamlit handles this).
- Both charts render and aren't horizontally cut off.
- The page is scrollable end-to-end without obvious layout breakage.

- [ ] **Step 6: Final commit**

```bash
git add pages/3_Meals.py
git commit -m "Meals page: per-meal scatter and final layout"
```

---

## Done criteria

All of the following are true:

- [ ] `pages/3_Meals.py` exists, ~120 lines, contains exactly the structure above.
- [ ] `app.py`, `sheets.py`, `config.py`, `pages/1_Observations.py`, `pages/2_Training.py` are byte-identical to their pre-plan versions (`git diff main -- <path>` shows nothing for each).
- [ ] Google Sheet schema is unchanged — no new tabs, no new columns.
- [ ] Five commits exist on the branch, one per task.
- [ ] Manual verification at the end of Task 5 (Meals page + cross-page integrity + mobile viewport) all passed.
