"""Read original JPEG bytes; generate metadata and a local, offline review index."""
from pathlib import Path
from collections import Counter
import hashlib, json, html, subprocess
from datetime import datetime
from PIL import Image
root=Path(__file__).resolve().parent
repo=root.parents[2]
code='0f0747a9d449e26e93885b3bf469a726f99ffaa8'
records=json.loads((root/'capture-records.json').read_text(encoding='utf-8'))
assert len({r['file'] for r in records})==len(records)
assert {p.relative_to(root).as_posix() for p in root.rglob('*.jpg')}=={r['file'] for r in records}
code_time=datetime.fromisoformat(subprocess.check_output(['git','show','-s','--format=%cI',code],cwd=repo,text=True).strip())
items=[]
for original in records:
 r=dict(original)
 if r['state'].startswith('baseline-') and r['sourceHead']!=code:
  assert datetime.fromisoformat(r['capturedAt'].replace('Z','+00:00'))>=code_time
  r['recordedSourceHead']=r['sourceHead']
  r['sourceHead']=code
  r['metadataCorrection']='Capture closure retained prior sourceHead label; baseline batch executed after final code commit. Raw capture-records.json and JPEG bytes retained.'
 p=root/r['file']; data=p.read_bytes()
 with Image.open(p) as im: pixels=list(im.size); assert im.format=='JPEG'
 assert r['requested']==[r['dom']['width'],r['dom']['height']]
 snapshot=p.with_suffix('.txt')
 items.append({**r,'pixels':pixels,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'dimensionMatch':pixels==r['requested'],'browser':r.get('browser','Codex in-app browser'),'snapshot':snapshot.relative_to(root).as_posix(),'snapshotSha256':hashlib.sha256(snapshot.read_bytes()).hexdigest()})
items.sort(key=lambda r:(r['module'],r['state'],-r['requested'][0]))
(root/'manifest.json').write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
modules=['overview','reports','customers','suppliers','contacts','follow-ups','products','categories','product-parameters','skus','sku-packaging','sku-trade-units','product-certificates','hs-codes','inventory','inventory-movements','quotes','orders','purchase-orders','finance','receivables','payables','transactions','import','organization','access-denied','access-status-error']
for m in modules:
 for w in [1440,1280,1024]: assert any(r['module']==m and r['state']=='baseline-page' and r['requested'][0]==w and r['sourceHead']==code for r in items),(m,w)
