"""Stage the browser compiler unit for a native Kotoba host.

Only the module export declaration changes; all workbook, formula and
migration definitions are identical. The OS runtime and host remain separate.
"""
from browser_source import stage as browser_stage

def stage(root):
    source = browser_stage(root)
    old = '(ns hyokeisan.sheet (:export [main]))'
    new = '(ns hyokeisan.sheet (:export [init view step snap-encode snap-decode ui-from-hs1 ui-view ui-step browser-wrap browser-unpack browser-protect browser-view-node main]))'
    if not source.startswith(old):
        raise ValueError('unexpected staged module declaration')
    return new + source[len(old):]
