"""
One-time script: parses the historical Apple Notes log and writes it into the
Google Sheet. Clears any existing rows (including test rows) and rewrites the
header to match the new 6-column schema.

Run once from the project root:
    python import_history.py

After it prints the summary, open the Sheet to spot-check.
"""

import json
import re
import uuid
from datetime import datetime

import gspread
import toml
from google.oauth2.service_account import Credentials

from config import EVENTS_TAB, HEADER, SHEET_ID

YEAR = 2026
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

RAW_NOTES = r"""
ichi daily log
4/18
7:39 尿1次
8:10 吃饭 16g
8:18 屎1次（✅ 1+0.5 = 1.5条）
10:53 尿1次
12:45 吃饭 16g
12:50 尿1次
13:11 屎1次（✅0.2+0.1*3+0.2 = 0.7条 其中0.2❌）
15:22 尿1次
16:43 尿1次
16:47 吃饭 16g
17:00 尿1次
17:48 尿1次
20:23 尿1次
20:30 吃饭16g
21:08 屎1次（❌ 1+0.3+0.1*2 = 1.5条）

4/17（中午12点撤playpen）
7:50 尿1次
8:22 吃饭16g
8:35 屎1次（✅1.1+0.1+0.2= 1.4条）
10:58 尿1次
12:51 尿1次
12:59 吃饭16g
15:05 尿1次
16:45 吃饭 16g
17:00 尿1次
19:50 尿1次
20:12 吃饭 16g
20:30 尿1次
20:40 屎1次
23:13 尿1次

4/16
8:00 尿1次
8:13 屎1次（✅1+0.5+0.3 = 1.8条）
8:46 吃饭16g
11:06 尿1次
13:17 尿1次
13:20 吃饭16g
13:31 屎1次（✅0.25+0.25+0.25+0.5 = 1.25条）
13:51 尿1次
15:50 尿1次
17:08 吃饭16g
17:14 尿1次
19:12 尿1次
20:54 尿1次
20:56 吃饭16g
21:39 尿1点+屎1次（✅0.2+0.25+1条）
23:29 尿1次 尿1次

4/15
7:40 尿1次
7:53 吃饭16g
08:02 屎1次 （0.3条❌ +1.2+0.1 ✅ = 1.6条）
10:10 尿1次
12:29 尿1次
12:32 吃饭16g
15:06 尿1次
16:48 吃饭16g
17:09 尿1次
20:18 尿1次
20:30 吃饭16g
20:52 屎1次（0.3+0.3 ✅+0.3❌=0.9）
23:25 尿1次

4/14
8:10 尿1次
8:14 吃饭 16g
10:59 尿1次
12:34 尿1次
12:35 吃饭 16g
12:47 屎1次（❌1.6条）
13:06 尿1次
15:15 尿1次
16:40 吃饭 16g
16:50 尿1次（❌）
17:20 尿1次（❌）
20:05 尿1次
20:29 吃饭16g
21:05 尿1次
21:07 屎1次
23:12 尿1次

4月13日
8:23 尿1次
8:27 吃饭16g
8:39 屎1次（✅ 1.8条+1颗）
12:07 尿1次
12:10 吃饭16g
12:39 尿1次
15:00 尿1次
15:39 屎1次（✅1.5条 可捏）
16:52 吃饭14g
16:57 尿1次
17:18 尿1次
19:28 尿1次
20:50 吃饭16g
21:08 尿1次
23:43 尿1次
00:06 屎1次（✅1.5条 可捏）

3月21日
17:00 吃饭
20:50 拉屎

3月22日
7:00 尿2次
7:30 吃饭
11:23 尿1次
12:00 吃饭
12:27 拉屎
16:30 尿1次
17:30 吃饭
19:40 尿1次
22:40 尿1次
02:50 尿1次

3月23日
7:30 吃饭
7:50 尿1次
12:50 吃饭
13:18 尿1次
13:42 拉屎
18:40 尿1次
19:30 吃饭
22:15 尿1次

3月24日
7:30 尿1次
7:50 吃饭
11:25 尿1次
12:15 吃饭
13:15 拉屎
16:15 尿1次
18:30 尿1次
19:30 尿1次
19:31 吃饭
22:00 拉稀

3月25日
04:40 拉了1次
06:30 尿1次
10:45 尿1次
12:30 吃饭
17:30 尿1次
19:30 吃饭
22:30 尿1次

3月26日
7:10 尿1次
7:30 吃饭
12:10 尿1次
12:25 吃饭
15:40 尿1次
19:10 吃饭
20:40 尿1次
22:30 尿1次

3月27日
7:00 尿1次
7:10 屎1次
7:15 吃饭
10:50 尿1次
12:20 吃饭
14:46 尿1次
19:10 尿1次
19:15 吃饭
22:45 尿1次

3月28日
6:00 尿1次
7:40 吃饭
8:00 屎1次
12:10 尿1次
12:15 吃饭 6g老粮 1g新粮
16:06 尿1次
19:20 吃饭 5g老粮 2g新粮
19:49 尿1次
23:10 尿1次
23:25 屎1次

3月29日
6:30 尿1次
7:45 吃饭 5g老粮 2g新粮
8:10 屎1次
10:52 尿1次
12:30 吃饭 5g老粮 2g新粮
14:55 尿1次
19:10 吃饭 5g老粮 2g新粮
20:25 尿1次
23:15 尿1次

3月30日
7:30 尿1次
7:31 吃饭 5g老粮 2g新粮
7:45 屎1次（错位子）
12:02 吃饭 5g老粮 2g新粮
12:22 尿1次
16:36 尿1次
19:15 吃饭 5g老粮 2g新粮
19:50 尿1次
00:00 尿1次
00:20 屎1次（✅对位子）

3月31日
7:35 尿1次
7:36 吃饭 4g老粮 3g新粮
12:20 尿1次
12:22 吃饭 4g老粮 3g新粮
17:20 尿1次
19:30 吃饭 4g老粮 3g新粮
21:53 尿1次

4月1日
7:20 尿1次
7:25 吃饭 4g老粮 3g新粮
8:00 屎1次（错位子）
12:20 吃饭 4g老粮 4g新粮
12:50 尿1次
14:58 尿1次
17:05 尿1次
19:25 吃饭 4g老粮 4g新粮
19:55 尿1次
21:20 尿1次
21:25 屎1次（错位子）

4月2日
7:25 尿1次
7:32 吃饭 4g老粮 4g新粮
7:33 2ml albon day1
10:53 尿1次
12:43 吃饭 4g老粮 4g新粮
13:10 尿1次
13:50 屎1次（错位子）
15:40 尿1次
17:40 尿1次
19:25 吃饭 4g老粮 6g新粮
19:50 尿1次
23:23 尿1次

4月3日
7:30 尿1次
7:40 吃饭 4g老粮 6g新粮
7:41 1ml albon day2
8:05 屎1次（错位子）
10:28 尿1次
12:25 吃饭 4g老粮 6g新粮
12:58 尿1次
17:15 尿1次
19:25 吃饭 4g老粮 6g新粮
21:16 尿1次
00:11 尿1次
00:40 屎1次（错位子）

4月4日
7:15 尿1次（✅playpen 尿板里）
7:30 吃饭 3.5g老粮 6.5g新粮
7:31 1ml albon day3
11:45 尿1次
12:03 吃饭 3.1g老粮 6.9g新粮
12:50 屎1次（✅对位子）
15:40 尿1次
17:50 尿1次
19:25 吃饭 2g老粮 8g新粮
19:50 尿1次
00:16 尿1次
00:55 屎1次（错位子）

4月5日
7:40 尿1次（✅playpen 尿板里）
8:00 尿1次
8:05 吃饭 10g新粮
8:06 1ml albon day4
8:55 屎1次（错位子）
11:20 尿1次
13:10 吃饭 1g老粮 9g新粮
13:50 尿1次
16:20 尿1次
19:25 吃饭 1g老粮 9g新粮
19:53 尿1次
21:02 尿1次
23:20 尿1次

4月6日
7:12 尿1次
7:20 1ml albon day5
7:30 吃饭 1g老粮 9g新粮
7:53 屎1次（✅对位子 2条）
10:21 尿1次
12:20 吃饭 1g老粮 9g新粮
12:46 尿1次
15:58 尿1次
17:29 吃饭 12g新粮
17:49 尿1次
20:40 吃饭 12g新粮
21:15 尿1次
21:29 屎1次（完整1条）
22:05 尿1次
00:11 尿1次

4月7日
7:06 尿1次
7:11 1ml albon day6
7:20 吃饭 16g新粮
7:37 屎1次（❌pee pad边缘外面 3中等条）
10:06 尿1次
12:30 吃饭 16g新粮
12:56 尿1次
16:31 尿1次
16:32 吃饭 12g新粮
19:50 尿1次
20:20 吃饭 14g新粮
21:02 尿1次
21:05 屎1次（✅基本在pee pad里 1.5条）
23:53 尿1次

4月8日
6:40 尿1次
7:20 1ml albon day7
7:25 吃饭 16g新粮
7:57 屎1次（❌错位子 1.5条 干）
11:01 尿1次
12:28 吃饭 16g新粮
12:46 尿1次
16:27 吃饭 15g新粮
16:35 尿1次
16:49 屎1次（✅pee pad上 1.5条 干）
19:50 尿1次
20:00 吃饭 15g新粮
20:55 尿1次（❌尿错）
22:40 尿1次
23:10 屎1次（2条小小的干干的）

4月9日
5:45 尿1次
6:30 1ml albon day8
6:35 吃饭 18g
9:15 尿1次
11:34 尿1次
12:30 吃饭 18g
12:39 屎1次（✅peepad上 1.5条 干）
16:10 尿1次
16:30 吃饭 16g
18:05 屎1次（❌peepad旁边 1.5条 干）
20:30 尿1次
20:31 吃饭 16g
21:03 尿1次
00:12 尿1次

4月10日
6:10 尿1次
7:30 1ml albon day9
7:40 吃饭 18g
7:54 屎1次（✅pee pad上 1.5条 干）
11:00 尿1次
13:40 吃饭 18g
13:44 尿1次
15:41 尿1次
16:30 吃饭 16g
16:46 屎1次（❌pee pad边缘 干）
20:30 尿1次
20:40 吃饭 16g
21:26 屎1次（✅pee pad上 干）
00:10 尿1次

4月11日
7:38 尿1次
7:40 吃饭 18g
7:57 屎1次（1条+0.5条）
10:27 尿1次
12:25 吃饭 18g
12:35 尿1次
15:38 尿1次
16:30 吃饭 18g
16:49 尿1次
20:25 尿1次
20:30 吃饭 18g
21:00 屎1次（✅pee pad上 1.2条 硬）
23:49 尿1次
01:20 尿1次

4月12日
08:27 尿1次
08:33 吃饭 18g
08:45 屎1次（✅pee pad上 1.5条 偏硬）
09:05 尿1次
12:29 尿1次
12:48 吃饭 15g
13:28 尿1次
14:55 尿1次
16:32 吃饭 13g
16:48 尿1次
17:13 尿1次
20:24 尿1次
20:27 吃饭 13g
20:37 屎1次（✅pee pad上 1.5条 成型）
20:57 尿1次
23:45 尿1次
01:36 尿1次
"""