summary={'images':len(items),'latestCodeImages':sum(r['sourceHead']==code for r in items),'latestRouteBaseline':81,'dimensionMismatches':sum(not r['dimensionMatch'] for r in items),'latestBaselineDimensionMismatches':sum(r['state']=='baseline-page' and not r['dimensionMatch'] for r in items),'originalBytes':sum(r['bytes'] for r in items),'codeHead':code,'independentVisual':'PENDING','routes':27}
(root/'evidence-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# R0-F9 原始截图清单','','每一张均为浏览器原始 JPEG，未编辑、拉伸或重编码。文件名末尾为请求视口宽度，实际像素见本表；二者不一致时保留 ISS-100 待核实。全部独立视觉待审。','','| 原图 | 请求视口 | 实际像素 | 来源代码 | SHA-256 |','|---|---|---|---|---|']
for r in items: lines.append(f"| [{r['file']}]({r['file']}) | {'×'.join(map(str,r['requested']))} | {'×'.join(map(str,r['pixels']))} | `{r['sourceHead'][:7]}` | `{r['sha256']}` |")
(root/'SCREENSHOTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
payload=json.dumps(items,ensure_ascii=False).replace('<','\\u003c')
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SUNJACK ERP · R0-F9 全站截图索引</title><style>body{font:15px/1.6 system-ui,sans-serif;margin:0;background:#f3f6f4;color:#183c33}header{padding:24px 32px;background:#143e35;color:white}main{padding:24px 32px}h1{font-size:26px;margin:0}p{max-width:1000px}nav{display:flex;gap:12px;flex-wrap:wrap;position:sticky;top:0;background:#f3f6f4;padding:14px 0;z-index:1}label{display:grid;font-size:13px}select{padding:9px;border:1px solid #a7beb3;border-radius:6px;font:inherit;max-width:240px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:18px}article{background:white;border:1px solid #d4e2da;border-radius:10px;overflow:hidden}article div{padding:14px}img{display:block;width:100%;height:auto}h2{font-size:17px;margin:0}small{display:block;overflow-wrap:anywhere}a{color:#167459}.warn{color:#a04f1d}code{font-size:12px}#count{font-weight:600}</style><header><h1>R0-F9 全站截图索引</h1><p>27 路由 · 原始页面、表单、详情与异常状态。ChatGPT 独立视觉：待审。</p></header><main><p>默认展示最终代码的 27 路由基线。预览等比显示；点击“打开原图”查看原始 JPEG。请求视口与实际像素分别列出，不把尺寸差异当作精确尺寸通过。全部文件可离线浏览。</p><p><a href="manifest.json">完整尺寸、URL、时间与 SHA-256</a> · <a href="SCREENSHOTS.md">截图清单</a> · <a href="../../R0-F9-全站UIUX最终审查.md">审查报告</a></p><nav><label>代码批次<select id="code"><option value="baseline">最终27路由基线</option><option value="latest">最终代码全部状态</option><option value="all">全部批次（含初查）</option></select></label><label>模块<select id="module"><option value="">全部模块</option></select></label><label>页面状态<select id="state"><option value="">全部状态</option></select></label><label>请求视口<select id="width"><option value="">三种视口</option><option>1440</option><option>1280</option><option>1024</option></select></label><label>尺寸<select id="dimension"><option value="">全部</option><option value="mismatch">仅像素不一致</option></select></label></nav><p id="count" role="status"></p><section class="grid" id="grid"></section></main><script>const rows=PAYLOAD,latest="CODE";const q=s=>document.querySelector(s);for(const key of ['module','state'])for(const value of [...new Set(rows.map(r=>r[key]))].sort()){const o=document.createElement('option');o.value=value;o.textContent=value;q('#'+key).append(o)}function render(){const batch=q('#code').value;const selected=rows.filter(r=>(batch==='all'||r.sourceHead===latest&&(batch!=='baseline'||r.state==='baseline-page'))&&(!q('#module').value||r.module===q('#module').value)&&(!q('#state').value||r.state===q('#state').value)&&(!q('#width').value||r.requested[0]===Number(q('#width').value))&&(!q('#dimension').value||!r.dimensionMatch));q('#count').textContent=`显示 ${selected.length} / ${rows.length} 张原图；独立视觉待审`;q('#grid').replaceChildren();for(const r of selected){const card=document.createElement('article');const detail=document.createElement('div');const title=document.createElement('h2');title.textContent=r.module+' · '+r.state;detail.append(title);for(const text of [`请求 ${r.requested.join('×')} · 实际 ${r.pixels.join('×')}`,r.browser,`代码 ${r.sourceHead}`,r.url,`SHA-256 ${r.sha256}`]){const line=document.createElement('small');line.textContent=text;detail.append(line)}if(!r.dimensionMatch){const w=document.createElement('p');w.className='warn';w.textContent='像素与请求视口不一致 · ISS-100待核实';detail.append(w)}const link=document.createElement('a');link.href=r.file;link.target='_blank';link.rel='noopener';link.textContent='打开原图';detail.append(link);const snap=document.createElement('a');snap.href=r.snapshot;snap.textContent=' · DOM观察记录';detail.append(snap);const img=document.createElement('img');img.src=r.file;img.alt=r.module+' '+r.state+' '+r.requested[0];img.loading='lazy';card.append(detail,img);q('#grid').append(card)}}for(const el of document.querySelectorAll('select'))el.addEventListener('change',render);render();</script></html>'''.replace('PAYLOAD',payload).replace('"CODE"',json.dumps(code))
(root/'index.html').write_text(page,encoding='utf-8')
fingerprints={}
for name in ['frontend','backend']:
 fingerprints[name]=subprocess.check_output(['git','rev-parse',f'{code}:{name}'],cwd=repo,text=True).strip()
(root/'source-baseline.json').write_text(json.dumps({'codeHead':code,'gitTrees':fingerprints,'note':'Final documentation-only delivery must have the same frontend/backend Git trees.'},indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
