#!/usr/bin/env python3
"""Exercise the local Hyokeisan browser candidate on loopback Chrome.
Usage: python3 scripts/check-browser-ui.py AMU_DIR BUILD_DIR OUTPUT_DIR CHROME
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
site = out / 'site'; shutil.copytree(build, site)
spec = importlib.util.spec_from_file_location('browser', amu / 'scripts/seed/check-wasm32-browser.py')
browser = importlib.util.module_from_spec(spec); spec.loader.exec_module(browser)
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(out)))
threading.Thread(target=server.serve_forever, daemon=True).start()
pipe = browser.Pipe(str(chrome), profile)
url = f'http://127.0.0.1:{server.server_port}/site/index.html'
try:
    target = pipe.call('Target.createTarget', {'url': 'about:blank'})['targetId']
    session = pipe.call('Target.attachToTarget', {'targetId': target, 'flatten': True})['sessionId']
    pipe.call('Network.enable', {}, session); pipe.call('Page.navigate', {'url': url}, session)
    def evaluate(expr):
        result = pipe.call('Runtime.evaluate', {'expression': expr, 'returnByValue': True}, session)
        if 'exceptionDetails' in result: raise ValueError(result['exceptionDetails'])
        return result.get('result', {}).get('value')
    def wait(expr, label, seconds=90):
        end = time.time() + seconds
        while time.time() < end:
            if evaluate(expr): return
            time.sleep(.2)
        raise TimeoutError(label + ': ' + str(evaluate('document.body.innerText')))
    def reload_page():
        evaluate("window.__reloadMarker = true")
        pipe.call('Page.reload', {}, session)
        wait("window.__reloadMarker !== true", 'new document after reload')
    def input_(cell, text):
        evaluate("(()=>{let e=document.querySelector('[data-k="+cell+"]');e.value="+json.dumps(text,ensure_ascii=False)+";e.dispatchEvent(new Event('input',{bubbles:true}));})()")
    def shown(cell, value):
        wait("document.querySelector('[data-k="+cell+"]')?.parentElement.querySelector('.value')?.textContent === "+json.dumps(value,ensure_ascii=False), cell + ' result')
    wait("document.querySelector('[data-k=c0]') !== null", 'initial grid')
    if evaluate("document.querySelector('[data-k=c0]').getAttribute('aria-label')") != 'セル A1': raise ValueError('A1 lacks accessible name')
    if evaluate("document.querySelector('[data-k=c15]').getAttribute('aria-label')") != 'セル D4': raise ValueError('D4 lacks accessible name')
    evaluate("document.querySelector('[data-k=c0]').click()")
    time.sleep(1)
    if evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')") is not None: raise ValueError('focusing input wrote state')
    input_('c0', '3'); shown('c0', '3')
    input_('c1', '4'); shown('c1', '4')
    input_('c4', '=A1+B1'); shown('c4', '7')
    input_('c2', '=SUM(A1:B1)'); shown('c2', '7')
    input_('c5', '=A1-B1'); shown('c5', '-1')
    input_('c6', '=-3*B1'); shown('c6', '-12')
    input_('c7', '=ああ1234'); shown('c7', '#ERROR')
    input_('c8', '=é'); shown('c8', '#ERROR')
    input_('c0', '6'); shown('c4', '10'); shown('c2', '10')
    input_('c3', '=D1'); shown('c3', '#ERROR')
    saved = evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')")
    if not saved or '=SUM(A1:B1)' not in saved: raise ValueError('saved formula missing')
    # Simulate composition while an earlier field's view is in flight.
    original_other = evaluate("document.querySelector('[data-k=c1]').value")
    evaluate("window.originalWorker=window.Worker;window.imeDelay=false;window.Worker=class extends window.originalWorker {postMessage(m,...rest){if(m.args[0]==='view'&&!window.imeDelay){window.imeDelay=true;setTimeout(()=>super.postMessage(m,...rest),1500)}else super.postMessage(m,...rest)}}")
    input_('c1', 'IME補助')
    wait("window.imeDelay === true", 'pending view before composition')
    evaluate("(()=>{let e=document.querySelector('[data-k=c0]');window.imeNode=e;e.dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true}));e.value='仮変換';e.dispatchEvent(new InputEvent('input',{bubbles:true,isComposing:true,inputType:'insertCompositionText',data:'仮変換'}));})()")
    wait("localStorage.getItem('itonami.hyokeisan.candidate.hs1')?.includes('IME補助')", 'other field save during composition')
    if not evaluate("window.imeNode === document.querySelector('[data-k=c0]')") or evaluate("document.querySelector('[data-k=c0]').value") != '仮変換': raise ValueError('composition node or text replaced')
    if evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')?.includes('仮変換')"): raise ValueError('incomplete composition saved')
    evaluate("(()=>{let e=document.querySelector('[data-k=c0]');e.value='日本語';e.dispatchEvent(new CompositionEvent('compositionend',{bubbles:true,data:'日本語'}));e.dispatchEvent(new InputEvent('input',{bubbles:true,isComposing:false,inputType:'insertText',data:'日本語'}));})()")
    wait("localStorage.getItem('itonami.hyokeisan.candidate.hs1')?.includes('日本語') && document.getElementById('status').textContent === '保存しました'", 'completed composition save')
    evaluate("window.Worker=window.originalWorker")
    input_('c0', '6');input_('c1', original_other)
    wait("localStorage.getItem('itonami.hyokeisan.candidate.hs1') === "+json.dumps(saved,ensure_ascii=False)+" && document.getElementById('status').textContent === '保存しました'", 'restore after composition')
    input_('c0', 'x' * 129)
    wait("document.getElementById('status').textContent.includes('入力が長すぎます')", 'oversized input')
    if evaluate("document.querySelector('[data-k=c0]').value.length") != 129 or evaluate("document.getElementById('retry-save').hidden"): raise ValueError('oversized input discarded')
    if evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')") != saved: raise ValueError('oversized input clobbered storage')
    input_('c0', '6'); wait("document.getElementById('retry-save').hidden && localStorage.getItem('itonami.hyokeisan.candidate.hs1') === " + json.dumps(saved,ensure_ascii=False) + " && document.getElementById('status').textContent === '保存しました'", 'correct oversized input')
    reload_page(); shown('c4', '10'); shown('c2', '10'); shown('c3', '#ERROR'); shown('c5', '2'); shown('c6', '-12'); shown('c7', '#ERROR'); shown('c8', '#ERROR')
    # A downloaded HS1 can be explicitly reviewed and restored; invalid input
    # and storage failure must never replace the current document.
    download = out / 'downloads'
    download.mkdir()
    pipe.call('Browser.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': str(download)})
    evaluate("document.querySelector('[data-k=backup-export]').click()")
    end = time.time() + 90
    while time.time() < end and not (download / 'hyokeisan-backup.hs1').exists(): time.sleep(.2)
    exported = download / 'hyokeisan-backup.hs1'
    if not exported.exists() or exported.read_text() != saved: raise ValueError('backup download mismatch')
    evaluate("(()=>{let e=document.querySelector('[data-k=c0]');e.value='バックアップ前';e.dispatchEvent(new Event('input',{bubbles:true}));})()")
    wait("localStorage.getItem('itonami.hyokeisan.candidate.hs1')?.includes('バックアップ前')", 'edit before import')
    prior = evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')")
    def select_file(path):
        pipe.call('DOM.enable', {}, session)
        root = pipe.call('DOM.getDocument', {}, session)['root']['nodeId']
        node = pipe.call('DOM.querySelector', {'nodeId': root, 'selector': '#backup-file'}, session)['nodeId']
        pipe.call('DOM.setFileInputFiles', {'nodeId': node, 'files': [str(path)]}, session)
    select_file(exported)
    wait("document.getElementById('backup-dialog').open", 'backup preview')
    if evaluate("document.querySelector('#backup-preview [data-k=c0]')?.value") != '6': raise ValueError('preview mismatch')
    evaluate("document.getElementById('backup-cancel').click()")
    if evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')") != prior: raise ValueError('cancel changed storage')
    # Reset the input, as the user action does before selecting a file again.
    evaluate("document.getElementById('backup-file').value=''")
    select_file(exported)
    wait("document.getElementById('backup-dialog').open", 'backup preview again')
    evaluate("document.getElementById('backup-confirm').click()")
    wait("document.getElementById('status').textContent === 'バックアップから復元しました。'", 'restore backup')
    if evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')") != saved: raise ValueError('restore mismatch')
    if not evaluate("Object.keys(localStorage).some(k=>k.startsWith('itonami.hyokeisan.candidate.hs1.preimport.') && localStorage.getItem(k).includes('バックアップ前'))"): raise ValueError('missing prior backup')
    evaluate("document.querySelector('[data-k=backup-restore]').click()")
    wait("document.getElementById('backup-dialog').open", 'prior backup preview')
    evaluate("document.getElementById('backup-confirm').click()")
    wait("localStorage.getItem('itonami.hyokeisan.candidate.hs1')?.includes('バックアップ前')", 'restore prior')
    bad = out / 'bad.hs1'
    bad.write_bytes(b'HS1|bad')
    evaluate("document.getElementById('backup-file').value=''")
    select_file(bad)
    wait("document.getElementById('status').textContent.includes('バックアップを読み込めません')", 'bad backup refusal')
    if evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')") != prior or evaluate("document.getElementById('backup-dialog').open"): raise ValueError('bad import changed state')
    for name, contents in [('utf8.hs1', b'HS1|\xff'), ('large.hs1', b'HS1|' + b'x' * 35000), ('unknown.hs1', b'OLD|document')]:
        invalid = out / name
        invalid.write_bytes(contents)
        evaluate("document.getElementById('status').textContent='' ; document.getElementById('backup-file').value=''")
        select_file(invalid)
        wait("document.getElementById('status').textContent.includes('バックアップを読み込めません')", name + ' refusal')
        if evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')") != prior or evaluate("document.getElementById('backup-dialog').open"): raise ValueError(name + ' changed state')
    evaluate("document.getElementById('backup-file').value=''")
    select_file(exported)
    wait("document.getElementById('backup-dialog').open", 'quota backup preview')
    evaluate("window.savedSetItem=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k.includes('.preimport.'))throw Error('quota');return window.savedSetItem.call(this,k,v)};document.getElementById('backup-confirm').click()")
    wait("document.getElementById('status').textContent.includes('復元できませんでした')", 'backup quota refusal')
    if evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')") != prior: raise ValueError('quota import changed state')
    evaluate("Storage.prototype.setItem=window.savedSetItem")
    # Fail the second write after the recovery copy succeeds.
    backup_keys = set(evaluate("Object.keys(localStorage).filter(k=>k.startsWith('itonami.hyokeisan.candidate.hs1.preimport.'))"))
    evaluate("document.getElementById('backup-file').value='';document.getElementById('status').textContent=''")
    select_file(exported)
    wait("document.getElementById('backup-dialog').open", 'current-write failure preview')
    evaluate("Storage.prototype.setItem=function(k,v){if(k==='itonami.hyokeisan.candidate.hs1')throw Error('quota');return window.savedSetItem.call(this,k,v)};document.getElementById('backup-confirm').click()")
    wait("document.getElementById('status').textContent.includes('復元できませんでした')", 'current-write failure refusal')
    if evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')") != prior: raise ValueError('failed current write changed state')
    after_keys = set(evaluate("Object.keys(localStorage).filter(k=>k.startsWith('itonami.hyokeisan.candidate.hs1.preimport.'))"))
    new_keys = after_keys - backup_keys
    if len(new_keys) != 1 or evaluate("localStorage.getItem(" + json.dumps(next(iter(new_keys))) + ")") != prior: raise ValueError('pre-import copy missing after failed current write')
    evaluate("Storage.prototype.setItem=window.savedSetItem;document.getElementById('backup-file').value=''")
    # Return to the original exported fixture through the validated import path.
    select_file(exported)
    wait("document.getElementById('backup-dialog').open", 'return backup preview')
    evaluate("document.getElementById('backup-confirm').click()")
    wait("document.querySelector('[data-k=c0]')?.value === '6' && document.getElementById('status').textContent === 'バックアップから復元しました。'", 'return to test state')
    second = pipe.call('Target.createTarget', {'url': url})['targetId']
    second_session = pipe.call('Target.attachToTarget', {'targetId': second, 'flatten': True})['sessionId']
    def second_eval(expr):
        result = pipe.call('Runtime.evaluate', {'expression': expr, 'returnByValue': True}, second_session)
        if 'exceptionDetails' in result: raise ValueError(result['exceptionDetails'])
        return result.get('result', {}).get('value')
    end = time.time() + 90
    while time.time() < end and second_eval("document.querySelector('[data-k=c0]')?.value") != '6': time.sleep(.2)
    if second_eval("document.querySelector('[data-k=c0]')?.value") != '6': raise TimeoutError('second tab')
    pipe.call('DOM.enable', {}, second_session)
    second_root = pipe.call('DOM.getDocument', {}, second_session)['root']['nodeId']
    second_file = pipe.call('DOM.querySelector', {'nodeId': second_root, 'selector': '#backup-file'}, second_session)['nodeId']
    pipe.call('DOM.setFileInputFiles', {'nodeId': second_file, 'files': [str(exported)]}, second_session)
    end = time.time() + 90
    while time.time() < end and not second_eval("document.getElementById('backup-dialog').open"): time.sleep(.2)
    if not second_eval("document.getElementById('backup-dialog').open"): raise TimeoutError('second tab backup preview')
    pipe.call('Page.bringToFront', {}, session)
    wait("document.visibilityState === 'visible'", 'foreground first tab')
    input_('c0', '8'); shown('c4', '12')
    saved_after_edit = evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')")
    pipe.call('Page.bringToFront', {}, second_session)
    second_eval("document.getElementById('backup-confirm').click()")
    end = time.time() + 90
    while time.time() < end and not second_eval("document.getElementById('status')?.textContent.includes('復元できませんでした')"): time.sleep(.2)
    if not second_eval("document.getElementById('status')?.textContent.includes('別のタブ')") or evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')") != saved_after_edit: raise ValueError('conflicting import clobbered state')
    second_eval("(()=>{let e=document.querySelector('[data-k=c0]');e.value='77';e.dispatchEvent(new Event('input',{bubbles:true}));})()")
    end = time.time() + 90
    while time.time() < end and not second_eval("document.getElementById('status')?.textContent.includes('保存できませんでした')"): time.sleep(.2)
    if not second_eval("document.getElementById('status')?.textContent.includes('保存できませんでした')"): raise TimeoutError('stale tab refusal')
    if not second_eval("document.getElementById('status')?.textContent.includes('別のタブ')"): raise ValueError('conflict reason not shown')
    if second_eval("document.querySelector('[data-k=c0]')?.value") != '77' or second_eval("document.getElementById('retry-save').hidden"): raise ValueError('conflict discarded input')
    second_eval("document.getElementById('status').textContent='';document.getElementById('retry-save').click()")
    end = time.time() + 90
    while time.time() < end and not second_eval("document.getElementById('status')?.textContent.includes('別のタブ')"): time.sleep(.2)
    if not second_eval("document.getElementById('status')?.textContent.includes('別のタブ')") or second_eval("document.querySelector('[data-k=c0]')?.value") != '77': raise ValueError('conflict retry lost input')
    saved = evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')")
    if '77' in saved: raise ValueError('stale tab clobbered state')
    pipe.call('Target.closeTarget', {'targetId': second})
    pipe.call('Page.bringToFront', {}, session)
    wait("document.visibilityState === 'visible'", 'foreground after second tab')
    evaluate("window.savedTimer=window.setTimeout;window.savedTimeoutWorker=window.Worker;window.Worker=class extends window.savedTimeoutWorker {postMessage(msg){if(msg.args[0]!=='step')super.postMessage(msg)}};window.setTimeout=(f,n)=>window.savedTimer(f,n===30000?1:n)")
    input_('c0', '9')
    wait("document.getElementById('status').textContent.includes('時間内に完了しませんでした')", 'worker timeout')
    if evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')") != saved: raise ValueError('timeout clobbered storage')
    if evaluate("document.querySelector('[data-k=c0]')?.value") != '9' or evaluate("document.getElementById('retry-save').hidden"): raise ValueError('timeout discarded input')
    evaluate("document.querySelector('[data-k=backup-export]').click()")
    if not evaluate("document.getElementById('status').textContent.includes('未保存')"): raise ValueError('backup allowed with unsaved input')
    evaluate("window.setTimeout=window.savedTimer;window.Worker=window.savedTimeoutWorker;document.getElementById('retry-save').click()")
    wait("document.querySelector('[data-k=c0]')?.value === '9' && document.getElementById('retry-save').hidden && document.getElementById('status').textContent === '保存しました'", 'timeout retry')
    input_('c0','8'); wait("localStorage.getItem('itonami.hyokeisan.candidate.hs1') === " + json.dumps(saved,ensure_ascii=False), 'restore timeout fixture')
    background=pipe.call('Target.createTarget', {'url':'about:blank'})['targetId']
    wait("document.visibilityState === 'hidden'", 'hidden tab')
    evaluate("window.savedTimeoutWorker=window.Worker;window.Worker=class extends window.savedTimeoutWorker {postMessage(msg){if(msg.args[0]!=='step')super.postMessage(msg)}}")
    started = time.monotonic()
    input_('c0','背景入力'); wait("document.getElementById('status').textContent.includes('時間内に完了しませんでした')", 'hidden timeout', seconds=90)
    elapsed = time.monotonic() - started
    if elapsed < 29 or evaluate("document.visibilityState") != 'hidden': raise ValueError('hidden timeout did not use the real timer')
    pipe.call('Page.bringToFront', {}, session); wait("document.visibilityState === 'visible'", 'return to tab')
    if evaluate("document.querySelector('[data-k=c0]')?.value") != '背景入力' or evaluate("document.getElementById('retry-save').hidden") or evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')") != saved: raise ValueError('hidden timeout discarded input')
    pipe.call('Target.closeTarget', {'targetId':background})
    evaluate("window.Worker=window.savedTimeoutWorker;document.getElementById('retry-save').click()")
    wait("localStorage.getItem('itonami.hyokeisan.candidate.hs1')?.includes('背景入力') && document.getElementById('retry-save').hidden", 'hidden retry')
    input_('c0','8'); wait("localStorage.getItem('itonami.hyokeisan.candidate.hs1') === " + json.dumps(saved,ensure_ascii=False), 'restore hidden fixture')
    reload_page(); shown('c0', '8'); shown('c4', '12')
    evaluate("window.savedWorker=window.Worker;window.Worker=class extends window.savedWorker {postMessage(msg){if(msg.args[0]==='view'){this.terminate();queueMicrotask(()=>this.onerror(new Event('error')))}else super.postMessage(msg)}}")
    input_('c0', '中断')
    wait("document.getElementById('status').textContent.includes('保存できませんでした')", 'worker interruption')
    if evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')") != saved: raise ValueError('interrupted render clobbered storage')
    if evaluate("document.querySelector('[data-k=c0]')?.value") != '中断' or evaluate("document.getElementById('retry-save').hidden"): raise ValueError('interrupted input discarded')
    evaluate("window.Worker=window.savedWorker;document.getElementById('retry-save').click()")
    wait("localStorage.getItem('itonami.hyokeisan.candidate.hs1')?.includes('中断') && document.getElementById('retry-save').hidden", 'interruption retry')
    input_('c0','8'); wait("localStorage.getItem('itonami.hyokeisan.candidate.hs1') === " + json.dumps(saved,ensure_ascii=False), 'restore interruption fixture')
    reload_page(); shown('c0', '8'); shown('c4', '12')
    evaluate("window.quotaSetter=Storage.prototype.setItem;Storage.prototype.setItem = function(){throw new Error('quota')}")
    input_('c0', '9')
    wait("document.getElementById('status').textContent.includes('保存できませんでした')", 'storage failure')
    if evaluate("document.querySelector('[data-k=c0]')?.value") != '9' or evaluate("document.getElementById('retry-save').hidden"): raise ValueError('quota discarded input')
    if evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')") != saved: raise ValueError('storage clobbered')
    evaluate("Storage.prototype.setItem=window.quotaSetter;document.getElementById('retry-save').click()")
    wait("document.querySelector('[data-k=c0]')?.value === '9' && document.getElementById('retry-save').hidden && document.getElementById('status').textContent === '保存しました'", 'quota retry')
    input_('c0','8');wait("localStorage.getItem('itonami.hyokeisan.candidate.hs1') === " + json.dumps(saved,ensure_ascii=False), 'restore quota fixture')
    old_c1=evaluate("document.querySelector('[data-k=c1]').value")
    evaluate("window.partialSetter=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(v.includes('未保存表'))throw Error('quota');return window.partialSetter.call(this,k,v)};(()=>{for(const [k,v] of [['c0','未保存表'],['c1','追加セル']]){let e=document.querySelector('[data-k='+k+']');e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}));}})()")
    wait("localStorage.getItem('itonami.hyokeisan.candidate.hs1')?.includes('追加セル')", 'other field save')
    if evaluate("document.querySelector('[data-k=c0]')?.value") != '未保存表' or evaluate("document.getElementById('retry-save').hidden"): raise ValueError('successful redraw erased failed edit')
    evaluate("Storage.prototype.setItem=window.partialSetter;document.getElementById('retry-save').click()")
    wait("localStorage.getItem('itonami.hyokeisan.candidate.hs1')?.includes('未保存表') && localStorage.getItem('itonami.hyokeisan.candidate.hs1')?.includes('追加セル') && document.getElementById('retry-save').hidden", 'multiple edits retry')
    input_('c0','8');input_('c1',old_c1);wait("localStorage.getItem('itonami.hyokeisan.candidate.hs1') === " + json.dumps(saved,ensure_ascii=False), 'restore multi fixture')
    reload_page(); shown('c0', '8')
    evaluate("localStorage.setItem('itonami.hyokeisan.candidate.hs1','HS1|bad')")
    reload_page()
    wait("document.getElementById('status').textContent.includes('開けません')", 'corruption refusal')
    if evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')") != 'HS1|bad': raise ValueError('corrupt data overwritten')
    # An older HS1-only app must refuse an authentic HW3, without changing it.
    evaluate("localStorage.setItem('itonami.hyokeisan.candidate.hs1','HW3|0:0:6:1:s1:S')")
    reload_page()
    wait("document.getElementById('status').textContent.includes('開けません')", 'future snapshot refusal')
    if evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')") != 'HW3|0:0:6:1:s1:S' or evaluate("document.querySelector('[data-k=c0]') !== null"):
        raise ValueError('old app overwrote or opened HW3')
    reload_page()
    wait("document.getElementById('status').textContent.includes('開けません')", 'future snapshot refusal after reload')
    if evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')") != 'HW3|0:0:6:1:s1:S': raise ValueError('HW3 overwritten on reload')
    evaluate("localStorage.removeItem('itonami.hyokeisan.candidate.hs1')")
    tampered = out / 'tampered'; shutil.copytree(site, tampered)
    bundle = tampered / 'bundle.js'; content = bundle.read_text()
    content, count = __import__('re').subn(r'(export const wasmSha256 = ")[0-9a-f]{64}(";)', r'\g<1>' + '0' * 64 + r'\g<2>', content)
    if count != 1: raise ValueError('digest mutation anchor')
    bundle.write_text(content)
    pipe.call('Page.navigate', {'url': f'http://127.0.0.1:{server.server_port}/tampered/index.html'}, session)
    wait("document.getElementById('status')?.textContent.includes('開けません')", 'digest refusal')
    if evaluate("document.querySelector('[data-k=c0]') !== null || localStorage.getItem('itonami.hyokeisan.candidate.hs1') !== null"):
        raise ValueError('tampered candidate ran or wrote state')
    requests = [e['params']['request']['url'] for e in pipe.events if e.get('method') == 'Network.requestWillBeSent']
    if any(u.split('?', 1)[0].endswith('/favicon.ico') for u in requests): raise ValueError('unversioned favicon request')
    if not requests or any(not u.startswith(f'http://127.0.0.1:{server.server_port}/') for u in requests): raise ValueError('unexpected network request')
    (out / 'result.json').write_text(json.dumps({'status':'PASS','checks':['backup-export-import-cancel-restore','backup-invalid-both-write-failures-conflict','grid','addition','subtraction-multiplication-reload','unicode-formula-save-reload','sum','recalculate','cycle','save-reload','synthetic-composition-with-concurrent-redraw','oversized-refusal','concurrent-tab-refusal','worker-timeout-retry','hidden-timeout-retry','worker-interruption-retry','storage-failure-retry','multiple-unsaved-fields','corrupt-refusal','future-HW3-refusal','digest-refusal','loopback-only']},indent=2)+'\n')
    print('PASS_HYOKEISAN_BROWSER_UI grid, calculation, save and refusal')
finally:
    pipe.close(); server.shutdown(); server.server_close()
