#!/usr/bin/env python3
"""Check a bounded legacy grid matrix parser; this is not a full import.

Usage: python3 scripts/check-legacy-grid.py AMU_DIR OUTPUT_DIR CHROME
Fixtures are synthetic; no user data, browser integration or QEMU is implied.
"""
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

if len(sys.argv) != 4: raise SystemExit(__doc__)
amu, out, chrome = [Path(x).resolve() for x in sys.argv[1:]]
out.mkdir(parents=True, exist_ok=False)
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'scripts'))
from browser_source import stage
source = stage(root, entry=False)
for name in ('json_string.kotoba', 'legacy_grid.kotoba'):
    module = (root / 'src/hyokeisan' / name).read_text(encoding='utf-8')
    module, count = re.subn(r'\A\(ns\s+hyokeisan\.[\s\S]*?\)\)\s*', '', module, count=1)
    if count != 1: raise ValueError('module header: ' + name)
    source += '\n' + module.replace('(js/', '(').replace('(workbook/', '(')

def frame(s): return str(len(s.encode('utf-8'))) + ':' + s
rows = [['a', '雪', '', 'emoji😀'], [], ['=A1+2']] + [['1'] for _ in range(70)] + [['x'] * 1024]
raw = json.dumps(rows, ensure_ascii=False, separators=(',', ':'))
escaped = json.dumps([['雪😀', 'line\nnext', '"\\/']], ensure_ascii=True, separators=(',', ':'))
escaped_expected = ''.join(frame('1') + frame(str(c + 1)) + frame(v)
                           for c, v in enumerate(['雪😀', 'line\nnext', '"\\/']))
grid_object = json.dumps({**{'Sheet' + str(i): [[str(i)]] for i in range(40)},
                          '予算!': [['雪', '😀']]}, ensure_ascii=False, separators=(',', ':'))
object_expected = frame('1') + frame('1') + frame('雪') + frame('1') + frame('2') + frame('😀')
bad_objects = ['{"A":[["a"]],"\\u0041":[["b"]]}', '{"A":[["a"]],}',
               '{"A":[["a"]],"B":[[null]]}', '{"A":[["a"]]} trailing', '{"A":null}']
expected = ''.join(frame(str(r + 1)) + frame(str(c + 1)) + frame(v)
                   for r, row in enumerate(rows) for c, v in enumerate(row) if v)
literal = lambda x: json.dumps(x, ensure_ascii=False)
bad = ['[[],]', '[["x",]]', '[["x"]] trailing', '[[null]]', '[["\\q"]]',
       '[["\\雪"]]', '[["a"]', '[1]', '{"x":1}', '[["\\uD800"]]']
fixture = '\n(defn main [] :i64\n (let [v (legacy-grid-cells ' + literal(raw) + ')] (if (and ' + \
    '(option-some?-of [:option :string] v) (string=? (option-value-of [:option :string] v "") ' + literal(expected) + ') ' + \
    '(string=? (option-value-of [:option :string] (legacy-grid-cells ' + literal(escaped) + ') "bad") ' + literal(escaped_expected) + ') ' + \
    '(string=? (option-value-of [:option :string] (legacy-grid-find ' + literal(grid_object) + ' "予算!") "bad") ' + literal(object_expected) + ') ' + \
    '(not (option-some?-of [:option :string] (legacy-grid-find ' + literal(grid_object) + ' "missing"))) ' + \
    ' '.join('(not (option-some?-of [:option :string] (legacy-grid-find ' + literal(item) + ' "A")))' for item in bad_objects) + ' ' + \
    ' '.join('(not (option-some?-of [:option :string] (legacy-grid-cells ' + literal(item) + ')))' for item in bad) + ') 0 1)))\n'
anchor = '(string-concat acc (wf-cell row col value))'
if source.count(anchor) != 1: raise ValueError('coordinate mutation anchor changed')
cases = [('grid', source, 0), ('coordinate-mutant', source.replace(anchor, '(string-concat acc (wf-cell col row value))', 1), 1)]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
mac = load('mac', amu / 'scripts/seed/check-aiueos-user-macos-native.py')
browser = load('browser', amu / 'scripts/seed/check-wasm32-browser.py')
compiler = amu / 'seed/bootstrap/aarch64-macos/amu-full-root.macho'
runs = []
for name, program, expected_result in cases:
    path = out / (name + '.kotoba'); path.write_text(program + fixture, encoding='utf-8')
    result = subprocess.run([str(amu / 'bin/amu'), 'run', str(path)], cwd=out, capture_output=True, text=True, timeout=120, check=True)
    if result.stdout.strip() != str(expected_result): raise ValueError(name + ' native result: ' + repr(result.stdout))
    mac.native_run(compiler, out, 'compile', path.name, '--target', 'wasm32-browser', '--output', name + '.wasm')
    runs.append((name, out / (name + '.wasm'), dict(fuel=25000000, allow=[], args=[], files={})))
version, reports = browser.run_modules(str(chrome), out, runs, timeout=300)
for name, _, expected_result in cases:
    result = reports[name]
    if result.get('exit') != 0 or not re.search(rf'\{{:status :ok :result {expected_result}(?:\s|\}})', result.get('report') or ''):
        raise ValueError(name + ' Wasm result: ' + repr(result))
(out / 'receipt.json').write_text(json.dumps({'sourceSha256': hashlib.sha256(source.encode()).hexdigest(),
    'compilerSha256': hashlib.sha256(compiler.read_bytes()).hexdigest(), 'browser': version, 'reports': reports,
    'scope': 'synthetic single-grid parser; not full migration'}, indent=2) + '\n')
print('PASS_LEGACY_GRID native and Chrome Wasm, coordinate mutant')
