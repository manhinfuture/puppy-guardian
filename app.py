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
from sheets import append_event, delete_event, read_all_events, update_event

TZ = ZoneInfo(TIMEZONE)
ICONS = {"pee": "💦", "poop": "💩", "meal": "🍽", "medicine": "💊"}
LBS_TO_GRAMS = 453.592

st.set_page_config(page_title="Puppy Guardian", page_icon="🐶")
st.title("🐶 Puppy Guardian")


def _compute_age(dob: date, today: date) -> str:
    years = today.year - dob.year
    months = today.month - dob.month
    day_offset = today.day - dob.day
    if day_offset < 0:
        months -= 1
        # days remaining after the last completed month boundary
        prev_month_date = date(today.year, today.month, 1) - timedelta(days=1)
        day_offset += prev_month_date.day
    if months < 0:
        years -= 1
        months += 12

    if years >= 1:
        if months == 0:
            return f"{years} year{'s' if years != 1 else ''}"
        return f"{years}y {months}m"

    weeks = day_offset // 7
    parts = []
    if months:
        parts.append(f"{months} month{'s' if months != 1 else ''}")
    if weeks:
        parts.append(f"{weeks} week{'s' if weeks != 1 else ''}")
    if not parts:
        days = (today - dob).days
        return f"{days} day{'s' if days != 1 else ''}"
    return " ".join(parts)


