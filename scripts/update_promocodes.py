
import json
import re
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

DATA_FILE = Path("promocodes.json")

SOURCES = [
    "https://www.pcgamesn.com/wuthering-waves/codes",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ECHO-PromoCodes/1.0)"
}

CODE_PATTERN = re.compile(r"^[A-Z0-9]{6,24}$")

# Never publish our development test code.
BLOCKED_CODES = {"ECHO-TEST-ONLY"}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lines = []
        self.parts = []
        self.skip = 0

    def flush(self):
        text = " ".join(" ".join(self.parts).split())
        if text:
            self.lines.append(text)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1
        elif tag in ("p", "li", "h2", "h3", "h4", "tr"):
            self.flush()

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.skip = max(0, self.skip - 1)
        elif tag in ("p", "li", "h2", "h3", "h4", "tr"):
            self.flush()

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

    def finish(self):
        self.flush()
        return self.lines


def fetch_codes(url):
    request = urllib.request.Request(url, headers=HEADERS)

    with urllib.request.urlopen(request, timeout=20) as response:
        page = response.read().decode("utf-8", errors="replace")

    parser = PageParser()
    parser.feed(page)
    lines = parser.finish()

    active = False
    results = {}

    for line in lines:
        lower = line.lower()

        if "expired codes" in lower:
            active = False
            break

        if "here are all the active" in lower:
            active = True
            continue

        if not active:
            continue

        if lower.startswith("code rewards"):
            continue

        # Expected table row: CODE + reward description.
        match = re.match(
            r"^([A-Z0-9]{6,24})\s+(.+)$",
            line,
        )

        if not match:
            continue

        code = match.group(1).upper()
        rewards = match.group(2).strip()

        if code in BLOCKED_CODES:
            continue

        if not CODE_PATTERN.fullmatch(code):
            continue

        if len(rewards) > 250:
            continue

        results[code] = {
            "code": code,
            "rewards": rewards,
        }

    return results


def main():
    if DATA_FILE.exists():
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    else:
        data = {"updatedAt": None, "codes": []}

    known = {}

    for item in data.get("codes", []):
        if not isinstance(item, dict):
            continue

        code = str(item.get("code", "")).strip().upper()

        if not code or code in BLOCKED_CODES:
            continue

        known[code] = item

    original = {
        str(item.get("code", "")).strip().upper()
        for item in data.get("codes", [])
        if isinstance(item, dict)
    }

    discovered = {}

    for source in SOURCES:
        try:
            found = fetch_codes(source)
            discovered.update(found)
            print(f"{source}: found {len(found)} codes")
            for code in found:
                print(f"Found candidate: {code}")
        except Exception as error:
            print(f"Source unavailable: {source}: {error}")

    for code, item in discovered.items():
        if code not in known:
            known[code] = item

    if set(known) == original:
        print("No changes.")
        return

    result = {
        "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "codes": list(known.values()),
    }

    DATA_FILE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Saved {len(known)} codes.")


if __name__ == "__main__":
    main()
