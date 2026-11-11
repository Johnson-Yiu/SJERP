"""Join isolated Playwright profiles to the original A3 case records."""
import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import re

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def cases(suite, titles=()):
    title = suite.get("title")
    if title and not title.endswith(".spec.js"):
        titles = (*titles, title)
    for spec in suite.get("specs", ()):
        file = Path(spec["file"].replace("\\", "/")).name
        for test in spec["tests"]:
            yield (file, " › ".join((*titles, spec["title"]))), test
    for child in suite.get("suites", ()):
        yield from cases(child, titles)


def case_status(test, result):
    status = result.get("status")
    if status == "passed":
        return "PASS" if test["status"] == "expected" else "UNEXPECTED_PASS"
    if not status or (status == "skipped" and test.get("expectedStatus") != "skipped"):
        return "NOT_RUN"
    return status.upper()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    own_root = Path(__file__).resolve().parent
    prior_path = own_root.parent / "release-integration-acceptance-03" / "chrome-case-results.json"
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    renamed = json.loads((own_root / "cash-case-reconciliation.json").read_text(encoding="utf-8"))
    cash_titles = {case["a3Title"]: case["currentTitle"] for case in renamed["cases"]}
    before = {
        (case["spec"], cash_titles.get(case["title"], case["title"]) if case["spec"] == "cash-events-p2b.spec.js" else case["title"]): case["attempts"]
        for case in prior["cases"]
    }

    evidence = args.evidence.resolve()
    if os.name == "nt":
        evidence = Path("\\\\?\\" + str(evidence))
    summary_path = evidence / "suite-run-summary.json"
    suite_summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else None
    if suite_summary and suite_summary["source"] != args.source:
        raise ValueError("Suite summary source differs from requested source.")

    rows = []
    joined = defaultdict(list)
    reports = sorted(evidence.rglob("playwright-report.json"))
    if not reports:
        raise ValueError("No Playwright case reports were found.")
    for path in reports:
        relative = path.relative_to(evidence)
        profile = relative.parts[0] if relative.parts[0] != "artifacts" else "isolated"
        report = json.loads(path.read_text(encoding="utf-8"))
        for suite in report["suites"]:
            for (file, title), test in cases(suite):
                result = test["results"][-1] if test["results"] else {}
                status = case_status(test, result)
                failure = ANSI.sub("", result.get("error", {}).get("message", ""))
                row = {
                    "profile": profile, "file": file, "title": title, "status": status,
                    "report": relative.as_posix(), "project": test.get("projectName"),
                    "attempts": [attempt["status"] for attempt in test["results"]],
                    "annotations": result.get("annotations", test.get("annotations", [])),
                    "error": [line.strip() for line in failure.splitlines() if line.strip()][:8],
                    "a3Attempts": before.get((file, title), []),
                }
                rows.append(row)
                joined[(file, title)].append({"profile": profile, "status": status})
    a3_unresolved = [
        {"file": file, "title": title, "a3Status": attempts[-1]["status"], "candidate": joined[(file, title)]}
        for (file, title), attempts in before.items()
        if attempts and attempts[-1]["status"] not in {"PASS", "SKIPPED"}
    ]
    payload = {
        "source": args.source,
        "suiteComplete": suite_summary is not None,
        "profiles": len({row["profile"] for row in rows}),
        "counts": Counter(row["status"] for row in rows),
        "a3HistoricalNonPassingCases": a3_unresolved,
        "cases": rows,
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("source", "suiteComplete", "profiles", "counts")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
