"""Run the existing purchase-page source regression without installing dependencies."""
from pathlib import Path
import subprocess
import sys
import zipfile

root = Path(__file__).resolve().parents[3]
version = subprocess.run(['node', '--version'], capture_output=True)
result = subprocess.run(['node', '--test', 'src/views/PurchaseOrderPage.test.js'], cwd=root / 'frontend', capture_output=True)
raw = b'COMMAND: node --test src/views/PurchaseOrderPage.test.js\n' + version.stdout + result.stdout + result.stderr + f'\nEXIT={result.returncode}\n'.encode()
with zipfile.ZipFile(Path(__file__).with_name('frontend.raw.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
    archive.writestr('frontend.raw.log', raw)
sys.stdout.buffer.write(raw)
raise SystemExit(result.returncode)
