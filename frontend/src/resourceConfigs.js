export const resourceConfigs = {
  suppliers: {
    title: '供应商管理', eyebrow: 'Supplier directory', endpoint: 'suppliers', key: 'name',
    description: '维护采购供应商、二字代码、主要产品、联系人与付款条款。',
    columns: [['name', '供应商'], ['code', '二字代码', 'tag'], ['country', '国家/地区'], ['main_products', '主要产品'], ['supply_category_names', '可供分类', 'labels'], ['contact_name', '联系人'], ['phone', '电话'], ['email', '邮箱'], ['store_url', '店铺链接'], ['payment_terms', '付款条款']],
    fields: [['name', '供应商名称', 'text', true], ['code', '二字代码', 'text', true], ['country', '国家/地区'], ['main_products', '主要产品'], ['contact_name', '联系人'], ['phone', '电话'], ['email', '邮箱', 'email'], ['store_url', '店铺链接', 'url'], ['payment_terms', '付款条款'], ['supply_categories', '可供产品分类', 'remote_multi', true, 'categories/tree', 'name'], ['notes', '备注', 'textarea']],
    detail: true,
  },
  customers: {
    title: '客户管理', eyebrow: 'Customer portfolio', endpoint: 'customers', key: 'name',
    description: '集中维护客户画像与归属；客户阶段由跟进、报价和正式订单自动更新。下次跟进由最新跟进记录自动更新。',
    columns: [
      ['name', '客户名称'], ['code', '客户编号'], ['status', '状态', 'status'], ['country', '国家/地区'], ['region', '业务区域'],
      ['owner', '负责人'], ['next_follow_up', '下次跟进', 'date'], ['order_count', '订单数', 'number'], ['sales_amount', '累计销售额', 'rmb'],
    ],
    fields: [
      ['code', '客户编号', 'readonly', true], ['name', '客户名称', 'text', true], ['country', '国家/地区'], ['region', '业务区域'], ['source', '客户来源', 'combo', false, 'customers/sources'],
      ['owner', '负责人'], ['website', '网站', 'url'], ['address', '地址', 'textarea'], ['notes', '备注', 'textarea'],
    ],
    detail: true,
  },
  contacts: {
    title: '联系人', eyebrow: 'Contacts', endpoint: 'contacts', key: 'name',
    description: '记录客户关键联系人与决策链信息。',
    columns: [['customer_name', '所属客户'], ['name', '姓名'], ['title', '职位'], ['email', '邮箱'], ['phone', '电话'], ['whatsapp', 'WhatsApp'], ['is_primary', '主联系人', 'boolean']],
    fields: [
      ['customer', '所属客户', 'remote', true, 'customers', 'name'], ['name', '姓名', 'text', true], ['title', '职位'], ['email', '邮箱', 'email'],
      ['phone', '电话'], ['whatsapp', 'WhatsApp'], ['is_primary', '设为主联系人', 'checkbox'], ['notes', '备注', 'textarea'],
    ],
    detail: true,
  },
  'follow-ups': {
    title: '跟进记录', eyebrow: 'Relationship cadence', endpoint: 'follow-ups', key: 'subject',
    description: '保存每次沟通、结果与明确的下一步动作。',
    columns: [['followed_at', '跟进时间', 'datetime'], ['customer_name', '客户'], ['subject', '主题'], ['type_display', '方式', 'tag'], ['result', '结果'], ['next_follow_up', '下次跟进', 'date'], ['owner', '跟进人']],
    fields: [
      ['customer', '客户', 'remote', true, 'customers', 'name'], ['contact', '联系人', 'remote', false, 'contacts', 'name'], ['followed_at', '跟进时间', 'datetime-local', true],
      ['type', '跟进方式', 'combo', true, 'follow-ups/methods'],
      ['subject', '主题'], ['content', '跟进记录 / 解决方案', 'richtext'], ['result', '客户回复 / 客户疑问', 'richtext'], ['next_action', '下一步'], ['next_follow_up', '下次跟进', 'date'], ['owner', '跟进人'],
    ],
    detail: true,
  },
  products: {
    title: '产品管理', eyebrow: 'Product catalog', endpoint: 'products', key: 'name',
    description: '按产品族维护销售目录；具体销售规格在 SKU 中管理。',
    columns: [['code', '产品编号'], ['name', '产品名称'], ['category_name', '分类'], ['status', '状态', 'status'], ['sku_count', 'SKU 数', 'number'], ['parameter_count', '参数', 'number'], ['certificate_count', '证书', 'number']],
    fields: [
      ['code', '产品编号', 'text', true], ['name', '产品名称', 'text', true], ['category', '产品分类', 'remote', false, 'categories', 'name'],
      ['status', '状态', 'select', true, { active: '在售', development: '开发中', discontinued: '停产' }], ['description', '产品描述', 'textarea'],
    ],
    detail: true,
  },
  skus: {
    title: 'SKU 管理', eyebrow: 'Sellable variants', endpoint: 'skus', key: 'display_name_cn',
    description: '管理实际报价和下单使用的规格、成本、单位与默认售价。',
    columns: [['display_name_cn', '内部名称'], ['sales_model', '对外型号'], ['sku_code', 'SKU Code'], ['specification', '规格'], ['stock_quantity', '库存', 'number'], ['unit', '单位'], ['cost_price', '成本价', 'money'], ['default_price', '默认售价', 'money'], ['currency', '币种', 'tag'], ['active', '启用', 'boolean']],
    fields: [
      ['product', '所属产品', 'remote', true, 'products', 'name'], ['sku', 'SKU', 'text', true], ['specification', '规格'], ['unit', '单位'],
      ['cost_price', '成本价', 'number'], ['default_price', '默认售价', 'number'], ['currency', '币种', 'select', true, { USD: 'USD', CNY: 'CNY', EUR: 'EUR', GBP: 'GBP' }], ['active', '启用', 'checkbox'],
    ],
    detail: true,
  },
  transactions: {
    title: '财务流水', eyebrow: 'Cash ledger', endpoint: 'transactions', key: 'transaction_no',
    description: '登记实际收支，并追溯到客户和订单。所有人民币汇总按发生时汇率计算。',
    columns: [['transaction_date', '日期', 'date'], ['transaction_no', '流水号'], ['direction_display', '方向', 'direction'], ['category', '分类'], ['customer_name', '客户'], ['order_no', '归属订单'], ['amount', '金额', 'money'], ['currency', '币种', 'tag'], ['rmb_amount', '折合人民币', 'rmb']],
    fields: [
      ['transaction_no', '流水号', 'text', true], ['transaction_date', '发生日期', 'date', true], ['direction', '收支方向', 'select', true, { income: '收入', expense: '支出' }],
      ['category', '收支分类', 'text', true], ['amount', '金额', 'number', true], ['currency', '币种', 'select', true, { USD: 'USD', CNY: 'CNY', EUR: 'EUR', GBP: 'GBP' }], ['exchange_rate', '对人民币汇率', 'number', true],
      ['customer', '关联客户', 'remote', false, 'customers', 'name'], ['supplier', '关联供应商', 'remote', false, 'suppliers', 'name'], ['order', '关联订单', 'remote', false, 'orders', 'order_no'], ['purchase_order', '关联采购单', 'remote', false, 'purchase-orders', 'purchase_no'], ['payment_method', '支付方式'], ['reference', '外部参考号'], ['notes', '备注', 'textarea'],
    ],
    detail: true,
  },
  categories: {
    title: '产品分类', eyebrow: 'Catalog structure', endpoint: 'categories', key: 'name',
    description: '用于经营分析的产品大类，保持简洁稳定即可。',
    columns: [['name', '分类名称'], ['product_count', '产品数', 'number'], ['description', '说明']],
    fields: [['name', '分类名称', 'text', true], ['description', '说明', 'textarea']],
    detail: true,
  },
  'inventory-movements': {
    title: '库存流水', eyebrow: 'Inventory ledger', endpoint: 'inventory-movements', key: 'movement_no',
    description: '按 SKU 记录真实出入库，自动形成当前库存。',
    columns: [['movement_date', '日期', 'date'], ['movement_no', '流水号'], ['type_display', '类型', 'tag'], ['sku_code', 'SKU'], ['product_name', '产品'], ['signed_quantity', '库存变动', 'signed'], ['overage_summary', '超到说明'], ['reversal_status', '冲销状态'], ['warehouse', '仓库'], ['related_order_nos', '关联订单']],
    fields: [
      ['movement_no', '流水号', 'readonly'], ['movement_date', '发生日期', 'date', true],
      ['type', '类型', 'select', true, { adjust_in: '盘盈入库', adjust_out: '盘亏出库', sample_out: '样品出库', return_in: '客户退回', transfer_in: '调拨入库', transfer_out: '调拨出库', production_in: '生产入库', production_out: '生产领料', other_in: '其他入库', other_out: '其他出库' }],
      ['sku', 'SKU', 'remote', true, 'skus', 'sku'], ['order', '关联订单', 'remote', false, 'orders', 'order_no'], ['quantity', '数量', 'number', true],
      ['warehouse', '仓库'], ['unit_cost', '单位成本', 'number'], ['reference', '参考号'], ['notes', '备注', 'textarea'],
    ], detail: true,
  },
  'product-parameters': {
    title: '产品参数', eyebrow: 'Product specifications', endpoint: 'product-parameters', key: 'name',
    description: '将功率、色温、尺寸、防护等级等规格结构化保存。',
    columns: [['product_name', '产品'], ['group', '分组'], ['name', '参数名称'], ['value', '参数值'], ['unit', '单位'], ['sort_order', '排序', 'number']],
    fields: [['product', '所属产品', 'remote', true, 'products', 'name'], ['group', '参数分组'], ['name', '参数名称', 'text', true], ['value', '参数值', 'text', true], ['unit', '单位'], ['sort_order', '排序', 'number']],
    detail: true,
  },
  'product-certificates': {
    title: '产品证书', eyebrow: 'Compliance documents', endpoint: 'product-certificates', key: 'name',
    description: '管理 CE、RoHS、UL 等证书编号、机构和有效期。',
    columns: [['product_name', '产品'], ['name', '证书名称'], ['certificate_no', '证书编号'], ['issuer', '签发机构'], ['issued_date', '签发日期', 'date'], ['expires_on', '有效期至', 'date'], ['expiry_status', '有效状态']],
    fields: [['product', '所属产品', 'remote', true, 'products', 'name'], ['name', '证书名称', 'text', true], ['certificate_no', '证书编号'], ['issuer', '签发机构'], ['issued_date', '签发日期', 'date'], ['expires_on', '有效期至', 'date'], ['file_url', '文件链接', 'url'], ['notes', '备注', 'textarea']],
    detail: true,
  },
}
