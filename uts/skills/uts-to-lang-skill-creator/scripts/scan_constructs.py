#!/usr/bin/env python3
"""Corpus construct scanner for UTS pseudocode.

Usage: scan_constructs.py <spec-clone>/uts/<module>

Prints the uppercase keywords and snake_case calls used in `pseudo` fences,
outside comments and string literals, with counts. Compare its output with the
construct catalogue; also use it to list the harness symbols the corpus uses.
"""
import collections, pathlib, re, sys


def main(argv):
    if len(argv) != 2 or not pathlib.Path(argv[1]).is_dir():
        print("usage: scan_constructs.py <spec-clone>/uts/<module>", file=sys.stderr)
        return 2
    root = pathlib.Path(argv[1])
    keywords, calls = collections.Counter(), collections.Counter()
    for path in root.rglob("*.md"):
        in_pseudo = False
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("```"):
                in_pseudo = (line.strip() == "```pseudo") if not in_pseudo else False
                continue
            if not in_pseudo or line.lstrip().startswith(("#", "//")):
                continue
            line = re.sub(r'"[^"]*"', '""', line)                 # ignore string literals
            line = re.split(r"\s(?:#|//)\s", line, maxsplit=1)[0]  # drop trailing comments
            keywords.update(re.findall(r"\b[A-Z][A-Z_]+\b", line))
            calls.update(re.findall(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\s*\(", line))
    for title, counter in (("KEYWORDS", keywords), ("SNAKE_CASE CALLS", calls)):
        print("==", title)
        for name, count in sorted(counter.items()):
            print(f"{count:6d}  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
