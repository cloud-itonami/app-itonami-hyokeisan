#!/usr/bin/env python3
"""Link the browser-staged Hyokeisan model into a native Kotoba host.

Usage: script AMU_DIR KOTOBA_DIR BROWSER_BUILD OUTPUT_DIR
Synthetic macOS Arm only. This does not qualify OS GUI, QEMU or persistence.
"""
import hashlib,importlib.util,json,sys,types
from pathlib import Path
from browser_source import stage as browser_stage
from native_workbook_source import stage as host_stage
if len(sys.argv)!=5:raise SystemExit(__doc__)
amu,kotoba,build,out=map(lambda x:Path(x).resolve(),sys.argv[1:]);root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('native_gate',kotoba/'lib/kotoba.hata/scripts/native_gate.py');ng=importlib.util.module_from_spec(spec);spec.loader.exec_module(ng)
args=types.SimpleNamespace(compiler=amu/'seed/bootstrap/aarch64-macos/amu-full-root.macho',compiler_sha256='2c551579c06a0228029bb06bae177e93126ecbbc37d636d693c471dbac8d1536',packager=amu/'seed/bootstrap/aarch64-macos/kotoba-packager-root.macho',packager_sha256='e95284408f091c8979ef74ece57116a4df2250e61e42074da5dc95ca30264142',output=out)
gate=ng.NativeGate(args)
if not gate.darwin:raise ValueError('test qualifies macOS Arm only')
browser=browser_stage(root);host=host_stage(root);driver=(root/'tests/native_workbook_host.kotoba').read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest()
receipt=json.loads((build/'build-receipt.json').read_text())
if browser.encode()!=(build/'program.kotoba').read_bytes() or sha(browser.encode())!=receipt['sourceSha256'] or (root/'browser/app.js').read_bytes()!=(build/'app.js').read_bytes():raise ValueError('stale browser candidate')
if host.split('\n',1)[1]!=browser.split('\n',1)[1]:raise ValueError('model body changed')
files={'hyokeisan/sheet.kotoba':host.encode(),'hyokeisan/native_workbook_host.kotoba':driver}
image=gate.build('host','hyokeisan/native_workbook_host.kotoba',files);gate.run('linked-model',image)
needle=b'(string=? target "sheet-add")) (ui-new-sheet raw 1)'
if files['hyokeisan/sheet.kotoba'].count(needle)!=1:raise ValueError('mutation anchor')
mutant=dict(files);mutant['hyokeisan/sheet.kotoba']=mutant['hyokeisan/sheet.kotoba'].replace(needle,b'(string=? target "sheet-add")) (ui-wrap raw id top left)')
broken=gate.build('mutant','hyokeisan/native_workbook_host.kotoba',mutant);gate.run('mutation-detected',broken,expected=1)
# Missing transition must return a normal refusal, not crash the host fixture.
mutant=dict(files);mutant['hyokeisan/sheet.kotoba']=mutant['hyokeisan/sheet.kotoba'].replace(needle,b'(string=? target "never-add")) (ui-new-sheet raw 1)')
broken=gate.build('refusal-mutant','hyokeisan/native_workbook_host.kotoba',mutant);gate.run('refusal-detected',broken,expected=1)

gate.finish('PASS_HYOKEISAN_LINKED_HOST',observerSHA256=sha(Path(__file__).read_bytes()),stagerSHA256=sha((root/'scripts/native_workbook_source.py').read_bytes()),browserStagerSHA256=sha((root/'scripts/browser_source.py').read_bytes()),nativeGateSHA256=sha((kotoba/'lib/kotoba.hata/scripts/native_gate.py').read_bytes()),browserBuild=receipt,hostSourceSha256=sha(host.encode()),scope='macOS Arm native synthetic data; no Itonami OS GUI, QEMU, durable storage or release')
