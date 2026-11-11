"""Summarize recorded Playwright cases without copying test attachments or console output."""
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

root = Path(__file__).resolve().parent
ansi = re.compile(r"\x1b\[[0-9;]*m")
cases = defaultdict(list)
full_counts = Counter()
retry_counts = Counter()


def visit(suite, titles=()):
    title = suite.get("title")
    if title and not title.endswith(".spec.js"):
        titles = (*titles, title)
    for spec in suite.get("specs", []):
        for test in spec["tests"]:
            yield spec, test, " › ".join((*titles, spec["title"]))
    for child in suite.get("suites", []):
        yield from visit(child, titles)


for report in sorted((root / "final-runs" / "chrome" / "artifacts").rglob("playwright-report.json"),
                     key=lambda path: json.loads(path.read_text(encoding="utf-8"))["stats"]["startTime"]):
    payload = json.loads(report.read_text(encoding="utf-8"))
    run = report.parent.name
    time = payload["stats"]["startTime"]
    for suite in payload["suites"]:
        for spec, test, title in visit(suite):
            result = test["results"][-1] if test["results"] else {}
            status = result.get("status", "not_run").upper()
            if status == "SKIPPED" and test.get("expectedStatus") != "skipped":
                status = "NOT_RUN"
            if test["status"] == "expected" and status == "PASSED":
                status = "PASS"
            error = ansi.sub("", result.get("error", {}).get("message", ""))
            detail = [line.strip() for line in error.splitlines() if line.strip()][:8]
            key = Path(spec["file"].replace("\\", "/")).name, title
            attempt = {"status": status, "run": run, "time": time, "error": detail}
            if cases[key]:
                retry_counts[status] += 1
            else:
                full_counts[status] += 1
            cases[key].append(attempt)

source = root / "h1-browser-triage.csv"
with source.open(encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)
    fields = reader.fieldnames
    rows = list(reader)

for row in rows:
    field = fields[1]
    match = re.fullmatch(r".*?[\\/]([^\\/]+\.spec\.js):\d+:\d+ › (.*)", row[field])
    history = cases.get(match.groups(), []) if match else []
    row[fields[-1]] = " → ".join(f"{item['status']} [{item['run']}]" for item in history) or "NOT_RUN"

with source.open("w", encoding="utf-8-sig", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=fields, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(rows)

(root / "chrome-case-results.json").write_text(json.dumps({
    "firstObserved": full_counts,
    "retries": retry_counts,
    "latest": Counter(value[-1]["status"] for value in cases.values()),
    "cases": [{"spec": key[0], "title": key[1], "attempts": attempts} for key, attempts in cases.items()],
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
