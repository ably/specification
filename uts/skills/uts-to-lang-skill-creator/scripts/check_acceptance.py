#!/usr/bin/env python3
"""Automated acceptance check on a generated uts-to-* skill (Phase 6, 8.9; Phase 7, section 9).

Usage: check_acceptance.py <repo> <skill-dir> [--records <dir>] [--final] [--markdown]

Read-only. It runs inspect_existing_skill.py's checks on the skill, reads the
working records' acceptance checklist (acceptance-checklist.md; for older
records, the Final report's "Acceptance checklist" section), and checks:
- every row of the skill creator's template is present, in guide section 13
  order, with a status: ✓ with evidence, "✓ static; behaviour at first
  translation" with evidence, ✗ or n/a with a reason, or open;
- every inspector `fail` is explained: its row is ✗ or n/a with a reason (a
  fail under a ✓ row, or under an open row, is unexplained);
- the records exist: repo-profile.md, uts-infra-design.md, design-record.md,
  the checklist, the infra README with a Known gaps section and, with
  --final, final-report.md.
With --final (Phase 7, the completion gate) it also needs no open row and the
"Independent verification" line recorded with no unresolved dispute. Rows are
matched to the template by their first column; a reworded row (an older
template) is matched by similarity and reported.

Prints one JSON object: `ok`, `repo`, `skill`, `recordsDir`, `final`,
`checklist` (file, evidenceColumn, counts, missingRows, unexpectedRows,
outOfOrder, reworded, problems), `inspector` (summary, unexplainedFails,
explainedFails, unmatchedItems), `records` (present, missing), `verification`,
`gate` (passed, reasons) and `summaryMarkdown`. --markdown prints only the
Markdown summary. Exit 0 when the check ran (the verdict is `gate.passed`); 1
with {"ok": false} on an error (CHECK_ERROR); 2 on a usage error.

Regex and table parsing, not a review: the independent verifier (section 9)
is the review.
"""
import difflib, importlib.util, json, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("inspect_existing_skill", HERE / "inspect_existing_skill.py")
insp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(insp)

TEMPLATE = HERE.parent / "assets" / "templates" / "acceptance-checklist.md"
USAGE = "usage: check_acceptance.py <repo> <skill-dir> [--records <dir>] [--final] [--markdown]"
RECORDS = ("repo-profile.md", "uts-infra-design.md", "design-record.md")


def norm(text):
    return re.sub(r"\s+", " ", text.replace("`", "").replace("**", "")).strip().lower()


def item_matches(item, row):
    """An inspector item string ("A ... B", "..." for omitted text) matches a row when its parts occur in order."""
    parts = [norm(p) for p in item.split("...") if norm(p)]
    text, pos = norm(row), 0
    for part in parts:
        i = text.find(part, pos)
        if i < 0:
            return False
        pos = i + len(part)
    return bool(parts)


def align(template_items, record_items):
    """Map template row index -> record row index: identical text first, then by similarity (>= 0.5)."""
    t2r, r2t, ratios = {}, {}, {}
    tn, rn = [norm(t) for t in template_items], [norm(r) for r in record_items]
    for i, t in enumerate(tn):
        for j, r in enumerate(rn):
            if j not in r2t and t == r:
                t2r[i], r2t[j], ratios[i] = j, i, 1.0
                break
    pairs = []
    for i, t in enumerate(tn):
        if i in t2r:
            continue
        for j, r in enumerate(rn):
            if j in r2t:
                continue
            m = difflib.SequenceMatcher(None, t, r)
            if m.real_quick_ratio() >= 0.5 and m.quick_ratio() >= 0.5:
                ratio = m.ratio()
                if ratio >= 0.5:
                    pairs.append((ratio, -abs(i - j), i, j))
    for ratio, _, i, j in sorted(pairs, reverse=True):
        if i not in t2r and j not in r2t:
            t2r[i], r2t[j], ratios[i] = j, i, round(ratio, 2)
    # An abbreviated row ("`resolve_uts.py`", "Module notes ...; `objects` decided from evidence"): the same lead
    # (the text before the first ":", ";" or "("), or a prefix of the template's text.
    def lead(s):
        return re.split(r"[:;(]", s, maxsplit=1)[0].strip()
    for i, t in enumerate(tn):
        if i in t2r:
            continue
        def fits(j, r):
            return j not in r2t and len(lead(r)) >= 8 and (lead(r) == lead(t) or t.startswith(r))
        cands = [j for j, r in enumerate(rn) if fits(j, r)]
        if cands:
            j = min(cands, key=lambda j: abs(i - j))
            t2r[i], r2t[j], ratios[i] = j, i, round(difflib.SequenceMatcher(None, t, rn[j]).ratio(), 2)
    return t2r, ratios


