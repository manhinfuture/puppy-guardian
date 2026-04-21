"""
One-shot script to seed the Trainings tab with the starter curriculum.

Creates the Trainings tab if missing, writes headers, and inserts one row
per item in STARTER_CURRICULUM. Safe to run once; do not re-run — it will
duplicate rows.

Run from the project root:
    python seed_trainings.py
"""

import uuid

import gspread
from google.oauth2.service_account import Credentials

from config import STARTER_CURRICULUM, TRAININGS_HEADER, TRAININGS_TAB, SHEET_ID

SERVICE_ACCOUNT_FILE = "puppy-guardian-6af8197614d3.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def main() -> None:
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    sh = client.open_by_key(SHEET_ID)

    try:
        ws = sh.worksheet(TRAININGS_TAB)
        print(f"Tab '{TRAININGS_TAB}' already exists.")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(
            title=TRAININGS_TAB, rows=100, cols=len(TRAININGS_HEADER)
        )
        ws.append_row(TRAININGS_HEADER)
        print(f"Created tab '{TRAININGS_TAB}' with headers.")

    existing = ws.get_all_records()
    if existing:
        print(
            f"Tab already has {len(existing)} rows — refusing to seed. "
            "Delete rows manually if you want a clean seed."
        )
        return

    rows = []
    for item in STARTER_CURRICULUM:
        rows.append(
            [
                str(uuid.uuid4()),
                item["name"],
                item["category"],
                "not_started",
                0,
                "",
                "",
            ]
        )
    ws.append_rows(rows)
    print(f"Seeded {len(rows)} training items.")


if __name__ == "__main__":
    main()
