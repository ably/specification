#!/usr/bin/env python3
"""Check that this skill's stop points and ground rules stay within the context-compaction window (maintainers).

Usage: check_layout.py [SKILL_MD]

After a context compaction, Claude Code keeps only the start of an invoked
skill: about 5,000 tokens, which it counts as about 20,000 characters of the
text after the frontmatter, including a line with the install path. This
script measures, in characters after the frontmatter, where the stop-point
table of section 2.3 ends and where the ground rules (section 2) end, and checks
them against the limits below, which leave a margin for the install path and
for edits. SKILL_MD defaults to this skill's SKILL.md.

Prints one JSON object: `ok`, `skillMd`, `stopTableEnd`, `groundRulesEnd`,
`limits` and `warnings` (each limit exceeded, or a section not found). Read-only;
no network. Exit 0 when within the limits; 1 when not, or a section is missing;
2 on a usage error.

Rules: SKILL.md "Maintaining this skill".
"""
import json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
LIMITS = {"stopTableEnd": 16000, "groundRulesEnd": 18500}
USAGE = "usage: check_layout.py [SKILL_MD]"


def body(text):
    """The text after the YAML frontmatter, as Claude Code renders it (leading newlines dropped)."""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            text = text[end + 5:]
    return text.lstrip("\n")


def measure(text):
    """Offsets of the end of the stop-point table and of the end of section 2, or None if not found."""
    stop_end = rules_end = None
    start = text.find("\n## 2. Ground rules\n")
    if start != -1:
        nxt = text.find("\n## ", start + 1)
        rules_end = nxt + 1 if nxt != -1 else len(text)
        sec = text.find("\n### 2.3 ", start)
        if sec != -1 and sec < rules_end:
            pos = sec + 1
            for line in text[sec + 1:rules_end].splitlines(True):
                pos += len(line)
                if line.startswith("| **STOP-"):
                    stop_end = pos  # just after the last stop-point row
    return stop_end, rules_end


def usage_error(message):
    print(f"{USAGE}\ncheck_layout.py: error: {message}", file=sys.stderr)
    return 2


def main(argv):
    if "-h" in argv[1:] or "--help" in argv[1:]:
        print(__doc__.strip())
        return 0
    args = argv[1:]
    if any(a.startswith("-") for a in args):
        return usage_error(f"unknown option {next(a for a in args if a.startswith('-'))}")
    if len(args) > 1:
        return usage_error(f"expected at most one SKILL_MD, got {len(args)} arguments")
    path = pathlib.Path(args[0]).expanduser() if args else HERE.parent / "SKILL.md"
    if not path.is_file():
        return usage_error(f"not a file: {path}")
    stop_end, rules_end = measure(body(path.read_text(encoding="utf-8")))
    found = {"stopTableEnd": stop_end, "groundRulesEnd": rules_end}
    warnings = []
    for key, value in found.items():
        if value is None:
            warnings.append(f"{key}: section not found")
        elif value > LIMITS[key]:
            warnings.append(f"{key} {value} exceeds {LIMITS[key]}: move material from before it to after section 2")
    out = {
        "ok": not warnings,
        "skillMd": str(path.resolve()),
        "stopTableEnd": stop_end,
        "groundRulesEnd": rules_end,
        "limits": LIMITS,
        "warnings": warnings,
    }
    print(json.dumps(out, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
