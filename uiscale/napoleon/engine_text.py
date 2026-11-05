#!/usr/bin/env python3
"""Napoleon's engine-drawn text inventory (J37, D7): every engine-drawn text item, the layout or exe site behind it, the font it opens per factor and its state.

purpose: generate uiscale/napoleon/engine_text.json from the UI atlas (discovery/ui/engine_drawn.json and the per-context surfaces), the font model and engine-text rows (uiscale/napoleon/font_slots.json) and the scaler's slot rule; each item gets the vanilla font file and the file at each factor, and a state: covered_by_j66, built_here, vanilla_left (with a reason), art_not_text or open
usage: python3 uiscale/napoleon/engine_text.py [--check] [--out uiscale/napoleon/engine_text.json]   (also `python3 core/wsc.py uiscale engine-text [--check]`)
when: after a change to the atlas, font_slots.json or the scaler's slot rule; the tests gate runs --check (re-runs are byte-identical)
not-a-verb: a generator behind `wsc uiscale engine-text` (tools/verbs/uiscale.py), not a registry operation

Stdlib only (no game read): the atlas is the repo's discovery/ui data, built by J10 from the vanilla game.
"""
import argparse
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
for p in ('uiscale/core', 'discovery/core'):
    sys.path.insert(0, os.path.join(REPO, p))
import fontcheck  # noqa: E402
import scale  # noqa: E402

OUT = os.path.join(HERE, 'engine_text.json')
SLOTS = os.path.join(HERE, 'font_slots.json')
CONFIG = os.path.join(HERE, 'config.json')
ATLAS = os.path.join(REPO, 'discovery', 'ui')

# The engine-drawn text items (J10 atlas rows engine.*). kind layout: a layout the engine places (its text states use layout fonts);
# kind exe: text the exe draws with a font it opens itself (font_slots.json engine_text); kind art: text that is a picture.
ITEMS = [
    {'id': 'banner.land', 'row': 'engine.battle_unit_banners', 'kind': 'layout', 'context': 'battle', 'layout': 'battle ui/lb_unit_id'},
    {'id': 'banner.naval', 'row': 'engine.battle_unit_banners', 'kind': 'layout', 'context': 'battle', 'layout': 'battle ui/nb_unit_id'},
    {'id': 'banner.hud_flags', 'row': 'engine.battle_unit_banners', 'kind': 'layout', 'context': 'battle', 'layout': 'battle ui/battle_hud_flags'},
    {'id': 'campaign.city_info_bar', 'row': 'engine.campaign_map_labels', 'kind': 'layout', 'context': 'campaign', 'layout': 'campaign ui/city_info_bar'},
    {'id': 'campaign.faction_hud_flags', 'row': 'engine.campaign_map_labels', 'kind': 'layout', 'context': 'campaign', 'layout': 'campaign ui/faction_hud_flags'},
    {'id': 'engine.ribbon_text', 'row': 'engine.campaign_map_labels', 'kind': 'exe', 'file': 'frontend_22.cuf',
     'site': '0x1215a20 GetFont("Frontend", 22) for the ribbon.fx renderer', 'proof': 'pc',
     'note': 'candidate: map region and sea names drawn along ribbons; which text it is, is a PC question'},
    {'id': 'engine.overlay_text_style', 'row': None, 'kind': 'exe', 'file': 'frontend_22.cuf',
     'site': '0xdae510 GetFont("Frontend", 22): a text style built in the MVC Create UIs step', 'proof': 'pc',
     'note': 'candidate: the front-end version string and other engine overlay text'},
    {'id': 'engine.loading_screen.quote', 'row': 'engine.loading_screen', 'kind': 'exe',
     'files': ['frontend_20.cuf', 'frontend_18.cuf', 'frontend_16.cuf', 'frontend_14.cuf', 'frontend_12.cuf', 'frontend_10.cuf'],
     'site': '0x110d859 fit loop: the first file whose text fits the box', 'proof': 'static_only',
     'note': 'no scenario in the library shows a loading screen to the shot verbs; proved by the file survey (which file the loop keeps)'},
    {'id': 'engine.loading_screen.heading', 'row': 'engine.loading_screen', 'kind': 'art',
     'art': 'ui/frontend ui/loadingscreen/loading_screen_heading.tga', 'note': 'text drawn as art: the loading-screen art role (J36, J53), not fonts'},
    {'id': 'engine.subtitles', 'row': 'engine.subtitles', 'kind': 'open', 'proof': 'static_only',
     'note': 'no GetFont site with a subtitle string: the font is most likely a list slot by id; needs the file survey with a movie and subtitles on'},
    {'id': 'engine.credits', 'row': None, 'kind': 'open', 'proof': 'static_only',
     'note': 'text/credits.xml string fontsize attribute (data); reaches GetFont with the 6..32 rule if traced; credits stop the front-end pump, so no shot'},
    {'id': 'engine.dev_text', 'row': None, 'kind': 'exe', 'files': ['console_12.cuf', 'ingame_16.cuf', 'editor_12.cuf'],
     'site': '0xe33450 console, 0x1197430 render statistics, 0x117fb10 editor gadgets', 'proof': 'static_only', 'dev': True,
     'note': 'developer text, not player UI'},
]


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def load_surfaces(atlas_dir, contexts):
    out = {}
    for ctx in sorted(contexts):
        p = os.path.join(atlas_dir, f'{ctx}.json.gz')
        with gzip.open(p, 'rt', encoding='utf-8') as f:
            out.update(json.load(f)['surfaces'])
    return out


