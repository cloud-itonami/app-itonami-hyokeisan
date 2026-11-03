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
for name in ('json_string.kotoba', 'json_parse.kotoba', 'legacy_grid.kotoba', 'legacy_metadata.kotoba', 'legacy_workbook.kotoba', 'legacy_pull.kotoba'):
    module = (root / 'src/hyokeisan' / name).read_text(encoding='utf-8')
    module, count = re.subn(r'\A\(ns\s+hyokeisan\.[\s\S]*?\)\)\s*', '', module, count=1)
    if count != 1: raise ValueError('module header: ' + name)
    source += '\n' + module.replace('(js/', '(').replace('(json/', '(').replace('(workbook/', '(').replace('(grid/', '(').replace('(metadata/', '(').replace('(legacy/', '(').replace('(ui/', '(')

def frame(s): return str(len(s.encode('utf-8'))) + ':' + s
rows = [['a', '雪', '', 'emoji😀'], [], ['=A1+2']] + [['1'] for _ in range(70)] + [['x'] * 1024]
raw = json.dumps(rows, ensure_ascii=False, separators=(',', ':'))
escaped = json.dumps([['雪😀', 'line\nnext', '"\\/']], ensure_ascii=True, separators=(',', ':'))
escaped_expected = ''.join(frame('1') + frame(str(c + 1)) + frame(v)
                           for c, v in enumerate(['雪😀', 'line\nnext', '"\\/']))
long_text = ('a' * 31 + '😀' + '"\\\n' + '雪' * 8) * 100
long_token = json.dumps(long_text, ensure_ascii=True)
invalid_strings = ['"' + 'a' * 64 + '\\uD800"', '"' + 'a' * 65 + '"x"', '"' + 'a' * 80 + '雪',
                   '"' + 'x' * 1024 + '\\q"', '"' + 'x' * 1024 + '\\uD800"',
                   '"' + 'x' * 1024 + '\\uDC00"', '"' + 'x' * 1024 + '\\uD800\\u0041"']
buffered_text = ('雪😀\n\t"\\/é' * 150) + '\x00'
buffered_token = json.dumps(buffered_text, ensure_ascii=True)
boundary_token = '"' + 'a' * 29 + '\\uD83D\\uDE00' + 'b' * 29 + '"'
boundary_text = 'a' * 29 + '😀' + 'b' * 29
grid_object = json.dumps({**{'Sheet' + str(i): [[str(i)]] for i in range(40)},
                          '予算!': [['雪', '😀']]}, ensure_ascii=False, separators=(',', ':'))
object_expected = frame('1') + frame('1') + frame('雪') + frame('1') + frame('2') + frame('😀')
object_titles = ''.join(frame('Sheet' + str(i)) for i in range(40)) + frame('予算!')
metadata_items = [{'sheetId': i, 'title': 'Sheet' + str(i), 'index': i, 'rowCount': 1000, 'columnCount': 26} for i in range(40)]
metadata_items.append({'sheetId': 'final', 'title': '予算!', 'index': 40})
metadata = json.dumps(metadata_items, ensure_ascii=False, separators=(',', ':'))
metadata_pairs = ''.join(frame('n:' + str(i)) + frame('Sheet' + str(i)) for i in range(40)) + frame('s:final') + frame('予算!')
small_metadata = '[{"sheetId":0,"title":"A","color":"blue"},{"sheetId":"b","title":"B"}]'
small_grid = '{"B":[["x"]],"A":[["雪",""],["=A1+2","3"]]}'
provenance = 'LE1|' + frame('予算') + frame(small_metadata) + frame(small_grid)
cells_a = frame('1') + frame('1') + frame('雪') + frame('2') + frame('1') + frame('=A1+2') + frame('2') + frame('2') + frame('3')
cells_b = frame('1') + frame('1') + frame('x')
book = 'HW3|' + frame('予算') + frame(provenance) + frame(frame('n:0') + frame('A') + cells_a) + frame(frame('s:b') + frame('B') + cells_b)
candidate = 'HU1|' + frame(book) + frame('n:0') + frame('1') + frame('1')
edn = lambda value: json.dumps(value, ensure_ascii=False)
attrs = {':sheet/type': [edn('Spreadsheet')], ':sheet/id': [edn('sheet:book:demo')],
         ':sheet/slug': [edn('demo')], ':sheet/title': [edn('予算')], ':sheet/revision': ['7'],
         ':sheet/sheetsJson': [edn(small_metadata)], ':sheet/gridJson': [edn(small_grid)], ':sheet/unknown': [edn('retain')]}
