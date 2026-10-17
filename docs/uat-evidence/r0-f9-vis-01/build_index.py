"""Read original JPEG bytes; generate metadata/index, never transform images."""
import hashlib
import html
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent / 'r0-f9'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name, value):
    (ROOT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

old = json.loads((OLD/'manifest.json').read_text(encoding='utf-8'))
assert len(old) == 573
assert all(digest(OLD/x['file']) == x['sha256'] for x in old)
for x in old:
    with Image.open(OLD/x['file']) as im: assert list(im.size) == x['pixels']
records = json.loads((ROOT/'capture-records.json').read_text(encoding='utf-8'))
assert len({x['file'] for x in records}) == len(records)
manifest = []
for r in records:
    p = ROOT/r['file']
    with Image.open(p) as im: size = list(im.size)
    assert size == r['pixels'] and digest(p) == r['sha256']
    x = dict(r, bytes=p.stat().st_size, snapshot=r['file'].replace('.jpg','.txt'))
    x['snapshotSha256'] = digest(ROOT/x['snapshot'])
    x['role'] = 'diagnostic'
    if r['state'] == 'final-page' and r['module'] != 'sku-trade-units' or r['state'] == 'final-ready-page':
        x['role'] = 'final-route-baseline'
    elif r['state'] in ['complete-form','complete-detail','from-quote-complete','role-detail','actual-api-unavailable','actual-api-recovered','blank-cancel-complete']:
        text = (ROOT/x['snapshot']).read_text(encoding='utf-8')
        if r['state'] != 'complete-detail' or 'dialog ' in text or 'article "关联详情"' in text:
            x['role'] = 'representative'
    x['status'] = ('READY_PENDING_INDEPENDENT_VISUAL' if x['dimensionMatch'] else 'BLOCKED_EXACT_DIMENSIONS') if x['role'] != 'diagnostic' else 'DIAGNOSTIC_NOT_FINAL'
    manifest.append(x)
final = [x for x in manifest if x['role'] == 'final-route-baseline']
assert len(final) == 81 and len({x['module'] for x in final}) == 27
assert all(x.get('frameStable') for x in final)
assert all(x['before']['width'] == x['requested'][0] and x['after']['width'] == x['requested'][0] for x in final)
for module in {x['module'] for x in final}:
    group = [x for x in final if x['module'] == module]
    assert len({x['sha256'] for x in group}) == 3, module
exceptions = []
for x in old:
    if x['pixels'] == x['requested']: continue
    candidates = [y for y in final if y['module'] == x['module'] and y['requested'] == x['requested']]
    if x['module'] == 'chrome':
        candidates = [y for y in manifest if y['module'] == 'chrome' and y['requested'] == x['requested'] and 'skus' in y['state']]
    if 'new' in x['state']:
        candidates = [y for y in manifest if y['module'] == x['module'] and y['state'] == 'complete-form' and y['requested'] == x['requested']] or candidates
    exceptions.append(dict(old=x['file'],requested=x['requested'],oldPixels=x['pixels'],oldSha256=x['sha256'],
        replacement=[y['file'] for y in candidates],
        disposition='RECAPTURED' if candidates and all(y['dimensionMatch'] for y in candidates) else 'BLOCKED_EXACT_DIMENSIONS',
        scope='Current equivalent page/form; historical operation is not reasserted'))
assert len(exceptions) == 69
loading = []
for module, states in {
    'products':['baseline-detail-1280','baseline-detail-1440','final-status-visible-1280','final-status-visible-1440'],
    'orders':['baseline-detail-1440','from-quote-detail-1280','from-quote-detail-1440'],
    'inventory':['baseline-page-1440','final-page-1440'],
    'sku-trade-units':['baseline-page-1440','final-page-1440'],
    'organization':['final-page-1440'],
}.items():
    for state in states:
        width = int(state.rsplit('-',1)[1])
        target = 'complete-detail' if module == 'products' or module == 'orders' else 'final-ready-page' if module == 'sku-trade-units' else 'final-page'
        if state.startswith('from-quote'): target = 'from-quote-complete'
        replacement = f'{module}/{target}-{width}.jpg'
        r = next(x for x in manifest if x['file'] == replacement)
        loading.append(dict(old=f'{module}/{state}.jpg',replacement=replacement,frameStable=r['frameStable'],
                            dimensionMatch=r['dimensionMatch'],status=r['status'],businessLoad='COMPLETE'))
write('loading-comparison-12.json',loading)
write('manifest.json',manifest)
write('dimension-exceptions-69.json',exceptions)
write('evidence-summary.json',dict(images=len(manifest),original573HashesVerified=True,finalRouteBaseline=81,
    finalDimensionPass=sum(x['dimensionMatch'] for x in final),finalDimensionBlocked=sum(not x['dimensionMatch'] for x in final),
    independentVisual='PENDING',runtimeSourceHead='9d05a70c07d1d8eb9d080dd1d75ea608209a799b',
    runtimeCodeChanged=False,originalImagesModified=False,issue099='NEEDS_VERIFICATION_NOT_REPRODUCED',
    dimensionsBlocked=[x['file'] for x in final if not x['dimensionMatch']]))
lines=['# R0-F9-VIS-01 原始截图','', '所有 JPEG 均来自受支持浏览器截图接口，未缩放、补边、裁切或重编码。',
       '最终路由基线只使用 role=final-route-baseline；诊断图不可充当完成态。独立视觉待审。','',
       '|文件|请求|实际|状态|SHA-256|','|---|---|---|---|---|']
for x in manifest: lines.append(f"|[{x['file']}]({x['file']})|{x['requested']}|{x['pixels']}|{x['status']}|{x['sha256']}|")
(ROOT/'SCREENSHOTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
cards=[]
for x in manifest:
    attrs=' '.join(f'data-{k}="{html.escape(str(v))}"' for k,v in dict(module=x['module'],state=x['state'],width=x['requested'][0],role=x['role'],status=x['status']).items())
    cards.append(f'<article {attrs}><h3>{html.escape(x["file"])}</h3><p>{x["pixels"]} / 请求{x["requested"]} · {x["status"]}</p><a href="{x["file"]}" target="_blank"><img src="{x["file"]}"></a><details><summary>原图信息 / DOM</summary><a href="{x["snapshot"]}">DOM文本</a><pre>{html.escape(json.dumps(x,ensure_ascii=False,indent=2))}</pre></details></article>')
compare=[]
for x in exceptions:
    targets=' '.join(f'<a href="{y}">{y}</a>' for y in x['replacement']) or 'BLOCKED / 无等价原图'
    compare.append(f'<li><a href="../r0-f9/{x["old"]}">旧图 {x["old"]}</a> → {targets} · {x["disposition"]}</li>')
for x in loading:
    compare.append(f'<li>加载状态：<a href="../r0-f9/{x["old"]}">{x["old"]}</a> → <a href="{x["replacement"]}">{x["replacement"]}</a> · COMPLETE / {x["status"]}</li>')
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>R0-F9-VIS-01 视觉证据</title>
<style>body{font:15px system-ui;background:#f3f6f5;color:#183c33;margin:24px}header{position:sticky;top:0;background:#fff;padding:14px;z-index:2}main{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}article{background:#fff;padding:12px;border:1px solid #ccd9d3;min-width:0}img{width:100%;height:auto}h3{font-size:14px;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere}select{padding:8px;margin:4px}[hidden]{display:none}</style>
<header><h1>R0-F9-VIS-01 原始截图索引</h1><p>独立视觉待审。BLOCKED尺寸不能标为精确像素通过。点击图片查看未修改原图。</p>
<select id="role"><option value="final-route-baseline">最终81张路由基线</option><option value="representative">代表表单/详情</option><option value="diagnostic">诊断过程（不可验收）</option><option value="">全部</option></select>
<select id="module"><option value="">全部模块</option>MODULES</select><select id="width"><option value="">全部视口</option><option>1440</option><option>1280</option><option>1024</option></select><select id="state"><option value="">全部页面状态</option>STATES</select><span id="count"></span></header>
<details><summary>旧69张尺寸异常图逐项对照</summary><ol>COMPARE</ol></details><main>CARDS</main>
<script>function filter(){let n=0;document.querySelectorAll('article').forEach(a=>{a.hidden=['role','module','width','state'].some(k=>document.getElementById(k).value&&document.getElementById(k).value!==a.dataset[k]);if(!a.hidden)n++});document.getElementById('count').textContent=n+' 张'}document.querySelectorAll('select').forEach(s=>s.onchange=filter);filter()</script></html>'''
page=page.replace('STATES',''.join(f'<option>{html.escape(s)}</option>' for s in sorted({x['state'] for x in manifest}))).replace('MODULES',''.join(f'<option>{html.escape(m)}</option>' for m in sorted({x['module'] for x in manifest}))).replace('CARDS',''.join(cards)).replace('COMPARE',''.join(compare))
(ROOT/'index.html').write_text(page,encoding='utf-8')
print(json.dumps(json.loads((ROOT/'evidence-summary.json').read_text(encoding='utf-8')),ensure_ascii=False))
