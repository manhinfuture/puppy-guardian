import base64
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st

from config import EVENT_TYPES, PUPPY, TIMEZONE
from sheets import append_event, read_all_events

TZ = ZoneInfo(TIMEZONE)
ICONS = {"pee": "💦", "poop": "💩", "meal": "🍽", "medicine": "💊"}
LBS_TO_GRAMS = 453.592

st.set_page_config(page_title="Puppy Guardian", page_icon="🐶")
st.title("🐶 Puppy Guardian")


def _compute_age(dob: date, today: date) -> str:
    years = today.year - dob.year
    months = today.month - dob.month
    if today.day < dob.day:
        months -= 1
    if months < 0:
        years -= 1
        months += 12
    if years == 0:
        return f"{months} month{'s' if months != 1 else ''}"
    if months == 0:
        return f"{years} year{'s' if years != 1 else ''}"
    return f"{years}y {months}m"


def _profile_image_html(path: Path, size_px: int = 140) -> str:
    circle = (
        f"width:{size_px}px;height:{size_px}px;border-radius:50%;"
        "object-fit:cover;border:2px solid #eee;"
    )
    if path.exists():
        mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
        b64 = base64.b64encode(path.read_bytes()).decode()
        return f'<img src="data:{mime};base64,{b64}" style="{circle}" />'
    return (
        f'<div style="{circle}background:#f5f5f5;display:flex;'
        f'align-items:center;justify-content:center;font-size:{size_px // 2}px;">🐶</div>'
    )


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


