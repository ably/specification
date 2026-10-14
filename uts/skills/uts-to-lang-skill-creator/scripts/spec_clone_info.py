#!/usr/bin/env python3
"""Locate, validate and pin the local ably/specification clone (STOP-1).

Usage: spec_clone_info.py [SPEC_CLONE | --spec-clone PATH]

Precedence (ensure_spec_clone.py's): the path given (walked up to the clone
root from a path inside a clone), else the clone this skill is installed from,
else ABLY_SPEC_CLONE (UTS_SPEC_CLONE is read as a deprecated alias, with a
warning), else the shared default ~/.ably/specification. A path given that
isn't in a clone is NOT_A_SPEC_CLONE: it is never replaced by another
candidate. An ABLY_SPEC_CLONE path, or the default, that doesn't exist is
SPEC_CLONE_NOT_FOUND with `bootstrapPath`. A clone whose checkout lacks the
guide or this skill (a revision that predates them) is SPEC_CLONE_INCOMPLETE,
with `missing` and a message saying how to proceed. Only the shared clone is
synced (`syncEligible`); any other clone gets `notSyncedWarning`.

Prints one JSON object: `ok`, `specClone`, `kind`, `foundBy`,
`isSharedClone`, `syncEligible`, `notSyncedWarning`, `sha`, `branch`,
`detached`, `dirty`, `dirtyFiles`, `trackedChanges`, `operationInProgress`,
`upstream` {ref, sha, ahead, behind, lastFetch, lastFetchDays},
`onOriginMain`, `originUrl`,
`originIsAblySpecification`, `fastForwardBlockedBy`, `headAgeDays`,
`staleWarning`, `stalenessLine`, `syncPolicy`, `guideLastChange`, `skillDir`,
`skillRealpath`, `skillVersion`, `skillMatchesClone`, `paths` and `warnings`
(a list, possibly empty). Exit 0 on success; 1 with {"ok": false} and a `code`
(SPEC_CLONE_NOT_FOUND with `bootstrapPath`, NOT_A_SPEC_CLONE,
SPEC_CLONE_INCOMPLETE, SPEC_CLONE_ENV_CONFLICT, GIT_ERROR, INTERNAL_ERROR); 2
on a usage error. Read-only; never touches the network (the sync is
ensure_spec_clone.py's).

Rules: SKILL.md 2.6; references/orient.md 13.1, 13.9.
"""
import filecmp, importlib.util, json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("ensure_spec_clone", HERE / "ensure_spec_clone.py")
esc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(esc)

SKILL_NAME = "uts-to-lang-skill-creator"
SKILL_IN_CLONE = pathlib.Path("uts", "skills", SKILL_NAME)
REQUIRED = {
    "guide": "uts/docs/writing-uts-spec-translator-skills.md",
    "skillCreator": (SKILL_IN_CLONE / "SKILL.md").as_posix(),
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
    loc = esc.locate(given[0] if given else None, list(REQUIRED.values()))
    warnings = loc.pop("warnings", [])
    clone = pathlib.Path(loc["specClone"]) if loc.get("specClone") else None
    if clone is None:
        return fail(loc["code"], loc["message"], **{k: v for k, v in loc.items() if k not in ("ok", "code", "message")},
                    warnings=warnings)
    try:
        st = esc.status(clone)
        last = esc.git(clone, "log", "-1", "--format=%H %cd", "--",
                      REQUIRED["guide"], SKILL_IN_CLONE.as_posix()).strip()
    except (esc.GitError, OSError) as exc:
        return fail("GIT_ERROR", str(exc), specClone=str(clone), kind=loc.get("kind"), foundBy=loc.get("foundBy"),
                    warnings=warnings)
    if not loc["ok"]:
        return fail("SPEC_CLONE_INCOMPLETE", esc.incomplete_message(loc, st, clone), specClone=str(clone),
                    kind=loc["kind"], foundBy=loc["foundBy"], isSharedClone=loc.get("isSharedClone"),
                    syncEligible=loc.get("syncEligible"), notSyncedWarning=loc.get("notSyncedWarning"),
                    missing=loc["missing"], sha=st["head"], branch=st["branch"], detached=st["detached"],
                    upstream=st["upstream"], fastForwardBlockedBy=st["fastForwardBlockedBy"],
                    staleWarning=st["staleWarning"], stalenessLine=st["stalenessLine"], syncPolicy=esc.policy(),
                    warnings=warnings)

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
        "kind": loc["kind"],
        "foundBy": loc["foundBy"],
        "isSharedClone": loc["isSharedClone"],
        "syncEligible": loc["syncEligible"],
        "notSyncedWarning": loc["notSyncedWarning"],
        "sha": st["head"],
        "branch": st["branch"],
        "detached": st["detached"],
        "dirty": bool(st["dirtyFiles"]),
        "dirtyFiles": st["dirtyFiles"],
        "trackedChanges": st["trackedChanges"],
        "operationInProgress": st["operationInProgress"],
        "upstream": st["upstream"],
        "onOriginMain": st["onOriginMain"],
        "originUrl": st["originUrl"],
        "originIsAblySpecification": st["originIsAblySpecification"],
        "fastForwardBlockedBy": st["fastForwardBlockedBy"],
        "headAgeDays": st["headAgeDays"],
        "staleWarning": st["staleWarning"],
        "stalenessLine": st["stalenessLine"],
        "syncPolicy": esc.policy(),
        "guideLastChange": {
            "sha": last.split(" ", 1)[0] if last else None,
            "date": last.split(" ", 1)[1] if " " in last else None,
        },
        "skillDir": str(skill_dir),
        "skillRealpath": str(skill_real),
        "skillVersion": skill_version(skill_real),
        "skillMatchesClone": matches,
        "paths": {key: str(clone / rel) for key, rel in REQUIRED.items()},
        "warnings": warnings,
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
