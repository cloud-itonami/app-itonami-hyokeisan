#!/usr/bin/env python3
"""Exercise a clean browser-process restart of the Hyokeisan IDB candidate.

Usage: script AMU BUILD NEW_OUTPUT CHROME
Synthetic Chrome only; not crash, power-loss, eviction, other browser or release.
"""
import functools,http.server,importlib.util,json,sys,threading,time
from pathlib import Path
if len(sys.argv)!=5:raise SystemExit(__doc__)
amu,build,out,chrome=map(lambda s:Path(s).resolve(),sys.argv[1:]);out.mkdir(parents=True,exist_ok=False);(out/'profile').mkdir()
spec=importlib.util.spec_from_file_location('browser',amu/'scripts/seed/check-wasm32-browser.py');browser=importlib.util.module_from_spec(spec);spec.loader.exec_module(browser)
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(build)));threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}/index.html';pipe=None
try:
 def launch():
  global pipe
  pipe=browser.Pipe(str(chrome),out/'profile');target=pipe.call('Target.createTarget',{'url':'about:blank'})['targetId'];session=pipe.call('Target.attachToTarget',{'targetId':target,'flatten':True})['sessionId'];pipe.call('Page.enable',{},session);pipe.call('Page.navigate',{'url':url},session);return session
 def ev(x,s,awaited=False):
  r=pipe.call('Runtime.evaluate',{'expression':x,'returnByValue':True,'awaitPromise':awaited},s)
  if 'exceptionDetails' in r:raise ValueError(r['exceptionDetails'])
  return r.get('result',{}).get('value')
 def wait(x,s,label):
  until=time.time()+75
  while time.time()<until:
   try:
    if ev(x,s):return
   except RuntimeError as e:
    if not any(m in str(e) for m in ('Execution context was destroyed','Cannot find context with specified id')):raise
   time.sleep(.1)
  raise TimeoutError(label+': '+str(ev("document.getElementById('status')?.textContent",s)))
 def waitSaved(text,s):
  until=time.time()+75
  while time.time()<until:
   value=ev('new Promise((resolve,reject)=>{const r=indexedDB.open("itonami.office.hyokeisan.v2",1);r.onsuccess=()=>{const d=r.result,t=d.transaction("records","readonly"),g=t.objectStore("records").get("current");g.onsuccess=()=>resolve(g.result?.value??null);g.onerror=()=>reject(Error("read"));t.oncomplete=()=>d.close()};r.onerror=()=>reject(Error("open"))})',s,True)
   if value is not None and text in value and ev('document.getElementById("status").textContent==="保存しました"',s):return
   time.sleep(.1)
  raise TimeoutError('saved text')
 first=launch();wait('document.querySelector("[data-k=c0]")!==null',first,'initial')
 def enter(key,value):ev('(()=>{let e=document.querySelector("[data-k='+key+']");e.value='+json.dumps(value,ensure_ascii=False)+';e.dispatchEvent(new Event("input",{bubbles:true}))})()',first)
 enter('c0','6');waitSaved('6',first)
 enter('c1','4');waitSaved('4',first)
 enter('c4','=A1+B1');wait('document.querySelector("[data-k=c4]")?.parentElement.querySelector(".value")?.textContent==="10" && document.getElementById("status").textContent==="保存しました"',first,'formula')
 waitSaved('=A1+B1',first);assert ev('localStorage.getItem("itonami.hyokeisan.candidate.hs1")',first) is None
 pipe.close();pipe=None
 second=launch();wait('document.querySelector("[data-k=c0]")?.value==="6" && document.querySelector("[data-k=c1]")?.value==="4" && document.querySelector("[data-k=c4]")?.value==="=A1+B1" && document.querySelector("[data-k=c4]")?.parentElement.querySelector(".value")?.textContent==="10"',second,'restart formula')
 assert ev('document.getElementById("storage-conflict").hidden && !document.getElementById("legacy-migration").open',second)
 report={'status':'PASS_HYOKEISAN_IDB_RESTART_SYNTHETIC','scope':'synthetic Chrome clean process restart; no crash/power-loss, storage eviction, old-client coordination, QEMU or release'};(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],flush=True)
finally:
 if pipe:pipe.close()
 server.shutdown();server.server_close()
