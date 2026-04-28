from datetime import timedelta
from typing import Optional
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


# --- Metric cards ---
this_week_start = pd.Timestamp(today - timedelta(days=6), tz=TZ)
prior_week_start = pd.Timestamp(today - timedelta(days=13), tz=TZ)

this_week = meals[meals["timestamp"] >= this_week_start]
prior_week = meals[
    (meals["timestamp"] >= prior_week_start) & (meals["timestamp"] < this_week_start)
]


def _avg_per_day(subset: pd.DataFrame) -> Optional[float]:
    if subset.empty:
        return None
    return subset["grams"].sum() / 7.0


def _avg_meal_size(subset: pd.DataFrame) -> Optional[float]:
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
