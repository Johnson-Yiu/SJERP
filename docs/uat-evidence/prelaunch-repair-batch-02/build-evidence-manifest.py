"""Index original PNG bytes and successful scoped Chrome runs; never edits images."""
import hashlib
import json
import os
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if os.name == 'nt' and not str(ROOT).startswith('\\\\?\\'):
    ROOT = Path('\\\\?\\' + str(ROOT))
APP_SOURCE = '71592c9087198787baf03b22a4b5e0707b561505'
SUITES = {
    'refund': ('integrated/cancel-refund-closeout-02.spec.js', 1),
    'cost': ('integrated/cost-currency-integrity-02.spec.js', 1),
    'draft': ('integrated/product-draft-protection-01.spec.js', 1),
    'packaging': ('integrated/product-packaging-p2-05.spec.js', 1),
    'feedback-1366': ('integrated/prelaunch-p1-05-feedback-02.spec.js', 2),
    'feedback-1920': ('feedback-1920', 2),
    'related': ('related-final', 3),
    'category-tabs': ('integrated/prelaunch-ui-category-tabs-02.spec.js', 5),
    'delete-bank': ('integrated/ui-prelaunch-polish-01.spec.js', 4),
    'history': ('integrated/prelaunch-history-correction-02.spec.js', 1),
    'interaction': ('final-ui', 11),
}


def main():
    records = []
    suites = []
    # These are historical scoped captures. Later certification records its own HEAD.
    current_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    later_changes = subprocess.check_output(['git', 'diff', '--name-only', APP_SOURCE, 'HEAD', '--', 'backend', 'frontend/src'], text=True).splitlines()
    for name, (folder, count) in SUITES.items():
        directory = ROOT / folder
        runs = sorted((directory / 'artifacts').glob('*'), key=lambda p: p.stat().st_mtime)
        assert runs, name
        result = json.loads((runs[-1] / '.last-run.json').read_text(encoding='utf-8'))
        assert result['status'] == 'passed' and not result['failedTests'], (name, result)
        suites.append({'suite': name, 'directory': folder, 'run': runs[-1].name, 'testsPassed': count})
        for file in sorted(directory.rglob('*.png')):
            data = file.read_bytes()
            assert data[:8] == b'\x89PNG\r\n\x1a\n', str(file)
            width, height = struct.unpack('>II', data[16:24])
            records.append({'suite': name, 'file': file.relative_to(ROOT).as_posix(),
                            'pixels': [width, height], 'sha256': hashlib.sha256(data).hexdigest()})
    report = {
        'applicationSource': APP_SOURCE,
        'scope': 'Original scoped Chrome PNGs captured before final certification. Later source changes and final-HEAD reruns are recorded separately.',
        'indexGeneratedAtHead': current_head,
        'applicationFilesChangedSinceCapture': later_changes,
        'imageProcessing': 'None: no cropping, scaling, compositing or re-encoding.',
        'zoom': 'Default native 100%; refund/chrome/run.json records actual Chrome settings 100% and 125% and viewport metrics.',
        'suites': suites,
        'passedTests': sum(s['testsPassed'] for s in suites),
        'screenshots': records,
    }
    (ROOT / 'screenshot-manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"{report['passedTests']} scoped tests, {len(records)} original PNGs indexed")


if __name__ == '__main__':
    main()
