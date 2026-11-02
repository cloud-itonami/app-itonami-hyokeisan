#!/usr/bin/env python3
"""Verify HX1 downgrade refusal and HS1 multiline preservation on loopback.

Usage: python3 scripts/check-multiline-compat.py AMU_DIR NEW_BUILD OLD_BUILD OUTPUT_DIR CHROME
Synthetic data only; old candidate and current candidate share one isolated origin.
"""
import functools, http.server, importlib.util, json, shutil, sys, threading, time
from pathlib import Path

if len(sys.argv) != 6: raise SystemExit(__doc__)
amu,new,old,out,chrome = map(lambda s:Path(s).resolve(),sys.argv[1:])
out.mkdir(parents=True,exist_ok=False); (out/'profile').mkdir()
shutil.copytree(new,out/'new'); shutil.copytree(old,out/'old')
spec=importlib.util.spec_from_file_location('browser',amu/'scripts/seed/check-wasm32-browser.py')
browser=importlib.util.module_from_spec(spec);spec.loader.exec_module(browser)
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args): pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(out)))
threading.Thread(target=server.serve_forever,daemon=True).start();pipe=browser.Pipe(str(chrome),out/'profile')
key='itonami.hyokeisan.candidate.hs1'; base=f'http://127.0.0.1:{server.server_port}/'
try:
 target=pipe.call('Target.createTarget',{'url':'about:blank'})['targetId'];session=pipe.call('Target.attachToTarget',{'targetId':target,'flatten':True})['sessionId']
 pipe.call('Network.enable',{},session);pipe.call('Page.enable',{},session)
 def ev(expr):
  r=pipe.call('Runtime.evaluate',{'expression':expr,'returnByValue':True},session)
  if 'exceptionDetails' in r: raise ValueError(r['exceptionDetails'])
  return r.get('result',{}).get('value')
 def wait(expr,label):
  until=time.time()+90
  while time.time()<until:
   try:
    if ev(expr): return
   except RuntimeError as e:
    if not any(x in str(e) for x in ('Execution context was destroyed','Cannot find context with specified id','Inspected target navigated or closed')): raise
   time.sleep(.2)
  raise TimeoutError(label+': '+str(ev("document.getElementById('status')?.textContent")))
 def navigate(path):
  pipe.call('Page.navigate',{'url':base+path+'/index.html'},session)
 def input_(key_,text):
  ev("(()=>{const x=document.querySelector('[data-k="+key_+"]');x.value="+json.dumps(text,ensure_ascii=False)+";x.dispatchEvent(new Event('input',{bubbles:true}));})()")
 navigate('new');wait("document.querySelector('[data-k=c0]')?.tagName==='TEXTAREA'",'new initial')
 text='最初😀\n第二行';input_('c0',text)
 wait("localStorage.getItem("+json.dumps(key)+")?.startsWith('HX1|1') && document.getElementById('status').textContent==='保存しました'",'multiline saved')
 saved=ev('localStorage.getItem('+json.dumps(key)+')')
 navigate('old');wait("document.getElementById('status')?.textContent.includes('開けません')",'old rejects HX1')
 if ev('localStorage.getItem('+json.dumps(key)+')') != saved or ev("document.querySelector('[data-k=c0]') !== null"): raise ValueError('old editor accepted or modified HX1')
 navigate('new');wait("document.querySelector('[data-k=c0]')?.value === "+json.dumps(text,ensure_ascii=False),'new reopens')
 if ev('localStorage.getItem('+json.dumps(key)+')') != saved: raise ValueError('new reopen changed bytes')
 # Prior HS1 with line breaks remains readable and upgrades on the next edit.
 legacy='HS1|'+saved[5:];ev('localStorage.setItem('+json.dumps(key)+','+json.dumps(legacy,ensure_ascii=False)+')')
 # Simulate another tab changing the saved value between read and lock.
 foreign=saved
 race_script="window.originalGet=Storage.prototype.getItem;window.originalSet=Storage.prototype.setItem;window.readCount=0;Storage.prototype.getItem=function(k){if(this===localStorage && k==="+json.dumps(key)+" && ++window.readCount===2)window.originalSet.call(this,k,"+json.dumps(foreign,ensure_ascii=False)+");return window.originalGet.call(this,k)}"
 racing=pipe.call('Page.addScriptToEvaluateOnNewDocument',{'source':race_script},session)['identifier']
 navigate('new');wait("document.getElementById('status')?.textContent.includes('開けません')",'protection conflict refusal')
 if ev('localStorage.getItem('+json.dumps(key)+')')!=foreign or ev("document.querySelector('[data-k=c0]') !== null"):raise ValueError('protection overwrote concurrent update')
 pipe.call('Page.removeScriptToEvaluateOnNewDocument',{'identifier':racing},session)
 ev('localStorage.setItem('+json.dumps(key)+','+json.dumps(legacy,ensure_ascii=False)+')')
 # A failed protection write must leave the original bytes and editor closed.
 injected=pipe.call('Page.addScriptToEvaluateOnNewDocument',{'source':"window.originalSet=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(this===localStorage && k==="+json.dumps(key)+")throw Error('quota');return window.originalSet.call(this,k,v)}"},session)['identifier']
 navigate('new');wait("document.getElementById('status')?.textContent.includes('開けません')",'protection write refusal')
 if ev('localStorage.getItem('+json.dumps(key)+')')!=legacy or ev("document.querySelector('[data-k=c0]') !== null"):raise ValueError('failed protection changed or exposed state')
 pipe.call('Page.removeScriptToEvaluateOnNewDocument',{'identifier':injected},session);navigate('new')
 wait("document.querySelector('[data-k=c0]')?.value === "+json.dumps(text,ensure_ascii=False)+" && localStorage.getItem("+json.dumps(key)+")?.startsWith('HX1|1')",'legacy multiline auto-protected')
 protected=ev('localStorage.getItem('+json.dumps(key)+')');navigate('old')
 wait("document.getElementById('status')?.textContent.includes('開けません')",'old refuses auto-protected state')
 if ev('localStorage.getItem('+json.dumps(key)+')')!=protected:raise ValueError('old version changed protected state')
 navigate('new');wait("document.querySelector('[data-k=c0]')?.value === "+json.dumps(text,ensure_ascii=False),'auto-protected state reopens')
 input_('c1','編集後');wait("localStorage.getItem("+json.dumps(key)+")?.startsWith('HX1|1') && document.getElementById('status').textContent==='保存しました'",'legacy upgrade')
 if ev("document.querySelector('[data-k=c0]')?.value") != text: raise ValueError('legacy line breaks lost')
 # Textarea/input normalization must not silently alter persisted CR bytes.
 current=ev('localStorage.getItem('+json.dumps(key)+')');assert text in current
 cr=current.replace(text,text.replace('\n','\r'),1);ev('localStorage.setItem('+json.dumps(key)+','+json.dumps(cr,ensure_ascii=False)+')');navigate('new')
 wait("document.getElementById('status')?.textContent.includes('開けません')",'CR refusal')
 if ev('localStorage.getItem('+json.dumps(key)+')')!=cr: raise ValueError('CR snapshot overwritten')
 # Legacy grid has a multiline cell on a non-selected sheet. The exact JSON
 # and IDs must survive, and an older build must refuse the whole workbook.
 meta='[{"sheetId":0,"title":"A"},{"sheetId":1,"title":"B"}]'
 grid=json.dumps({'A':[['=1+2']],'B':[['一行\n二行']]},ensure_ascii=False,separators=(',',':'))
 mf=out/'legacy-sheets.json';gf=out/'legacy-grid.json';mf.write_text(meta);gf.write_text(grid)
 ev('localStorage.removeItem('+json.dumps(key)+')');navigate('new');wait("document.querySelector('[data-k=c0]') !== null",'blank for legacy')
 pipe.call('DOM.enable',{},session)
 def choose(selector,path):
  doc=pipe.call('DOM.getDocument',{},session)['root']['nodeId'];node=pipe.call('DOM.querySelector',{'nodeId':doc,'selector':selector},session)['nodeId']
  pipe.call('DOM.setFileInputFiles',{'nodeId':node,'files':[str(path)]},session)
 ev("document.getElementById('legacy-title').value='旧表'");choose('#legacy-sheets',mf);choose('#legacy-grid',gf)
 ev("document.getElementById('legacy-preview').click()");wait("document.getElementById('backup-dialog').open",'legacy preview')
 if not ev("document.getElementById('backup-label').textContent.includes('数式 1 件')"):raise ValueError('HX1 formula audit missing')
 ev("document.getElementById('backup-confirm').click()");wait("document.getElementById('status').textContent === 'バックアップから復元しました。'",'legacy import')
 imported=ev('localStorage.getItem('+json.dumps(key)+')')
 if not imported.startswith('HX1|2'):raise ValueError('multiline legacy not protected')
 def frame(data,pos):
  end=data.index(b':',pos);size=int(data[pos:end]);start=end+1;return data[start:start+size],start+size
 book,_=frame(imported.encode('utf-8'),5)
 if not book.startswith(b'HW3|'):raise ValueError('missing workbook')
 _,pos=frame(book,4);provenance,_=frame(book,pos)
 if not provenance.startswith(b'LE1|'):raise ValueError('missing source provenance')
 title,pos=frame(provenance,4);raw_meta,pos=frame(provenance,pos);raw_grid,pos=frame(provenance,pos)
 if [title.decode(),raw_meta.decode(),raw_grid.decode()] != ['旧表',meta,grid] or pos!=len(provenance):raise ValueError('legacy provenance changed')
 navigate('old');wait("document.getElementById('status')?.textContent.includes('開けません')",'old rejects legacy workbook')
 if ev('localStorage.getItem('+json.dumps(key)+')')!=imported:raise ValueError('old editor changed workbook')
 navigate('new');wait("document.querySelector('[data-k=sheet-next]') !== null",'legacy reopens')
 ev("document.querySelector('[data-k=sheet-next]').click()");wait("document.querySelector('[data-k=c0]')?.value === "+json.dumps('一行\n二行',ensure_ascii=False),'offscreen sheet preserved')
 wait("document.getElementById('status').textContent==='保存しました'",'sheet navigation persisted')
 current=ev('localStorage.getItem('+json.dumps(key)+')')
 # An existing HU1 workbook also upgrades on load without changing its text.
 old_book='HU1|'+current[5:];ev('localStorage.setItem('+json.dumps(key)+','+json.dumps(old_book,ensure_ascii=False)+')');navigate('new')
 wait("document.querySelector('[data-k=c0]')?.value === "+json.dumps('一行\n二行',ensure_ascii=False)+" && localStorage.getItem("+json.dumps(key)+")?.startsWith('HX1|2')",'old workbook auto-protected')
 current=ev('localStorage.getItem('+json.dumps(key)+')')
 # Explicit import of an older HU1 multiline backup must protect it before commit.
 backup=out/'old.hu1';backup.write_text('HU1|'+current[5:]);choose('#backup-file',backup)
 wait("document.getElementById('backup-dialog').open",'old backup preview')
 ev("document.getElementById('backup-confirm').click()");wait("document.getElementById('status').textContent === 'バックアップから復元しました。'",'old backup commit')
 if not ev('localStorage.getItem('+json.dumps(key)+")?.startsWith('HX1|2')"):raise ValueError('legacy backup not protected')
 # Malformed discriminators are refused without touching stored bytes.
 for bad in ['HX1|3', 'HX1|😀', 'HX1|1bad']:
  ev('localStorage.setItem('+json.dumps(key)+','+json.dumps(bad,ensure_ascii=False)+')');navigate('new')
  wait("document.getElementById('status')?.textContent.includes('開けません')",'invalid HX1 refusal')
  if ev('localStorage.getItem('+json.dumps(key)+')')!=bad:raise ValueError('invalid HX1 overwritten')
 requests=[e['params']['request']['url'] for e in pipe.events if e.get('method')=='Network.requestWillBeSent']
 if not requests or any(not x.startswith(base) for x in requests):raise ValueError('unexpected request')
 (out/'result.json').write_text(json.dumps({'status':'PASS','checks':['HX1 old editor refuses without write','new editor reopens exact text','HS1 auto-protection, conflict and failed-write refusal','CR normalization refusal','legacy grid provenance and offscreen multiline','old workbook backup protected','invalid HX1 refusal','loopback only'],'scope':'synthetic candidate, no real-user migration or release'},ensure_ascii=False,indent=2)+'\n')
 print('PASS_HYOKEISAN_MULTILINE_COMPAT')
finally:
 pipe.close();server.shutdown();server.server_close()
