"""Exercise PG17 client's real stdin argument semantics using invalid synthetic bytes."""
import argparse
import json
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--pg-restore", required=True)
args = parser.parse_args()
results = []
for extra in (("--list", "-"), ("--list",)):
    result = subprocess.run([args.pg_restore, *extra], input=b"SYNTHETIC INVALID ARCHIVE", capture_output=True, timeout=30)
    results.append({"arguments": list(extra), "exit": result.returncode,
                    "stderr": result.stderr.decode("utf-8", errors="replace").strip()})
if 'could not open input file "-"' not in results[0]["stderr"] or "does not appear to be a valid archive" not in results[1]["stderr"]:
    raise RuntimeError("Unexpected PG17 stdin behavior")
print(json.dumps({"status": "PASS", "results": results}))
