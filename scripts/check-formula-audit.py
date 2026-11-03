#!/usr/bin/env python3
"""Check complete formula counting and bounded location reporting in native/Wasm.

Usage: python3 scripts/check-formula-audit.py AMU_DIR OUTPUT_DIR CHROME
Synthetic fixtures; a formula inventory does not assess calculation compatibility.
"""
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

amu, out, chrome = map(lambda s: Path(s).resolve(), sys.argv[1:])
out.mkdir(parents=True, exist_ok=False)
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'scripts'))
from browser_source import stage
source = stage(root, entry=False)
frame = lambda s: str(len(s.encode('utf-8'))) + ':' + s
cell = lambda row, col, value: frame(str(row)) + frame(str(col)) + frame(value)
first = frame('s:1') + frame('見積<&') + ''.join(cell(i, 1, '=A1/2') for i in range(1, 23))
second = frame('s:2') + frame('別紙') + cell(50, 27, '=3+4')
book = 'HW3|' + frame('Book') + frame('') + frame(first) + frame(second)
state = 'HU1|' + frame(book) + frame('s:1') + frame('1') + frame('1')
expected = 'FA1|' + frame('23') + frame('20') + ''.join(frame('s:1') + frame('見積<&') + frame('A' + str(i)) for i in range(1, 21))
second_book = 'HW3|' + frame('Book') + frame('') + frame(frame('s:1') + frame('見積<&') + cell(1, 1, 'text') + cell(2, 1, '=1+2')) + frame(second)
second_state = 'HU1|' + frame(second_book) + frame('s:1') + frame('1') + frame('1')
second_expected = 'FA1|' + frame('2') + frame('2') + frame('s:1') + frame('見積<&') + frame('A2') + frame('s:2') + frame('別紙') + frame('AA50')
empty_book = 'HW3|' + frame('Book') + frame('') + frame(frame('s:1') + frame('Empty') + cell(1, 1, 'text'))
empty_state = 'HU1|' + frame(empty_book) + frame('s:1') + frame('1') + frame('1')
long_id, long_title = 'x' * 1024, 'y' * 1024
long_sheet = frame(long_id) + frame(long_title) + ''.join(cell(i, 1, '=1') for i in range(1, 11))
long_book = 'HW3|' + frame('Book') + frame('') + frame(long_sheet)
long_state = 'HU1|' + frame(long_book) + frame(long_id) + frame('1') + frame('1')
long_expected = 'FA1|' + frame('10') + frame('7') + ''.join(frame(long_id) + frame(long_title) + frame('A' + str(i)) for i in range(1, 8))
literal = lambda s: json.dumps(s, ensure_ascii=False)
fixture = f'''
(defn eq-audit [state :string expected :string] :bool
  (let [r (formula-audit state)] (and (option-some?-of [:option :string] r)
    (string=? (option-value-of [:option :string] r "") expected))))
(defn main [] :i64
  (if (and (eq-audit {literal(state)} {literal(expected)})
           (eq-audit {literal(second_state)} {literal(second_expected)})
           (eq-audit {literal(empty_state)} "FA1|1:01:0")
           (eq-audit {literal(long_state)} {literal(long_expected)})
           (not (option-some?-of [:option :string] (formula-audit "HU1|bad")))) 0 1))
'''
anchor = '(< shown 20)'
if source.count(anchor) != 1: raise ValueError('mutation anchor changed')
cases = [('audit', source, 0), ('location-limit-mutant', source.replace(anchor, '(< shown 19)', 1), 1)]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
mac = load('mac', amu / 'scripts/seed/check-aiueos-user-macos-native.py')
browser = load('browser', amu / 'scripts/seed/check-wasm32-browser.py')
compiler = amu / 'seed/bootstrap/aarch64-macos/amu-full-root.macho'
runs = []
for name, code, expected_exit in cases:
    p = out / (name + '.kotoba'); p.write_text(code + '\n' + fixture, encoding='utf-8')
    native = subprocess.run([str(amu / 'bin/amu'), 'run', str(p)], cwd=out, capture_output=True, text=True, timeout=120, check=True)
    if native.stdout.strip() != str(expected_exit): raise ValueError(name + ': native ' + repr(native.stdout))
    mac.native_run(compiler, out, 'compile', p.name, '--target', 'wasm32-browser', '--output', name + '.wasm')
    runs.append((name, out / (name + '.wasm'), dict(fuel=25000000, allow=[], args=[], files={})))
version, reports = browser.run_modules(str(chrome), out, runs, timeout=300)
for name, _, expected_exit in cases:
    r = reports[name]
    if r.get('exit') != 0 or not re.search(rf'\{{:status :ok :result {expected_exit}(?:\s|\}})', r.get('report') or ''):
        raise ValueError(name + ': browser ' + repr(r))
(out / 'receipt.json').write_text(json.dumps({'sourceSha256': hashlib.sha256(source.encode()).hexdigest(),
    'compilerSha256': hashlib.sha256(compiler.read_bytes()).hexdigest(), 'browser': version,
    'checks': ['cross-sheet coordinates', 'all 23 counted', 'first 20 only', 'long labels bounded without truncating count', 'empty', 'invalid refusal', 'location-limit mutant'],
    'limitations': ['synthetic only', 'no formula result or compatibility validation', 'no QEMU or publication']}, indent=2) + '\n')
print('PASS_FORMULA_AUDIT native and Wasm, including location-limit mutant')
