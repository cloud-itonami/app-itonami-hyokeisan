#!/usr/bin/env python3
"""Synthetic Chrome test of explicit HS1-to-workbook upgrade and editing.

Usage: python3 scripts/check-workbook-browser.py AMU_DIR BUILD_DIR OLD_BUILD_DIR OUTPUT_DIR CHROME
This uses isolated loopback storage and fixtures only; no real migration is performed.
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

if len(sys.argv) != 6:
    raise SystemExit(__doc__)
amu, build, old_build, out, chrome = [Path(x).resolve() for x in sys.argv[1:]]
out.mkdir(parents=True, exist_ok=False)
profile = out / 'profile'; profile.mkdir()
site = out / 'site'; shutil.copytree(build, site)
old = out / 'old'; shutil.copytree(old_build, old)
download = out / 'downloads'; download.mkdir()
spec = importlib.util.spec_from_file_location('browser', amu / 'scripts/seed/check-wasm32-browser.py')
browser = importlib.util.module_from_spec(spec); spec.loader.exec_module(browser)
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(out)))
threading.Thread(target=server.serve_forever, daemon=True).start()
pipe = browser.Pipe(str(chrome), profile)
base = f'http://127.0.0.1:{server.server_port}/'
key = 'itonami.hyokeisan.candidate.hs1'
try:
    target = pipe.call('Target.createTarget', {'url': 'about:blank'})['targetId']
    session = pipe.call('Target.attachToTarget', {'targetId': target, 'flatten': True})['sessionId']
    pipe.call('Network.enable', {}, session)
    pipe.call('Page.navigate', {'url': base + 'site/index.html'}, session)
    pipe.call('Browser.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': str(download)})
    def ev(expr):
        r = pipe.call('Runtime.evaluate', {'expression': expr, 'returnByValue': True}, session)
        if 'exceptionDetails' in r: raise ValueError(r['exceptionDetails'])
        return r.get('result', {}).get('value')
    def wait(expr, label, timeout=120):
        until = time.time() + timeout
        while time.time() < until:
            try:
                if ev(expr): return
            except RuntimeError as e:
                if not any(x in str(e) for x in ('Inspected target navigated or closed', 'Execution context was destroyed', 'Cannot find context with specified id')): raise
            time.sleep(.2)
        raise TimeoutError(label + ': ' + str(ev('document.body.innerText')))
    def click(key_):
        ev("document.querySelector('[data-k="+key_+"]').click()")
    def input_(key_, value):
        ev("(()=>{let e=document.querySelector('[data-k="+key_+"]');e.value="+json.dumps(value,ensure_ascii=False)+";e.dispatchEvent(new Event('input',{bubbles:true}));})()")
        wait("document.getElementById('status').textContent==='保存しました' && localStorage.getItem("+json.dumps(key)+")?.includes("+json.dumps(value,ensure_ascii=False)+")", 'input '+key_)
    def snapshot(): return ev('localStorage.getItem('+json.dumps(key)+')')
    def reload():
        ev('window.__reloadMarker=true'); pipe.call('Page.reload', {}, session)
        wait('window.__reloadMarker !== true', 'reload')
    wait("document.querySelector('[data-k=c0]') !== null", 'initial')
    input_('c0', '3'); other = snapshot(); input_('c1', '=A1+3'); input_('c15', '旧の右下😀')
    prior = snapshot()
    if not prior.startswith('HS1|'): raise ValueError('missing original HS1')
    click('workbook-upgrade')
    wait("document.getElementById('backup-dialog').open", 'upgrade preview')
    if snapshot() != prior: raise ValueError('preview changed HS1')
    ev("document.getElementById('backup-cancel').click()")
    if snapshot() != prior: raise ValueError('cancel changed HS1')
    # Each storage failure must retain the original HS1; the second case
    # must also leave the recovery copy created before the failed write.
    click('workbook-upgrade'); wait("document.getElementById('backup-dialog').open", 'backup failure preview')
    ev("window.__setter=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k.includes('.preimport.'))throw Error('quota');return window.__setter.call(this,k,v)};document.getElementById('status').textContent='';document.getElementById('backup-confirm').click()")
    wait("document.getElementById('status').textContent.includes('復元できませんでした')", 'backup failure')
    if snapshot() != prior: raise ValueError('failed backup overwrote HS1')
    ev("Storage.prototype.setItem=window.__setter")
    click('workbook-upgrade'); wait("document.getElementById('backup-dialog').open", 'primary failure preview')
    ev("Storage.prototype.setItem=function(k,v){if(k==="+json.dumps(key)+")throw Error('quota');return window.__setter.call(this,k,v)};document.getElementById('status').textContent='';document.getElementById('backup-confirm').click()")
    wait("document.getElementById('status').textContent.includes('復元できませんでした')", 'primary failure')
    if snapshot() != prior or not ev("Object.keys(localStorage).some(k=>k.startsWith("+json.dumps(key+'.preimport.')+") && localStorage.getItem(k) === "+json.dumps(prior,ensure_ascii=False)+")"):
        raise ValueError('failed primary write lost original or recovery copy')
    ev("Storage.prototype.setItem=window.__setter")
    click('workbook-upgrade'); wait("document.getElementById('backup-dialog').open", 'stale upgrade preview')
    ev("localStorage.setItem("+json.dumps(key)+","+json.dumps(other,ensure_ascii=False)+");document.getElementById('backup-confirm').click()")
    wait("document.getElementById('status').textContent.includes('別のタブ')", 'stale upgrade refusal')
    if snapshot() != other: raise ValueError('stale upgrade overwrote newer data')
    ev("localStorage.setItem("+json.dumps(key)+","+json.dumps(prior,ensure_ascii=False)+")")
    click('workbook-upgrade'); wait("document.getElementById('backup-dialog').open", 'upgrade preview again')
    ev("document.getElementById('backup-confirm').click()")
    wait("localStorage.getItem("+json.dumps(key)+")?.startsWith('HU1|') && document.getElementById('status').textContent==='バックアップから復元しました。'", 'confirmed upgrade')
    if prior not in snapshot(): raise ValueError('original HS1 provenance absent')
    if not ev("Object.keys(localStorage).some(k=>k.startsWith("+json.dumps(key+'.preimport.')+") && localStorage.getItem(k) === "+json.dumps(prior,ensure_ascii=False)+")"):
        raise ValueError('original HS1 backup absent')
    if ev("document.querySelector('[data-k=c0]').value") != '3' or ev("document.querySelector('[data-k=c15]').value") != '旧の右下😀' or ev("document.querySelector('[data-k=c1]').parentElement.querySelector('.value').textContent") != '6':
        raise ValueError('HS1 cells changed on conversion')
    click('sheet-add'); wait("document.body.innerText.includes('Sheet 1') && document.getElementById('status').textContent==='保存しました'", 'add sheet')
    click('page-right'); wait("document.querySelector('[data-k=c0]')?.getAttribute('aria-label')==='セル E1' && document.getElementById('status').textContent==='保存しました'", 'page right')
    input_('c0', '別シート E1')
    click('page-down'); wait("document.querySelector('[data-k=c15]')?.getAttribute('aria-label')==='セル H8' && document.getElementById('status').textContent==='保存しました'", 'page down')
    input_('c15', '別シート H8')
    click('sheet-prev'); wait("document.querySelector('[data-k=c0]')?.getAttribute('aria-label')==='セル A1' && document.querySelector('[data-k=c0]')?.value==='3' && document.getElementById('status').textContent==='保存しました'", 'original sheet')
    click('sheet-next'); wait("document.body.innerText.includes('Sheet 1') && document.getElementById('status').textContent==='保存しました'", 'second sheet')
    click('page-right'); wait("document.querySelector('[data-k=c0]')?.getAttribute('aria-label')==='セル E1' && document.querySelector('[data-k=c0]')?.value==='別シート E1' && document.getElementById('status').textContent==='保存しました'", 'offscreen cell retained')
    click('page-down'); wait("document.querySelector('[data-k=c15]')?.value==='別シート H8' && document.getElementById('status').textContent==='保存しました'", 'second offscreen cell retained')
    saved = snapshot(); reload()
    wait("document.querySelector('[data-k=c15]')?.value==='別シート H8'", 'workbook reload')
    if snapshot() != saved or prior not in saved: raise ValueError('workbook or original provenance changed on reload')
    # Another tab sees the same saved workbook, but a stale edit must not win.
    second = pipe.call('Target.createTarget', {'url': base + 'site/index.html'})['targetId']
    second_session = pipe.call('Target.attachToTarget', {'targetId': second, 'flatten': True})['sessionId']
    def second_ev(expr):
        r = pipe.call('Runtime.evaluate', {'expression': expr, 'returnByValue': True}, second_session)
        if 'exceptionDetails' in r: raise ValueError(r['exceptionDetails'])
        return r.get('result', {}).get('value')
    until = time.time()+120
    while time.time()<until and second_ev("document.querySelector('[data-k=c15]')?.value") != '別シート H8': time.sleep(.2)
    if second_ev("document.querySelector('[data-k=c15]')?.value") != '別シート H8': raise TimeoutError('second workbook tab')
    pipe.call('Page.bringToFront', {}, session); wait("document.visibilityState==='visible'", 'foreground workbook')
    input_('c15', '別シート H8 更新'); saved = snapshot()
    pipe.call('Page.bringToFront', {}, second_session)
    second_ev("(()=>{let e=document.querySelector('[data-k=c15]');e.value='他タブの未保存';e.dispatchEvent(new Event('input',{bubbles:true}));})()")
    until = time.time()+120
    while time.time()<until and not second_ev("document.getElementById('status')?.textContent.includes('別のタブ')"): time.sleep(.2)
    if not second_ev("document.getElementById('status')?.textContent.includes('別のタブ')") or second_ev("document.querySelector('[data-k=c15]').value") != '他タブの未保存' or snapshot() != saved:
        raise ValueError('stale workbook tab lost input or overwrote state')
    pipe.call('Target.closeTarget', {'targetId': second});pipe.call('Page.bringToFront', {}, session)
    wait("document.visibilityState==='visible'", 'foreground after conflict')
    click('backup-export')
    exported = download / 'hyokeisan-backup.hu1'
    until = time.time() + 30
    while time.time() < until and not exported.exists(): time.sleep(.2)
    if not exported.exists() or exported.read_text() != saved: raise ValueError('workbook export mismatch')
    def choose(path):
        ev("document.getElementById('backup-file').value='';document.getElementById('status').textContent=''")
        pipe.call('DOM.enable', {}, session)
        root = pipe.call('DOM.getDocument', {}, session)['root']['nodeId']
        node = pipe.call('DOM.querySelector', {'nodeId':root,'selector':'#backup-file'}, session)['nodeId']
        pipe.call('DOM.setFileInputFiles', {'nodeId':node,'files':[str(path)]}, session)
    bad = out / 'bad.hu1'; bad.write_text('HU1|01:a', encoding='utf-8')
    choose(bad); wait("document.getElementById('status').textContent.includes('読み込めません')", 'malformed workbook refusal')
    if snapshot() != saved or ev("document.getElementById('backup-dialog').open"): raise ValueError('invalid workbook altered storage')
    choose(exported); wait("document.getElementById('backup-dialog').open", 'workbook import preview')
    ev("document.getElementById('backup-cancel').click()")
    if snapshot() != saved: raise ValueError('cancelled workbook import changed storage')
    choose(exported); wait("document.getElementById('backup-dialog').open", 'workbook import confirmation preview')
    ev("document.getElementById('status').textContent='';document.getElementById('backup-confirm').click()")
    wait("localStorage.getItem("+json.dumps(key)+")==="+json.dumps(saved,ensure_ascii=False)+" && document.getElementById('status').textContent==='バックアップから復元しました。'", 'workbook import confirmed')
    # Existing app on the same origin refuses HU1 and leaves the bytes intact.
    pipe.call('Page.navigate', {'url': base + 'old/index.html'}, session)
    wait("document.getElementById('status')?.textContent.includes('開けません')", 'old app refuses workbook')
    if snapshot() != saved or ev("document.querySelector('[data-k=c0]') !== null"): raise ValueError('old app modified workbook')
    pipe.call('Page.navigate', {'url': base + 'site/index.html'}, session)
    wait("document.querySelector('[data-k=c15]')?.value==='別シート H8 更新'", 'new app reopens workbook')
    prior_file = out / 'prior.hs1'; prior_file.write_text(prior, encoding='utf-8')
    choose(prior_file); wait("document.getElementById('backup-dialog').open", 'prior HS1 preview')
    ev("document.getElementById('backup-confirm').click()")
    wait("localStorage.getItem("+json.dumps(key)+")==="+json.dumps(prior,ensure_ascii=False)+" && document.getElementById('status').textContent==='バックアップから復元しました。'", 'prior HS1 restored')
    if ev("document.querySelector('[data-k=c0]').value") != '3': raise ValueError('prior HS1 not restored')
    click('backup-restore'); wait("document.getElementById('backup-dialog').open", 'prior workbook recovery preview')
    ev("document.getElementById('status').textContent='';document.getElementById('backup-confirm').click()")
    wait("localStorage.getItem("+json.dumps(key)+")==="+json.dumps(saved,ensure_ascii=False)+" && document.getElementById('status').textContent==='バックアップから復元しました。'", 'prior workbook recovered')
    requests = [e['params']['request']['url'] for e in pipe.events if e.get('method') == 'Network.requestWillBeSent']
    if not requests or any(not u.startswith(base) for u in requests): raise ValueError('unexpected network request')
    (out / 'result.json').write_text(json.dumps({'status':'PASS','checks':['HS1 preview/cancel','backup and explicit upgrade','backup and primary failures','stale upgrade refusal','multiple sheets','offscreen cells','formula','save/reload','stale workbook tab','HU1 export','HU1 import preview/cancel/confirm and malformed refusal','old-app refusal','prior HS1 restore','prior workbook recovery','loopback only'],
        'limitations':['synthetic fixtures','no old-origin export','no real migration','formula subset','no QEMU or release qualification']},indent=2)+'\n')
    print('PASS_WORKBOOK_BROWSER explicit upgrade, editing, save/reload and rollback')
finally:
    pipe.close(); server.shutdown(); server.server_close()
