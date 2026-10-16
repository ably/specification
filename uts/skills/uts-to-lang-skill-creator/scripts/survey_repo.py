#!/usr/bin/env python3
"""First-pass, read-only survey of a target SDK repository (Phase 1, step 1b).

Usage: survey_repo.py <repo> [<test-root> ...]

A starting point for the discovery checklist, not an answer to it: follow the
evidence, and adapt or extend the searches for the repo's language.

Prints plain text, in sections: HEAD and status, extension counts (top 20),
likely test roots, the roots searched, submodules, candidate mocks, fakes and
stubs, existing UTS tags, and existing skills (including uts-to-* skill
directories that are symlinks). Outside a git repository it says so and lists
files by a directory walk. Exit 0 on success; 2 on a usage error. Read-only
(git runs with --no-optional-locks); never touches the network.

Rules: references/phase-1-understand-repo.md 3.2.
"""
import collections, importlib.util, os, pathlib, re, subprocess, sys

_spec = importlib.util.spec_from_file_location("detect_liveobjects",
                                                pathlib.Path(__file__).resolve().parent / "detect_liveobjects.py")
lo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lo)

MOCK_RE = re.compile(r"class (Mock|Fake|Stub)|(Mock|Fake)[A-Z][A-Za-z]*(Transport|Http|Clock|Timer|Socket)")
SKILL_DIRS = tuple(root + "/" for root in lo.SKILL_ROOTS)
TEST_ROOT_RE = re.compile(r"(^|/)(test|tests|spec|specs)/", re.IGNORECASE)
USAGE = "usage: survey_repo.py <repo> [<test-root> ...]"


def git(repo, *args):
    """git's output, or None when it fails (not a git repository, no commits): never its error text."""
    out = subprocess.run(["git", "-C", str(repo), "--no-optional-locks", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return out.stdout if out.returncode == 0 else None


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


def usage_error(message):
    print(f"{USAGE}\nsurvey_repo.py: error: {message}", file=sys.stderr)
    return 2


def main(argv):
    if "-h" in argv[1:] or "--help" in argv[1:]:
        print(__doc__.strip())
        return 0
    unknown = [a for a in argv[1:] if a.startswith("-")]
    if unknown:
        return usage_error(f"unknown option {unknown[0]}")
    if len(argv) < 2:
        return usage_error("expected <repo>")
    repo = pathlib.Path(argv[1]).expanduser()
    if not repo.is_dir():
        return usage_error(f"not a directory: {argv[1]}")
    repo = repo.resolve()
    listed = git(repo, "ls-files")
    is_git = listed is not None
    files = listed.splitlines() if is_git else lo.walk_files(repo)

    print("== HEAD and status")
    if is_git:
        print((git(repo, "rev-parse", "HEAD") or "(no commits)").strip())
        print((git(repo, "status", "--porcelain") or "").strip() or "(clean)")
    else:
        print("(not a git repository: files listed by a directory walk, skipping build and vendored directories)")

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
    if is_git:
        print((git(repo, "submodule", "status") or "").strip() or "(none)")
    else:
        print("(not a git repository)")

    print("\n== Candidate mocks, fakes and stubs (first 40)")
    print("\n".join(grep(roots, MOCK_RE, 40)) or "(none)")

    print("\n== Existing UTS tags (first 10)")
    print("\n".join(grep(roots, re.compile(r"UTS:"), 10)) or "(none)")

    print("\n== Existing skills")
    skills = {f for f in files if f.startswith(SKILL_DIRS) and f.endswith("SKILL.md")}
    for base in SKILL_DIRS:
        for d in sorted((repo / base).glob("uts-to-*")) if (repo / base).is_dir() else []:
            link = f" -> {os.readlink(d)}" if d.is_symlink() else ""
            skills.add(f"{display(d, repo)}/{link}" if link else f"{display(d, repo)}/SKILL.md")
    print("\n".join(sorted(skills)) or "(none)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
