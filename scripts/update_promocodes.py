
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

# Temporary allowlist for testing the complete system.
APPROVED_CODES = {"WUTHERINGGIFT"}


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

    def get_text(self):
        return " ".join(self.parts)


def fetch_page_text():
    request = urllib.request.Request(SOURCE, headers=HEADERS)

    with urllib.request.urlopen(request, timeout=20) as response:
        page = response.read().decode("utf-8", errors="replace")

    parser = TextParser()
    parser.feed(page)

    return parser.get_text()


def main():
    try:
        text = fetch_page_text()
    except Exception as error:
        print(f"Source unavailable: {error}")
        return

    found = []

    for code in sorted(APPROVED_CODES):
        pattern = rf"(?<![A-Za-z0-9]){re.escape(code)}(?![A-Za-z0-9])"

        if re.search(pattern, text, re.IGNORECASE):
            found.append(code)
            print(f"Found approved code: {code}")

    print(f"Approved codes found: {len(found)}")

    if not found:
        print("No approved codes found. Existing data unchanged.")
        return

    if DATA_FILE.exists():
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    else:
        data = {"updatedAt": None, "codes": []}

    existing = {
        item["code"].upper(): item
        for item in data.get("codes", [])
        if isinstance(item, dict)
        and isinstance(item.get("code"), str)
        and item["code"].upper() in APPROVED_CODES
    }

    changed = False

    for code in found:
        if code not in existing:
            existing[code] = {
                "code": code,
                "rewards": "Найден на PCGamesN — работоспособность не подтверждена",
            }
            changed = True

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
