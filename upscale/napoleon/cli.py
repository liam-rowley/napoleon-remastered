r"""Napoleon driver of the UI art upscaler (J36): plan, run, verify, sheets, pack over the assets registry, in the art_build Python.

purpose: run the game-agnostic upscale/core over the Napoleon UI art roles (registry rows, files read through the J7 PackFS) and write results to the work folder, the assets registry and the sheets
usage: <work>\art_build\py\python.exe upscale/napoleon/cli.py <plan|run|verify|sheets|pack> --work <dir> [--roles a,b] [--sample N] [--limit N] [--model NAME] [--device cuda|cpu] [--registry] ; normally started by `python3 core/wsc.py upscale <verb>`
when: any upscale step; the host tests call the same functions with the 'lanczos' stand-in
not-a-verb: runs inside the embeddable Python of art_build (no wsc there); `wsc upscale` is the verb that starts it

Reads the game folder and writes only under --work (and, with --registry, registries/assets.jsonl of this repo). The game folder is never written.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path[:0] = [os.path.join(REPO, 'upscale', 'core'), os.path.join(REPO, 'discovery', 'core')]

import rules  # noqa: E402

REGISTRY = os.path.join(REPO, 'registries', 'assets.jsonl')
DEFAULT_WORK = r'C:\napoleon_remastered_pc\upscale\work'
IMG = ('tga', 'dds', 'jpg', 'png')


def load_json(p):
    return json.load(open(p, encoding='utf-8'))


def items_for(roles, registry=REGISTRY):
    """the registry rows of roles, in --roles order (registry order within a role), so a brief's 'small roles first' holds (J51 review)"""
    roles = list(roles)
    out = []
    for line in open(registry, encoding='utf-8'):
        r = json.loads(line)
        if r['role'] not in roles:
            continue
        kind, sub, w, h, mips = rules.parse_format(r['format'])
        out.append({'id': r['id'], 'path': r['path'], 'role': r['role'], 'fmt': kind + (' ' + sub if sub else ''), 'w': w, 'h': h, 'mips': mips})
    return sorted(out, key=lambda it: roles.index(it['role']))


def apply_registry(updates, registry=REGISTRY):
    """set upscale_method / upscale_status on the rows named in updates {id: {field: value}}; every other byte of the file is kept"""
    lines = open(registry, encoding='utf-8').read().split('\n')
    out = []
    for ln in lines:
        if ln.strip():
            r = json.loads(ln)
            if r['id'] in updates:
                r.update(updates[r['id']])
                ln = json.dumps(r, ensure_ascii=False)
        out.append(ln)
    with open(registry, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(out))


