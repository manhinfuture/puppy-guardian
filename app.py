import uuid
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st

from config import EVENT_TYPES, TIMEZONE
from sheets import append_event, read_all_events

TZ = ZoneInfo(TIMEZONE)
ICONS = {"pee": "💦", "poop": "💩", "meal": "🍽", "medicine": "💊"}

st.set_page_config(page_title="Puppy Guardian", page_icon="🐶")
st.title("🐶 Puppy Guardian")
st.caption("Tracking Ichi")


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


def _static_bar_chart(series: pd.Series, x_label: str, x_type: str = "O") -> alt.Chart:
    data = series.reset_index()
    data.columns = [x_label, "count"]
    chart = (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_label}:{x_type}", title=x_label, sort=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("count:Q", title="count"),
            tooltip=[x_label, "count"],
        )
        .properties(height=300)
        .configure_view(strokeWidth=0)
    )
    return chart


def _humanize(delta: timedelta) -> str:
    total_min = int(delta.total_seconds() // 60)
    if total_min < 1:
        return "just now"
    if total_min < 60:
        return f"{total_min}m ago"
    hours, minutes = divmod(total_min, 60)
    if hours < 24:
        return f"{hours}h {minutes}m ago" if minutes else f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


df = _load_events()
now_local = datetime.now(TZ)
today = now_local.date()

# --- Status strip ---
st.subheader("Right now")
STATUS_TYPES = ["pee", "poop", "meal"]
cols = st.columns(len(STATUS_TYPES))
for col, et in zip(cols, STATUS_TYPES):
    with col:
        label = f"{ICONS.get(et, '')} {et.capitalize()}"
        sub = df[df["event_type"] == et] if not df.empty else df
        if sub.empty:
            st.metric(label, "—", "0 today", delta_color="off")
        else:
            last_ts = sub["timestamp"].max()
            since = _humanize(now_local - last_ts.to_pydatetime())
            today_count = int((sub["timestamp"].dt.date == today).sum())
            st.metric(label, since, f"{today_count} today", delta_color="off")

# --- Log form ---
st.header("Log an event")

with st.form("log_event", clear_on_submit=True):
    event_type = st.selectbox("Event type", EVENT_TYPES)

    col1, col2 = st.columns(2)
    with col1:
        event_date = st.date_input("Date", value=now_local.date())
    with col2:
        event_time = st.time_input("Time", value=now_local.time())

    amount_grams = st.number_input(
        "Amount in grams (for meals only — leave 0 otherwise)",
        min_value=0.0,
        step=1.0,
        value=0.0,
    )

    location_correct = st.radio(
        "Correct location? (for pee/poop only)",
        options=["not noted", "yes", "no"],
        horizontal=True,
    )

    notes = st.text_area("Notes (optional)", placeholder="e.g. soft stool, ate slowly")

    submitted = st.form_submit_button("Save event")

if submitted:
    timestamp = datetime.combine(event_date, event_time).isoformat(timespec="seconds")
    grams_value = str(amount_grams) if event_type == "meal" and amount_grams > 0 else ""
    location_value = location_correct if location_correct != "not noted" else ""
    append_event(
        event_id=str(uuid.uuid4()),
        timestamp=timestamp,
        event_type=event_type,
        amount_grams=grams_value,
        location_correct=location_value,
        notes=notes,
    )
    st.toast(f"Logged {event_type} at {timestamp}")
    st.rerun()

# --- Charts ---
st.header("Charts")

if df.empty:
    st.info("Log some events to see charts.")
else:
    window_days = 14
    window_start = pd.Timestamp(today - timedelta(days=window_days - 1), tz=TZ)
    window_dates = pd.date_range(window_start.date(), today, freq="D").date
    recent_df = df[df["timestamp"] >= window_start].copy()
    recent_df["date"] = recent_df["timestamp"].dt.date

    # Potty accuracy: this week vs last week
    potty = df[df["event_type"].isin(["pee", "poop"])]
    potty = potty[potty["location_correct"].isin(["yes", "no"])]
    this_week_cut = now_local - timedelta(days=7)
    last_week_cut = now_local - timedelta(days=14)
    this_week = potty[potty["timestamp"] >= this_week_cut]
    last_week = potty[(potty["timestamp"] >= last_week_cut) & (potty["timestamp"] < this_week_cut)]

    def _accuracy(subset: pd.DataFrame) -> Optional[float]:
        if subset.empty:
            return None
        return (subset["location_correct"] == "yes").mean() * 100

    tw = _accuracy(this_week)
    lw = _accuracy(last_week)
    acc_col, _ = st.columns([1, 3])
    with acc_col:
        if tw is None:
            st.metric("Potty accuracy (7d)", "—", "no data", delta_color="off")
        else:
            delta_text = f"{tw - lw:+.0f}% vs last week" if lw is not None else "no last-week data"
            st.metric("Potty accuracy (7d)", f"{tw:.0f}%", delta_text)

    # Poop charts (stacked vertically for readability)
    st.subheader("💩 Poop")
    poop = recent_df[recent_df["event_type"] == "poop"]

    st.caption("Time of day by date (last 14 days) — each dot is one poop")
    if poop.empty:
        st.info("No poop events in the last 14 days.")
    else:
        dots_df = pd.DataFrame({
            "date": poop["timestamp"].dt.strftime("%-m/%-d"),
            "hour_of_day": poop["timestamp"].dt.hour + poop["timestamp"].dt.minute / 60,
            "time": poop["timestamp"].dt.strftime("%H:%M"),
        })
        dot_chart = (
            alt.Chart(dots_df)
            .mark_circle(size=100, opacity=0.7)
            .encode(
                x=alt.X("date:O", title="date", sort=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y(
                    "hour_of_day:Q",
                    title="hour of day",
                    scale=alt.Scale(domain=[0, 24]),
                    axis=alt.Axis(values=list(range(0, 25, 3))),
                ),
                tooltip=["date", "time"],
            )
            .properties(height=320)
            .configure_view(strokeWidth=0)
        )
        st.altair_chart(dot_chart, use_container_width=True)

    st.caption("Daily count (last 14 days)")
    if poop.empty:
        st.info("No poop events in the last 14 days.")
    else:
        daily = poop.groupby("date").size().reindex(window_dates, fill_value=0)
        daily.index = [f"{d.month}/{d.day}" for d in daily.index]
        daily.index.name = "date"
        st.altair_chart(
            _static_bar_chart(daily, "date", x_type="O"),
            use_container_width=True,
        )

    # Pee chart
    st.subheader("💦 Pee")
    st.caption("Daily count (last 14 days)")
    pee = recent_df[recent_df["event_type"] == "pee"]
    if pee.empty:
        st.info("No pee events in the last 14 days.")
    else:
        daily_pee = pee.groupby("date").size().reindex(window_dates, fill_value=0)
        daily_pee.index = [f"{d.month}/{d.day}" for d in daily_pee.index]
        daily_pee.index.name = "date"
        st.altair_chart(
            _static_bar_chart(daily_pee, "date", x_type="O"),
            use_container_width=True,
        )

# --- Recent events ---
st.header("Recent events")

if df.empty:
    st.info("No events yet. Log one above!")
else:
    display = df.copy()
    display["date"] = display["timestamp"].dt.strftime("%Y-%m-%d")
    display["time"] = display["timestamp"].dt.strftime("%H:%M")
    recent = display.sort_values("timestamp", ascending=False).head(20)
    st.dataframe(
        recent[["date", "time", "event_type", "amount_grams", "location_correct", "notes"]],
        hide_index=True,
        use_container_width=True,
    )

# --- CSV export ---
st.header("Export")

if df.empty:
    st.caption("Nothing to export yet.")
else:
    export_df = df.sort_values("timestamp").copy()
    export_df["timestamp"] = export_df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    csv_bytes = export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name=f"puppy_guardian_{today.isoformat()}.csv",
        mime="text/csv",
    )