_DATE_SLASH = re.compile(r"^(\d{1,2})/(\d{1,2})(?:\(|\s|$)")
_DATE_CN = re.compile(r"^(\d{1,2})月(\d{1,2})日")
_TIME_LINE = re.compile(r"^(\d{1,2}):(\d{2})\s*(.*)$")
_GRAM = re.compile(r"(\d+(?:\.\d+)?)\s*g")
_PEE_COUNT = re.compile(r"尿\s*(\d+)\s*次")


def parse_date(line: str):
    m = _DATE_SLASH.match(line)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = _DATE_CN.match(line)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def location_from_text(text: str):
    has_good = "✅" in text or "对位子" in text or "pee pad上" in text or "peepad上" in text or "pee pad里" in text or "尿板里" in text
    has_bad = "❌" in text or "错位子" in text or "尿错" in text or "pee pad边缘" in text or "peepad旁" in text or "pee pad外" in text
    if has_good and not has_bad:
        return "yes"
    if has_bad and not has_good:
        return "no"
    if has_good and has_bad:
        # both present — treat summary ✅ as the outcome
        return "yes"
    return ""


def sum_grams(text: str) -> float:
    return sum(float(x) for x in _GRAM.findall(text))


def parse_event_segment(text: str):
    """Returns a list of (event_type, amount_grams, location_correct, notes)."""
    events = []
    notes_full = text.strip()

    # Medicine (albon)
    if "albon" in text.lower():
        events.append(("medicine", "", "", notes_full))
        return events

    # Meal
    if "吃饭" in text:
        grams = sum_grams(text)
        grams_str = str(grams) if grams > 0 else ""
        # strip "吃饭" prefix from notes for cleanliness
        note = re.sub(r"^吃饭\s*", "", notes_full).strip()
        events.append(("meal", grams_str, "", note))
        return events

    # Poop
    if "屎" in text or "拉屎" in text or "拉稀" in text or "拉了" in text:
        loc = location_from_text(text)
        note = notes_full
        if "拉稀" in text:
            note = (note + " | loose stool").strip(" |")
        events.append(("poop", "", loc, note))
        # Some lines have "屎1次+尿1次" — handle pee too if present
        if _PEE_COUNT.search(text) or "尿1点" in text:
            count_m = _PEE_COUNT.search(text)
            count = int(count_m.group(1)) if count_m else 1
            for _ in range(count):
                events.append(("pee", "", location_from_text(text), notes_full))
        return events

    # Pee (possibly multiple)
    if "尿" in text:
        m = _PEE_COUNT.search(text)
        count = int(m.group(1)) if m else 1
        loc = location_from_text(text)
        for _ in range(count):
            events.append(("pee", "", loc, notes_full))
        return events

    # Fallback — vomit or unknown
    if "吐" in text:
        events.append(("poop", "", "", (notes_full + " | vomit").strip(" |")))
        return events

    # Unknown — skip with a marker
    events.append(("unknown", "", "", notes_full))
    return events


