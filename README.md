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
- 已保存报价是不可变快照。调整价格、明细或条款时请使用“创建修订版”；原报价保留不变，新版本按 `<根报价号>-1`、`<根报价号>-2` 顺序编号，并在报价列表中分别保留历史记录。
- 编辑器中的“预览 PI”只预览当前草稿，不会保存。保存并导出后，Excel 文件名严格使用完整报价号，例如 `SJ20260815DE001-2.xlsx`；工作表中的 `Invoice No.` 与文件名中的报价号完全一致。

PI Excel 由后端调用 Node.js 执行 `scripts/generate_quote_xlsx.mjs` 生成。部署机器需安装 Node.js，并确保项目根目录可解析 `@oai/artifact-tool`。如果 `node` 不在 `PATH` 中，可设置 `QUOTE_XLSX_NODE_BINARY` 为 Node.js 可执行文件的绝对路径。请保留 `文档/PI模板Proforma Invoice Sunjack Lighting.xlsx` 的文件名和路径，导出会在原模板布局上填充动态明细。

## PostgreSQL 切换

安装 PostgreSQL 驱动并设置环境变量：

```powershell
pip install psycopg[binary]
$env:DATABASE_URL="postgresql://user:password@localhost:5432/senju"
python backend/manage.py migrate
```

## CSV 导入

系统内“数据导入”页面提供客户、产品、SKU、订单、流水的模板字段说明。建议按客户 → 产品 → SKU → 订单 → 流水的顺序导入，以便自动建立关联。
