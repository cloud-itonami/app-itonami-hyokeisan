#!/usr/bin/env python3
"""Synthetic, explicit two-file legacy workbook import in local Chrome.
Usage: python3 scripts/check-legacy-import-browser.py AMU_DIR BUILD_DIR OUTPUT_DIR CHROME
The fixture does not prove origin, revision consistency, or real-user migration.
"""
import functools,http.server,importlib.util,json,shutil,sys,threading,time
from pathlib import Path
if len(sys.argv)!=5: raise SystemExit(__doc__)
amu,build,out,chrome=map(lambda x:Path(x).resolve(),sys.argv[1:]);out.mkdir(parents=True,exist_ok=False)
profile=out/'profile';profile.mkdir();shutil.copytree(build,out/'site')
spec=importlib.util.spec_from_file_location('browser',amu/'scripts/seed/check-wasm32-browser.py');browser=importlib.util.module_from_spec(spec);spec.loader.exec_module(browser)
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(out)))
threading.Thread(target=server.serve_forever,daemon=True).start();pipe=browser.Pipe(str(chrome),profile)
base=f'http://127.0.0.1:{server.server_port}/';key='itonami.hyokeisan.candidate.hs1'
meta='[{"sheetId":0,"title":"A","color":"blue"},{"sheetId":"b","title":"B"}]'
grid='{"B":[["x"]],"A":[["雪",""],["=A1+2","3"]]}'
edn=lambda value:json.dumps(value,ensure_ascii=False)
attrs={':sheet/type':[edn('Spreadsheet')],':sheet/id':[edn('sheet:book:demo')],':sheet/slug':[edn('demo')],
       ':sheet/title':[edn('予算')],':sheet/revision':['7'],':sheet/sheetsJson':[edn(meta)],
       ':sheet/gridJson':[edn(grid)],':sheet/unknown':[edn('保持')]}
pull_obj={'ok':True,'graph':'bfixture','entity':'sheet:book:demo','attrs':attrs}
pull=json.dumps(pull_obj,ensure_ascii=False,separators=(',',':'))
bad_pull=json.loads(pull);bad_pull['entity']='sheet:book:other';bad_pull=json.dumps(bad_pull,ensure_ascii=False,separators=(',',':'))
hostile_pull=json.loads(pull);hostile_pull['graph']='<img src=x onerror=alert(1)>';hostile_pull=json.dumps(hostile_pull,ensure_ascii=False,separators=(',',':'))
wide_meta='[{"sheetId":0,"title":"A"}]'
wide_grid=json.dumps({'A':[['1']*1024]},separators=(',',':'))
wide_attrs=dict(attrs);wide_attrs[':sheet/title']=[edn('Wide')];wide_attrs[':sheet/sheetsJson']=[edn(wide_meta)];wide_attrs[':sheet/gridJson']=[edn(wide_grid)]
wide_pull=json.dumps({'ok':True,'graph':'bfixture','entity':'sheet:book:demo','attrs':wide_attrs},ensure_ascii=False,separators=(',',':'))
def pull_with_columns(count):
 value=dict(wide_attrs)
 value[':sheet/gridJson']=[edn(json.dumps({'A':[['1']*count]},separators=(',',':')))]
 return json.dumps({'ok':True,'graph':'bfixture','entity':'sheet:book:demo','attrs':value},ensure_ascii=False,separators=(',',':'))
near_pull=pull_with_columns(1600)
over_pull=pull_with_columns(1700)
files={}
for name,value in [('sheets',meta),('grid',grid),('invalid','{"A":[]}'),('pull',pull),('bad-pull',bad_pull),('hostile-pull',hostile_pull),('wide-meta',wide_meta),('wide-grid',wide_grid),('wide-pull',wide_pull),('near-pull',near_pull),('over-pull',over_pull)]:
 files[name]=out/(name+'.json');files[name].write_text(value,encoding='utf-8')