def text_states(surface):
    """[(component path, state name, font)] of the states that carry text (a text key or text length)"""
    out = []
    for c in surface.get('components', []):
        for st in c.get('states', []):
            if st.get('text_key') or st.get('text_len'):
                out.append((c['path'], st.get('name', ''), st.get('font', '')))
    return out


def layout_item(spec, surfaces, model, factors):
    s = surfaces.get(spec['layout'])
    it = {'id': spec['id'], 'row': spec['row'], 'source': f"layout {spec['layout']}", 'context': spec['context']}
    if s is None:
        it.update(state='open', reason=f"layout {spec['layout']} not in the atlas")
        return it
    ts = text_states(s)
    it['opened_by'] = sorted(s.get('opened_by', []))
    if not ts:
        it.update(state='art_not_text', text_states=0,
                  reason='no text-bearing state: the layout draws art only (its art is scaled with the layouts)')
        return it
    fonts = sorted({f for _, _, f in ts})
    it['text_states'] = len(ts)
    it['text_components'] = sorted({p for p, _, _ in ts})
    it['fonts'] = {f: {'vanilla_file': model.file_of(f),
                       'at': {('%g' % fa): {'name': scale.font_slot(f, spec['context']),
                                            'file': model.file_of(scale.font_slot(f, spec['context']))} for fa in factors}} for f in fonts}
    it.update(state='covered_by_j66', reason='a scaled layout: its text states take the scaler\'s slot at the factor (J66 fonts pack)')
    return it


def exe_item(spec, plans):
    files = spec.get('files') or [spec['file']]
    it = {'id': spec['id'], 'row': spec['row'], 'source': f"exe {spec['site']}", 'files': files, 'proof': spec['proof'], 'note': spec['note']}
    if spec.get('dev'):
        it.update(state='vanilla_left', reason='developer text (console, render statistics, editor): not player UI')
        return it
    at = {}
    for fa, plan in plans.items():
        at[fa] = {f: ('render' if f in plan['render'] else 'skipped: ' + plan['skipped'].get(f, 'not in font_slots.json engine_text'))
                  for f in files}
    it['at'] = at
    built = all(v == 'render' for a in at.values() for v in a.values())
    it.update(state='built_here' if built else 'vanilla_left',
              reason='rendered at the install factor into the file the exe opens' if built else 'not every file is rendered at every factor: see at')
    return it


def build(surfaces, slots, factors, engine_drawn=None):
    """the inventory dict (deterministic). surfaces: {layout: atlas surface}; slots: font_slots.json; factors: [2.0, ...]"""
    model = fontcheck.Model(slots['engine'])
    layout_files = {}
    for fa in factors:
        fs = set()
        for spec in ITEMS:
            if spec['kind'] == 'layout' and spec['layout'] in surfaces:
                for _, _, f in text_states(surfaces[spec['layout']]):
                    fs.add(scale.font_file(scale.font_slot(f, spec['context'])))
        layout_files[fa] = fs
    # every scaled layout's slot files matter for the plan, not only the engine items': the generator gets them from the slot rule over all surfaces
    for fa in factors:
        for name, s in surfaces.items():
            ctx = scale.context_of('ui\\' + name.replace('/', '\\'))
            for f in s.get('fonts', []):
                ff = scale.font_file(scale.font_slot(f, ctx))
                if ff:
                    layout_files[fa].add(ff)
    plans = {('%g' % fa): fontcheck.plan_engine(slots['engine_text'], fa, layout_files[fa]) for fa in factors}
    rows = {r['id']: r for r in (engine_drawn or {}).get('items', [])}
    items = []
    for spec in ITEMS:
        if spec['kind'] == 'layout':
            it = layout_item(spec, surfaces, model, factors)
        elif spec['kind'] == 'exe':
            it = exe_item(spec, plans)
        elif spec['kind'] == 'art':
            it = {'id': spec['id'], 'row': spec['row'], 'source': f"art {spec['art']}", 'state': 'art_not_text', 'reason': spec['note']}
        else:
            it = {'id': spec['id'], 'row': spec['row'], 'source': 'unknown', 'state': 'open', 'proof': spec['proof'], 'reason': spec['note']}
        if it.get('row') and rows and it['row'] not in rows:
            it['row_missing'] = True
        items.append(it)
    return {'generator': 'uiscale/napoleon/engine_text.py', 'factors': [('%g' % f) for f in factors],
            'model': slots['engine']['evidence'], 'plans': plans, 'items': items}


def dumps(d):
    return json.dumps(d, indent=1, sort_keys=True, ensure_ascii=False) + '\n'


def generate(atlas_dir=ATLAS):
    slots = load(SLOTS)
    factors = load(CONFIG)['factors']
    ctxs = {s['context'] for s in ITEMS if s['kind'] == 'layout'} | {'common', 'frontend', 'template'}
    surfaces = load_surfaces(atlas_dir, ctxs)
    return build(surfaces, slots, factors, load(os.path.join(atlas_dir, 'engine_drawn.json')))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true', help='fail if the committed inventory differs from a fresh run')
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args(argv)
    text = dumps(generate())
    if a.check:
        old = open(a.out, encoding='utf-8').read() if os.path.exists(a.out) else ''
        if old != text:
            print(f'engine_text: {os.path.relpath(a.out, REPO)} is stale: run python3 uiscale/napoleon/engine_text.py')
            return 1
        print('engine_text: up to date')
        return 0
    with open(a.out, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    d = json.loads(text)
    for it in d['items']:
        print(f"{it['id']:<30} {it['state']:<15} {it.get('reason', '')[:90]}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