def registry_updates(man, items):
    up = {}
    for it in items:
        e = man['entries'].get(it['id'])
        up[it['id']] = rules.registry_fields(e['status'] if e else rules.PENDING, e.get('method', '') if e else '')
    return up


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', choices=['plan', 'run', 'verify', 'sheets', 'compare', 'pack'])
    ap.add_argument('--work', default=DEFAULT_WORK)
    ap.add_argument('--roles', help='comma list; default: the configured first_roles')
    ap.add_argument('--sample', type=int, default=0, help='a fixed sample of N assets across the roles (same sample every time)')
    ap.add_argument('--limit', type=int, default=0, help='stop after N freshly processed assets')
    ap.add_argument('--model', help='force one model (or lanczos) for every role')
    ap.add_argument('--device', default=None)
    ap.add_argument('--models-dir')
    ap.add_argument('--games', default=os.path.join(REPO, 'discovery', 'napoleon', 'games.json'))
    ap.add_argument('--registry', action='store_true', help='write upscale_status / upscale_method into registries/assets.jsonl')
    ap.add_argument('--out', help='pack: output folder (default <work>\\packs)')
    a = ap.parse_args(argv)

    cfg = load_json(os.path.join(HERE, 'config.json'))
    pins = load_json(os.path.join(HERE, 'models.json'))['models']
    roles = a.roles.split(',') if a.roles else cfg['first_roles']
    role_cfgs = cfg['roles']
    items = items_for(roles)
    if a.sample:
        import contact
        by = {}
        for it in items:
            by.setdefault(it['role'], []).append(it)
        per = max(1, a.sample // max(1, len(by)))
        items = [it for r in sorted(by) for it in sorted(by[r], key=lambda x: contact.hashlib.sha256(('sample' + x['id']).encode()).hexdigest())[:per]]
    byid = {it['id']: it for it in items}
    work = a.work
    os.makedirs(work, exist_ok=True)
    models_dir = a.models_dir or os.path.join(os.path.dirname(os.path.normpath(work)), 'art_build', 'models')

    if a.action == 'plan':
        import batch
        per, rows = batch.plan(items, role_cfgs, cfg)
        res = {'roles': per, 'total': len(items), 'run': sum(1 for r in rows if r['decision'] == 'run')}
        json.dump(res, open(os.path.join(work, 'plan.json'), 'w'), indent=1, sort_keys=True)
        print(json.dumps(res, indent=1, sort_keys=True))
        if a.registry:
            man = {'entries': {}}
            from_plan = {}
            for r in rows:
                from_plan[r['id']] = rules.registry_fields(rules.skipped(r['decision'][5:]) if r['decision'] != 'run' else rules.PENDING)
            # keep finished rows: only rows without a status or with todo are written
            cur = {}
            for ln in open(REGISTRY, encoding='utf-8'):
                x = json.loads(ln)
                cur[x['id']] = x.get('upscale_status')
            apply_registry({i: f for i, f in from_plan.items() if cur.get(i) in (None, 'todo', 'not_needed')})
        return 0

    if a.action == 'run':
        import batch
        import model as modelmod
        dev = a.device or cfg['run']['device']
        cfg['encoder'] = cfg.get('encoder', 'python')
        read_fs = _packfs(a.games)
        man = batch.run(items, lambda it: read_fs.read(it['path']), work, cfg, pins, models_dir, role_cfgs, a.limit, dev, model_override=a.model)
        if a.registry:
            apply_registry(registry_updates(man, items))
        return 0

    if a.action == 'verify':
        import batch
        res = batch.verify(work, set(roles) if a.roles else None)
        return 1 if res['failed'] else 0

    if a.action == 'sheets':
        import batch
        import contact
        read_fs = _packfs(a.games)
        man = batch.load_manifest(work)
        es = [e for e in man['entries'].values() if e['role'] in roles]
        read = lambda it: read_fs.read(it['path'])
        allit = {it['id']: it for it in items_for(roles)}
        outdir = os.path.join(REPO, 'extract', 'napoleon', 'upscale_sheets')
        for r in roles:
            p = contact.role_sheet(r, es, work, read, allit, os.path.join(outdir, r + '.png'))
            print('sheet', r, p)
        print('hard', contact.hard_case_sheet(es, work, read, allit, os.path.join(outdir, 'hard_cases_%s.png' % os.path.basename(os.path.normpath(work)))))
        return 0

    if a.action == 'compare':
        import batch
        import contact
        read_fs = _packfs(a.games)
        read = lambda it: read_fs.read(it['path'])
        works, ents = {}, {}
        for name in pins:
            w = os.path.join(work, 'cmp_' + name)
            man = batch.run(items, lambda it: read_fs.read(it['path']), w, cfg, pins, models_dir, role_cfgs, 0, a.device or cfg['run']['device'], model_override=name)
            works[name], ents[name] = w, [e for e in man['entries'].values()]
        outdir = os.path.join(REPO, 'extract', 'napoleon', 'upscale_sheets')
        for r in roles:
            print('compare', r, contact.compare_sheet(r, works, ents, read, byid, os.path.join(outdir, 'compare_' + r + '.png')))
        return 0

    if a.action == 'pack':
        import batch
        import pack
        man = batch.load_manifest(work)
        ver = batch.verify(work, set(roles))
        ok = {i for i, e in man['entries'].items() if e['status'] == 'done' and i not in ver['failed']}
        credits = sorted({pins[n]['credit'] for n in man.get('models', {}) if n in pins})
        out = a.out or os.path.join(work, 'packs')
        for r in roles:
            ents = pack.plan(man, work, {r}, cfg['pack_prefix'], ok)
            if ents:
                pack.build(cfg['pack_name'].format(role=r), ents, work, out, credits)
        return 0


def _packfs(games):
    from packfs import PackFS
    return PackFS.from_games(load_json(games), 'napoleon')


if __name__ == '__main__':
    sys.exit(main())
