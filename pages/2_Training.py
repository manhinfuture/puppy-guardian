import uuid
from datetime import datetime, date
from typing import Optional
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from config import TIMEZONE, TRAINING_STATUSES
from sheets import (
    add_training,
    delete_training,
    read_trainings,
    update_training,
)

TZ = ZoneInfo(TIMEZONE)
STALE_DAYS = 5
STATUS_ORDER = {"practicing": 0, "not_started": 1, "reliable": 2}
STATUS_BADGE = {
    "not_started": "⚪ not started",
    "practicing": "🟡 practicing",
    "reliable": "🟢 reliable",
}
STATUS_SHORT = {
    "not_started": "⚪",
    "practicing": "🟡",
    "reliable": "🟢",
}

st.set_page_config(page_title="Training · Puppy Guardian", page_icon="🎓")
st.title("🎓 Training")
st.caption("Curriculum checklist — what to work on next with Ichi.")
st.caption("Status key: ⚪ not started · 🟡 practicing · 🟢 reliable.")


def _load() -> pd.DataFrame:
    df = read_trainings()
    if df.empty:
        return df
    df["name"] = df["name"].fillna("").astype(str)
    df["category"] = df["category"].fillna("").astype(str)
    df["status"] = df["status"].fillna("not_started").astype(str)
    df["notes"] = df["notes"].fillna("").astype(str)
    df["session_count"] = pd.to_numeric(df["session_count"], errors="coerce").fillna(0).astype(int)
    df["last_practiced"] = pd.to_datetime(df["last_practiced"], errors="coerce").dt.date
    return df


today = datetime.now(TZ).date()


def _stale_days(last_practiced) -> Optional[int]:
    if not isinstance(last_practiced, date) or pd.isna(last_practiced):
        return None
    return (today - last_practiced).days


def _render_row(row: pd.Series) -> None:
    tid = row["training_id"]
    editing = st.session_state.get("editing_train_id") == tid
    pending_delete = st.session_state.get("pending_delete_train_id") == tid

    if editing:
        with st.form(f"edit_train_{tid}"):
            new_name = st.text_input("Name", value=row["name"], key=f"edit_name_{tid}")
            new_category = st.text_input(
                "Category", value=row["category"], key=f"edit_cat_{tid}"
            )
            new_status = st.selectbox(
                "Status",
                options=TRAINING_STATUSES,
                index=TRAINING_STATUSES.index(row["status"])
                if row["status"] in TRAINING_STATUSES
                else 0,
                key=f"edit_status_{tid}",
            )
            new_count = st.number_input(
                "Session count",
                min_value=0,
                step=1,
                value=int(row["session_count"]),
                key=f"edit_count_{tid}",
            )
            new_last = st.date_input(
                "Last practiced",
                value=row["last_practiced"] if isinstance(row["last_practiced"], date) and not pd.isna(row["last_practiced"]) else None,
                key=f"edit_last_{tid}",
            )
            new_notes = st.text_area("Notes", value=row["notes"], key=f"edit_notes_{tid}")
            c1, c2, _ = st.columns([1, 1, 4])
            save = c1.form_submit_button("Save")
            cancel = c2.form_submit_button("Cancel")
        if save:
            update_training(
                training_id=tid,
                name=new_name.strip(),
                category=new_category.strip(),
                status=new_status,
                session_count=int(new_count),
                last_practiced=new_last.isoformat() if new_last else "",
                notes=new_notes.strip(),
            )
            st.session_state.pop("editing_train_id", None)
            st.toast("Training updated")
            st.rerun()
        if cancel:
            st.session_state.pop("editing_train_id", None)
            st.rerun()
        st.markdown(
            '<hr style="margin:4px 0;border:none;border-top:1px solid #eee;" />',
            unsafe_allow_html=True,
        )
        return

    cols = st.columns([1.8, 1.1, 0.6, 1.3, 1.0, 0.6, 0.6], vertical_alignment="center")

    name_md = f"**{row['name']}**"
    stale = _stale_days(row["last_practiced"])
    if row["status"] == "practicing" and stale is not None and stale >= STALE_DAYS:
        name_md += f"  \n<span style='color:#b85c00;font-size:0.85em;'>⚠️ haven't practiced in {stale} days</span>"
    if row["notes"]:
        preview = row["notes"].strip().splitlines()[0]
        if len(preview) > 60:
            preview = preview[:57] + "…"
        name_md += f"  \n<span style='color:#666;font-size:0.85em;'>{preview}</span>"
    cols[0].markdown(name_md, unsafe_allow_html=True)

    current_status = row["status"] if row["status"] in TRAINING_STATUSES else "not_started"
    new_status = cols[1].selectbox(
        "status",
        options=TRAINING_STATUSES,
        index=TRAINING_STATUSES.index(current_status),
        key=f"status_{tid}",
        label_visibility="collapsed",
        format_func=lambda s: STATUS_SHORT[s],
    )
    if new_status != current_status:
        update_training(
            training_id=tid,
            name=row["name"],
            category=row["category"],
            status=new_status,
            session_count=int(row["session_count"]),
            last_practiced=row["last_practiced"].isoformat()
            if isinstance(row["last_practiced"], date) and not pd.isna(row["last_practiced"])
            else "",
            notes=row["notes"],
        )
        st.rerun()

    cols[2].write(f"{int(row['session_count'])}×")
    cols[3].write(
        row["last_practiced"].isoformat() if isinstance(row["last_practiced"], date) and not pd.isna(row["last_practiced"]) else "—"
    )

    if cols[4].button("trained today", key=f"train_{tid}", use_container_width=True):
        update_training(
            training_id=tid,
            name=row["name"],
            category=row["category"],
            status=row["status"],
            session_count=int(row["session_count"]) + 1,
            last_practiced=today.isoformat(),
            notes=row["notes"],
        )
        st.toast(f"Logged a session for {row['name']}")
        st.rerun()

    if pending_delete:
        if cols[5].button("✓", key=f"confirm_train_{tid}", help="Confirm delete"):
            delete_training(tid)
            st.session_state.pop("pending_delete_train_id", None)
            if st.session_state.get("editing_train_id") == tid:
                st.session_state.pop("editing_train_id", None)
            st.toast("Training deleted")
            st.rerun()
        if cols[6].button("✕", key=f"cancel_train_{tid}", help="Cancel"):
            st.session_state.pop("pending_delete_train_id", None)
            st.rerun()
    else:
        if cols[5].button("✏️", key=f"edit_btn_{tid}", help="Edit"):
            st.session_state["editing_train_id"] = tid
            st.session_state.pop("pending_delete_train_id", None)
            st.rerun()
        if cols[6].button("🗑️", key=f"del_btn_{tid}", help="Delete"):
            st.session_state["pending_delete_train_id"] = tid
            st.rerun()

    st.markdown(
        '<hr style="margin:4px 0;border:none;border-top:1px solid #eee;" />',
        unsafe_allow_html=True,
    )


