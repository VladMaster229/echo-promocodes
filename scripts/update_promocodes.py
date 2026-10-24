
import json
import re
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

SOURCE = "https://www.pcgamesn.com/wuthering-waves/codes"
DATA_FILE = Path("promocodes.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ECHO-PromoCodes/1.0)",
    "Accept-Language": "en-US,en;q=0.9",
}

CODE_PATTERN = re.compile(r"^[A-Z0-9]{6,24}$")

# Words that must never become promo codes.
BLOCKED = {
    "WUTHERINGWAVES",
    "WUTHERING",
    "ASTRITE",
    "RESONANCE",
    "SHELLCREDITS",
    "REDEEM",
    "REWARDS",
    "EXPIRED",
    "CODES",
    "ECHO",
}


class PromoParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1
            return

        if self.skip:
            return

        if tag == "tr":
            self.row = []

        elif tag in ("td", "th") and self.row is not None:
            self.cell = []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.skip = max(0, self.skip - 1)
            return

        if self.skip:
            return

        if tag in ("td", "th") and self.cell is not None:
            value = " ".join(" ".join(self.cell).split())
            self.row.append(value)
            self.cell = None

        elif tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if not self.skip and self.cell is not None:
            self.cell.append(data)


def fetch_candidates():
    request = urllib.request.Request(SOURCE, headers=HEADERS)

    with urllib.request.urlopen(request, timeout=20) as response:
        html = response.read().decode("utf-8", errors="replace")

    parser = PromoParser()
    parser.feed(html)

    candidates = {}

    for row in parser.rows:
        if len(row) < 2:
            continue

        code = row[0].strip().upper()
        rewards = row[1].strip()

        if not CODE_PATTERN.fullmatch(code):
            continue

        if code in BLOCKED:
            continue

        if not rewards or len(rewards) > 250:
            continue

        candidates[code] = {
            "code": code,
            "rewards": rewards,
        }

    return candidates


def main():
    try:
        candidates = fetch_candidates()
    except Exception as error:
        print(f"Source unavailable: {error}")
        return

    print(f"Candidates found: {len(candidates)}")

    for code in candidates:
        print(f"Candidate: {code}")

    # New candidates are logged, not published automatically.
    # This prevents a website layout change from publishing fake codes.
    if not candidates:
        print("No candidates found. Existing data unchanged.")
        return

    if DATA_FILE.exists():
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    else:
        data = {"updatedAt": None, "codes": []}

    existing = {
        item["code"].upper()
        for item in data.get("codes", [])
        if isinstance(item, dict)
        and isinstance(item.get("code"), str)
    }

    new_codes = sorted(set(candidates) - existing)

    if new_codes:
        print("New candidates require review:")
        for code in new_codes:
            print(f"REVIEW: {code}")
    else:
        print("No new candidates.")

    print("promocodes.json unchanged for safety.")


if __name__ == "__main__":
    main()
