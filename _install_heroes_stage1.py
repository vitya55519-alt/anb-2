# -*- coding: utf-8 -*-
"""Stage 1: replace the heroines with the six heroes in every per-character table.

Run once from the repo root: python _install_heroes_stage1.py
It rewrites dict/set literals by variable name (AST positions), so the code
around them stays untouched.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from _heroes_data import DEFAULT_HERO, HEROES

ROOT = Path(__file__).resolve().parent
CHAR_DIR = ROOT / 'data' / 'characters'


def r(v) -> str:
    return repr(v)


def face(cid):
    f = HEROES[cid]['folder']
    return f'00_{f}_canonical_face.png'


def look(cid):
    f = HEROES[cid]['folder']
    return f'01_{f}_canonical_look.png'


def dict_src(items, indent='    ') -> str:
    lines = ['{']
    for k, v in items:
        lines.append(f'{indent}{k}: {v},')
    lines.append('}')
    return '\n'.join(lines)


def list_block(values, indent='        ') -> str:
    inner = '\n'.join(f'{indent}{r(v)},' for v in values)
    return '[\n' + inner + '\n    ]'


def gen_retention(field):
    return dict_src([(r(cid), list_block(h[field])) for cid, h in HEROES.items()])


GEN = {
    # main.py
    ('main.py', 'LIBRARY_CHARACTERS'): lambda: dict_src(
        [(r(cid), r(f"{h['emoji']} {h['name']}")) for cid, h in HEROES.items()]),
    ('main.py', 'candidates'): lambda: dict_src(
        [(r(cid), f"base / {r(h['folder'])} / {r(face(cid))}") for cid, h in HEROES.items()], indent='        ')
        .replace('\n}', '\n    }'),
    ('main.py', '_PICKER_GIRLS'): lambda: '(\n' + '\n'.join(
        f"    ({r(cid)}, {r(h['picker_ru'])}, {r(h['picker_en'])})," for cid, h in list(HEROES.items())[:5]) + '\n)',
    # voices
    ('services/voice_service.py', 'CHARACTER_VOICE_PROFILES'): lambda: dict_src(
        [(r(cid), "{\n        'ru': ('ru-RU-DmitryNeural', {'rate': '+0%', 'pitch': '+0Hz'}),\n"
                  f"        'en': ({r(h['edge_en'])}, {{'rate': '+0%', 'pitch': '+0Hz'}}),\n    }}")
         for cid, h in HEROES.items()]),
    ('services/voice_service.py', 'CUSTOM_CHARACTER_VOICE_PROFILE'): lambda: (
        "{\n    'ru': ('ru-RU-DmitryNeural', {'rate': '+3%', 'pitch': '+0Hz'}),\n"
        "    'en': ('en-US-GuyNeural', {'rate': '+3%', 'pitch': '+0Hz'}),\n}"),
    ('services/voice_service.py', 'GEMINI_TTS_VOICES'): lambda: dict_src(
        [(r(cid), r(h['gemini'])) for cid, h in HEROES.items()]),
    ('services/voice_service.py', 'GEMINI_FEMALE_VOICES'): lambda: (
        "(\n    'Algieba', 'Achird', 'Iapetus', 'Orus', 'Algenib', 'Umbriel',\n"
        "    'Puck', 'Charon', 'Fenrir', 'Enceladus', 'Schedar', 'Sadachbia',\n)"),
    ('services/voice_service.py', 'GEMINI_TTS_MANNER'): lambda: dict_src(
        [(r(cid), r(h['manner'])) for cid, h in HEROES.items()]),
    ('services/voice_service.py', 'GROK_ARA_CHARACTERS'): lambda: 'frozenset({\n    ' + ', '.join(
        r(cid) for cid, h in HEROES.items() if h['grok'] == 'rex') + ',\n})',
    ('services/voice_humanize.py', 'SOFT_CHARACTERS'): lambda: "frozenset({'minjun_01', 'maksim_01'})",
    # daily life, partners, plots
    ('services/daily_life.py', 'ROUTINES'): lambda: dict_src(
        [(r(cid), '{\n' + '\n'.join(f"        {r(k)}: {r(v)}," for k, v in h['routine'].items()) + '\n    }')
         for cid, h in HEROES.items()]),
    ('services/custom_character_service.py', '_PARTNER_BY_CHARACTER'): lambda: dict_src(
        [(r(cid), r(h['partner'])) for cid, h in HEROES.items()]),
    ('services/storylines_data.py', 'PLOTS'): lambda: dict_src(
        [(r(cid), '[\n' + '\n'.join(f'        {r(p)},' for p in h['plots']) + '\n    ]')
         for cid, h in HEROES.items()]),
    ('services/voice_samples.py', 'VOICE_SAMPLES'): lambda: dict_src(
        [(r(cid), '(\n' + '\n'.join(f'        {r(s)},' for s in h['samples']) + '\n    )')
         for cid, h in HEROES.items()]),
    # cards
    ('services/character_card_service.py', 'DEFAULT_CARDS'): lambda: dict_src(
        [(r(cid), '{\n'
          f"        \"display_name\": {r(h['name'])},\n"
          "        \"gender\": \"male\",\n"
          f"        \"age\": {h['age']},\n"
          f"        \"short_bio\": {r(h['bio'])},\n"
          "        \"status\": \"active\",\n"
          f"        \"button_emoji\": {r(h['emoji'])},\n"
          "        \"is_visible\": True,\n    }")
         for cid, h in HEROES.items()]),
    ('services/character_card_service.py', 'SCENARIO_HOOKS'): lambda: dict_src(
        [(r(cid), r(h['hook'])) for cid, h in HEROES.items()]),
    ('services/character_card_service.py', 'OPENING_SCENES'): lambda: dict_src(
        [(r(cid), r(h['opening'])) for cid, h in HEROES.items()]),
    ('services/character_card_service.py', '_old_bios'): lambda: '{}',
    ('services/relationship_engine.py', 'CHARACTER_PACE'): lambda: dict_src(
        [(r(cid), r(h['pace'])) for cid, h in HEROES.items()]),
    ('services/relationship_engine.py', 'PACE_HINTS'): lambda: dict_src(
        [(r(cid), r(h['pace_hint'])) for cid, h in HEROES.items()]),
    # storefront faces and bodies
    ('services/webapp_service.py', '_FACE_REFERENCES'): lambda: dict_src(
        [(r(cid), f"('references', {r(h['folder'])}, {r(face(cid))})") for cid, h in HEROES.items()]),
    ('services/photo_service.py', 'BODY_SPECS'): lambda: dict_src(
        [(r(cid), r(h['body'])) for cid, h in HEROES.items()]),
}
for _name, _field in [('MORNING_MESSAGES', 'morning'), ('EVENING_MESSAGES', 'evening'), ('MISS_TEXTS', 'miss'),
                      ('JEALOUSY_TEXTS', 'jealousy'), ('CLIFFHANGER_TEXTS', 'cliff'), ('GIFT_MESSAGES', 'gift'),
                      ('STORY_TEMPLATES', 'stories'), ('MINI_QUESTS', 'quests'), ('WEEKLY_DATES', 'dates')]:
    GEN[('services/retention_features_service.py', _name)] = (lambda f=_field: gen_retention(f))


def _offsets(src: str):
    starts = [0]
    for line in src.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    return starts


def replace_values(path: str, names: dict[str, callable]) -> None:
    p = ROOT / path
    src = p.read_text(encoding='utf-8')
    tree = ast.parse(src)
    spans = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Name) and t.id in names and node.value is not None:
                    v = node.value
                    spans.append((v.lineno, v.col_offset, v.end_lineno, v.end_col_offset, t.id))
    found = {s[4] for s in spans}
    missing = set(names) - found
    if missing:
        raise SystemExit(f'{path}: not found {missing}')
    off = _offsets(src)
    # the byte/char offsets: ast col offsets are in UTF-8 bytes
    lines = src.splitlines(keepends=True)

    def pos(line, col):
        b = lines[line - 1].encode('utf-8')[:col].decode('utf-8')
        return off[line - 1] + len(b)

    for l1, c1, l2, c2, name in sorted(spans, reverse=True):
        a, b = pos(l1, c1), pos(l2, c2)
        src = src[:a] + names[name]() + src[b:]
    ast.parse(src)
    p.write_text(src, encoding='utf-8')
    print('patched', path, sorted(found))


def write_characters():
    template = json.loads((CHAR_DIR / 'vlada_01.json').read_text(encoding='utf-8'))
    for cid, h in HEROES.items():
        d = json.loads(json.dumps(template))
        d['id'] = cid
        d['name'] = h['name']
        d['age'] = h['age']
        d['personality']['core'] = h['core']
        d['personality']['stable_tastes'] = h['tastes']
        d['personality']['communication'].update(
            tone=h['tone'], humor='в его характере', flirting=h['flirting'], initiative=h['initiative'])
        f = h['folder']
        vi = d['visual_identity']
        vi['photo_style'] = {
            'hair_colors': [], 'hairstyles': [],
            'colors': ['black', 'white', 'navy', 'grey', 'olive'],
            'wardrobe_style': f'Stylish modern menswear for a {h["age"]}-year-old man. All outfits are complete.',
        }
        vi['description'] = f'original synthetic adult man {h["age"]} y.o.; {h["looks"]}'
        vi['reference_folder'] = f'data/references/{f}'
        vi['reference_assets'] = [face(cid), look(cid)]
        vi['preserve_identity'] = [h['looks'], h['body']]
        vi['identity_lock'] = f'{h["name_en"]} is an adult man, {h["age"]}. Preserve his face and build from the canonical references in every photo.'
        vi['identity_version'] = f'{f}_v1_2026_11_07'
        for k in ('openai_face_anchor',):
            vi[k] = face(cid)
        for k in ('openai_body_anchor', 'openai_safe_body_anchor', 'openai_secondary_identity_anchor',
                  'seedream_body_anchor', 'seedream_identity_anchor'):
            vi[k] = look(cid)
        vi['body_spec'] = h['body']
        (CHAR_DIR / f'{cid}.json').write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    keep = set(HEROES) | {'leo', 'maksim'}
    for p in CHAR_DIR.glob('*.json'):
        stem = p.stem
        base = stem[:-4] if stem.endswith('_dna') else stem
        if stem in HEROES or base in keep or base in HEROES:
            continue
        p.unlink()
    print('characters written:', sorted(HEROES))


def main():
    by_file: dict[str, dict] = {}
    for (path, name), fn in GEN.items():
        by_file.setdefault(path, {})[name] = fn
    for path, names in by_file.items():
        replace_values(path, names)
    write_characters()
    # Fallback lookups by the old default id go to the default hero.
    for p in [ROOT / 'main.py', ROOT / 'config.py', *(ROOT / 'services').glob('*.py')]:
        s = p.read_text(encoding='utf-8')
        n = s.replace("'anna_01'", r(DEFAULT_HERO)).replace('"anna_01"', '"%s"' % DEFAULT_HERO)
        if p.name == 'config.py':
            n = n.replace('CHARACTER_DIR / "anna.json"', f'CHARACTER_DIR / "{DEFAULT_HERO}.json"')
        if n != s:
            p.write_text(n, encoding='utf-8')
            print('default id ->', p.relative_to(ROOT))


if __name__ == '__main__':
    main()
