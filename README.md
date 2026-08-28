# 森爵外贸 CRM + ERP

面向小型外贸团队的轻量业务管理系统。首版覆盖客户、联系人、跟进、产品与 SKU、报价、订单、财务流水、CSV 导入和经营仪表盘。

## 关联详情

- 所有业务列表均支持点击整行打开详情抽屉。
- 客户可查看联系人、订单、采购明细、报价、跟进和财务流水。
- 产品可查看 SKU、销售订单、库存流水、结构化参数和证书档案。
- 联系人、SKU、报价、订单、跟进、流水等记录可继续点击关联数据递进查看。
- 产品参数、产品证书、库存流水提供独立的新建、编辑和删除管理页面。

## 技术栈

- 前端：Vue 3 + Vite
- 后端：Django + Django REST Framework
- 数据库：默认 SQLite，可通过环境变量切换 PostgreSQL

## 本地启动

Windows 首次使用可在项目根目录直接执行：

```powershell
.\setup.ps1
.\start.ps1
```

也可以分步启动：

```powershell
# 后端
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
python backend/manage.py migrate
python backend/manage.py seed_demo
python backend/manage.py runserver

# 新终端启动前端
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5191`。后端 API 位于 `http://localhost:8100/api/`。

## 报价与 PI 工作流

- 在“SKU 管理”的新建或编辑弹窗中上传产品图片；支持 GIF、JPEG、PNG 和 WebP。图片随 SKU 保存，重新打开 SKU 仍可预览，也可在编辑时清除。
- 已保存报价是不可变快照。调整价格、明细或条款时请使用“创建修订版”，并填写本次修改说明；原报价保留不变。新版本仍按 `<根报价号>-1`、`<根报价号>-2` 顺序编号，但会记录实际从哪个版本修改而来。
- 编辑器中的“预览 PI”只预览当前草稿，不会保存。保存并导出后，Excel 文件名严格使用完整报价号，例如 `SJ20260815DE001-2.xlsx`；工作表中的 `Invoice No.` 与文件名中的报价号完全一致。

PI Excel 由后端读取已保存的报价快照，组装 Export DTO 后调用 Node.js 执行 `scripts/generate_quote_xlsx.mjs`。部署机器需安装 Node.js，并确保项目根目录可解析 `@oai/artifact-tool`；如果 `node` 不在 `PATH` 中，可设置 `QUOTE_XLSX_NODE_BINARY` 为 Node.js 可执行文件的绝对路径。

默认模板位于 `templates/quotation/报价单模板.xlsx`。字体、颜色、Logo、边框、列宽、静态文案、打印设置等请直接编辑该文件；代码会保留其样式并只填入数据、复制动态商品行、插入图片和移动下方区域。模板中动态区域的位置集中在 `scripts/quotation_template_config.mjs`，仅在更改数据槽位或行结构时才需同步修改该映射。

## PostgreSQL 切换

## 报价工作台日常流程

1. 在“报价管理”点击任一报价，打开报价专用工作台；概览页可直接预览 PI、导出 Excel、创建迭代版或转为订单。
2. 在“版本谱系”以树状关系查看原始报价及全部迭代版；每个版本保留自己的商品和价格快照、修改说明与直接来源版本。查看其他版本详情后，可用“返回上一版本”回到原版本。
3. 在“重要备注”记录需要跨版本追溯的沟通信息。备注会显示在该原始报价的全部版本中，并标明来源版本；不再生效的备注会保留并以删除线显示，同时记录最近一次失效的时间与操作人，可恢复生效。备注可能已过时，且不一定适用于最终订单，因此不会写入 PI 或 Excel。
4. 点击“转为订单”进入预填订单草稿，补充交期后保存。保存成功会将来源报价标记为“已接受”；同一版本可转出多张订单，订单分页会汇总整个报价链的转单历史。

安装 PostgreSQL 驱动并设置环境变量：

```powershell
pip install psycopg[binary]
$env:DATABASE_URL="postgresql://user:password@localhost:5432/senju"
python backend/manage.py migrate
```

## CSV 导入

系统内“数据导入”页面提供客户、产品、SKU、订单、流水的模板字段说明。建议按客户 → 产品 → SKU → 订单 → 流水的顺序导入，以便自动建立关联。
