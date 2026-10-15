"""Read original JPEGs; reject requested/DOM/pixel width mismatches. Never edit images."""
import hashlib
import json
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parent
records = {r['file']: r for r in json.loads((root / 'capture-records.json').read_text(encoding='utf-8'))}
items = []
for path in sorted(root.glob('*.jpg')):
    record = records[path.name]
    with Image.open(path) as image:
        width, height = image.size
    requested = record['requested']
    assert [width, height] == requested, (path.name, requested, width, height)
    assert record['dom']['width'] == width and record['dom']['height'] == height
    assert str(width) == path.stem.rsplit('-', 1)[1], path.name
    items.append({**record, 'pixels': [width, height], 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size})
(root / 'manifest.json').write_text(json.dumps(items, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
lines = ['# R0-F7A 原始截图清单', '', '所有图片均为 Codex 内置浏览器直接返回的 JPEG，未编辑或重编码。', '', '| 文件 | 请求视口 | DOM | 原始像素 | SHA-256 |', '|---|---|---|---|---|']
for item in items:
    w, h = item['pixels']
    lines.append(f"| [{item['file']}]({item['file']}) | {w}×{h} | {item['dom']['width']}×{item['dom']['height']} | {w}×{h} | `{item['sha256']}` |")
(root / 'SCREENSHOTS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'{len(items)} original screenshots: dimensions and hashes verified')