def parse_notes(raw: str):
    rows = []
    warnings = []
    current_month = None
    current_day = None
    prev_hour = None  # used to detect date-rollover past midnight

    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith("ichi"):
            continue  # title lines

        date = parse_date(line)
        if date:
            current_month, current_day = date
            prev_hour = None
            continue

        m = _TIME_LINE.match(line)
        if not m or current_month is None:
            warnings.append(f"Skipped: {line}")
            continue

        hour, minute, rest = int(m.group(1)), int(m.group(2)), m.group(3)

        # Treat very-early-morning times as belonging to the next day
        # (e.g. "00:06" or "01:20" logged under the previous date's header)
        effective_month, effective_day = current_month, current_day
        if hour < 5 and prev_hour is not None and prev_hour >= 20:
            # rollover — add one day (simple: increment day, ignore month edge cases)
            try:
                next_dt = datetime(YEAR, current_month, current_day)
                next_dt = next_dt.replace(day=current_day + 1)
                effective_month, effective_day = next_dt.month, next_dt.day
            except ValueError:
                # end of month — let it fail safely, keep original date
                pass

        try:
            ts = datetime(YEAR, effective_month, effective_day, hour, minute, 0)
        except ValueError as e:
            warnings.append(f"Bad date for line: {line} ({e})")
            continue

        events = parse_event_segment(rest)
        for ev_type, grams, loc, note in events:
            if ev_type == "unknown":
                warnings.append(f"Unknown event @ {ts.isoformat()}: {rest}")
                continue
            rows.append(
                [
                    str(uuid.uuid4()),
                    ts.isoformat(timespec="seconds"),
                    ev_type,
                    grams,
                    loc,
                    note,
                ]
            )

        prev_hour = hour

    # Sort by timestamp so the Sheet reads chronologically
    rows.sort(key=lambda r: r[1])
    return rows, warnings


def get_worksheet():
    secrets = toml.load(".streamlit/secrets.toml")
    sa_info = json.loads(secrets["gcp_service_account_json"])
    creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet(EVENTS_TAB)


def main():
    rows, warnings = parse_notes(RAW_NOTES)
    print(f"Parsed {len(rows)} events.")
    counts = {}
    for r in rows:
        counts[r[2]] = counts.get(r[2], 0) + 1
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")
    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for w in warnings[:20]:
            print(f"  - {w}")

    confirm = input("\nClear the Sheet and import these rows? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Aborted.")
        return

    ws = get_worksheet()
    ws.clear()
    ws.update([HEADER] + rows, "A1")
    print(f"Done. Wrote {len(rows)} rows + header to '{EVENTS_TAB}'.")


if __name__ == "__main__":
    main()
