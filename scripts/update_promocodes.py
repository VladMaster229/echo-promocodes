
import json
import re
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

DATA_FILE = Path("promocodes.json")

SOURCE = "https://www.pcgamesn.com/wuthering-waves/codes"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ECHO-PromoCodes/1.0)",
    "Accept-Language": "en-US,en;q=0.9",
}

# Only Latin letters and digits, without spaces.
CODE_PATTERN = re.compile(r"[A-Z0-9]{6,24}", re.ASCII)

BLOCKED_CODES = {"ECHO-TEST-ONLY"}

# First approved candidate from our diagnostic run.
# Additional codes will be reviewed before publication.
APPROVED_CODES = {"WUTHERINGGIFT"}


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1
        elif self.skip == 0:
            if tag == "tr":
                self.row = []
            elif tag in ("td", "th") and self.row is not None:
                self.cell = []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.skip = max(0, self.skip - 1)
        elif self.skip == 0:
            if tag in ("td", "th") and self.cell is not None:
                value = " ".join(" ".join(self.cell).split())
                self.row.append(value)
                self.cell = None
            elif tag == "tr" and self.row is not None:
                if self.row:
                    self.rows.append(self.row)
                self.row = None

    def handle_data(self, data):
        if self.skip == 0 and self.cell is not None:
            self.cell.append(data)


def fetch_codes():
    request = urllib.request.Request(SOURCE, headers=HEADERS)

    with urllib.request.urlopen(request, timeout=20) as response:
        page = response.read().decode("utf-8", errors="replace")

    parser = TableParser()
    parser.feed(page)

    results = {}

    for row in parser.rows:
        if len(row) < 2:
            continue

        code = row[0].strip().upper()
        rewards = row[1].strip()

        if not CODE_PATTERN.fullmatch(code):
            continue

        if code in BLOCKED_CODES:
            continue

        if code not in APPROVED_CODES:
            print(f"Candidate needs review: {code}")
            continue

        if not rewards:
            continue

        results[code] = {
            "code": code,
            "rewards": rewards[:250],
        }

    return results


def main():
    try:
        discovered = fetch_codes()
    except Exception as error:
        print(f"Source unavailable: {error}")
        return

    print(f"Approved codes found: {len(discovered)}")

    for code in discovered:
        print(f"Found: {code}")

    if DATA_FILE.exists():
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    else:
        data = {"updatedAt": None, "codes": []}

    existing = {
        item["code"].upper(): item
        for item in data.get("codes", [])
        if isinstance(item, dict)
        and isinstance(item.get("code"), str)
        and CODE_PATTERN.fullmatch(item["code"].upper())
        and item["code"].upper() in APPROVED_CODES
    }

    changed = False

    for code, item in discovered.items():
        if code not in existing:
            existing[code] = item
            changed = True

    # Remove invalid or test entries if any remain.
    if len(existing) != len(data.get("codes", [])):
        changed = True

    if not changed:
        print("No changes.")
        return

    result = {
        "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "codes": list(existing.values()),
    }

    DATA_FILE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Saved {len(existing)} approved codes.")


if __name__ == "__main__":
    main()
