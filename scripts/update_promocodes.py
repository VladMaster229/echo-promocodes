
import json
import re
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

SOURCE = "https://www.pcgamesn.com/wuthering-waves/codes"
OUTPUT = Path(__file__).resolve().parents[1] / "promocodes.json"

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
    "CODEREWARDS",
    "SENIOR",
    "UPDATED",
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
    request = urllib.request.Request(
        SOURCE,
        headers=HEADERS,
    )

    with urllib.request.urlopen(
        request,
        timeout=20,
    ) as response:
        html = response.read().decode(
            "utf-8",
            errors="replace",
        )

    parser = PageParser()
    parser.feed(html)

    return parser.get_lines()


def find_codes(lines):
    codes = []
    in_active_section = False
    section_found = False

    for line in lines:
        lower = line.lower()

        if (
            "active wuthering waves codes" in lower
            or "latest wuthering waves codes" in lower
            or "here are all the active" in lower
        ):
            in_active_section = True
            section_found = True
            continue

        if not in_active_section:
            continue

        if (
            "expired codes" in lower
            or "how to redeem" in lower
            or "how do i redeem" in lower
        ):
            break

        # Only accept a code attached to the site's
        # "Copy code" control.
        match = re.match(
            r"^([A-Za-z0-9]{6,24})\s+Copy\s+code(?=\d|\s|$)",
            line,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        code = match.group(1).upper()

        if (
            not CODE_PATTERN.fullmatch(code)
            or code in BLOCKED
        ):
            continue

        # Extract reward text after "Copy code".
        rewards_match = re.match(
            r"^[A-Za-z0-9]{6,24}\s*Copy\s+code\s*(.*)$",
            line,
            flags=re.IGNORECASE,
        )

        rewards = (
            rewards_match.group(1).strip()
            if rewards_match
            else ""
        )

        # The source may be outdated, so never
        # claim that a code is verified in-game.
        description = (
            f"{rewards} — источник PCGamesN, "
            "работоспособность не подтверждена"
            if rewards
            else "Источник PCGamesN — "
                 "работоспособность не подтверждена"
        )

        if not any(item["code"] == code for item in codes):
            codes.append({
                "code": code,
                "rewards": description,
            })

    return section_found, codes


def load_existing():
    if not OUTPUT.exists():
        return {"updatedAt": None, "codes": []}

    with OUTPUT.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if (
        not isinstance(data, dict)
        or not isinstance(data.get("codes"), list)
    ):
        raise ValueError("Invalid existing promocodes.json")

    return data


def main():
    try:
        lines = fetch_lines()
        print(f"Page lines: {len(lines)}")

        section_found, codes = find_codes(lines)

        if not section_found:
            print("Active codes section not found.")
            print("promocodes.json unchanged for safety.")
            return

        print(f"Codes found: {len(codes)}")

        for item in codes:
            print(f"FOUND: {item['code']}")

        if not codes:
            print("No reliable codes detected.")
            print("promocodes.json unchanged for safety.")
            return

        existing = load_existing()

        # Preserve previously published codes.
        # A source listing alone does not establish
        # that older codes have expired.
        merged = []
        known = set()

        for item in existing["codes"] + codes:
            if not isinstance(item, dict):
                continue

            code = item.get("code")

            if not isinstance(code, str):
                continue

            code = code.strip().upper()

            if (
                not CODE_PATTERN.fullmatch(code)
                or code in known
            ):
                continue

            known.add(code)
            merged.append({
                **item,
                "code": code,
            })

        # Replace descriptions for codes found
        # in the current source.
        fresh_by_code = {
            item["code"]: item
            for item in codes
        }

        merged = [
            fresh_by_code.get(item["code"], item)
            for item in merged
        ]

        if merged == existing["codes"]:
            print("No changes.")
            return

        updated = {
            **existing,
            "updatedAt": date.today().isoformat(),
            "codes": merged,
        }

        OUTPUT.write_text(
            json.dumps(
                updated,
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )

        print(f"Saved {len(merged)} codes.")

    except Exception as error:
        print(f"Update failed: {error}")
        print("promocodes.json unchanged for safety.")
        raise


if __name__ == "__main__":
    main()
