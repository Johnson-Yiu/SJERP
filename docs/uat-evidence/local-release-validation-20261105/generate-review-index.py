"""Index curated issue mappings to actual test declarations and assertions, not acceptance."""
import ast
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent / "REVIEW-INDEX.md"
source=ROOT / "docs/uat-evidence/integration-closeout-02/review-backlog.json"
rows=json.loads(source.read_text(encoding="utf-8"))["rows"]
if len(rows)!=86 or len({r["id"] for r in rows})!=86:
    raise SystemExit("Expected the preserved 86 unique issue mappings")

def reference(path, line=1):
    return "[" + path.replace("|", "\\|") + ":" + str(line) + "](../../../" + path.replace(" ", "%20") + "#L" + str(line) + ")"

def tests(path, issue):
    file=ROOT/path
    if not file.is_file(): return []
    try: lines=file.read_text(encoding="utf-8").splitlines()
    except (UnicodeError, OSError): return []
    candidates=[]
    if file.suffix==".py":
        try: tree=ast.parse("\n".join(lines))
        except SyntaxError: return []
        for node in ast.walk(tree):
            if isinstance(node,(ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                block=lines[node.lineno-1:node.end_lineno]
                assertion=next(((node.lineno+i,line.strip()) for i,line in enumerate(block) if re.search(r"\bassert\b|self\.assert",line)),None)
                if assertion: candidates.append((node.name,node.lineno,*assertion))
    else:
        for i,line in enumerate(lines):
            if re.search(r"\b(?:it|test)\s*\(",line):
                a=next(((n+1, lines[n].strip()) for n in range(i+1,min(len(lines),i+120)) if "expect(" in lines[n] or "assert." in lines[n]),None)
                if a: candidates.append((line.strip()[:100],i+1,*a))
    if issue.lower() in "\n".join(lines).lower():
        candidates.sort(key=lambda c: issue.lower() not in "\n".join(lines[max(0,c[1]-5):c[1]+8]).lower())
    return candidates[:2]

out=["# 87 项待复审：代码、断言与证据索引", "", "范围：继承原 86 条经人工整理的映射并单列 ISS-121；映射不是独立审查结论。下列断言是该映射测试文件内可直接查看的候选，**不保证每一条候选断言单独证明该 Issue**；需按业务关闭条件审阅完整测试和证据。没找到断言时标记待补，不因文件存在视为通过。", "", "源码映射继承 02140bf；当前交付必须另核对应用树对象。历史运行证据的 SHA 和失败不能随索引重写。", ""]
for row in rows:
    issue=row["id"]; out.extend([f"## {issue} — {', '.join(row.get('module', []))}", ""])
    impl=[e for e in row.get("code_entries",[]) if e.get("role")!="test" and (ROOT/e["path"]).is_file()]
    out.append("- 实现入口：" + ("；".join(reference(e["path"]) for e in impl[:4]) if impl else "未定位，需核查"))
    test_entries=[e for e in row.get("code_entries",[]) if e.get("role")=="test" or e["path"].endswith((".test.js", ".spec.js"))]
    found=[]
    for entry in test_entries:
        path=entry["path"]
        for name,line,assert_line,expr in tests(path,issue):
            found.append(f"{reference(path,line)} `{name}`；{reference(path,assert_line)} `{expr[:140].replace('`', chr(39))}`")
        if len(found)>=3: break
    if not found and issue in ("ISS-101", "ISS-102"):
        found=[reference("docs/uat-evidence/r0-f9-vis-01/capture-workflow.js", 3) + " 采集工具拒绝未稳定/仍加载状态；视口及帧校验见第 4–5 行，需与真实记录逐图核对（不是业务单元测试）"]
    out.append("- 断言候选：" + ("；".join(found[:3]) if found else "未自动定位可审阅断言；须人工补充"))
    artifacts=[]
    for item in row.get("evidence",{}).get("item_sources",[]):
        for a in item.get("artifact_refs",[]):
            path=a.get("resolved_path","")
            if path and (ROOT/path).is_file() and path not in artifacts: artifacts.append(path)
    out.append("- 原始证据：" + ("；".join(reference(path) for path in artifacts[:3]) if artifacts else "见原复审包，具体原始证据须人工补齐"))
    gaps=row.get("closing_gaps",[])
    if gaps: out.append("- 待独立复审：" + str(gaps[0].get("statement", "见原清单")).replace("\n"," "))
    out.append("")
out.extend(["## ISS-121 — 历史接续", "", "- 实现、逐项断言、历史资金/库存/履约合成证据及未决边界见 [ISS-121 复审补充](../integration-closeout-02/ISS121-REVIEW-SUPPLEMENT.md)。", "- 三表追加保护：[合同测试](../../../backend/crm/tests/test_history_operational_contracts.py#L75)；财务与库存见同一补充文档中的具名断言。", "- 本索引不是独立接受，不关闭任何 Issue。", ""])
OUT.write_text("\n".join(out),encoding="utf-8")
print("indexed", len(rows)+1, "issues; assertion candidates require independent review")
