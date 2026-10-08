#!/usr/bin/env python3
"""First-pass, read-only survey of a target SDK repository (Phase 1, step 1b).

Usage: survey_repo.py <repo> [<test-root> ...]

Prints the HEAD SHA and dirty state, file-extension counts, likely test roots,
submodule status, candidate mocks and fakes, and existing UTS tags. It is a
starting point for the discovery checklist, not an answer to it: follow the
evidence, and adapt or extend the searches for the repo's language.
"""
import collections, pathlib, re, subprocess, sys

MOCK_RE = re.compile(r"class (Mock|Fake|Stub)|(Mock|Fake)[A-Z][A-Za-z]*(Transport|Http|Clock|Timer|Socket)")
TEST_ROOT_RE = re.compile(r"(^|/)(test|tests|spec|specs)/", re.IGNORECASE)


def git(repo, *args):
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")
    return out.stdout if out.returncode == 0 else f"(git {' '.join(args)} failed: {out.stderr.strip()})\n"


def grep(roots, pattern, limit):
    hits = []
    for root in roots:
        for path in sorted(pathlib.Path(root).rglob("*")):
            if not path.is_file() or any(part.startswith(".") for part in path.relative_to(root).parts):
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            for n, line in enumerate(lines, 1):
                if pattern.search(line):
                    hits.append(f"{path}:{n}: {line.strip()[:160]}")
                    if len(hits) >= limit:
                        return hits
    return hits


def display(path, repo):
    try:
        return str(path.relative_to(repo))
    except ValueError:
        return str(path)


def main(argv):
    if len(argv) < 2 or not pathlib.Path(argv[1]).is_dir():
        print("usage: survey_repo.py <repo> [<test-root> ...]", file=sys.stderr)
        return 2
    repo = pathlib.Path(argv[1]).resolve()
    files = git(repo, "ls-files").splitlines()

    print("== HEAD and status")
    print(git(repo, "rev-parse", "HEAD").strip())
    print(git(repo, "status", "--porcelain").strip() or "(clean)")

    print("\n== Extension counts (top 20)")
    exts = collections.Counter(f.rsplit(".", 1)[-1] if "." in f.rsplit("/", 1)[-1] else "(none)" for f in files)
    for ext, count in exts.most_common(20):
        print(f"{count:7d}  {ext}")

    print("\n== Likely test roots (first 50 files under test/tests/spec dirs)")
    test_files = [f for f in files if TEST_ROOT_RE.search(f)]
    for f in test_files[:50]:
        print(f)
    roots = [repo / r for r in argv[2:]] or sorted({repo / f.split("/")[0] for f in test_files})
    print("\n== Roots searched below: " + (", ".join(display(r, repo) for r in roots) or "(none)"))

    print("\n== Submodules")
    print(git(repo, "submodule", "status").strip() or "(none)")

    print("\n== Candidate mocks, fakes and stubs (first 40)")
    print("\n".join(grep(roots, MOCK_RE, 40)) or "(none)")

    print("\n== Existing UTS tags (first 10)")
    print("\n".join(grep(roots, re.compile(r"UTS:"), 10)) or "(none)")

    print("\n== Existing skills")
    print("\n".join(f for f in files if f.startswith((".claude/skills/", ".agents/skills/", ".codex/skills/")) and f.endswith("SKILL.md"))
          or "(none)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
