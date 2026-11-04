#!/usr/bin/env python3
"""Run actual PG17 client in this job's service container; bridge owned temp files."""
import os
from pathlib import Path
import subprocess
import sys

tool = Path(sys.argv[0]).name
if tool not in {"pg_dump", "pg_restore"}:
    raise SystemExit("Unexpected PostgreSQL tool")
container = os.environ["SUNJACK_CI_POSTGRES_CONTAINER"]
arguments = sys.argv[1:]
command = ["docker", "exec", "-i", "-e", "PGHOST=127.0.0.1", "-e", "PGPORT=5432",
           "-e", "PGUSER=" + os.environ["PGUSER"], container, tool]
if tool == "pg_dump" and "--file" in arguments:
    index = arguments.index("--file")
    target = Path(arguments[index + 1])
    arguments = arguments[:index] + arguments[index + 2:]
    with target.open("xb") as output:
        result = subprocess.run(command + arguments, stdout=output, stderr=subprocess.PIPE)
elif tool == "pg_restore" and "--version" not in arguments:
    source = Path(arguments[-1])
    with source.open("rb") as input_file:
        result = subprocess.run(command + arguments[:-1] + ["-"], stdin=input_file, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
else:
    result = subprocess.run(command + arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    sys.stdout.buffer.write(result.stdout)
if result.returncode:
    # Only the isolated service's synthetic diagnostics are emitted.
    sys.stderr.buffer.write(result.stderr)
raise SystemExit(result.returncode)
