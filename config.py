from datetime import date

SHEET_ID = "1fPaDbihVcgHxBuFMwi6Z7OJ3Ju6M1ioOksKkyFahtco"
EVENTS_TAB = "Events"
EVENT_TYPES = ["pee", "poop", "meal", "medicine", "weight"]
HEADER = ["event_id", "timestamp", "event_type", "amount_grams", "location_correct", "notes"]
TIMEZONE = "America/Los_Angeles"

OBSERVATIONS_TAB = "Observations"
OBSERVATIONS_HEADER = ["observation_id", "date", "notes", "resolved"]

TRAININGS_TAB = "Trainings"
TRAININGS_HEADER = [
    "training_id",
    "name",
    "category",
    "status",
    "session_count",
    "last_practiced",
    "notes",
]
TRAINING_STATUSES = ["not_started", "practicing", "reliable"]
STARTER_CURRICULUM = [
    {"name": "Name recognition (look at me)", "category": "Foundation"},
    {"name": "Sit", "category": "Obedience"},
    {"name": "Down", "category": "Obedience"},
    {"name": "Stay", "category": "Obedience"},
    {"name": "Come (recall)", "category": "Obedience"},
    {"name": "Leave it", "category": "Manners"},
    {"name": "Drop it", "category": "Manners"},
    {"name": "Loose-leash walking", "category": "Manners"},
    {"name": "Crate / place / settle", "category": "Manners"},
    {"name": "Bite inhibition (no nipping)", "category": "Manners"},
]

PUPPY = {
    "name": "Ichi",
    "breed": "Shiba Inu",
    "sex": "female",
    "date_of_birth": date(2026, 2, 6),
    "photo_path": "assets/ichi.jpeg",
}