def check(repo, skill_arg, records_arg, final):
    skill_dir = insp.named_path(repo, skill_arg)
    if not (skill_dir / "SKILL.md").is_file():
        raise ValueError(f"no SKILL.md in {skill_dir}")
    real = str(skill_dir.resolve())
    installs = insp.find_skills(repo, skill_arg).get(real) or [{"path": insp.display(skill_dir, repo),
                                                                "symlink": skill_dir.is_symlink()}]
    rec_dir = pathlib.Path(records_arg).expanduser() if records_arg else pathlib.Path(real) / "generation"
    skill = insp.inspect_skill(repo, real, installs, rec_dir if records_arg else None)

    template = insp.parse_checklist(TEMPLATE.read_text(encoding="utf-8"))["rows"]
    parsed = insp.read_checklist(rec_dir) if rec_dir.is_dir() else None
    rows = parsed["rows"] if parsed else []
    t2r, ratios = align([t["item"] for t in template], [r["item"] for r in rows])
    problems = []
    for r in rows:
        if r["kind"] == "unknown":
            problems.append({"item": r["item"], "problem": f"unrecognised status {r['status']!r}"})
        elif r["kind"] in ("done", "static") and not r["evidence"]:
            problems.append({"item": r["item"], "problem": "✓ without evidence (counts as open)"})
        elif r["kind"] in ("fail", "na") and not r["reason"]:
            problems.append({"item": r["item"], "problem": f"{r['status']} without a reason (counts as open)"})
    matched = [t2r[i] for i in sorted(t2r)]
    out_of_order = [rows[j]["item"] for k, j in enumerate(matched) if k and j < max(matched[:k])]
    checklist = {
        "file": parsed["file"] if parsed else None,
        "evidenceColumn": parsed["evidenceColumn"] if parsed else None,
        "counts": insp.checklist_counts(rows),
        "missingRows": [t["item"] for i, t in enumerate(template) if i not in t2r],
        "unexpectedRows": [r["item"] for j, r in enumerate(rows) if j not in set(t2r.values())],
        "outOfOrder": out_of_order,
        "reworded": [
            dict(template=template[i]["item"], record=rows[t2r[i]]["item"], similarity=ratios[i])
            for i in sorted(t2r) if ratios[i] < 1.0],
        "problems": problems,
    }

    unexplained, explained, unmatched = [], [], []
    for c in skill["checks"]:
        if c["status"] != "fail":
            continue
        ti = next((i for i, t in enumerate(template) if item_matches(c["item"], t["item"])), None)
        row = rows[t2r[ti]] if ti is not None and ti in t2r else None
        entry = dict(
            id=c["id"], item=c["item"], evidence=c["evidence"], row=row["item"] if row else None,
            rowStatus=row["status"] if row else None)
        if ti is None:
            unmatched.append(c["item"])
        if row and row["kind"] in ("fail", "na") and row["reason"]:
            explained.append(entry)
        else:
            entry["why"] = ("no checklist row matches the item" if ti is None else "its row is missing"
                            if row is None else f"its row is {row['status'] or 'open'}, not ✗ or n/a with a reason")
            unexplained.append(entry)

    present = {n: (rec_dir / n).is_file() for n in RECORDS + (("final-report.md",) if final else ())}
    present["acceptance checklist"] = parsed is not None
    kg = next((c for c in skill["checks"] if c["id"] == "H-readme-known-gaps"), None)
    present["README with Known gaps"] = bool(kg and kg["status"] == "pass")
    missing = [n for n, ok in present.items() if not ok]

    verification = parsed["verification"] if parsed else None
    unresolved = re.search(r"(?i)unresolved\s*(\d+)", verification or "")
    reasons = []
    if not parsed:
        reasons.append(f"no acceptance checklist in {rec_dir}")
    if unexplained:
        reasons.append(f"{len(unexplained)} unexplained inspector fail(s)")
    if missing:
        reasons.append("missing records: " + ", ".join(missing))
    if checklist["missingRows"] or checklist["unexpectedRows"] or out_of_order:
        reasons.append("checklist rows differ from the template (missing, extra or out of order)")
    if final:
        if checklist["counts"]["openTotal"]:
            reasons.append(f"{checklist['counts']['openTotal']} open row(s)")
        if not verification:
            reasons.append("the independent verification isn't recorded")
        elif unresolved and int(unresolved.group(1)):
            reasons.append(f"{unresolved.group(1)} unresolved dispute(s) from the verification")
    finished = (skill.get("records") or {}).get("runStatus") == "finished"
    if final and finished and reasons:
        reasons.append("the Design record's Run status says finished, but the gate doesn't pass")

    independent = bool(verification) and not re.search(r"(?i)not independent", verification or "")
    result = {
        "ok": True, "repo": str(repo), "skill": insp.display(skill_dir, repo),
        "recordsDir": insp.display(rec_dir, repo), "final": final, "checklist": checklist,
        "inspector": dict(summary=skill["summary"], unexplainedFails=unexplained, explainedFails=explained,
                          unmatchedItems=unmatched),
        "records": {"present": present, "missing": missing},
        "verification": dict(
            line=verification, independent=independent, unresolved=int(unresolved.group(1)) if unresolved else None),
        "gate": {"passed": not reasons, "reasons": reasons},
    }
    result["summaryMarkdown"] = summary(result)
    return result


