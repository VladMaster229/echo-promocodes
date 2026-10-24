import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from html import unescape

DATA_FILE = Path("promocodes.json")

# Public community-maintained Wuthering Waves code list
SOURCES = [
    "https://www.pcgamesn.com/wuthering-waves/codes",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ECHO-PromoCodes/1.0)"
}

# Only accept code-like strings from HTML code elements.
CODE_PATTERN = re.compile(r"^[A-Z0-9]{5,24}$")


def fetch_codes(url):
    request = urllib.request.Request(url, headers=HEADERS)

    with urllib.request.urlopen(request, timeout=20) as response:
        html = response.read().decode("utf-8", errors="replace")

    candidates = re.findall(
        r"<code\b[^>]*>(.*?)</code>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    found = set()

    for candidate in candidates:
        value = unescape(re.sub(r"<[^>]+>", "", candidate)).strip().upper()

        if CODE_PATTERN.fullmatch(value):
            found.add(value)

    return found


def main():
    existing = {"updatedAt": None, "codes": []}

    if DATA_FILE.exists():
        existing = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    known = {
        item["code"].upper(): item
        for item in existing.get("codes", [])
        if isinstance(item, dict) and isinstance(item.get("code"), str)
    }

    discovered = set()
    successful_sources = 0

    for source in SOURCES:
        try:
            codes = fetch_codes(source)
            discovered.update(codes)
            successful_sources += 1
            print(f"{source}: found {len(codes)} candidates")
        except Exception as error:
            print(f"Source unavailable: {source}: {error}")

    if successful_sources == 0:
        print("No sources available. Keeping existing data.")
        return

    new_codes = discovered - set(known)

    for code in sorted(new_codes):
        known[code] = {
            "code": code,
            "rewards": "Найден в публичном источнике — не проверен",
        }

    if not new_codes:
        print("No new codes.")
        return

    result = {
        "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "codes": list(known.values()),
    }

    DATA_FILE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Added {len(new_codes)} new candidate codes.")


if __name__ == "__main__":
    main()
