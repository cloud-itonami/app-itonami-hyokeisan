#!/usr/bin/env python3
"""Stage the canonical Hyokeisan modules for the selfhost browser compiler."""
import re


def stage(root, entry=True):
    source = (root / 'src/hyokeisan/sheet.kotoba').read_text(encoding='utf-8')
    source, n = re.subn(r'\A\(ns\s+hyokeisan\.sheet\s*\(:export \[main\]\)\)',
                        '(ns hyokeisan.sheet (:export [main]))', source, count=1)
    anchor = '(defn main [] :i64 (test-sheet))'
    if n != 1 or source.count(anchor) != 1:
        raise SystemExit('unexpected sheet source')
    source = source[:source.index(anchor)]
    modules = [
        ('workbook.kotoba', r'\A\(ns\s+hyokeisan\.workbook\s*\(:export \[main\]\)\)', '(defn main [] :i64\n'),
        ('migrate_hs1.kotoba', r'\A\(ns\s+hyokeisan\.migrate-hs1\s*\(:export \[hs1-to-workbook\]\)\s*\(:require \[hyokeisan\.sheet :as sheet\]\s*\[hyokeisan\.workbook :as workbook\]\)\)', None),
        ('workbook_ui.kotoba', r'\A\(ns\s+hyokeisan\.workbook-ui\s*\(:export \[ui-from-hs1 ui-view ui-step\]\)\s*\(:require \[hyokeisan\.sheet :as sheet\]\s*\[hyokeisan\.workbook :as workbook\]\s*\[hyokeisan\.migrate-hs1 :as migrate\]\)\)', None),
    ]
    for filename, pattern, end in modules:
        module = (root / 'src/hyokeisan' / filename).read_text(encoding='utf-8')
        module, n = re.subn(pattern, '', module, count=1)
        if n != 1 or (end and module.count(end) != 1):
            raise SystemExit('unexpected module ' + filename)
        if end:
            module = module[:module.index(end)]
        for prefix in ('sheet/', 'workbook/', 'migrate/'):
            module = module.replace('(' + prefix, '(')
        source += '\n' + module
    if entry:
        source += '\n' + (root / 'src/hyokeisan/browser-entry.kotoba').read_text(encoding='utf-8')
    return source
