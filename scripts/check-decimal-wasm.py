#!/usr/bin/env python3
"""Independent rational fixtures for the bounded Kotoba decimal arithmetic.

Usage: python3 scripts/check-decimal-wasm.py AMU_DIR OUTPUT_DIR CHROME
Python derives expected rational values; Kotoba checks them in native and Wasm.
"""
import hashlib
import importlib.util
import json
import random
import re
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

if len(sys.argv) != 4: raise SystemExit(__doc__)
amu, out, chrome = map(lambda s: Path(s).resolve(), sys.argv[1:])
out.mkdir(parents=True, exist_ok=False)
source = (Path(__file__).resolve().parents[1] / 'src/hyokeisan/sheet.kotoba').read_text()
anchor = '(defn main [] :i64 (test-sheet))'
if source.count(anchor) != 1: raise ValueError('main anchor changed')
scale, maximum = 1000000, 1000000000000000
rng = random.Random(70420261103)
values = [0, 1, -1, 10, -1000, 125000, -333333, 1000000, -2000000,
          999999, 999999000000, -999999000000, maximum, -maximum]
values += [rng.randint(-maximum, maximum) for _ in range(24)]
pairs = [(a,b) for a,b in zip(values, reversed(values))]
pairs += [(rng.randint(-10**9, 10**9)*1000, rng.randint(-10**6, 10**6)*1000) for _ in range(40)]
pairs += [(rng.randint(-10**12, 10**12), rng.choice([1,10,100,1000,10000,100000,1000000,2000000])) for _ in range(40)]
pairs += [(100000, 200000), (1250000, 2000000), (-1000000, 8000000),
          (1,1), (maximum,scale), (maximum,1), (1,2), (scale,3*scale), (0,0), (0,-1)]

def expected(op, a, b):
    if op == 'divide' and b == 0: return None
    result = Fraction(a*b, scale) if op == 'multiply' else Fraction(a*scale, b)
    if result.denominator != 1 or abs(result.numerator) > maximum: return None
    return result.numerator

def assertion(fn, a, b):
    e = expected('multiply' if fn == 'decimal-multiply' else 'divide',a,b)
    expr = f'({fn} {a} {b})'
    if e is None: return f'(not (option-some?-of [:option :i64] {expr}))'
    return f'(and (option-some?-of [:option :i64] {expr}) (= (option-value-of [:option :i64] {expr} 0) {e}))'

checks = [assertion(fn,a,b) for fn in ('decimal-multiply','exact-divide') for a,b in pairs]
for text, value in [('0',0), ('-0.000001',-1), ('.5',500000), ('1.',1000000),
                    ('000.001',1000), ('999999.999999',999999999999)]:
    expr = '(parse-number ' + json.dumps(text) + ')'
    checks.append(f'(and (option-some?-of [:option :i64] {expr}) (= (option-value-of [:option :i64] {expr} 0) {value}))')
for text in ('-', '.', '1.0000001', '1000000', '1..2', '1e3', '1é'):
    expr = '(parse-number ' + json.dumps(text, ensure_ascii=False) + ')'
    checks.append(f'(not (option-some?-of [:option :i64] {expr}))')
checks += ['(string=? (format-number -1) "-0.000001")',
           '(string=? (format-number 1200000) "1.2")',
           '(string=? (format-number 1000000000000000) "1000000000")']
fixture = '(defn main [] :i64 (if (and\n  ' + '\n  '.join(checks) + ') 0 1))\n'
src = out/'decimal-oracle.kotoba';src.write_text(source.replace(anchor, fixture),encoding='utf-8')
native = subprocess.run([str(amu/'bin/amu'),'run',str(src)],capture_output=True,text=True,check=True,timeout=120)
if native.stdout.strip() != '0': raise ValueError('native: '+repr(native.stdout))
spec = importlib.util.spec_from_file_location('mac',amu/'scripts/seed/check-aiueos-user-macos-native.py')
mac = importlib.util.module_from_spec(spec);spec.loader.exec_module(mac)
compiler = amu/'seed/bootstrap/aarch64-macos/amu-full-root.macho'
mac.native_run(compiler,out,'compile',src.name,'--target','wasm32-browser','--output','decimal-oracle.wasm')
subprocess.run([sys.executable,str(amu/'scripts/seed/check-wasm32-browser.py'),'--browser',str(chrome),
                '--app',str(out/'decimal-oracle.wasm'),'--output',str(out/'browser')],check=True)
report = json.loads((out/'browser/app.json').read_text()).get('report','')
if not re.search(r'\{:status :ok :result 0(?:\s|\})',report): raise ValueError(report)
(out/'receipt.json').write_text(json.dumps({'status':'PASS','randomSeed':70420261103,'pairCount':len(pairs),
  'assertionCount':len(checks),'sourceSha256':hashlib.sha256(source.encode()).hexdigest(),
  'generatedFixtureSha256':hashlib.sha256(fixture.encode()).hexdigest(),
  'compilerSha256':hashlib.sha256(compiler.read_bytes()).hexdigest(),
  'wasmSha256':hashlib.sha256((out/'decimal-oracle.wasm').read_bytes()).hexdigest(),
  'scope':'bounded rational arithmetic only; not full spreadsheet compatibility'},indent=2)+'\n')
print('PASS_HYOKEISAN_DECIMAL_RATIONAL native and Chrome Wasm')
