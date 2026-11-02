#!/usr/bin/env python3
"""Exercise one edit in a synthetic 1,024-cell, two-sheet workbook in Chrome.

Usage: python3 scripts/check-workbook-large.py AMU_DIR BUILD_DIR OUTPUT_DIR CHROME
The byte oracle checks that the off-screen cells and other sheet remain intact.
"""
import functools
import http.server
import importlib.util
import json
import shutil
import sys
import threading
import time
from pathlib import Path
if len(sys.argv) != 5: raise SystemExit(__doc__)
amu, build, out, chrome = [Path(x).resolve() for x in sys.argv[1:]]
out.mkdir(parents=True, exist_ok=False)
profile = out / 'profile'; profile.mkdir()
shutil.copytree(build, out / 'site')
spec = importlib.util.spec_from_file_location('browser', amu / 'scripts/seed/check-wasm32-browser.py')
browser = importlib.util.module_from_spec(spec); spec.loader.exec_module(browser)
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(out)))
threading.Thread(target=server.serve_forever, daemon=True).start()
pipe = browser.Pipe(str(chrome), profile)
def frame(s): return str(len(s.encode('utf-8'))) + ':' + s
def cell(row, col, value): return frame(str(row)) + frame(str(col)) + frame(value)
def make_state(first, other="other-sheet😀", selected="s1", top="1", left="1"):
    cells = ''.join(cell(i, 1, first if i == 1 else 'v' + str(i)) for i in range(1, 1025))
    first_sheet = frame('s1') + frame('Sheet One') + cells
    second_sheet = frame('s2') + frame('Sheet Two') + cell(50, 27, other)
    book = 'HW3|' + frame('workbook') + frame('provenance unchanged') + frame(first_sheet) + frame(second_sheet)
    return 'HU1|' + frame(book) + frame(selected) + frame(top) + frame(left)
original, expected = make_state('v1'), make_state('edited')
key = 'itonami.hyokeisan.candidate.hs1'
url = f'http://127.0.0.1:{server.server_port}/site/index.html'
try:
    target = pipe.call('Target.createTarget', {'url': 'about:blank'})['targetId']
    session = pipe.call('Target.attachToTarget', {'targetId': target, 'flatten': True})['sessionId']
    pipe.call('Network.enable', {}, session); pipe.call('Page.navigate', {'url': url}, session)
    def ev(expr):
        r=pipe.call('Runtime.evaluate', {'expression':expr,'returnByValue':True}, session)
        if 'exceptionDetails' in r: raise ValueError(r['exceptionDetails'])
        return r.get('result',{}).get('value')
    def wait(expr, label, timeout=120):
        end=time.time()+timeout
        while time.time()<end:
            try:
                if ev(expr): return
            except RuntimeError as e:
                if not any(x in str(e) for x in ('Inspected target navigated or closed','Execution context was destroyed','Cannot find context with specified id')): raise
            time.sleep(.2)
        raise TimeoutError(label+': '+str(ev('document.body.innerText')))
    wait("document.querySelector('[data-k=c0]') !== null",'initial app')
    ev('localStorage.setItem('+json.dumps(key)+','+json.dumps(original,ensure_ascii=False)+');window.__old=true')
    pipe.call('Page.reload',{},session); wait('window.__old !== true','reload')
    wait("document.querySelector('[data-k=c0]')?.value==='v1'",'large workbook open')
    if ev('localStorage.getItem('+json.dumps(key)+')') != original: raise ValueError('open changed workbook')
    ev("(()=>{let e=document.querySelector('[data-k=c0]');e.value='edited';e.dispatchEvent(new Event('input',{bubbles:true}));})()")
    wait("document.getElementById('status').textContent==='保存しました' && localStorage.getItem("+json.dumps(key)+") !== "+json.dumps(original,ensure_ascii=False),'large workbook save')
    actual=ev('localStorage.getItem('+json.dumps(key)+')')
    if actual != expected: raise ValueError('offscreen cell, provenance or second sheet changed')
    ev('window.__old=true');pipe.call('Page.reload',{},session);wait('window.__old !== true','saved reload')
    wait("document.querySelector('[data-k=c0]')?.value==='edited'",'large workbook reopen')
    if ev('localStorage.getItem('+json.dumps(key)+')') != expected: raise ValueError('reopen changed workbook')
    # Navigate to the second sheet's AA50, edit it, and verify the original
    # 1,024-cell first sheet and provenance byte-for-byte.
    ev("document.querySelector('[data-k=sheet-next]').click()")
    wait("document.body.innerText.includes('Sheet Two') && document.getElementById('status').textContent==='保存しました'",'second sheet')
    for label in ('E','I','M','Q','U','Y'):
        ev("document.querySelector('[data-k=page-right]').click()")
        wait("document.querySelector('[data-k=c0]')?.getAttribute('aria-label')==='セル "+label+"1' && document.getElementById('status').textContent==='保存しました'",'horizontal navigation '+label)
    for row in range(5,50,4):
        ev("document.querySelector('[data-k=page-down]').click()")
        wait("document.querySelector('[data-k=c0]')?.getAttribute('aria-label')==='セル Y"+str(row)+"' && document.getElementById('status').textContent==='保存しました'",'vertical navigation '+str(row))
    if ev("document.querySelector('[data-k=c6]').getAttribute('aria-label')") != 'セル AA50' or ev("document.querySelector('[data-k=c6]').value") != 'other-sheet😀':
        raise ValueError('AA50 not accessible')
    ev("(()=>{let e=document.querySelector('[data-k=c6]');e.value='updated AA50';e.dispatchEvent(new Event('input',{bubbles:true}));})()")
    expected2=make_state('edited','updated AA50','s2','49','25')
    wait("localStorage.getItem("+json.dumps(key)+")?.includes('updated AA50') && document.getElementById('status').textContent==='保存しました'",'AA50 saved')
    if ev('localStorage.getItem('+json.dumps(key)+')') != expected2: raise ValueError('AA50 edit wrote wrong cell or changed other data')
    ev('window.__old=true');pipe.call('Page.reload',{},session);wait('window.__old !== true','AA50 reload')
    wait("document.querySelector('[data-k=c6]')?.value==='updated AA50'",'AA50 reopened')
    if ev('localStorage.getItem('+json.dumps(key)+')') != expected2: raise ValueError('AA50 edit changed other data')
    requests=[e['params']['request']['url'] for e in pipe.events if e.get('method')=='Network.requestWillBeSent']
    if not requests or any(not u.startswith(f'http://127.0.0.1:{server.server_port}/') for u in requests): raise ValueError('unexpected network request')
    (out/'result.json').write_text(json.dumps({'status':'PASS','cells':1024,'otherSheetCell':'edited at AA50','firstSheet':'1024 cells unchanged','provenance':'unchanged','snapshotBytes':len(expected.encode()),'scope':'synthetic Chrome loopback'},indent=2)+'\n')
    print('PASS_WORKBOOK_LARGE 1024 cells, second sheet, edit, save and reload')
finally:
    pipe.close();server.shutdown();server.server_close()
