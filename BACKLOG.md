# Puppy Guardian — Backlog

This file captures ideas and features that are **not** part of the current MVP but shouldn't be forgotten.

**Rules for this file:**
- Anything can be added at any time. No idea is too big or too small.
- Items stay here until they're promoted to `PLAN.md` (meaning: we're about to build them).
- This file is **not** a roadmap. There's no commitment to build any of it.
- The AI should read this file before making structural decisions, so it doesn't write code that *unnecessarily* blocks a listed idea. But the AI should **not** pre-build flexibility for anything here — just avoid painting into a corner.

## Near-term candidates (likely to promote within a few months)

- **Dark mode / mobile polish** — the default Streamlit look may feel cramped on phones. Worth a pass once daily use confirms phone is the primary surface.
- **Reminders / nudges** — "last poop was 10 hours ago" push notification. Unclear whether this requires leaving Streamlit or can be done via email / Telegram / Twilio.
- **Per-puppy support** — if a second dog joins the household, need a `puppy_name` column and filter. Schema already anticipates this.
- **Vet records attachment** — upload PDFs of vaccination records, vet visit notes. Likely lives as a Google Drive folder linked from the app rather than inside the Sheet.
- **Weekly summary email** — automated digest: total events, any anomalies, sent to both users every Sunday.
- **Daily meal grams vs. target** — bar chart of daily `amount_grams` sum with a target line, to answer "did she hit her ration today?" Promote when the vet gives a concrete grams/day target.
- **Configurable default meal grams** — when selecting `meal` in the log form, prefill the amount field with a user-set default (rather than 0). Default must be editable from the UI and persist across sessions. Requires a new `Settings` tab in the Google Sheet (key/value), moving the event-type selectbox outside the form so it triggers a rerun on change, and a small settings expander for editing the default. Deferred because the storage + reactive-form plumbing is disproportionate for the current pain; revisit if manual meal-gram entry remains a daily friction point after the Phase 4 soak.

## Medium-term (requires real design work)

- **AI-driven camera detection** — Reolink E1 Zoom 4K feed → YOLOv8-pose → event auto-logged with `logged_by: ai`. Requires always-on host, which means rethinking hosting. Validate the detection pipeline in a Jupyter notebook with 20 recorded clips *before* committing to this feature.
  - References: [calebolson123/DogPoopDetector](https://github.com/calebolson123/DogPoopDetector), [ReolinkCameraAPI/reolinkapipy](https://github.com/ReolinkCameraAPI/reolinkapipy), [Ultralytics Dog-Pose](https://docs.ultralytics.com/datasets/pose/dog-pose/)
- **Keyframe images attached to events** — once the camera exists, AI-detected events should include a snapshot. Storage likely Google Drive folder, referenced by URL in the Sheet.
- **LLM scoring / categorization** — e.g. "was this stool normal?" via a vision LLM. Model-agnostic wrapper (OpenAI / Anthropic / Gemini / local Ollama) so we can swap.
- **Bristol stool scale scoring** — reality check needed: keyframes capture the dog, not the stool itself. May require a second ground-level camera or be dropped entirely. Don't build without validating feasibility.
- **Richer charts / health trends** — stool consistency trend, meal-to-poop time distribution. (Weight tracking shipped manually in Phase 3 — smart-scale automation is still backlogged as a future enhancement.)
- **Smart-scale weight automation** — push weight readings from a WiFi-connected pet scale directly into the Sheet, removing manual entry. Only worth it if manual logging becomes a chore.
- **SQLite or Postgres storage** — only if Google Sheets hits a performance or query limit, which is many thousands of events away.

## Longer-term / speculative

- **Drag-drop widget dashboard** — Next.js + `react-grid-layout` + TypeScript, phone-home-screen feel. Worth considering only if Streamlit's layout becomes a real limitation *and* we decide to invest in a polished UI.
- **Life Dashboard unification** — merge with FinBoard (the user's existing finance app at `/Users/jethrotsa/Personal Dashboard Project/`). The two projects currently have different stacks on purpose. Unification likely means either (a) rebuilding FinBoard in the puppy app's stack, or (b) a thin top-level shell that embeds both. Revisit only after both projects are independently stable and loved.
- **Multi-household / share with friends** — currently scoped to two Google accounts. Opening up means real auth, permissions, privacy work.
- **Mobile app** — native iOS/Android. Probably unnecessary if the web app works well on phones.
- **Home Assistant integration** — if the user has a smart home setup, push events into it.
- **Local LLM option** — run scoring on a local model (Ollama) instead of hitted hosted APIs. Privacy + cost driver.
- **NAS / self-hosted deployment** — move off Streamlit Cloud to user's own hardware. Only worth it if cloud hosting becomes a real blocker.

## Explicitly NOT doing

- Building proprietary ML models from scratch. Always prefer pretrained models + fine-tuning.
- Proprietary camera integrations beyond Reolink.
- Anything purely cosmetic before the product is proven useful.

---

**How to use this file:**
- Add ideas freely as they occur
- When planning the next phase, re-read this file to see what's bubbling up
- To promote something: copy the item into `PLAN.md` as a new phase, delete it from here
