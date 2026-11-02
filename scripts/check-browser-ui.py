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
    input_('c0', '6'); shown('c4', '10'); shown('c2', '10')
    input_('c3', '=D1'); shown('c3', '#ERROR')
    saved = evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')")
    if not saved or '=SUM(A1:B1)' not in saved: raise ValueError('saved formula missing')
    input_('c0', 'x' * 129)
    wait("document.getElementById('status').textContent.includes('入力が長すぎます')", 'oversized input')
    shown('c0', '6')
    if evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')") != saved: raise ValueError('oversized input clobbered storage')
    pipe.call('Page.reload', {}, session); shown('c4', '10'); shown('c2', '10'); shown('c3', '#ERROR')
    second = pipe.call('Target.createTarget', {'url': url})['targetId']
    second_session = pipe.call('Target.attachToTarget', {'targetId': second, 'flatten': True})['sessionId']
    def second_eval(expr):
        result = pipe.call('Runtime.evaluate', {'expression': expr, 'returnByValue': True}, second_session)
        if 'exceptionDetails' in result: raise ValueError(result['exceptionDetails'])
        return result.get('result', {}).get('value')
    end = time.time() + 90
    while time.time() < end and second_eval("document.querySelector('[data-k=c0]')?.value") != '6': time.sleep(.2)
    if second_eval("document.querySelector('[data-k=c0]')?.value") != '6': raise TimeoutError('second tab')
    input_('c0', '8'); shown('c4', '12')
    second_eval("(()=>{let e=document.querySelector('[data-k=c0]');e.value='77';e.dispatchEvent(new Event('input',{bubbles:true}));})()")
    end = time.time() + 90
    while time.time() < end and not second_eval("document.getElementById('status')?.textContent.includes('保存できませんでした')"): time.sleep(.2)
    if not second_eval("document.getElementById('status')?.textContent.includes('保存できませんでした')"): raise TimeoutError('stale tab refusal')
    saved = evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')")
    if '77' in saved: raise ValueError('stale tab clobbered state')
    pipe.call('Target.closeTarget', {'targetId': second})
    evaluate("window.savedWorker=window.Worker;window.Worker=class extends window.savedWorker {postMessage(msg){if(msg.args[0]==='view'){this.terminate();queueMicrotask(()=>this.onerror(new Event('error')))}else super.postMessage(msg)}}")
    input_('c0', '中断')
    wait("document.getElementById('status').textContent.includes('保存できませんでした')", 'worker interruption')
    if evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')") != saved: raise ValueError('interrupted render clobbered storage')
    evaluate("window.Worker=window.savedWorker")
    pipe.call('Page.reload', {}, session); shown('c0', '8'); shown('c4', '12')
    evaluate("Storage.prototype.setItem = function(){throw new Error('quota')}")
    input_('c0', '9')
    wait("document.getElementById('status').textContent.includes('保存できませんでした')", 'storage failure')
    shown('c0', '8'); shown('c4', '12')
    if evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')") != saved: raise ValueError('storage clobbered')
    pipe.call('Page.reload', {}, session); shown('c0', '8')
    evaluate("localStorage.setItem('itonami.hyokeisan.candidate.hs1','HS1|bad')")
    pipe.call('Page.reload', {}, session)
    wait("document.getElementById('status').textContent.includes('開けません')", 'corruption refusal')
    if evaluate("localStorage.getItem('itonami.hyokeisan.candidate.hs1')") != 'HS1|bad': raise ValueError('corrupt data overwritten')
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
    if not requests or any(not u.startswith(f'http://127.0.0.1:{server.server_port}/') for u in requests): raise ValueError('unexpected network request')
    (out / 'result.json').write_text(json.dumps({'status':'PASS','checks':['grid','addition','sum','recalculate','cycle','save-reload','oversized-refusal','concurrent-tab-refusal','worker-interruption','storage-failure','corrupt-refusal','digest-refusal','loopback-only']},indent=2)+'\n')
    print('PASS_HYOKEISAN_BROWSER_UI grid, calculation, save and refusal')
finally:
    pipe.close(); server.shutdown(); server.server_close()
