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

## PostgreSQL 切换

安装 PostgreSQL 驱动并设置环境变量：

```powershell
pip install psycopg[binary]
$env:DATABASE_URL="postgresql://user:password@localhost:5432/senju"
python backend/manage.py migrate
```

## CSV 导入

系统内“数据导入”页面提供客户、产品、SKU、订单、流水的模板字段说明。建议按客户 → 产品 → SKU → 订单 → 流水的顺序导入，以便自动建立关联。
