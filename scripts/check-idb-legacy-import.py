#!/usr/bin/env python3
"""Synthetic, explicit legacy workbook import into transactional storage in local Chrome.
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
grid='{"B":[["x","=12/-3"],["","=9/2"]],"A":[["雪",""],["=A1+2","3"]]}'
edn=lambda value:json.dumps(value,ensure_ascii=False)
attrs={':sheet/type':[edn('Spreadsheet')],':sheet/id':[edn('sheet:book:demo')],':sheet/slug':[edn('demo')],
       ':sheet/title':[edn('予算')],':sheet/revision':['7'],':sheet/sheetsJson':[edn(meta)],
       ':sheet/gridJson':[edn(grid)],':sheet/unknown':[edn('保持')]}
pull_obj={'ok':True,'graph':'bfixture','entity':'sheet:book:demo','attrs':attrs}
pull=json.dumps(pull_obj,ensure_ascii=False,separators=(',',':'))+'\n'
bad_pull=json.loads(pull);bad_pull['entity']='sheet:book:other';bad_pull=json.dumps(bad_pull,ensure_ascii=False,separators=(',',':'))
hostile_pull=json.loads(pull);hostile_pull['graph']='<img src=x onerror=alert(1)>';hostile_pull=json.dumps(hostile_pull,ensure_ascii=False,separators=(',',':'))
wide_meta='[{"sheetId":0,"title":"A"}]'
hostile_title='<img src=x onerror=alert(1)>'
hostile_meta=json.dumps([{'sheetId':'safe','title':hostile_title}],separators=(',',':'))
hostile_grid=json.dumps({hostile_title:[['=1+2']]},separators=(',',':'))
formula_grid=json.dumps({'A':[['=1+2'] for _ in range(23)]},separators=(',',':'))
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
for name,value in [('sheets',meta),('grid',grid),('invalid','{"A":[]}'),('pull',pull),('bad-pull',bad_pull),('hostile-pull',hostile_pull),('hostile-meta',hostile_meta),('hostile-grid',hostile_grid),('formula-grid',formula_grid),('wide-meta',wide_meta),('wide-grid',wide_grid),('wide-pull',wide_pull),('near-pull',near_pull),('over-pull',over_pull)]:
 files[name]=out/(name+'.json');files[name].write_text(value,encoding='utf-8')
f=lambda s:str(len(s.encode()))+':'+s
cell=lambda r,c,v:f(str(r))+f(str(c))+f(v)
provenance='LE1|'+f('予算')+f(meta)+f(grid)
a=f('n:0')+f('A')+cell(1,1,'雪')+cell(2,1,'=A1+2')+cell(2,2,'3')
b=f('s:b')+f('B')+cell(1,1,'x')+cell(1,2,'=12/-3')+cell(2,2,'=9/2')
book='HW3|'+f('予算')+f(provenance)+f(a)+f(b)
expected='HU1|'+f(book)+f('n:0')+f('1')+f('1')
pull_book='HW3|'+f('予算')+f('LE2|'+f(pull))+f(a)+f(b)
pull_expected='HX1|2'+f(pull_book)+f('n:0')+f('1')+f('1')
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
 download=out/'downloads';download.mkdir();pipe.call('Browser.setDownloadBehavior',{'behavior':'allow','downloadPath':str(download)})
 def ev(expr, awaited=False):
  r=pipe.call('Runtime.evaluate',{'expression':expr,'returnByValue':True,'awaitPromise':awaited},session)
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
 def stored():return ev('new Promise((resolve,reject)=>{const r=indexedDB.open("itonami.office.hyokeisan.v2",1);r.onsuccess=()=>{const d=r.result,t=d.transaction("records","readonly"),g=t.objectStore("records").get("current");g.onsuccess=()=>resolve(g.result?.value??null);g.onerror=()=>reject(Error("read"));t.oncomplete=()=>d.close()};r.onerror=()=>reject(Error("open"))})',True)
 def record(key):return ev('new Promise((resolve,reject)=>{const r=indexedDB.open("itonami.office.hyokeisan.v2",1);r.onsuccess=()=>{const d=r.result,t=d.transaction("records","readonly"),g=t.objectStore("records").get('+json.dumps(key)+');g.onsuccess=()=>resolve(g.result||null);g.onerror=()=>reject(Error("read"));t.oncomplete=()=>d.close()};r.onerror=()=>reject(Error("open"))})',True)
 def export_source(part,expected):
  filename={'title':'hyokeisan-legacy-title.txt','sheets':'hyokeisan-legacy-sheets.json','grid':'hyokeisan-legacy-grid.json','pull':'hyokeisan-legacy-pull.json'}[part]
  path=download/filename
  if path.exists():path.unlink()
  ev("document.querySelector('[data-k=backup-legacy-"+part+"]').click()")
  until=time.time()+90
  while time.time()<until and not path.exists():time.sleep(.2)
  if not path.exists() or path.read_bytes()!=expected.encode('utf-8'):raise ValueError(part+' original export differs')
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
 ev("document.getElementById('legacy-title').value='予算'");choose('#legacy-sheets',files['sheets']);choose('#legacy-grid',files['grid']);preview()
 assert stored()==baseline and ev("document.querySelector('#backup-preview [data-k=c0]')?.value")=='雪'
 assert ev("['数式 3 件','互換性と計算結果は確認されていません'].every(v=>document.getElementById('backup-label').textContent.includes(v))")
 ev("document.getElementById('backup-confirm').click()");wait("document.getElementById('status').textContent.includes('復元しました')",'import')
 assert stored()==expected
 for part,value in [('title','予算'),('sheets',meta),('grid',grid)]:export_source(part,value)
 assert stored()==expected
 choose('#legacy-pull',files['pull']);ev("document.getElementById('legacy-pull-preview').click()");wait("document.getElementById('backup-dialog').open",'pull preview')
 assert stored()==expected and ev("['数式 3 件','bfixture','sheet:book:demo','版: 7','権限による欠落'].every(v=>document.getElementById('backup-label').textContent.includes(v))")
 ev("document.getElementById('backup-confirm').click()");wait("document.getElementById('status').textContent.includes('復元しました')",'pull import')
 assert stored()==pull_expected
 export_source('pull',pull)
 before=record('current')
 choose('#legacy-pull',files['near-pull'])
 ev("document.getElementById('status').textContent='';document.getElementById('legacy-pull-preview').click()")
 wait("document.getElementById('backup-dialog').open || document.getElementById('status').textContent.includes('読み込めません')",'near-limit preview')
 if not ev("document.getElementById('backup-dialog').open"):
  assert stored()==pull_expected
  raise ValueError('near-limit candidate refused and prior state was preserved')
 assert stored()==pull_expected and ev("document.querySelector('#backup-preview [data-k=c0]')?.value")=='1'
 ev("document.getElementById('backup-confirm').click()")
 wait("document.getElementById('status').textContent.includes('復元しました')",'near-limit commit')
 assert stored()==near_expected and record('backup:'+str(before['revision']).zfill(16))==before
 export_source('pull',near_pull)
 ev('window.__old=true');pipe.call('Page.reload',{},session)
 wait("window.__old!==true && document.querySelector('[data-k=c0]')?.value==='1'",'near-limit reload')
 assert stored()==near_expected
 report={'status':'PASS_HYOKEISAN_IDB_LEGACY_SYNTHETIC','nearSnapshotBytes':len(near_expected.encode()),'nearCells':1600,'nearBackupVerified':True,'checks':['two-file-preview-formula-audit','atomic-confirm','source-export-exact','pull-preview-identity-formula-audit','pull-source-export-exact','near-limit-pull-restore-reload'],'scope':'synthetic data and Chrome loopback; source authority and real-user migration unverified'}
 (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(report['status'])
finally:
 pipe.close();server.shutdown();server.server_close()
