
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

SOURCE = "https://www.pcgamesn.com/wuthering-waves/codes"
DATA_FILE = Path("promocodes.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ECHO-PromoCodes/1.0)",
    "Accept-Language": "en-US,en;q=0.9",
}

CODE_PATTERN = re.compile(r"^[A-Z0-9]{6,24}$")

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


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1
        elif not self.skip and tag in (
            "p", "li", "h2", "h3", "h4", "tr", "br"
        ):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.skip = max(0, self.skip - 1)
        elif not self.skip and tag in (
            "p", "li", "h2", "h3", "h4", "tr"
        ):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

    def get_lines(self):
        text = "".join(self.parts)
        return [
            " ".join(line.split())
            for line in text.splitlines()
            if line.strip()
        ]


def fetch_lines():
    request = urllib.request.Request(SOURCE, headers=HEADERS)

    with urllib.request.urlopen(request, timeout=20) as response:
        html = response.read().decode("utf-8", errors="replace")

    parser = PageParser()
    parser.feed(html)
    return parser.get_lines()


def find_candidates(lines):
    candidates = set()
    in_active_section = False

    for line in lines:
        lower = line.lower()

        if (
            "active wuthering waves codes" in lower
            or "latest wuthering waves codes" in lower
            or "here are all the active" in lower
        ):
            in_active_section = True
            continue

        if not in_active_section:
            continue

        if (
            "expired codes" in lower
            or "how to redeem" in lower
            or "how do i redeem" in lower
        ):
            break

        # A code must appear at the beginning of a list entry.
        match = re.match(
            r"^([A-Za-z0-9]{6,24})(?=\s|:|–|—|-|$)",
            line,
        )

        if not match:
            continue

        code = match.group(1).upper()

        if CODE_PATTERN.fullmatch(code) and code not in BLOCKED:
            candidates.add(code)

    return sorted(candidates)


def main():
    try:
        lines = fetch_lines()
    except Exception as error:
        print(f"Source unavailable: {error}")
        return

    print(f"Page lines: {len(lines)}")

    candidates = find_candidates(lines)

    print(f"Candidates found: {len(candidates)}")

    for code in candidates:
        print(f"REVIEW: {code}")

    if not candidates:
        print("No candidates. Showing relevant page lines:")

        for line in lines:
            lower = line.lower()
            if (
                "code" in lower
                or "wutheringgift" in lower
            ):
                print("PAGE:", line[:200])

    print("promocodes.json unchanged for safety.")


if __name__ == "__main__":
    main()
