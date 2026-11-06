export const longName='R0-F2 长名称客户及照明产品系列用于办公页面换行验收'.repeat(3)
export const operator={user_id:4242,authenticated:true,development_superadmin:true,has_all_permissions:true,name:'R0-F2 QA'}
export const catalog={sources:{sales:{label:'销售报表',dimensions:['time','customer','country','category'],dates:{order_date:'订单日期',created_at:'创建时间'},note:'有效销售合同金额，按订单汇率折人民币，不代表实收。'},purchase:{label:'采购报表',dimensions:['time','supplier'],dates:{order_date:'下单日期'},note:'有效采购合同金额。'},customers:{label:'客户增长',dimensions:['time','source'],dates:{created_at:'创建时间'},note:'按档案创建时间统计。'},cash:{label:'现金收支',dimensions:['time','direction','category'],dates:{transaction_date:'发生日期'},note:'已确认收支，收入为正、支出为负。'},inventory:{label:'库存变动',dimensions:['time','warehouse'],dates:{movement_date:'发生日期'},note:'期间库存变动，不是当前余额。'}},dimensions:{time:'时间',customer:'客户',country:'国家',category:'产品主分类',supplier:'供应商',source:'来源',direction:'收支方向',warehouse:'仓库'},grains:{day:'日',month:'月',year:'年'}}
export function report(params,empty=false){
 const filters=Object.fromEntries([...params].filter(([k])=>k.startsWith('filter_')).map(([k,v])=>[k.slice(7),v]))
 const second=params.get('group_by_2')
 const rows=Array.from({length:20},(_,i)=>{const firstKey=String((i%4)+1),secondKey=String((i%3)+11);return {key:second?JSON.stringify([firstKey,secondKey]):firstKey,label:params.get('group_by')==='time'?`2026-${String(i%12+1).padStart(2,'0')}`:longName+String(i+1),groups:second?[{dimension:params.get('group_by'),key:firstKey,label:`国家 ${firstKey}`},{dimension:second,key:secondKey,label:`客户 ${secondKey}`}]:undefined,amount:String(123456789012.12-i*100),count:1,quantities:{pcs:'1234567'}}})
 return {source:params.get('source'),group_by:params.get('group_by'),group_by_2:second,date_field:params.get('date_field')||'order_date',date_label:'订单日期',period:{date_from:params.get('date_from')||'2026-01-01',date_to:params.get('date_to')||'2026-10-14'},comparison:params.get('comparison')||'previous',comparison_period:{date_from:'2025-01-01',date_to:'2025-10-14'},totals:{amount:empty?'0':'123456789012.12',count:empty?0:20,quantities:empty?{}:{pcs:'1234567'}},changes:{amount:0,count:0},rows:empty?[]:rows,filters,filter_summary:Object.entries(filters).map(([dimension,value])=>({dimension,value,label:longName,name:catalog.dimensions[dimension]})),note:'分组按当前数据口径，金额按合同汇率折人民币。'}
}
export function details(params){
 const purchase=params.get('source')==='purchase'
 return {source:params.get('source'),group_by:params.get('group_by'),group_by_2:params.get('group_by_2')||undefined,date_field:params.get('date_field')||'order_date',date_label:purchase?'下单日期':'订单日期',period:{date_from:params.get('date_from')||'2026-01-01',date_to:params.get('date_to')||'2026-10-22'},count:3,page:1,page_size:20,page_count:1,totals:{amount:'123456789012.12',count:1,quantities:{pcs:'1234567'}},rows:[{id:`${purchase?'purchase':'sales'}-item-1`,document_id:1,document_no:purchase?'PO-DETAIL-1':'SO-DETAIL-1',document_date:'2026-10-14',customer_name:purchase?'':'长名称验收客户',supplier_name:purchase?'长名称供应商':'',sku:'SKU-DETAIL',product_name:'历史商品名称',quantity:'1234567',unit:'pcs',amount:'123456789012.12',status:purchase?'ordered':'confirmed',status_display:purchase?'已下单':'已确认',is_adjustment:false}]}
}
export function dashboard(empty=false){return {date_ranges:{as_of:'2026-10-22',year_start:'2026-01-01',year_end:'2026-10-22',trend_start:'2025-11-01',trend_end:'2026-10-22'},summary:{sales_ytd:empty?0:'123456789012.12',sales_last_ytd:empty?0:'123456789012.12',orders_ytd:empty?0:30,active_customers:empty?0:20,follow_ups_due:empty?0:5,receipts_rmb:empty?0:'123456789012.12',payments_rmb:empty?0:100,certificate_attention:empty?0:3,certificate_expired:empty?0:1,certificate_expiring:empty?0:2},monthly_sales:empty?[]:Array.from({length:12},(_,i)=>({month:`${2025+Math.floor((i+11)/12)}-${String((i+10)%12+1).padStart(2,'0')}`,sales:'123456789012.12',orders:2})),category_sales:empty?[]:Array.from({length:8},(_,i)=>({sku__product__category__name:longName+i,sales:'123456789012.12'})),top_customers:empty?[]:[{id:7,name:longName,country:'China',orders:4,sales:'123456789012.12'}],due_follow_ups:empty?[]:[{id:8,customer_name:longName,subject:longName,owner:'验收员工长名称',next_follow_up:'2026-10-14'}],certificate_alerts:empty?[]:[{id:9,product_name:longName,certificate_name:longName,certificate_no:'CERT-QA-9',expires_on:'2026-10-14',expiry_state:'expiring',days_to_expiry:0}]}}
export async function mockApi(page,{restricted=false,empty=false,failDashboard=false,failCatalog=false,failReport=false}={}){
 const state={failDashboard,failCatalog,failReport,empty,reportRequests:[],detailRequests:[]}
 await page.route('**/api/**',async route=>{
  const url=new URL(route.request().url()); const path=url.pathname
  if(path.includes('current-operator')) return route.fulfill({json:restricted?{user_id:4242,authenticated:true,rbac_enforcement:true,development_superadmin:false,has_all_permissions:false,permissions:{dashboard:{view:true},reports:{view:true},customers:{view:true}}}:operator})
  if(path==='/api/dashboard/') return state.failDashboard?route.fulfill({status:400,json:{detail:'经营数据暂不可用'}}):route.fulfill({json:dashboard(state.empty)})
  if(path==='/api/reports/catalog/') return state.failCatalog?route.fulfill({status:400,json:{detail:'报表选项暂不可用'}}):route.fulfill({json:catalog})
  if(path==='/api/reports/data/') {state.reportRequests.push(url.searchParams);return state.failReport?route.fulfill({status:400,json:{detail:'报表数据暂不可用'}}):route.fulfill({json:report(url.searchParams,state.empty)})}
  if(path==='/api/reports/details/') {state.detailRequests.push(url.searchParams);return route.fulfill({json:details(url.searchParams)})}
  return route.fulfill({json:[]})
 });return state
}