pull_obj = {'ok': True, 'graph': 'bfixture', 'entity': 'sheet:book:demo', 'attrs': attrs}
pull = json.dumps(pull_obj, ensure_ascii=False, separators=(',', ':'))
pull_book = 'HW3|' + frame('予算') + frame('LE2|' + frame(pull)) + frame(frame('n:0') + frame('A') + cells_a) + frame(frame('s:b') + frame('B') + cells_b)
unicode_source_book = 'HW3|' + frame('予算') + frame('😀x') + frame(frame('n:0') + frame('A') + cells_a)
malformed_source_book = 'HW3|' + frame('予算') + frame('LE1|1:x0:0:extra') + frame(frame('n:0') + frame('A') + cells_a)
pull_candidate = 'HU1|' + frame(pull_book) + frame('n:0') + frame('1') + frame('1')
pull_info = 'LP1|' + frame('bfixture') + frame('sheet:book:demo') + frame('7')
def altered_pull(change):
    value = json.loads(pull)
    change(value)
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
bad_pulls = [altered_pull(lambda x: x.update(entity='sheet:book:other')),
             altered_pull(lambda x: x['attrs'].update({':sheet/id': [edn('sheet:book:other')]})),
             altered_pull(lambda x: x['attrs'].pop(':sheet/gridJson')),
             altered_pull(lambda x: x['attrs'].update({':sheet/title': [edn('x'), edn('y')]})),
             altered_pull(lambda x: x['attrs'].update({':sheet/title': []})),
             altered_pull(lambda x: x['attrs'].update({':sheet/title': ['null']})),
             altered_pull(lambda x: x['attrs'].update({':sheet/title': [edn('x'), 'null']})),
             altered_pull(lambda x: x['attrs'].update({':sheet/revision': ['-1']})),
             altered_pull(lambda x: x.update(ok=False)), '{"ok":true,"datoms":[]}']
large_metadata = '[{"sheetId":0,"title":"A"}]'
large_grid = json.dumps({'A': [['x' * 20] * 800]}, separators=(',', ':'))
bad_metadata = ['[{"sheetId":1,"title":"A"},{"sheetId":1,"title":"B"}]',
                '[{"sheetId":1,"title":"A"},{"sheetId":2,"title":"A"}]',
                '[{"sheetId":1,"title":"A","title":"B"}]',
                '[{"sheetId":-1,"title":"A"}]', '[{"sheetId":1}]', '[{"sheetId":1,"title":"A"},]',
                '[{"sheetId":1,"title":"A"}] trailing']
bad_objects = ['{"A":[["a"]],"\\u0041":[["b"]]}', '{"A":[["a"]],}',
               '{"A":[["a"]],"B":[[null]]}', '{"A":[["a"]]} trailing', '{"A":null}']
match_grid = '{"A":[["one"]],"B":[]}'
matching = [frame('A') + frame('B'), frame('B') + frame('A')]
mismatching = [frame('A'), frame('A') + frame('B') + frame('C'),
               frame('A') + frame('A'), frame('A') + '2:B']
expected = ''.join(frame(str(r + 1)) + frame(str(c + 1)) + frame(v)
                   for r, row in enumerate(rows) for c, v in enumerate(row) if v)