def _format_duration(delta: timedelta) -> str:
    total_min = int(delta.total_seconds() // 60)
    if total_min < 60:
        return f"{total_min}m"
    hours, minutes = divmod(total_min, 60)
    return f"{hours}h {minutes}m" if minutes else f"{hours}h"


def _avg_daytime_interval(sub: pd.DataFrame, window_start: pd.Timestamp) -> Optional[timedelta]:
    # Excludes overnight gaps: only pairs consecutive same-type events that fall
    # within 06:00-23:59 on the same calendar day.
    if sub.empty:
        return None
    recent = sub[sub["timestamp"] >= window_start].copy()
    hour = recent["timestamp"].dt.hour
    recent = recent[hour >= 6]
    if len(recent) < 2:
        return None
    recent = recent.sort_values("timestamp")
    recent["date"] = recent["timestamp"].dt.date
    gaps = recent["timestamp"].diff()
    same_day = recent["date"] == recent["date"].shift()
    gaps = gaps[same_day]
    if gaps.empty:
        return None
    return gaps.mean().to_pytimedelta()


df = _load_events()
now_local = datetime.now(TZ)
today = now_local.date()

# --- Profile ---
_photo = Path(__file__).parent / PUPPY["photo_path"]
_prof_left, _prof_right = st.columns([1, 3])
with _prof_left:
    st.markdown(_profile_image_html(_photo), unsafe_allow_html=True)
with _prof_right:
    _dob = PUPPY["date_of_birth"]
    _age = _compute_age(_dob, today)
    st.markdown(f"### {PUPPY['name']}")
    st.markdown(
        f"**Breed:** {PUPPY['breed']}  \n"
        f"**Sex:** {PUPPY['sex'].capitalize()}  \n"
        f"**DOB:** {_dob.strftime('%Y-%m-%d')} ({_age})"
    )
    _weights = df[df["event_type"] == "weight"].copy() if not df.empty else pd.DataFrame()
    if not _weights.empty:
        _weights["_lbs"] = pd.to_numeric(_weights["amount_grams"], errors="coerce") / LBS_TO_GRAMS
        _weights = _weights.dropna(subset=["_lbs"]).sort_values("timestamp")
    if _weights.empty:
        st.markdown("**Current weight:** — (no weight logged yet)")
    else:
        _latest = _weights.iloc[-1]
        st.markdown(
            f"**Current weight:** {_latest['_lbs']:.2f} lbs "
            f"(as of {_latest['timestamp'].strftime('%Y-%m-%d')})"
        )

st.divider()

# --- Status strip ---
st.subheader("Right now")
STATUS_TYPES = ["pee", "poop", "meal"]
avg_window_start = pd.Timestamp(today - timedelta(days=13), tz=TZ)
cols = st.columns(len(STATUS_TYPES))
for col, et in zip(cols, STATUS_TYPES):
    with col:
        label = f"{ICONS.get(et, '')} {et.capitalize()}"
        sub = df[df["event_type"] == et] if not df.empty else df
        if sub.empty:
            st.metric(label, "—", "0 today", delta_color="off")
            st.caption("avg: —")
        else:
            last_ts = sub["timestamp"].max()
            since = _humanize(now_local - last_ts.to_pydatetime())
            today_count = int((sub["timestamp"].dt.date == today).sum())
            st.metric(label, since, f"{today_count} today", delta_color="off")
            avg = _avg_daytime_interval(sub, avg_window_start)
            st.caption(f"avg: {_format_duration(avg)} · 14d" if avg else "avg: — · 14d")

# --- Log form ---
st.header("Log an event")

with st.form("log_event", clear_on_submit=True):
    event_type = st.selectbox("Event type", EVENT_TYPES)

    col1, col2 = st.columns(2)
    with col1:
        event_date = st.date_input("Date", value=now_local.date())
    with col2:
        event_time = st.time_input("Time", value=now_local.time())

    amount_input = st.number_input(
        "Amount — meals: grams · weight: lbs (leave 0 otherwise)",
        min_value=0.0,
        step=0.1,
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
    if event_type == "meal" and amount_input > 0:
        grams_value = str(amount_input)
    elif event_type == "weight" and amount_input > 0:
        grams_value = str(round(amount_input * LBS_TO_GRAMS, 2))
    else:
        grams_value = ""
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

    # Potty accuracy trend (last 8 weeks, by calendar week)
    st.caption("Potty accuracy by week (last 8 weeks)")
    if potty.empty:
        st.info("No potty events with a noted location yet.")
    else:
        trend = potty.copy()
        trend["week_start"] = (trend["timestamp"] - pd.to_timedelta(trend["timestamp"].dt.weekday, unit="D")).dt.normalize()
        weekly = (
            trend.groupby("week_start")
            .apply(lambda g: (g["location_correct"] == "yes").mean() * 100)
            .rename("accuracy")
            .reset_index()
        )
        cutoff = pd.Timestamp(today - timedelta(weeks=7), tz=TZ).normalize()
        cutoff = cutoff - pd.to_timedelta(cutoff.weekday(), unit="D")
        weekly = weekly[weekly["week_start"] >= cutoff]
        weekly["week"] = weekly["week_start"].dt.strftime("%-m/%-d")
        trend_chart = (
            alt.Chart(weekly)
            .mark_line(point=True)
            .encode(
                x=alt.X("week:O", title="week of", sort=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("accuracy:Q", title="accuracy %", scale=alt.Scale(domain=[0, 100])),
                tooltip=["week", alt.Tooltip("accuracy:Q", format=".0f")],
            )
            .properties(height=260)
            .configure_view(strokeWidth=0)
        )
        st.altair_chart(trend_chart, use_container_width=True)

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

# --- Weight ---
st.header("⚖️ Weight")

weights = df[df["event_type"] == "weight"].copy() if not df.empty else pd.DataFrame()
if not weights.empty:
    weights["weight_lbs"] = pd.to_numeric(weights["amount_grams"], errors="coerce") / LBS_TO_GRAMS
    weights = weights.dropna(subset=["weight_lbs"]).sort_values("timestamp")

if weights.empty:
    st.info("No weight records yet. Log a weight event above to start tracking.")
else:
    latest = weights.iloc[-1]
    st.caption(
        f"Current: **{latest['weight_lbs']:.2f} lbs** (as of {latest['timestamp'].strftime('%-m/%-d')})"
    )
    weight_chart_df = pd.DataFrame({
        "date": weights["timestamp"].dt.strftime("%-m/%-d"),
        "weight_lbs": weights["weight_lbs"].round(2),
    })
    weight_chart = (
        alt.Chart(weight_chart_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("date:O", title="date", sort=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("weight_lbs:Q", title="weight (lbs)"),
            tooltip=["date", alt.Tooltip("weight_lbs:Q", format=".2f")],
        )
        .properties(height=300)
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(weight_chart, use_container_width=True)

# --- Recent events ---
st.header("Recent events")

if df.empty:
    st.info("No events yet. Log one above!")
else:
    display = df.copy()
    display["date"] = display["timestamp"].dt.strftime("%Y-%m-%d")
    display["time"] = display["timestamp"].dt.strftime("%H:%M")

    def _format_amount(row):
        raw = pd.to_numeric(row["amount_grams"], errors="coerce")
        if pd.isna(raw) or raw == 0:
            return ""
        if row["event_type"] == "weight":
            return f"{raw / LBS_TO_GRAMS:.2f} lbs"
        if row["event_type"] == "meal":
            return f"{raw:g} g"
        return str(raw)

    display["amount"] = display.apply(_format_amount, axis=1)
    recent = display.sort_values("timestamp", ascending=False).head(20)
    st.dataframe(
        recent[["date", "time", "event_type", "amount", "location_correct", "notes"]],
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
    csv_bytes = export_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name=f"puppy_guardian_{today.isoformat()}.csv",
        mime="text/csv",
    )