def _render_category(subset: pd.DataFrame) -> None:
    header = st.columns([1.8, 1.1, 0.6, 1.3, 1.0, 0.6, 0.6])
    for col, label in zip(
        header, ["Name", "Status", "Count", "Last", "", "", ""]
    ):
        col.markdown(f"**{label}**")
    st.markdown(
        '<hr style="margin:4px 0;border:none;border-top:1px solid #bbb;" />',
        unsafe_allow_html=True,
    )
    subset = subset.copy()
    subset["_order"] = subset["status"].map(STATUS_ORDER).fillna(99)
    subset = subset.sort_values(["_order", "name"])
    for _, row in subset.iterrows():
        _render_row(row)


df = _load()

if df.empty:
    st.info(
        "No training items yet. Run `python seed_trainings.py` once to seed the "
        "starter curriculum, or add an item below."
    )
else:
    categories = sorted(df["category"].unique().tolist())
    for cat in categories:
        st.subheader(cat or "Uncategorized")
        _render_category(df[df["category"] == cat])

# --- Add item ---
with st.expander("Add training item", expanded=False):
    existing_cats = sorted(df["category"].unique().tolist()) if not df.empty else []
    with st.form("add_training", clear_on_submit=True):
        new_name = st.text_input("Name", key="new_train_name")
        if existing_cats:
            cat_choice = st.selectbox(
                "Category (existing)",
                options=["— new —"] + existing_cats,
                key="new_train_cat_choice",
            )
        else:
            cat_choice = "— new —"
        new_cat_text = st.text_input(
            "New category (leave blank to use selected above)",
            key="new_train_cat_text",
        )
        new_notes = st.text_area("Notes (optional)", key="new_train_notes")
        submitted = st.form_submit_button("Add")
    if submitted:
        final_cat = new_cat_text.strip() or (cat_choice if cat_choice != "— new —" else "")
        if not new_name.strip():
            st.warning("Please enter a name.")
        elif not final_cat:
            st.warning("Please pick or enter a category.")
        else:
            add_training(
                training_id=str(uuid.uuid4()),
                name=new_name.strip(),
                category=final_cat,
                status="not_started",
                session_count=0,
                last_practiced="",
                notes=new_notes.strip(),
            )
            st.toast("Training added")
            st.rerun()