export function sharedTemplateReport(params){
 const second=params.get('group_by_2')
 return {source:params.get('source')||'sales',group_by:params.get('group_by')||'time',group_by_2:second||undefined,date_field:params.get('date_field')||'order_date',date_label:'订单日期',grain:params.get('grain')||'month',comparison:params.get('comparison')||'previous',period:{date_from:params.get('date_from')||'2026-01-01',date_to:params.get('date_to')||'2026-10-23'},comparison_period:{date_from:'2025-01-01',date_to:'2025-10-23'},totals:{amount:'100',count:1,quantities:{}},changes:{amount:null,count:null},rows:[{key:second?'["1","2"]':'1',label:'中国',groups:second?[{dimension:params.get('group_by'),key:'1',label:'中国'},{dimension:second,key:'2',label:'模板客户'}]:undefined,amount:'100',count:1,quantities:{}}],filters:{},filter_summary:[],note:'共享模板测试数据。'}
}

export async function mockSharedTemplateApi(page,state,role='employee'){
 const manager=role==='manager'
 state.conflictNext = state.conflictNext || null
 const operator=manager?{authenticated:true,development_superadmin:false,has_all_permissions:false,name:'共享模板管理员',rbac_enforcement:true,permissions:{reports:{view:true,create:true,update:true,delete:true,export:true},orders:{view:true},customers:{view:true},products:{view:true},skus:{view:true},categories:{view:true}}}:{authenticated:true,development_superadmin:false,has_all_permissions:false,name:'共享模板员工',rbac_enforcement:true,permissions:{reports:{view:true},orders:{view:true},customers:{view:true},products:{view:true},skus:{view:true},categories:{view:true}}}
 await page.route('**/api/**',async route=>{
  const request=route.request();const url=new URL(request.url());const path=url.pathname
  if(path.includes('current-operator')) return route.fulfill({json:operator})
  if(path==='/api/reports/catalog/') return route.fulfill({json:catalog})
  if(path==='/api/reports/data/') return route.fulfill({json:sharedTemplateReport(url.searchParams)})
  if(path==='/api/reports/templates/' && request.method()==='GET'){
   const rows=manager?state.templates:state.templates.filter(item=>item.published)
   return route.fulfill({json:{count:rows.length,next:null,previous:null,results:rows}})
  }
  if(path==='/api/reports/templates/' && request.method()==='POST'){
   const body=request.postDataJSON();const row={id:state.nextId++,name:body.name,description:body.description||'',config:body.config,published:false,published_at:null,config_version:1,created_by:1,creator_name:manager?'共享模板管理员':'共享模板员工',updated_by:1,updater_name:manager?'共享模板管理员':'共享模板员工',created_at:'2026-10-23T09:00:00Z',updated_at:'2026-10-23T09:00:00Z',can_use:false,can_manage:manager};state.templates.push(row);return route.fulfill({status:201,json:row})
  }
  const match=path.match(/^\/api\/reports\/templates\/(\d+)\/(.*)$/)
  if(match){
   const row=state.templates.find(item=>String(item.id)===match[1]);const action=match[2].replace(/\/$/,'')
   if(!row) return route.fulfill({status:404,json:{detail:'模板不存在'}})
   if(request.method()==='GET' && action==='history') return route.fulfill({json:[]})
   if(request.method()==='POST' && ['publish','unpublish'].includes(action)){if(state.conflictNext===action){state.conflictNext=null;return route.fulfill({status:409,json:{detail:'团队模板已被其他操作更新，请刷新后重试。'}})}row.published=action==='publish';row.published_at=row.published?'2026-10-23T09:00:00Z':null;row.can_use=row.published;row.config_version+=1;return route.fulfill({json:row})}
   if(request.method()==='PATCH'){const body=request.postDataJSON();row.name=body.name||row.name;row.description=body.description||'';row.config=body.config||row.config;row.config_version+=1;row.updated_at='2026-10-23T09:05:00Z';return route.fulfill({json:row})}
   if(request.method()==='DELETE'){state.templates=state.templates.filter(item=>item!==row);return route.fulfill({status:204,body:''})}
  }
  return route.fulfill({json:[]})
 });return state
}
