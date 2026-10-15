"""Read original JPEGs to make an inventory; never modifies an image."""
from pathlib import Path
from hashlib import sha256
import json
from PIL import Image

root = Path(__file__).resolve().parent
items = []
for path in sorted(root.glob('*.jpg')):
    with Image.open(path) as image:
        width, height = image.size
    requested = int(path.stem.rsplit('-', 1)[1])
    items.append(dict(file=path.name, viewport_requested=[requested, 1000], image_pixels=[width,height], bytes=path.stat().st_size, sha256=sha256(path.read_bytes()).hexdigest(), source='Codex in-app browser tab.screenshot({fullPage:false})', captured_on='2026-10-15'))
(root/'manifest.json').write_text(json.dumps(items, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
lines=['# R0-F6 原始截图清单', '', '| 文件 | 请求视口 | 原图像素 | SHA-256 |','|---|---|---|---|']
for row in items:
    lines.append(f"| [{row['file']}]({row['file']}) | {row['viewport_requested'][0]}×1000 | {row['image_pixels'][0]}×{row['image_pixels'][1]} | `{row['sha256']}` |")
(root/'SCREENSHOTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(f'{len(items)} original JPEGs inventoried')
