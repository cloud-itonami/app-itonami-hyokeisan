#!/usr/bin/env python3
"""Check the bounded sheet model and arithmetic mutant using Amu and Chrome.
Usage: python3 scripts/check-sheet-wasm.py AMU_DIR OUTPUT_DIR CHROME
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
source = (Path(__file__).resolve().parents[1] / 'src/hyokeisan/sheet.kotoba').read_text()
anchor = 'total (+ (option-value-of [:option :i64] a 0) (option-value-of [:option :i64] b 0))'
if source.count(anchor) != 1: raise ValueError('mutation anchor changed')
sub_anchor = '(if (string=? op "-") (- av bv) (* av bv))'
if source.count(sub_anchor) != 1: raise ValueError('subtraction mutation anchor changed')
spec = importlib.util.spec_from_file_location('mac', amu / 'scripts/seed/check-aiueos-user-macos-native.py')
mac = importlib.util.module_from_spec(spec); spec.loader.exec_module(mac)
compiler = amu / 'seed/bootstrap/aarch64-macos/amu-full-root.macho'
results = {}
cases = [
    ('sheet', source, 0),
    ('mutant', source.replace(anchor, anchor.replace('total (+', 'total (-')), 1),
    ('sub-mutant', source.replace(sub_anchor, sub_anchor.replace('(- av bv)', '(+ av bv)'), 1), 1),
    ('mul-mutant', source.replace(sub_anchor, sub_anchor.replace('(* av bv)', '(+ av bv)'), 1), 1),
]
for name, text, expected in cases:
    src = out / (name + '.kotoba'); src.write_text(text)
    run = subprocess.run([str(amu / 'bin/amu'), 'run', str(src)], capture_output=True, text=True, check=True, timeout=120)
    if run.stdout.strip() != str(expected): raise ValueError('native ' + name + ': ' + run.stdout)
    mac.native_run(compiler, out, 'compile', src.name, '--target', 'wasm32-browser', '--output', name + '.wasm')
    dest = out / (name + '-browser')
    subprocess.run([sys.executable, str(amu / 'scripts/seed/check-wasm32-browser.py'), '--browser', str(chrome),
                    '--app', str(out / (name + '.wasm')), '--output', str(dest)], check=True)
    report = json.loads((dest / 'app.json').read_text()).get('report', '')
    if not re.search(rf'\{{:status :ok :result {expected}(?:\s|\}})', report): raise ValueError(name + ': ' + report)
    results[name] = {'result': expected, 'wasmSha256': hashlib.sha256((out / (name + '.wasm')).read_bytes()).hexdigest()}
(out / 'receipt.json').write_text(json.dumps({'sourceSha256': hashlib.sha256(source.encode()).hexdigest(),
    'compilerSha256': hashlib.sha256(compiler.read_bytes()).hexdigest(), 'results': results}, indent=2) + '\n')
print('PASS_HYOKEISAN_MODEL native, Wasm and addition/subtraction/multiplication mutants')
