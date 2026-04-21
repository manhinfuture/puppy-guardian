import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from config import TIMEZONE
from sheets import (
    add_observation,
    delete_observation,
    read_observations,
    update_observation,
)

TZ = ZoneInfo(TIMEZONE)

st.set_page_config(page_title="Observations · Puppy Guardian", page_icon="📝")
st.title("📝 Observations")
st.caption("Notes to self about Ichi — things to revisit later.")


def _load() -> pd.DataFrame:
    df = read_observations()
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["resolved"] = df["resolved"].fillna("").astype(str)
    df["notes"] = df["notes"].fillna("").astype(str)
    return df


today = datetime.now(TZ).date()

# --- Add form ---
st.subheader("Add observation")
with st.form("add_observation", clear_on_submit=True):
    obs_date = st.date_input("Date", value=today, key="new_obs_date")
    obs_notes = st.text_area(
        "Notes",
        key="new_obs_notes",
        placeholder="e.g. Ichi is jumpy and biting everything — look into this",
    )
    submitted = st.form_submit_button("Add")

if submitted:
    if not obs_notes.strip():
        st.warning("Please enter some notes.")
    else:
        add_observation(
            observation_id=str(uuid.uuid4()),
            date_str=obs_date.isoformat(),
            notes=obs_notes.strip(),
            resolved="",
        )
        st.toast("Observation added")
        st.rerun()

df = _load()


def _render_row(row: pd.Series) -> None:
    oid = row["observation_id"]
    editing = st.session_state.get("editing_obs_id") == oid
    pending_delete = st.session_state.get("pending_delete_obs_id") == oid

    if editing:
        with st.form(f"edit_obs_{oid}"):
            new_date = st.date_input("Date", value=row["date"] or today, key=f"edit_date_{oid}")
            new_notes = st.text_area("Notes", value=row["notes"], key=f"edit_notes_{oid}")
            c1, c2, _ = st.columns([1, 1, 4])
            save = c1.form_submit_button("Save")
            cancel = c2.form_submit_button("Cancel")
        if save:
            update_observation(
                observation_id=oid,
                date_str=new_date.isoformat(),
                notes=new_notes.strip(),
                resolved=row["resolved"],
            )
            st.session_state.pop("editing_obs_id", None)
            st.toast("Observation updated")
            st.rerun()
        if cancel:
            st.session_state.pop("editing_obs_id", None)
            st.rerun()
        st.markdown(
            '<hr style="margin:4px 0;border:none;border-top:1px solid #eee;" />',
            unsafe_allow_html=True,
        )
        return

    cols = st.columns([1.2, 1.1, 4.0, 0.6, 0.6], vertical_alignment="center")
    cols[0].write(row["date"].isoformat() if row["date"] else "")
    is_resolved = row["resolved"] == "yes"
    new_state = cols[1].checkbox(
        "resolved",
        value=is_resolved,
        key=f"resolved_{oid}",
        label_visibility="collapsed",
    )
    if new_state != is_resolved:
        update_observation(
            observation_id=oid,
            date_str=row["date"].isoformat() if row["date"] else "",
            notes=row["notes"],
            resolved="yes" if new_state else "",
        )
        st.rerun()
    cols[2].write(row["notes"])
    if pending_delete:
        if cols[3].button("✓", key=f"confirm_obs_{oid}", help="Confirm delete"):
            delete_observation(oid)
            st.session_state.pop("pending_delete_obs_id", None)
            if st.session_state.get("editing_obs_id") == oid:
                st.session_state.pop("editing_obs_id", None)
            st.toast("Observation deleted")
            st.rerun()
        if cols[4].button("✕", key=f"cancel_obs_{oid}", help="Cancel"):
            st.session_state.pop("pending_delete_obs_id", None)
            st.rerun()
    else:
        if cols[3].button("✏️", key=f"edit_btn_{oid}", help="Edit"):
            st.session_state["editing_obs_id"] = oid
            st.session_state.pop("pending_delete_obs_id", None)
            st.rerun()
        if cols[4].button("🗑️", key=f"del_btn_{oid}", help="Delete"):
            st.session_state["pending_delete_obs_id"] = oid
            st.rerun()
    st.markdown(
        '<hr style="margin:4px 0;border:none;border-top:1px solid #eee;" />',
        unsafe_allow_html=True,
    )


def _render_section(subset: pd.DataFrame) -> None:
    if subset.empty:
        st.caption("Nothing here yet.")
        return
    header = st.columns([1.2, 1.1, 4.0, 0.6, 0.6])
    for col, label in zip(header, ["Date", "Resolved", "Notes", "", ""]):
        col.markdown(f"**{label}**")
    st.markdown(
        '<hr style="margin:4px 0;border:none;border-top:1px solid #bbb;" />',
        unsafe_allow_html=True,
    )
    subset = subset.sort_values("date", ascending=False, na_position="last")
    for _, row in subset.iterrows():
        _render_row(row)


if df.empty:
    st.info("No observations yet. Add one above.")
else:
    open_df = df[df["resolved"] != "yes"]
    resolved_df = df[df["resolved"] == "yes"]

    with st.expander(f"Open ({len(open_df)})", expanded=True):
        _render_section(open_df)

    with st.expander(f"Resolved ({len(resolved_df)})", expanded=False):
        _render_section(resolved_df)
