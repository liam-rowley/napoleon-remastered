#!/usr/bin/env python3
"""J67 run helper: a scratch copy of the harness adapter for a scale sitting. Usage: mk_adapter.py <WxH> <rules file or ''> <out.json>
Sets ctl.launch.size, dev.log_files=1, dev.file_rules (the scale rules: the adapter's own value, the fixed-sky rules, would drop the
templates redirect) and adds `frontend` to the settle scenes (as J37's sitting did)."""
import json
import sys

size, rules, out = sys.argv[1:4]
d = json.load(open('harness/napoleon/adapter.json', encoding='utf-8'))
launch = d['ctl']['launch']
launch['size'] = size
launch['keys']['dev.log_files'] = '1'
if rules:
    launch['keys']['dev.file_rules'] = rules
scenes = d['ctl']['settle']['ready_scenes']
if 'frontend' not in scenes:
    scenes.append('frontend')
json.dump(d, open(out, 'w', encoding='utf-8'), indent=1)
print(out, size, launch['keys'].get('dev.file_rules'))
