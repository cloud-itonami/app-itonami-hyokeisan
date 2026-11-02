#!/usr/bin/env python3
"""Test current-sheet formulas across the sparse workbook in native and Wasm.

Usage: python3 scripts/check-workbook-formula.py AMU_DIR OUTPUT_DIR CHROME
Synthetic fixtures; no full spreadsheet compatibility or QEMU is implied.
"""
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
if len(sys.argv) != 4: raise SystemExit(__doc__)
amu,out,chrome=[Path(x).resolve() for x in sys.argv[1:]];out.mkdir(parents=True,exist_ok=False)
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'scripts'))
from browser_source import stage
source=stage(root,entry=False)
fixture='''
(defn put! [raw :string id :string row :i64 col :i64 value :string] :string
  (option-value-of [:option :string] (wf-put raw id row col value) ""))
(defn fill [raw :string i :i64] :string
  (loop [book raw n i]
    (if (= n 64) book (recur (put! book "one" (+ 100 n) 1 "1") (+ n 1)))))
(defn result-is [raw :string id :string row :i64 col :i64 value :i64] :bool
  (let [result (formula-cell raw id row col "" 0)]
    (and (option-some?-of [:option :i64] result) (= (option-value-of [:option :i64] result 0) value))))
(defn result-bad [raw :string id :string row :i64 col :i64] :bool
  (not (option-some?-of [:option :i64] (formula-cell raw id row col "" 0))))
(defn main [] :i64
 (let [book (option-value-of [:option :string] (wf-new "book" "original") "")
       s1 (option-value-of [:option :string] (wf-add-sheet book "one" "One") "")
       s2 (option-value-of [:option :string] (wf-add-sheet s1 "two" "Two") "")
       a (put! s2 "one" 1 1 "3") b (put! a "one" 1 5 "4")
       c (put! b "one" 50 27 "=A1+E1") d (put! c "one" 51 27 "=SUM(A1:E1)")
       e (put! d "one" 52 27 "=-3*E1") f (put! e "one" 1048576 16384 "13")
       g (put! f "one" 53 27 "=XFD1048576") h (put! g "one" 55 27 "=AA56")
       j (put! h "one" 56 27 "=AA55") k (put! j "one" 57 27 "=XFE1")
       l (put! k "one" 58 27 "=ああ1234") m (put! l "one" 59 27 "=A1+2*3")
       p (put! m "two" 1 1 "7") q (put! p "two" 1 2 "=A1+2")
       r (fill q 0) final (put! r "one" 2 2 "=SUM(A100:A163)")]
  (if (and (wf-valid? final) (result-is final "one" 50 27 7) (result-is final "one" 51 27 7)
           (result-is final "one" 52 27 -12) (result-is final "one" 53 27 13)
           (result-bad final "one" 55 27) (result-bad final "one" 57 27)
           (result-bad final "one" 58 27) (result-bad final "one" 59 27)
           (result-is final "two" 1 2 9) (result-is final "one" 2 2 64)
           (= (formula-ref "A0") -1) (= (formula-ref "XFE1") -1)
           (= (formula-ref "A1048577") -1)) 0 1)))
'''
anchor='(+ (* col 26) (- c 64))'
if source.count(anchor)!=1: raise SystemExit('column mutation anchor changed')
cases=[('formula',source,0),('column-mutant',source.replace(anchor,'(+ (* col 26) (- c 65))',1),1)]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
mac=load('mac',amu/'scripts/seed/check-aiueos-user-macos-native.py');browser=load('browser',amu/'scripts/seed/check-wasm32-browser.py')
compiler=amu/'seed/bootstrap/aarch64-macos/amu-full-root.macho';runs=[]
for name,code,expected in cases:
 p=out/(name+'.kotoba');p.write_text(code+'\n'+fixture,encoding='utf-8')
 native=subprocess.run([str(amu/'bin/amu'),'run',str(p)],cwd=out,capture_output=True,text=True,timeout=120,check=True)
 if native.stdout.strip()!=str(expected):raise ValueError(name+': native result '+repr(native.stdout))
 mac.native_run(compiler,out,'compile',p.name,'--target','wasm32-browser','--output',name+'.wasm')
 runs.append((name,out/(name+'.wasm'),dict(fuel=25000000,allow=[],args=[],files={})))
version,lines=browser.run_modules(str(chrome),out,runs,timeout=300);results={}
for name,_,expected in cases:
 r=lines[name];report=r.get('report') or ''
 if r.get('exit')!=0 or not re.search(rf'\{{:status :ok :result {expected}(?:\s|\}})',report):raise ValueError(name+': browser '+repr(r))
 results[name]={'report':report,'wasmSha256':hashlib.sha256((out/(name+'.wasm')).read_bytes()).hexdigest()}
(out/'receipt.json').write_text(json.dumps({'sourceSha256':hashlib.sha256(source.encode()).hexdigest(),'compilerSha256':hashlib.sha256(compiler.read_bytes()).hexdigest(),'browser':version,'results':results,'limitations':['synthetic data','bounded formula subset','no QEMU or release']},indent=2)+'\n')
print('PASS_WORKBOOK_FORMULA native and Chrome Wasm with column mutant')
