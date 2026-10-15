"""Verify original browser JPEGs without rewriting any image."""
import hashlib
import json
from pathlib import Path
from PIL import Image
root = Path(__file__).resolve().parent
records = {r['file']: r for r in json.loads((root/'capture-records.json').read_text(encoding='utf-8'))}
items=[]
for path in sorted(root.glob('*.jpg')):
    r=records[path.name]
    with Image.open(path) as image: w,h=image.size
    requested=r['requested']
    if isinstance(requested,dict): requested=[requested['width'],requested['height']]
    assert requested==[w,h], (path.name,requested,w,h)
    assert r['dom']['width']==w and r['dom']['height']==h
    assert path.stem.rsplit('-',1)[1]==str(w)
    items.append({**r,'requested':requested,'pixels':[w,h],'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size})
(root/'manifest.json').write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# R0-F7B 原始截图清单','','Codex 内置浏览器直接返回的原始 JPEG；未编辑、缩放或重编码。DOM、请求视口、实际像素逐张核对。独立图片视觉尚待 ChatGPT 审查。','','| 文件 | 请求视口 / DOM / 实际像素 | SHA-256 |','|---|---|---|']
for r in items:
    w,h=r['pixels']; lines.append(f"| [{r['file']}]({r['file']}) | {w}×{h} / {w}×{h} / {w}×{h} | `{r['sha256']}` |")
(root/'SCREENSHOTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(f'{len(items)} original screenshots verified')
