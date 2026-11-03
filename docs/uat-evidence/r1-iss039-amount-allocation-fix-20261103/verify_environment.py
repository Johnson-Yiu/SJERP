"""Read-only verification against this checkout's exact runtime lock."""
from importlib.metadata import version
from pathlib import Path
import platform
import subprocess
import sys

root = Path(__file__).resolve().parents[3]
print("executable:", sys.executable)
print("Python:", platform.python_version())
assert sys.version_info[:3] == (3, 12, 16)
pins = []
for line in (root / "backend" / "requirements.lock").read_text().splitlines():
    if not line.strip() or line.startswith("#"):
        continue
    name, expected = line.split("==")
    actual = version(name)
    print(f"{name}: lock={expected}; installed={actual}; equal={actual == expected}")
    assert actual == expected
    pins.append(name)
print(f"All {len(pins)} exact runtime pins match.")
subprocess.run([sys.executable, "-m", "pip", "check"], check=True)
