#!/usr/bin/env python3
"""Verify provisional HS1 -> HW3 conversion using native Amu and browser Wasm.

Usage: python3 scripts/check-hs1-migration.py AMU_DIR OUTPUT_DIR CHROME
This stages source modules because the browser project linker is not qualified.
It does not modify browser storage or fetch old-origin data.
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
root = Path(__file__).resolve().parents[1]
paths = [root / 'src/hyokeisan/sheet.kotoba', root / 'src/hyokeisan/workbook.kotoba',
         root / 'src/hyokeisan/migrate_hs1.kotoba']
sheet, workbook, migration = [p.read_text(encoding='utf-8') for p in paths]
sheet, n = re.subn(r'\A\(ns\s+hyokeisan\.sheet\s*\(:export \[main\]\)\)', '(ns hs1-migration-test (:export [main]))', sheet, count=1)
anchor = '(defn main [] :i64 (test-sheet))'
if n != 1 or sheet.count(anchor) != 1:
    raise SystemExit('sheet source changed')
sheet = sheet[:sheet.index(anchor)]
workbook, n = re.subn(r'\A\(ns\s+hyokeisan\.workbook\s*\(:export \[main\]\)\)', '', workbook, count=1)
anchor = '(defn main [] :i64\n'
if n != 1 or workbook.count(anchor) != 1:
    raise SystemExit('workbook source changed')
workbook = workbook[:workbook.index(anchor)]
migration, n = re.subn(r'\A\(ns\s+hyokeisan\.migrate-hs1\s*\(:export \[hs1-to-workbook\]\)\s*\(:require \[hyokeisan\.sheet :as sheet\]\s*\[hyokeisan\.workbook :as workbook\]\)\)', '', migration, count=1)
if n != 1:
    raise SystemExit('migration namespace changed')
migration = migration.replace('(sheet/', '(').replace('(workbook/', '(')
fixture = '''
(defn fixture-state [state :document i :i64] :document
  (if (= i 16) state
    (fixture-state (step state (index-key i) "input"
                     (cond (= i 0) "日本語😀\\n" (= i 6) "" (= i 14) "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" (= i 15) "=A1+3" :else (string-from-i64 i))) (+ i 1))))
(defn fixture-check [state :document raw :string i :i64] :bool
  (if (= i 16) true
    (let [value (wf-get raw "hs1-sheet-1" (+ (quot i 4) 1) (+ (rem i 4) 1))]
      (and (option-some?-of [:option :string] value)
           (string=? (option-value-of [:option :string] value "") (cell-text state i))
           (fixture-check state raw (+ i 1))))))
(defn main [] :i64
  (let [state (fixture-state (init) 0) encoded (snap-encode state)
        original (option-value-of [:option :string] encoded "")
        converted (hs1-to-workbook original) raw (option-value-of [:option :string] converted "")]
    (if (and (option-some?-of [:option :string] encoded)
             (option-some?-of [:option :string] converted) (wf-valid? raw)
             (wf-valid? "HW3|0:0:6:1:s1:S")
             (string=? (option-value-of [:option :string] (wf-original raw) "") original)
             (fixture-check state raw 0)
             (not (option-some?-of [:option :document] (snap-decode raw)))
             (not (option-some?-of [:option :string] (hs1-to-workbook (string-concat original "junk"))))
             (not (option-some?-of [:option :string] (hs1-to-workbook "ああ")))
             (not (option-some?-of [:option :string] (hs1-to-workbook "HS1|01:a")))) 0 1)))
'''
mutation = 'row (+ (quot i 4) 1) col (+ (rem i 4) 1)'
if migration.count(mutation) != 1:
    raise SystemExit('coordinate mutation anchor changed')
cases = [('conversion', migration, 0),
         ('transposed-mutant', migration.replace(mutation, 'row (+ (rem i 4) 1) col (+ (quot i 4) 1)', 1), 1)]
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
    p.write_text('\n'.join([sheet, workbook, code, fixture]), encoding='utf-8')
    native = subprocess.run([str(amu / 'bin/amu'), 'run', str(p)], cwd=out, capture_output=True,
                            text=True, timeout=120, check=True)
    if native.stdout.strip() != str(expected):
        raise ValueError(name + ': native result ' + repr(native.stdout))
    mac.native_run(compiler, out, 'compile', p.name, '--target', 'wasm32-browser', '--output', name + '.wasm')
    runs.append((name, out / (name + '.wasm'), dict(fuel=25000000, allow=[], args=[], files={})))
version, lines = browser.run_modules(str(chrome), out, runs, timeout=300)
results = {}
for name, _, expected in cases:
    r = lines[name]; report = r.get('report') or ''
    if r.get('exit') != 0 or not re.search(rf'\{{:status :ok :result {expected}(?:\s|\}})', report):
        raise ValueError(name + ': browser result ' + repr(r))
    results[name] = {'report': report, 'wasmSha256': hashlib.sha256((out / (name + '.wasm')).read_bytes()).hexdigest()}
(out / 'receipt.json').write_text(json.dumps({'sourceSha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
    'compilerSha256': hashlib.sha256(compiler.read_bytes()).hexdigest(), 'browser': version, 'results': results,
    'limitations': ['synthetic data', 'staged source graph', 'no persistent upgrade, old-origin migration, UI or QEMU']},
    ensure_ascii=False, indent=2) + '\n')
print('PASS_HS1_TO_WORKBOOK native and browser Wasm, including transposed-coordinate control')
