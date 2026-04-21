from datetime import date

SHEET_ID = "1fPaDbihVcgHxBuFMwi6Z7OJ3Ju6M1ioOksKkyFahtco"
EVENTS_TAB = "Events"
EVENT_TYPES = ["pee", "poop", "meal", "medicine", "weight"]
HEADER = ["event_id", "timestamp", "event_type", "amount_grams", "location_correct", "notes"]
TIMEZONE = "America/Los_Angeles"

OBSERVATIONS_TAB = "Observations"
OBSERVATIONS_HEADER = ["observation_id", "date", "notes", "resolved"]

PUPPY = {
    "name": "Ichi",
    "breed": "Shiba Inu",
    "sex": "female",
    "date_of_birth": date(2026, 2, 6),
    "photo_path": "assets/ichi.jpeg",
}
