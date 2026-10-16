from pathlib import Path
import csv,io,json,hashlib
root=Path(__file__).resolve().parent/'files'
def emit(name,headers,rows):
    s=io.StringIO(newline='');w=csv.writer(s);w.writerow(headers);w.writerows(rows);(root/name).write_bytes(s.getvalue().encode('utf-8-sig'))
emit('A-customers-new.csv',['code','name','country','notes'],[['F8B-C01','中文客户 / Alpha & Co','China','含逗号, 引号"和换行\n第二行'],['F8B-C02','Beta测试','Germany','合成记录']])
emit('B-customers-update.csv',['code','name','country','notes'],[['F8B-C01','中文客户 Updated','China','更新内容, "确认"\n第二行']])
emit('C-customers-duplicate.csv',['code','name'],[['F8B-DUP','重复一'],['F8B-DUP','重复二']])
emit('D-customers-required.csv',['code','name'],[['F8B-BAD','']])
emit('E-skus-invalid-type.csv',['sku','product_code','cost_price'],[['F8B-BAD-S','F8B-P01','not-number']])
emit('F-skus-missing-product.csv',['sku','product_code'],[['F8B-MISSING','DOES-NOT-EXIST']])
emit('A-products-new.csv',['code','name','sales_model_prefix','description','status'],[['F8B-P01','中文产品 "灯具", Alpha','F8BP','多行\n规格说明','active']])
emit('B-products-update.csv',['code','name','sales_model_prefix','description','status'],[['F8B-P01','中文产品更新','F8BP','Updated description','active']])
emit('A-skus-new.csv',['sku','product_code','specification','unit','cost_price','default_price','currency'],[['F8B-S01','F8B-P01','5米/卷, "暖白"','pcs','2.50','5.00','USD']])
emit('B-skus-update.csv',['sku','product_code','specification','unit','cost_price','default_price','currency'],[['F8B-S01','F8B-P01','5米/卷, "暖白"','pcs','3.00','6.00','USD']])
emit('A-transactions-new.csv',['transaction_no','transaction_date','direction','category','amount','currency','exchange_rate','notes'],[['F8B-T01','2026-10-16','income','other','12.50','USD','1','合成测试, "非真实收款"']])
emit('J-transactions-duplicate.csv',['transaction_no','transaction_date','direction','category','amount'],[['F8B-T01','2026-10-16','income','other','99']])
emit('J-transactions-invalid.csv',['transaction_no','transaction_date','direction','category','amount'],[['F8B-TBAD','bad-date','invalid','other','oops']])
(root/'I-empty.csv').write_bytes(b'')
emit('I-wrong-header.csv',['wrong','columns'],[['x','y']])
(root/'I-invalid-encoding.csv').write_bytes('code,name\nF8B-GBK,中文'.encode('gbk'))
(root/'manifest.json').write_text(json.dumps([{'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in root.glob('*.csv')],indent=2),encoding='utf-8')
