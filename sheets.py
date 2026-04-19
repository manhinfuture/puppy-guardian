import json

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

from config import EVENTS_TAB, SHEET_ID

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


@st.cache_resource
def _get_worksheet():
    sa_info = json.loads(st.secrets["gcp_service_account_json"])
    creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet(EVENTS_TAB)


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
