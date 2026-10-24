
import html
import re
import urllib.request
from html.parser import HTMLParser

SOURCES = [
    "https://www.pcgamesn.com/wuthering-waves/codes",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ECHO-PromoCodes/1.0)"
}


class PageTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1
        elif tag in ("p", "li", "h2", "h3", "h4", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.skip = max(0, self.skip - 1)
        elif tag in ("p", "li", "h2", "h3", "h4", "tr"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def inspect_source(url):
    request = urllib.request.Request(url, headers=HEADERS)

    with urllib.request.urlopen(request, timeout=20) as response:
        page = response.read().decode("utf-8", errors="replace")

    parser = PageTextParser()
    parser.feed(page)

    text = html.unescape(" ".join(parser.parts))
    lines = [
        " ".join(line.split())
        for line in text.splitlines()
    ]

    lines = [line for line in lines if line]

    keywords = (
        "code",
        "redeem",
        "reward",
        "active",
        "expired",
        "wuthering",
    )

    matches = [
        line for line in lines
        if any(word in line.lower() for word in keywords)
    ]

    print(f"Source: {url}")
    print(f"HTML size: {len(page)} characters")
    print(f"Text lines: {len(lines)}")
    print(f"Relevant lines: {len(matches)}")

    for line in matches[:30]:
        print("PAGE:", line[:250])

    print("Diagnostic only: promocodes.json unchanged.")


def main():
    for source in SOURCES:
        try:
            inspect_source(source)
        except Exception as error:
            print(f"Source unavailable: {source}: {error}")


if __name__ == "__main__":
    main()
