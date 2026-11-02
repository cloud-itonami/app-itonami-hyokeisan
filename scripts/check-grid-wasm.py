#!/usr/bin/env python3
"""Run the Kotoba grid checks in selfhost Wasm with a row-stride mutant.

Usage: python3 scripts/check-grid-wasm.py AMU_DIR NEW_OUTPUT_DIR CHROME
The Amu checkout supplies its macOS ARM64 root and browser harness.
"""
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

if len(sys.argv) != 4:
    raise SystemExit(__doc__)
amu, out, chrome = (Path(x).resolve() for x in sys.argv[1:])
out.mkdir(parents=True, exist_ok=False)
source = Path(__file__).resolve().parents[1] / 'src/hyokeisan/grid.kotoba'
s = source.read_text(encoding='utf-8')
old = '(vector-assoc grid (+ (* row 4) col) value)'
if s.count(old) != 1:
    raise SystemExit('negative control does not match source')
spec = importlib.util.spec_from_file_location('amu_mac_native', amu / 'scripts/seed/check-aiueos-user-macos-native.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
for name, text, expected in [('grid', s, 0), ('mutant', s.replace(old, old.replace('row 4', 'row 3')), 1)]:
    (out / f'{name}.kotoba').write_text(text, encoding='utf-8')
    mod.native_run(amu / 'seed/bootstrap/aarch64-macos/amu-full-root.macho', out,
                   'compile', f'{name}.kotoba', '--target', 'wasm32-browser', '--output', f'{name}.wasm')
    run = out / f'{name}-browser'
    subprocess.run([sys.executable, str(amu / 'scripts/seed/check-wasm32-browser.py'),
                    '--browser', str(chrome), '--app', str(out / f'{name}.wasm'), '--output', str(run)], check=True)
    result = json.loads((run / 'app.json').read_text(encoding='utf-8'))
    if not re.search(rf'\{{:status :ok :result {expected}(?:\s|\}})', result.get('report', '')):
        raise SystemExit(f'{name}: unexpected guest result: {result.get("report")}')
    print(f'{name}: expected result {expected}')
