"""All discovered tests, partitioned into independent serial processes (Windows safe)."""
import collections,hashlib,json,os,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'docs/uat-evidence/new-product-reminders-20261105'/os.environ.get('REMINDER_FULL_OUTPUT','sqlite-final')
assert OUT.resolve().parent==(ROOT/'docs/uat-evidence/new-product-reminders-20261105').resolve()
OUT.mkdir(exist_ok=True)
os.environ.update(DJANGO_SETTINGS_MODULE='config.settings',APP_STAGE='development',DJANGO_DEBUG='1',DEVELOPMENT_SUPERADMIN='1',RBAC_ENFORCEMENT='0',DATABASE_URL='sqlite:///:memory:',AUDIT_LOG_ENABLED='1')
os.environ['OPS_TEST_OPENSSL']='D:/Program Files/Git/usr/bin/openssl.exe'
os.environ['PYTHONUTF8']='1'
if len(sys.argv)==1:
 source_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 assert subprocess.run(['git','diff','--quiet','HEAD','--','backend','frontend','templates'],cwd=ROOT).returncode==0
 children=[]
 for index in range(3):
  stream=(OUT/f'shard-{index}.log').open('wb')
  env={**os.environ,'MEDIA_ROOT':str(OUT/f'media-{index}')}
  proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),str(index)],cwd=ROOT/'backend',env=env,stdout=stream,stderr=subprocess.STDOUT)
  children.append((index,proc,stream))
 codes=[]
 for index,proc,stream in children:
  codes.append(proc.wait());stream.close()
 manifest=[json.loads((OUT/f'shard-{i}.json').read_text(encoding='utf-8')) for i in range(3)]
 expected=manifest[0]['all_ids']
 assert all(x['all_ids']==expected for x in manifest)
 selected=[test_id for x in manifest for test_id in x['selected_ids']]
 assert collections.Counter(selected)==collections.Counter(expected),'Shard coverage must equal entire original discovery, including multiplicity'
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==source_sha
 assert subprocess.run(['git','diff','--quiet','HEAD','--','backend','frontend','templates'],cwd=ROOT).returncode==0
 result={'source_sha':source_sha,'discovered':len(expected),'selected':len(selected),'complete_coverage':True,'exit_codes':codes,'all_passed':not any(codes),'shards':[{k:v for k,v in x.items() if k not in {'all_ids','selected_ids'}} for x in manifest]}
 (OUT/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(int(any(codes)))
index=int(sys.argv[1]);sys.path.insert(0,str(ROOT/'backend'))
import django
django.setup()
from crm.test_runner import DevelopmentAccessTestRunner
class Runner(DevelopmentAccessTestRunner):
 def build_suite(self,*args,**kwargs):
  suite=super().build_suite(*args,**kwargs)
  def flatten(items):
   for item in items:
    if isinstance(item,unittest.TestSuite):yield from flatten(item)
    else:yield item
  cases=list(flatten(suite));selected=[case for n,case in enumerate(cases) if n%3==index]
  record={'index':index,'python':sys.version,'django':django.get_version(),'all_ids':[c.id() for c in cases],'selected_ids':[c.id() for c in selected],'count':len(selected),'test_assertions':'original, unchanged','execution':'serial per process; independent memory database and media'}
  (OUT/f'shard-{index}.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
  print('FULL_DISCOVERY',len(cases),'SHARD',index,'SELECTED',len(selected),flush=True)
  return unittest.TestSuite(selected)
raise SystemExit(Runner(verbosity=1,interactive=False).run_tests([]))
