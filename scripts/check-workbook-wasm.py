#!/usr/bin/env python3
"""Check the unconnected sparse workbook candidate with native Amu and Chrome.

Usage: python3 scripts/check-workbook-wasm.py AMU_DIR OUTPUT_DIR CHROME
Fixtures are synthetic; this does not exercise the UI, legacy import or QEMU.
"""
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

if len(sys.argv) != 4:
    raise SystemExit(__doc__)
amu, out, chrome = [Path(x).resolve() for x in sys.argv[1:]]
out.mkdir(parents=True, exist_ok=False)
source_path = Path(__file__).resolve().parents[1] / 'src/hyokeisan/workbook.kotoba'
source = source_path.read_text(encoding='utf-8')
entry = '(defn main [] :i64'
if source.count(entry) != 1:
    raise SystemExit('workbook entry changed')
base = source.replace(entry, '(defn wf-self-test [] :i64')
fill = '''
(defn fixture-fill [raw :string i :i64 n :i64] :string
  (loop [raw raw i i]
    (if (= i n) raw
      (let [next (wf-put raw "s" (+ i 1) (+ (rem i 30) 1) (string-concat "cell" (string-from-i64 i)))]
        (if (option-some?-of [:option :string] next)
          (recur (option-value-of [:option :string] next "") (+ i 1)) "")))))
(defn main [] :i64
  (let [book (wf-new "title" "original") sheet (wf-add-sheet (option-value-of [:option :string] book "") "s" "tab")
        raw (fixture-fill (option-value-of [:option :string] sheet "") 0 256)]
    (if (and (= (wf-self-test) 0) (wf-valid? raw)
             (string=? (option-value-of [:option :string] (wf-get raw "s" 256 16) "") "cell255")) 0 1)))
'''
# Generate a deterministic fixture, rather than using Python as the verdict.
def frame(s):
    return str(len(s.encode('utf-8'))) + ':' + s
cells = ''.join(frame(str(i)) + frame(str((i - 1) % 30 + 1)) + frame('cell' + str(i - 1))
                for i in range(1, 1025))
raw = 'HW3|' + frame('title') + frame('original') + frame(frame('s') + frame('tab') + cells)
large = '''
(defn main [] :i64
  (let [raw FIXTURE put (wf-put raw "s" 1025 17 "last") next (option-value-of [:option :string] put "")]
    (if (and (= (wf-self-test) 0) (option-some?-of [:option :string] put)
             (string=? (option-value-of [:option :string] (wf-get next "s" 1025 17) "") "last")
             (string=? (option-value-of [:option :string] (wf-original next) "") "original")) 0 1)))
'''.replace('FIXTURE', json.dumps(raw, ensure_ascii=False))
cell_anchor = '(and (> count 0) (not (wf-before? last-r last-c r c)))'
sheet_anchor = '(string=? (wf-text sheet idf) id)'
if source.count(cell_anchor) != 1 or source.count(sheet_anchor) < 1:
    raise SystemExit('negative control anchor changed')
cases = [
    ('basic', source, 0),
    ('duplicate-cell-mutant', source.replace(cell_anchor, '(= 0 1)', 1), 1),
    ('duplicate-sheet-mutant', source.replace(sheet_anchor, '(= 0 1)', 1), 1),
    ('incremental-256', base + fill, 0),
    ('prebuilt-1024-edit', base + large, 0),
]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

mac = load('mac', amu / 'scripts/seed/check-aiueos-user-macos-native.py')
browser = load('browser', amu / 'scripts/seed/check-wasm32-browser.py')
compiler = amu / 'seed/bootstrap/aarch64-macos/amu-full-root.macho'
runs = []
for name, code, expected in cases:
    p = out / (name + '.kotoba')
    p.write_text(code, encoding='utf-8')
    native = subprocess.run([str(amu / 'bin/amu'), 'run', str(p)], cwd=out,
                            capture_output=True, text=True, timeout=120, check=True)
    if native.stdout.strip() != str(expected):
        raise ValueError(name + ': native result ' + repr(native.stdout))
    mac.native_run(compiler, out, 'compile', p.name, '--target', 'wasm32-browser', '--output', name + '.wasm')
    runs.append((name, out / (name + '.wasm'), dict(fuel=25000000, allow=[], args=[], files={})))
version, lines = browser.run_modules(str(chrome), out, runs, timeout=300)
results = {}
for name, _, expected in cases:
    r = lines[name]
    report = r.get('report') or ''
    if r.get('exit') != 0 or not re.search(rf'\{{:status :ok :result {expected}(?:\s|\}})', report):
        raise ValueError(name + ': browser result ' + repr(r))
    results[name] = {'report': report, 'wasmSha256': hashlib.sha256((out / (name + '.wasm')).read_bytes()).hexdigest()}
(out / 'receipt.json').write_text(json.dumps({
    'sourceSha256': hashlib.sha256(source_path.read_bytes()).hexdigest(),
    'compilerSha256': hashlib.sha256(compiler.read_bytes()).hexdigest(),
    'browser': version, 'results': results,
    'limitations': ['synthetic fixtures', 'no UI, legacy import, QEMU or release qualification'],
}, ensure_ascii=False, indent=2) + '\n')
print('PASS_WORKBOOK_CANDIDATE native and Chrome Wasm, bounded fixtures and duplicate controls')