def summary(r):
    c, i = r["checklist"], r["inspector"]
    n = c["counts"]
    s = i["summary"]
    kind = "final" if r["final"] else "Phase 6"
    no_ev = "" if c["evidenceColumn"] in (None, True) else ", no Evidence column"
    lines = [f"**Acceptance check** ({kind}): `{r['skill']}`, records `{r['recordsDir']}`"]
    counts = (f"{n['rows']} rows; ✓ {n['done']}, ✓ static {n['static']}, ✗ {n['fail']}, n/a {n['na']}, "
              f"open {n['openTotal']}")
    if n["noEvidence"] or n["noReason"]:
        counts += f" ({n['noEvidence']} ✓ without evidence, {n['noReason']} ✗ or n/a without a reason)"
    lines.append(f"- Checklist ({c['file'] or 'not found'}{no_ev}): {counts}")
    shape = (len(c["missingRows"]), len(c["unexpectedRows"]), len(c["outOfOrder"]), len(c["reworded"]))
    lines.append("- Rows against the template: %d missing, %d not in it, %d out of order, %d reworded" % shape)
    fails = (s.get("pass", 0), s.get("warn", 0), s.get("fail", 0), len(i["unexplainedFails"]))
    lines.append("- Inspector: %d pass, %d warn, %d fail (%d unexplained)" % fails)
    lines += [f"  - unexplained `{u['id']}`: {u['evidence']} ({u['why']})" for u in i["unexplainedFails"]]
    lines.append("- Records missing: " + (", ".join(r["records"]["missing"]) or "none"))
    lines.append("- Independent verification: " + (r["verification"]["line"] or "not recorded"))
    verdict = "passed" if r["gate"]["passed"] else "not passed: " + "; ".join(r["gate"]["reasons"])
    lines.append(("- Completion gate: " if r["final"] else "- Phase 6 result: ") + verdict)
    return "\n".join(lines)


def usage_error(message):
    print(f"{USAGE}\ncheck_acceptance.py: error: {message}", file=sys.stderr)
    return 2


def main(argv):
    if "-h" in argv[1:] or "--help" in argv[1:]:
        print(__doc__.strip())
        return 0
    args, records_arg, final, markdown = [], None, False, False
    it = iter(argv[1:])
    for a in it:
        if a == "--records":
            records_arg = next(it, "")
            if not records_arg or records_arg.startswith("-"):
                return usage_error(f"{a} needs a value")
        elif a == "--final":
            final = True
        elif a == "--markdown":
            markdown = True
        elif a.startswith("-"):
            return usage_error(f"unknown option {a}")
        else:
            args.append(a)
    if len(args) != 2:
        return usage_error(f"expected <repo> and <skill-dir>, got {len(args)} arguments")
    repo = pathlib.Path(args[0]).expanduser()
    if not repo.is_dir():
        return usage_error(f"not a directory: {args[0]}")
    try:
        result = check(repo.resolve(), args[1], records_arg, final)
    except Exception as exc:  # never crash: report a structured error
        print(json.dumps({"ok": False, "code": "CHECK_ERROR", "message": f"{type(exc).__name__}: {exc}"}, indent=2))
        return 1
    print(result["summaryMarkdown"] if markdown else json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
