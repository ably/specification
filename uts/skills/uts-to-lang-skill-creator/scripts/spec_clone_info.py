#!/usr/bin/env python3
"""Locate, validate and pin the local ably/specification clone (STOP-1).

Usage: spec_clone_info.py [SPEC_CLONE | --spec-clone PATH]

Discovery order: the path given (walked up to the clone root from a path inside
a clone), else UTS_SPEC_CLONE, else the clone this skill is installed from. A
path given (or UTS_SPEC_CLONE) that isn't in a clone is NOT_A_SPEC_CLONE: it is
never replaced by another candidate.

Prints one JSON object: `ok`, `specClone`, `foundBy`, `sha`, `dirty`,
`dirtyFiles`, `guideLastChange`, `skillDir`, `skillRealpath`, `skillVersion`,
`skillMatchesClone`, `paths` and `warnings` (a list, possibly empty). Exit 0 on
success; 1 with {"ok": false} and a `code` (SPEC_CLONE_NOT_FOUND,
NOT_A_SPEC_CLONE, GIT_ERROR, INTERNAL_ERROR); 2 on a usage error. Read-only;
never touches the network.

Rules: SKILL.md 2.6.
"""
import filecmp, json, os, pathlib, subprocess, sys

SKILL_NAME = "uts-to-lang-skill-creator"
SKILL_IN_CLONE = pathlib.Path("uts", "skills", SKILL_NAME)
REQUIRED = {
    "guide": "uts/docs/writing-uts-spec-translator-skills.md",
    "utsReadme": "uts/README.md",
    "writingDerivedTests": "uts/docs/writing-derived-tests.md",
    "writingTestSpecs": "uts/docs/writing-test-specs.md",
    "integrationTesting": "uts/docs/integration-testing.md",
    "proxy": "uts/docs/proxy.md",
    "mockHttp": "uts/rest/unit/helpers/mock_http.md",
    "mockWebsocket": "uts/realtime/unit/helpers/mock_websocket.md",
    "mockVcdiff": "uts/realtime/unit/helpers/mock_vcdiff.md",
    "standardTestPool": "uts/objects/helpers/standard_test_pool.md",
    "featuresSpecs": "specifications",
}


def fail(code, message, **extra):
    print(json.dumps({"ok": False, "code": code, "message": message, **extra}, indent=2))
    return 1


def git(clone, *args):
    out = subprocess.run(["git", "-C", str(clone), *args], capture_output=True, text=True, encoding="utf-8")
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or f"git {' '.join(args)} failed")
    return out.stdout


def is_spec_clone(path):
    return all((path / rel).exists() for rel in REQUIRED.values())


def skill_files(root):
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts)


def skill_version(skill_dir):
    try:
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.split("\n---", 1)[0].splitlines():
        if line.strip().startswith("version:"):
            return line.split(":", 1)[1].strip().strip('"')
    return None


USAGE = "usage: spec_clone_info.py [SPEC_CLONE | --spec-clone PATH]"


def usage_error(message):
    print(f"{USAGE}\nspec_clone_info.py: error: {message}", file=sys.stderr)
    return 2


def main(argv):
    if "-h" in argv[1:] or "--help" in argv[1:]:
        print(__doc__.strip())
        return 0
    given = []
    it = iter(argv[1:])
    for a in it:
        if a == "--spec-clone":
            value = next(it, "")
            if not value or value.startswith("-"):
                return usage_error(f"{a} needs a value")
            given.append(value)
        elif a.startswith("-"):
            return usage_error(f"unknown option {a}")
        else:
            given.append(a)
    if len(given) > 1:
        return usage_error("give the spec clone once (SPEC_CLONE or --spec-clone PATH)")
    skill_dir = pathlib.Path(__file__).absolute().parent.parent
    skill_real = skill_dir.resolve()
    candidates = []
    if given and given[0].strip():
        candidates.append(("argument", given[0]))
    if os.environ.get("UTS_SPEC_CLONE"):
        candidates.append(("UTS_SPEC_CLONE", os.environ["UTS_SPEC_CLONE"]))
    candidates.append(("skill location", str(skill_real.parent.parent.parent)))

    clone, source = None, None
    for source, raw in candidates:
        path = pathlib.Path(os.path.expanduser(raw)).resolve()
        # accept a path inside a clone (e.g. <clone>/uts/objects): walk up to the root
        found = next((p for p in [path, *path.parents] if is_spec_clone(p)), None)
        if found is not None:
            clone = found
            break
        if source != "skill location":
            missing = [rel for rel in REQUIRED.values() if not (path / rel).exists()]
            return fail("NOT_A_SPEC_CLONE", f"{path} (from {source}) is not an ably/specification clone",
                        missing=missing)
    if clone is None:
        return fail("SPEC_CLONE_NOT_FOUND",
                    "No spec clone given and the skill is not installed from one. "
                    "Ask the user for the path of their local ably/specification clone (STOP-1).")

    try:
        sha = git(clone, "rev-parse", "HEAD").strip()
        status = git(clone, "--no-optional-locks", "status", "--porcelain", "--untracked-files=all", "--", "uts",
                      "specifications").splitlines()
        last = git(clone, "log", "-1", "--format=%H %cd", "--",
                  "uts/docs/writing-uts-spec-translator-skills.md", SKILL_IN_CLONE.as_posix()).strip()
    except (RuntimeError, OSError) as exc:
        return fail("GIT_ERROR", str(exc), specClone=str(clone))

    clone_skill = clone / SKILL_IN_CLONE
    matches = None
    if clone_skill.is_dir():
        if clone_skill.resolve() == skill_real:
            matches = True
        else:
            files = skill_files(skill_real)
            matches = files == skill_files(clone_skill) and all(
                filecmp.cmp(skill_real / f, clone_skill / f, shallow=False) for f in files)

    result = {
        "ok": True,
        "specClone": str(clone),
        "foundBy": source,
        "sha": sha,
        "dirty": bool(status),
        "dirtyFiles": [line[3:] for line in status],
        "guideLastChange": {
            "sha": last.split(" ", 1)[0] if last else None,
            "date": last.split(" ", 1)[1] if " " in last else None,
        },
        "skillDir": str(skill_dir),
        "skillRealpath": str(skill_real),
        "skillVersion": skill_version(skill_real),
        "skillMatchesClone": matches,
        "paths": {key: str(clone / rel) for key, rel in REQUIRED.items()},
        "warnings": [],
    }
    if matches is False:
        result["warnings"].append(
            "SKILL_MISMATCH: the installed skill differs from the copy in this spec clone. "
            "Ask the user to refresh the install, or to confirm which version to follow (STOP-1)."
        )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception as exc:  # never crash: report as JSON
        sys.exit(fail("INTERNAL_ERROR", f"{type(exc).__name__}: {exc}"))