def _profile_circle_html(path: Path, size_px: int) -> str:
    circle = (
        f"width:{size_px}px;height:{size_px}px;border-radius:50%;"
        "object-fit:cover;border:2px solid #eee;flex-shrink:0;"
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
_dob = PUPPY["date_of_birth"]
_age = _compute_age(_dob, today)
_weights = df[df["event_type"] == "weight"].copy() if not df.empty else pd.DataFrame()
if not _weights.empty:
    _weights["_lbs"] = pd.to_numeric(_weights["amount_grams"], errors="coerce") / LBS_TO_GRAMS
    _weights = _weights.dropna(subset=["_lbs"]).sort_values("timestamp")
if _weights.empty:
    _weight_line = "<strong>Current weight:</strong> — (no weight logged yet)"
else:
    _latest = _weights.iloc[-1]
    _weight_line = (
        f"<strong>Current weight:</strong> {_latest['_lbs']:.2f} lbs "
        f"(as of {_latest['timestamp'].strftime('%Y-%m-%d')})"
    )

_circle_px = 150
_profile_html = f"""
<div style="display:flex; justify-content:center; align-items:center; gap:24px; margin:8px 0 20px 0;">
  {_profile_circle_html(_photo, _circle_px)}
  <div style="display:flex; flex-direction:column; justify-content:space-between; height:{_circle_px}px;">
    <div style="font-size:24px; font-weight:700; line-height:1;">{PUPPY['name']}</div>
    <div style="line-height:1.35;">
      <div><strong>Breed:</strong> {PUPPY['breed']}</div>
      <div><strong>Sex:</strong> {PUPPY['sex'].capitalize()}</div>
      <div><strong>DOB:</strong> {_dob.strftime('%Y-%m-%d')} ({_age})</div>
      <div>{_weight_line}</div>
    </div>
  </div>
</div>
"""
st.markdown(_profile_html, unsafe_allow_html=True)
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
editing_id = st.session_state.get("editing_event_id")
editing_row = None
if editing_id and not df.empty:
    match = df[df["event_id"] == editing_id]
    if not match.empty:
        editing_row = match.iloc[0]
    else:
        editing_id = None
        st.session_state.pop("editing_event_id", None)

if editing_row is not None:
    st.header("Edit event")
    st.caption(f"Editing event from {editing_row['timestamp'].strftime('%Y-%m-%d %H:%M')}")
else:
    st.header("Log an event")

if editing_row is not None:
    _default_type = editing_row["event_type"]
    _default_date = editing_row["timestamp"].date()
    _default_time = editing_row["timestamp"].time().replace(microsecond=0)
    _raw_grams = pd.to_numeric(editing_row["amount_grams"], errors="coerce")
    if pd.isna(_raw_grams) or _raw_grams == 0:
        _default_amount = 0.0
    elif _default_type == "weight":
        _default_amount = round(_raw_grams / LBS_TO_GRAMS, 2)
    else:
        _default_amount = float(_raw_grams)
    _default_loc = editing_row["location_correct"] if editing_row["location_correct"] in ("yes", "no") else "not noted"
    _default_notes = editing_row["notes"] or ""
else:
    _default_type = EVENT_TYPES[0]
    _default_date = now_local.date()
    _default_time = now_local.time()
    _default_amount = 0.0
    _default_loc = "not noted"
    _default_notes = ""

with st.form("log_event", clear_on_submit=editing_row is None):
    event_type = st.selectbox("Event type", EVENT_TYPES, index=EVENT_TYPES.index(_default_type))

    col1, col2 = st.columns(2)
    with col1:
        event_date = st.date_input("Date", value=_default_date)
    with col2:
        event_time = st.time_input("Time", value=_default_time)

    amount_input = st.number_input(
        "Amount — meals: grams · weight: lbs (leave 0 otherwise)",
        min_value=0.0,
        step=0.1,
        value=_default_amount,
    )

    location_correct = st.radio(
        "Correct location? (for pee/poop only)",
        options=["not noted", "yes", "no"],
        index=["not noted", "yes", "no"].index(_default_loc),
        horizontal=True,
    )

    notes = st.text_area("Notes (optional)", value=_default_notes, placeholder="e.g. soft stool, ate slowly")

    btn_cols = st.columns([1, 1, 4])
    with btn_cols[0]:
        submitted = st.form_submit_button("Update event" if editing_row is not None else "Save event")
    with btn_cols[1]:
        cancel_edit = st.form_submit_button("Cancel") if editing_row is not None else False

if editing_row is not None and cancel_edit:
    st.session_state.pop("editing_event_id", None)
    st.rerun()

if submitted:
    timestamp = datetime.combine(event_date, event_time).isoformat(timespec="seconds")
    if event_type == "meal" and amount_input > 0:
        grams_value = str(amount_input)
    elif event_type == "weight" and amount_input > 0:
        grams_value = str(round(amount_input * LBS_TO_GRAMS, 2))
    else:
        grams_value = ""
    location_value = location_correct if location_correct != "not noted" else ""
    if editing_row is not None:
        update_event(
            event_id=editing_id,
            timestamp=timestamp,
            event_type=event_type,
            amount_grams=grams_value,
            location_correct=location_value,
            notes=notes,
        )
        st.session_state.pop("editing_event_id", None)
        st.toast(f"Updated {event_type} at {timestamp}")
    else:
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
    def _format_amount(row):
        raw = pd.to_numeric(row["amount_grams"], errors="coerce")
        if pd.isna(raw) or raw == 0:
            return ""
        if row["event_type"] == "weight":
            return f"{raw / LBS_TO_GRAMS:.2f} lbs"
        if row["event_type"] == "meal":
            return f"{raw:g} g"
        return str(raw)

    recent = df.sort_values("timestamp", ascending=False).head(20)

    header_cols = st.columns([1.2, 0.9, 1.0, 1.1, 1.0, 2.5, 1.4])
    for col, label in zip(
        header_cols,
        ["Date", "Time", "Type", "Amount", "Location", "Notes", ""],
    ):
        col.markdown(f"**{label}**")
    st.markdown(
        '<hr style="margin:4px 0;border:none;border-top:1px solid #bbb;" />',
        unsafe_allow_html=True,
    )

    pending_delete = st.session_state.get("pending_delete_id")
    _row_divider = '<hr style="margin:4px 0;border:none;border-top:1px solid #eee;" />'

    for _, row in recent.iterrows():
        row_cols = st.columns([1.2, 0.9, 1.0, 1.1, 1.0, 2.5, 1.4], vertical_alignment="center")
        row_cols[0].write(row["timestamp"].strftime("%Y-%m-%d"))
        row_cols[1].write(row["timestamp"].strftime("%H:%M"))
        row_cols[2].write(row["event_type"])
        row_cols[3].write(_format_amount(row))
        row_cols[4].write(row["location_correct"] or "")
        row_cols[5].write(row["notes"] or "")
        with row_cols[6]:
            eid = row["event_id"]
            if pending_delete == eid:
                c1, c2 = st.columns(2)
                if c1.button("✓", key=f"confirm_{eid}", help="Confirm delete"):
                    delete_event(eid)
                    st.session_state.pop("pending_delete_id", None)
                    if st.session_state.get("editing_event_id") == eid:
                        st.session_state.pop("editing_event_id", None)
                    st.toast("Event deleted")
                    st.rerun()
                if c2.button("✕", key=f"cancel_{eid}", help="Cancel"):
                    st.session_state.pop("pending_delete_id", None)
                    st.rerun()
            else:
                c1, c2 = st.columns(2)
                if c1.button("✏️", key=f"edit_{eid}", help="Edit"):
                    st.session_state["editing_event_id"] = eid
                    st.session_state.pop("pending_delete_id", None)
                    st.rerun()
                if c2.button("🗑️", key=f"del_{eid}", help="Delete"):
                    st.session_state["pending_delete_id"] = eid
                    st.rerun()
        st.markdown(_row_divider, unsafe_allow_html=True)

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