f=lambda s:str(len(s.encode()))+':'+s
cell=lambda r,c,v:f(str(r))+f(str(c))+f(v)
provenance='LE1|'+f('予算')+f(meta)+f(grid)
a=f('n:0')+f('A')+cell(1,1,'雪')+cell(2,1,'=A1+2')+cell(2,2,'3')
b=f('s:b')+f('B')+cell(1,1,'x')
book='HW3|'+f('予算')+f(provenance)+f(a)+f(b)
expected='HU1|'+f(book)+f('n:0')+f('1')+f('1')
pull_book='HW3|'+f('予算')+f('LE2|'+f(pull))+f(a)+f(b)
pull_expected='HU1|'+f(pull_book)+f('n:0')+f('1')+f('1')
wide_source='LE1|'+f('Wide')+f(wide_meta)+f(wide_grid)
wide_cells=''.join(cell(1,i,'1') for i in range(1,1025))
wide_book='HW3|'+f('Wide')+f(wide_source)+f(f('n:0')+f('A')+wide_cells)
wide_expected='HU1|'+f(wide_book)+f('n:0')+f('1')+f('1')
wide_pull_book='HW3|'+f('Wide')+f('LE2|'+f(wide_pull))+f(f('n:0')+f('A')+wide_cells)
wide_pull_expected='HU1|'+f(wide_pull_book)+f('n:0')+f('1')+f('1')
near_cells=''.join(cell(1,i,'1') for i in range(1,1601))
near_book='HW3|'+f('Wide')+f('LE2|'+f(near_pull))+f(f('n:0')+f('A')+near_cells)
near_expected='HU1|'+f(near_book)+f('n:0')+f('1')+f('1')
if not 34000 < len(near_expected.encode()) <= 35000:raise ValueError('near-limit fixture size')
try:
 target=pipe.call('Target.createTarget',{'url':'about:blank'})['targetId'];session=pipe.call('Target.attachToTarget',{'targetId':target,'flatten':True})['sessionId']
 pipe.call('Network.enable',{},session);pipe.call('Page.navigate',{'url':base+'site/index.html'},session)
 def ev(expr):
  r=pipe.call('Runtime.evaluate',{'expression':expr,'returnByValue':True},session)
  if 'exceptionDetails' in r:raise ValueError(r['exceptionDetails'])
  return r.get('result',{}).get('value')
 def wait(expr,label):
  until=time.time()+120
  while time.time()<until:
   try:
    if ev(expr):return
   except RuntimeError as e:
    if not any(x in str(e) for x in ('Inspected target navigated or closed','Execution context was destroyed','Cannot find context with specified id')):raise
   time.sleep(.2)
  raise TimeoutError(label+': '+str(ev("document.getElementById('status')?.textContent")))
 def choose(selector,path):
  pipe.call('DOM.enable',{},session);doc=pipe.call('DOM.getDocument',{},session)['root']['nodeId'];node=pipe.call('DOM.querySelector',{'nodeId':doc,'selector':selector},session)['nodeId']
  pipe.call('DOM.setFileInputFiles',{'nodeId':node,'files':[str(path)]},session)
 def stored():return ev('localStorage.getItem('+json.dumps(key)+')')
 def preview():
  ev("document.getElementById('legacy-preview').click()")
  wait("document.getElementById('backup-dialog').open",'preview')
 def confirm_failure(restore):
  ev("document.getElementById('status').textContent='確認待ち';document.getElementById('backup-confirm').click()")
  wait("document.getElementById('status').textContent.includes('復元できませんでした')",'failed save')
  if stored()!=baseline:raise ValueError('failed save changed original')
  ev('Storage.prototype.setItem=window.originalSetter')
  if restore and not ev("Object.keys(localStorage).some(k=>k.startsWith("+json.dumps(key+'.preimport.')+")&&localStorage.getItem(k)==="+json.dumps(baseline,ensure_ascii=False)+")"):raise ValueError('backup missing')
 wait("document.querySelector('[data-k=c0]')!==null",'initial')
 ev("(()=>{let e=document.querySelector('[data-k=c0]');e.value='既存';e.dispatchEvent(new Event('input',{bubbles:true}))})()")
 wait("document.getElementById('status').textContent==='保存しました'",'baseline');baseline=stored()
 ev("document.getElementById('legacy-title').value='予算'")
 choose('#legacy-sheets',files['sheets']);choose('#legacy-grid',files['invalid'])
 ev("document.getElementById('status').textContent='';document.getElementById('legacy-preview').click()")
 wait("document.getElementById('status').textContent.includes('旧データを読み込めません')",'missing sheet refusal')
 if stored()!=baseline:raise ValueError('invalid source changed baseline')
 choose('#legacy-grid',files['grid']);preview()
 if stored()!=baseline or ev("document.querySelector('#backup-preview [data-k=c0]')?.value")!='雪':raise ValueError('preview mismatch')
 ev("document.getElementById('backup-cancel').click()")
 if stored()!=baseline:raise ValueError('cancel changed baseline')
 preview();ev("window.originalSetter=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(this===localStorage&&k.startsWith("+json.dumps(key+'.preimport.')+"))throw Error('quota');return window.originalSetter.call(this,k,v)}")
 confirm_failure(False)
 preview();ev("Storage.prototype.setItem=function(k,v){if(this===localStorage&&k==="+json.dumps(key)+")throw Error('quota');return window.originalSetter.call(this,k,v)}")
 confirm_failure(True)
 preview();ev("localStorage.setItem("+json.dumps(key)+",'external-change');document.getElementById('status').textContent='';document.getElementById('backup-confirm').click()")
 wait("document.getElementById('status').textContent.includes('別のタブ')",'stale refusal')
 if stored()!='external-change':raise ValueError('stale preview overwrote storage')
 ev('localStorage.setItem('+json.dumps(key)+','+json.dumps(baseline,ensure_ascii=False)+')')
 preview();ev("document.getElementById('backup-confirm').click()")
 wait("document.getElementById('status').textContent==='バックアップから復元しました。'",'commit')
 if stored()!=expected:raise ValueError('import differs from independent expected bytes')
 ev("document.querySelector('[data-k=sheet-next]').click()")
 wait("document.querySelector('[data-k=c0]')?.value==='x' && document.getElementById('status').textContent==='保存しました'",'second sheet')
 saved=stored();ev('window.__reloadMarker=true');pipe.call('Page.reload',{},session);wait('window.__reloadMarker!==true','reload')
 wait("document.querySelector('[data-k=c0]')?.value==='x'",'second sheet reopen')
 if stored()!=saved or provenance not in saved:raise ValueError('reopen changed data or provenance')
 baseline=saved
 choose('#legacy-pull',files['bad-pull'])
 ev("document.getElementById('status').textContent='';document.getElementById('legacy-pull-preview').click()")
 wait("document.getElementById('status').textContent.includes('旧 pull 応答を読み込めません')",'pull identity refusal')
 if stored()!=baseline:raise ValueError('invalid pull changed storage')
 choose('#legacy-pull',files['pull'])
 def pull_preview():
  ev("document.getElementById('status').textContent='';document.getElementById('legacy-pull-preview').click()")
  wait("document.getElementById('backup-dialog').open || document.getElementById('status').textContent.includes('旧 pull 応答を読み込めません')",'pull preview')
  if not ev("document.getElementById('backup-dialog').open"):raise ValueError('pull preview refused')
 choose('#legacy-pull',files['hostile-pull']);pull_preview()
 if not ev("document.getElementById('backup-label').textContent.includes('<img src=x')") or ev("document.querySelector('#backup-label img')!==null"):raise ValueError('pull metadata rendered as markup')
 ev("document.getElementById('backup-cancel').click()")
 if stored()!=baseline:raise ValueError('hostile preview changed storage')
 choose('#legacy-pull',files['pull'])
 pull_preview()
 if stored()!=baseline or ev("document.querySelector('#backup-preview [data-k=c0]')?.value")!='雪':raise ValueError('pull preview mismatch')
 if not ev("document.getElementById('backup-label').textContent.includes('権限による欠落')"):raise ValueError('pull visibility notice missing')
 if not ev("['bfixture','sheet:book:demo','版: 7'].every(v=>document.getElementById('backup-label').textContent.includes(v))"):raise ValueError('pull identity or revision missing')
 ev("document.getElementById('backup-cancel').click()")
 if stored()!=baseline:raise ValueError('pull cancel changed state')
 pull_preview();ev("window.originalSetter=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(this===localStorage&&k.startsWith("+json.dumps(key+'.preimport.')+"))throw Error('quota');return window.originalSetter.call(this,k,v)}")
 confirm_failure(False)
 pull_preview();ev("Storage.prototype.setItem=function(k,v){if(this===localStorage&&k==="+json.dumps(key)+")throw Error('quota');return window.originalSetter.call(this,k,v)}")
 confirm_failure(True)
 pull_preview();ev("localStorage.setItem("+json.dumps(key)+",'pull-external-change');document.getElementById('status').textContent='';document.getElementById('backup-confirm').click()")
 wait("document.getElementById('status').textContent.includes('別のタブ')",'pull stale refusal')
 if stored()!='pull-external-change':raise ValueError('stale pull preview overwrote storage')
 ev('localStorage.setItem('+json.dumps(key)+','+json.dumps(baseline,ensure_ascii=False)+')')
 pull_preview();ev("document.getElementById('backup-confirm').click()")
 wait("document.getElementById('status').textContent==='バックアップから復元しました。'",'pull commit')
 if stored()!=pull_expected:raise ValueError('pull import differs from independent expected bytes')
 ev('window.__reloadMarker=true');pipe.call('Page.reload',{},session);wait('window.__reloadMarker!==true','pull reload')
 wait("document.querySelector('[data-k=c0]')?.value==='雪'",'pull reopen')
 if stored()!=pull_expected:raise ValueError('pull reopen changed response or workbook')
 ev("document.getElementById('legacy-title').value='Wide'")
 choose('#legacy-sheets',files['wide-meta']);choose('#legacy-grid',files['wide-grid']);preview()
 if stored()!=pull_expected or ev("document.querySelector('#backup-preview [data-k=c0]')?.value")!='1':raise ValueError('wide preview changed state or failed')
 ev("document.getElementById('backup-confirm').click()")
 wait("document.getElementById('status').textContent==='バックアップから復元しました。'",'wide commit')
 if stored()!=wide_expected:raise ValueError('wide import did not preserve every cell and provenance')
 choose('#legacy-pull',files['wide-pull']);pull_preview()
 if stored()!=wide_expected or ev("document.querySelector('#backup-preview [data-k=c0]')?.value")!='1':raise ValueError('wide pull preview failed or changed state')
 ev("document.getElementById('backup-confirm').click()")
 wait("document.getElementById('status').textContent==='バックアップから復元しました。'",'wide pull commit')
 if stored()!=wide_pull_expected:raise ValueError('wide pull import lost cells or response bytes')
 choose('#legacy-pull',files['near-pull']);pull_preview()
 if stored()!=wide_pull_expected:raise ValueError('near-limit preview changed state')
 ev("document.getElementById('backup-confirm').click()")
 wait("document.getElementById('status').textContent==='バックアップから復元しました。'",'near-limit commit')
 if stored()!=near_expected:raise ValueError('near-limit pull lost cells or provenance')
 choose('#legacy-pull',files['over-pull'])
 ev("document.getElementById('status').textContent='';document.getElementById('legacy-pull-preview').click()")
 wait("document.getElementById('status').textContent.includes('旧 pull 応答を読み込めません')",'over-limit refusal')
 if stored()!=near_expected or ev("document.getElementById('backup-dialog').open"):raise ValueError('over-limit pull changed state')
 requests=[e['params']['request']['url'] for e in pipe.events if e.get('method')=='Network.requestWillBeSent']
 if not requests or any(not u.startswith(base) for u in requests):raise ValueError('unexpected network request')
 (out/'result.json').write_text(json.dumps({'status':'PASS','scope':'synthetic local Chrome','checks':['mismatched sheet and pull identity refusal','two-file and pull preview/cancel','backup and primary write failure','stale storage refusal','byte-exact import and pull provenance','1024-column import','1600-column near-limit pull','1700-column over-limit refusal','second sheet and reload','local requests only'],'nearLimitBytes':len(near_expected.encode()),'limitations':['no verified old export, authorization, completeness or revision','no real user migration','no QEMU or publication']},indent=2)+'\n')
 print('PASS_LEGACY_IMPORT_BROWSER')
finally:
 pipe.close();server.shutdown();server.server_close()