literal = lambda x: json.dumps(x, ensure_ascii=False)
bad = ['[[],]', '[["x",]]', '[["x"]] trailing', '[[null]]', '[["\\q"]]',
       '[["\\雪"]]', '[["a"]', '[1]', '{"x":1}', '[["\\uD800"]]']
fixture = '\n(defn main [] :i64\n (let [v (legacy-grid-cells ' + literal(raw) + ')] (if (and ' + \
    '(option-some?-of [:option :string] v) (string=? (option-value-of [:option :string] v "") ' + literal(expected) + ') ' + \
    '(string=? (option-value-of [:option :string] (legacy-grid-cells ' + literal(escaped) + ') "bad") ' + literal(escaped_expected) + ') ' + \
    '(string=? (option-value-of [:option :string] (json-unquote ' + literal(long_token) + ') "bad") ' + literal(long_text) + ') ' + \
    '(string=? (option-value-of [:option :string] (json-unquote ' + literal(buffered_token) + ') "bad") ' + literal(buffered_text) + ') ' + \
    '(string=? (option-value-of [:option :string] (json-unquote ' + literal(boundary_token) + ') "bad") ' + literal(boundary_text) + ') ' + \
    ' '.join('(not (option-some?-of [:option :string] (json-unquote ' + literal(item) + ')))' for item in invalid_strings) + ' ' + \
    '(string=? (option-value-of [:option :string] (legacy-grid-find ' + literal(grid_object) + ' "予算!") "bad") ' + literal(object_expected) + ') ' + \
    '(string=? (option-value-of [:option :string] (legacy-metadata-pairs ' + literal(metadata) + ') "bad") ' + literal(metadata_pairs) + ') ' + \
    '(string=? (option-value-of [:option :string] (legacy-metadata-titles ' + literal(metadata) + ') "bad") ' + literal(object_titles) + ') ' + \
    '(legacy-grid-match-titles ' + literal(grid_object) + ' (option-value-of [:option :string] (legacy-metadata-titles ' + literal(metadata) + ') "bad")) ' + \
    '(string=? (option-value-of [:option :string] (legacy-workbook-candidate "予算" ' + literal(small_metadata) + ' ' + literal(small_grid) + ') "bad") ' + literal(candidate) + ') ' + \
    '(string=? (option-value-of [:option :string] (legacy-pull-candidate ' + literal(pull) + ') "bad") ' + literal(pull_candidate) + ') ' + \
    '(string=? (option-value-of [:option :string] (legacy-pull-info ' + literal(pull) + ') "bad") ' + literal(pull_info) + ') ' + \
    '(string=? (option-value-of [:option :string] (ui-legacy-part ' + literal(book) + ' "sheets") "bad") ' + literal(small_metadata) + ') ' + \
    '(string=? (option-value-of [:option :string] (ui-legacy-part ' + literal(pull_book) + ' "pull") "bad") ' + literal(pull) + ') ' + \
    '(not (option-some?-of [:option :string] (ui-legacy-part ' + literal(book) + ' "pull"))) ' + \
    '(not (option-some?-of [:option :string] (ui-legacy-part ' + literal(unicode_source_book) + ' "title"))) ' + \
    '(not (option-some?-of [:option :string] (ui-legacy-part ' + literal(malformed_source_book) + ' "title"))) ' + \
    ' '.join('(not (option-some?-of [:option :string] (legacy-pull-candidate ' + literal(item) + ')))' for item in bad_pulls) + ' ' + \
    '(option-some?-of [:option :document] (ui-read ' + literal(candidate) + ')) ' + \
    '(not (option-some?-of [:option :string] (legacy-workbook-candidate "予算" ' + literal(small_metadata) + ' "{\\"A\\":[]}"))) ' + \
    '(not (option-some?-of [:option :string] (legacy-workbook-candidate "x" "[]" "{}"))) ' + \
    '(not (option-some?-of [:option :string] (legacy-workbook-candidate "big" ' + literal(large_metadata) + ' ' + literal(large_grid) + '))) ' + \
    ' '.join('(not (option-some?-of [:option :string] (legacy-metadata-pairs ' + literal(item) + ')))' for item in bad_metadata) + ' ' + \
    '(legacy-grid-match-titles ' + literal(grid_object) + ' ' + literal(object_titles) + ') ' + \
    '(not (option-some?-of [:option :string] (legacy-grid-find ' + literal(grid_object) + ' "missing"))) ' + \
    ' '.join('(legacy-grid-match-titles ' + literal(match_grid) + ' ' + literal(item) + ')' for item in matching) + ' ' + \
    ' '.join('(not (legacy-grid-match-titles ' + literal(match_grid) + ' ' + literal(item) + '))' for item in mismatching) + ' ' + \
    '(legacy-grid-match-titles "{}" "") (not (legacy-grid-match-titles "{}" "1:A")) ' + \
    ' '.join('(not (option-some?-of [:option :string] (legacy-grid-find ' + literal(item) + ' "A")))' for item in bad_objects) + ' ' + \
    ' '.join('(not (option-some?-of [:option :string] (legacy-grid-cells ' + literal(item) + ')))' for item in bad) + ') 0 1)))\n'
