import json
from typing import Optional

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

from config import (
    EVENTS_TAB,
    OBSERVATIONS_HEADER,
    OBSERVATIONS_TAB,
    SHEET_ID,
)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


@st.cache_resource
def _get_spreadsheet():
    sa_info = json.loads(st.secrets["gcp_service_account_json"])
    creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)


@st.cache_resource
def _get_worksheet():
    return _get_spreadsheet().worksheet(EVENTS_TAB)


@st.cache_resource
def _get_observations_ws():
    sh = _get_spreadsheet()
    try:
        ws = sh.worksheet(OBSERVATIONS_TAB)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=OBSERVATIONS_TAB, rows=100, cols=len(OBSERVATIONS_HEADER))
        ws.append_row(OBSERVATIONS_HEADER)
    return ws


def append_event(
    event_id: str,
    timestamp: str,
    event_type: str,
    amount_grams: str,
    location_correct: str,
    notes: str,
) -> None:
    ws = _get_worksheet()
    ws.append_row(
        [event_id, timestamp, event_type, amount_grams, location_correct, notes]
    )


def read_all_events() -> pd.DataFrame:
    ws = _get_worksheet()
    records = ws.get_all_records()
    return pd.DataFrame(records)


def _find_row_number(ws, event_id: str) -> Optional[int]:
    cell = ws.find(event_id, in_column=1)
    return cell.row if cell else None


def update_event(
    event_id: str,
    timestamp: str,
    event_type: str,
    amount_grams: str,
    location_correct: str,
    notes: str,
) -> bool:
    ws = _get_worksheet()
    row = _find_row_number(ws, event_id)
    if row is None:
        return False
    ws.update(
        f"A{row}:F{row}",
        [[event_id, timestamp, event_type, amount_grams, location_correct, notes]],
    )
    return True


def delete_event(event_id: str) -> bool:
    ws = _get_worksheet()
    row = _find_row_number(ws, event_id)
    if row is None:
        return False
    ws.delete_rows(row)
    return True


# --- Observations ---

def read_observations() -> pd.DataFrame:
    ws = _get_observations_ws()
    records = ws.get_all_records()
    return pd.DataFrame(records)


def add_observation(observation_id: str, date_str: str, notes: str, resolved: str = "") -> None:
    ws = _get_observations_ws()
    ws.append_row([observation_id, date_str, notes, resolved])


def update_observation(observation_id: str, date_str: str, notes: str, resolved: str) -> bool:
    ws = _get_observations_ws()
    row = _find_row_number(ws, observation_id)
    if row is None:
        return False
    ws.update(
        f"A{row}:D{row}",
        [[observation_id, date_str, notes, resolved]],
    )
    return True


def delete_observation(observation_id: str) -> bool:
    ws = _get_observations_ws()
    row = _find_row_number(ws, observation_id)
    if row is None:
        return False
    ws.delete_rows(row)
    return True
