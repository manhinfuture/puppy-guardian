import uuid
from datetime import datetime

import pandas as pd
import streamlit as st

from config import EVENT_TYPES
from sheets import append_event, read_all_events

st.set_page_config(page_title="Puppy Guardian", page_icon="🐶")
st.title("🐶 Puppy Guardian")

st.header("Log an event")

with st.form("log_event", clear_on_submit=True):
    event_type = st.selectbox("Event type", EVENT_TYPES)

    col1, col2 = st.columns(2)
    with col1:
        event_date = st.date_input("Date", value=datetime.now().date())
    with col2:
        event_time = st.time_input("Time", value=datetime.now().time())

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
    st.success(f"Logged {event_type} at {timestamp}")

st.header("Recent events")

df = read_all_events()
if df.empty:
    st.info("No events yet. Log one above!")
else:
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["date"] = df["timestamp"].dt.strftime("%Y-%m-%d")
    df["time"] = df["timestamp"].dt.strftime("%H:%M")
    recent = df.sort_values("timestamp", ascending=False).head(20)
    st.dataframe(
        recent[["date", "time", "event_type", "amount_grams", "location_correct", "notes"]],
        hide_index=True,
        use_container_width=True,
    )