anchor = '(if (= (string-byte-length value) 0) "" (wf-cell row col value))'
if source.count(anchor) != 1: raise ValueError('coordinate mutation anchor changed')
count_anchor = '(string=? (string-from-i64 count) expected)'
if source.count(count_anchor) != 1: raise ValueError('title-count mutation anchor changed')
id_anchor = '(lg-seen? ids ident)'
if source.count(id_anchor) != 1: raise ValueError('sheet-id mutation anchor changed')
provenance_anchor = '(wf-frame grid-json)'
if source.count(provenance_anchor) != 1: raise ValueError('provenance mutation anchor changed')
pull_id_anchor = '(not (string=? e (option-value-of [:option :string] id "")))'
if source.count(pull_id_anchor) != 1: raise ValueError('pull identity mutation anchor changed')
pull_source_anchor = '(string-concat "LE2|" (wf-frame raw))'
if source.count(pull_source_anchor) != 1: raise ValueError('pull provenance mutation anchor changed')
buffer_limit_anchor = '(if (>= next 131072) -2'
if source.count(buffer_limit_anchor) != 1: raise ValueError('buffer fallback mutation anchor changed')
pull_cardinality_anchor = '(option-some?-of [:option :string] second)'
if source.count(pull_cardinality_anchor) != 1: raise ValueError('pull cardinality mutation anchor changed')
surrogate_anchor = '(not (= (string-code-point-at s (+ p 7)) 117))) -1 (+ p 12))'
if source.count(surrogate_anchor) != 1: raise ValueError('surrogate split mutation anchor changed')
cases = [('grid', source, 0), ('buffer-fallback', source.replace(buffer_limit_anchor, '(if (>= next 8) -2', 1), 0), ('coordinate-mutant', source.replace(anchor, '(if (= (string-byte-length value) 0) "" (wf-cell col row value))', 1), 1),
         ('title-count-mutant', source.replace(count_anchor, 'true', 1), 1),
         ('duplicate-id-mutant', source.replace(id_anchor, 'false', 1), 1),
         ('provenance-mutant', source.replace(provenance_anchor, '(wf-frame "")', 1), 1),
         ('pull-id-mutant', source.replace(pull_id_anchor, 'false', 1), 1),
         ('pull-source-mutant', source.replace(pull_source_anchor, '(string-concat "LE2|" (wf-frame ""))', 1), 1),
         ('pull-cardinality-mutant', source.replace(pull_cardinality_anchor, 'false', 1), 1),
         ('surrogate-split-mutant', source.replace(surrogate_anchor, '(not (= (string-code-point-at s (+ p 7)) 117))) -1 (+ p 6))', 1), 1)]

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
