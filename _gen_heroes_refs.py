"""Stage 4: canonical face and look references for the six heroes.

Faces are NEW: text only, no image is sent to the model, so nobody real gets
cloned. The look is an edit from that new face, so the same man stays in every
shot. Runs on the owner's PC (the cloud container cannot reach SpicyAPI):

    python _gen_heroes_refs.py <key-file>                 # 2 variants per hero
    python _gen_heroes_refs.py <key-file> pick mark 2     # v2 -> canonical refs

Variants go to data/references/_heroes_variants/ so they can be reviewed; that
folder is deleted before the stage-4 merge.
"""
import json
import pathlib
import shutil
import sys
import time
import urllib.request
import uuid
import re

ROOT = pathlib.Path(__file__).resolve().parent
raw = pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')
m = re.search(r'SPICYAPI_KEY\s*=\s*["\']?([^\s"\']+)', raw)
KEY = m.group(1) if m else raw.strip()
BASE = 'https://api.spicyapi.ai/api/v1'
T2I = 'bytedance/seedream-5.0-pro/text-to-image'
EDIT = 'bytedance/seedream-5.0-pro/edit'
VAR = ROOT / 'data' / 'references' / '_heroes_variants'

QUALITY = (' High-end smartphone photo, attractive and well groomed, smooth clear skin, sharp focus on the eyes, '
           'original fictional man with a unique face, not a celebrity, not an actor, '
           'anatomically correct: exactly two arms and two hands, five fingers on each hand. '
           'Adult man, one person only, fully dressed, no nudity, no text, no watermark, no logo.')
SOFT = (' Warm romantic mood: a gentle confident closed-lip smile, no wide grin, warm eyes looking at the viewer, '
        'the kind of handsome man a woman wants to text at night.')

HEROES = {
    'mark': dict(
        face='handsome adult man, 29 years old, an architect, short neat dark brown hair, light stubble, warm brown '
             'eyes, strong jaw, kind face',
        body='a tall lean athletic build with broad shoulders and a flat toned stomach',
        shots=[('Portrait photo, navy fitted crew-neck sweater, sitting at a bright architecture studio desk with '
                'sketches and a model of a building behind him, soft daylight',
                'Full look, knees up: navy fitted crew-neck sweater, dark chinos, standing on a city rooftop at '
                'golden hour with the skyline behind him, hands in pockets'),
               ('Selfie portrait, white shirt with the top button open, evening city lights behind him on a balcony',
                'Full look, knees up: white shirt with rolled sleeves, dark trousers, leaning on a balcony railing '
                'with evening city lights behind him')]),
    'maksim': dict(
        face='handsome adult man, 27 years old, a chef, messy light brown hair, kind grey-green eyes, dimples, light '
             'stubble, warm open face',
        body='a strong athletic build with broad shoulders and muscular forearms',
        shots=[('Portrait photo, white chef jacket with sleeves rolled up, warm restaurant kitchen behind him, soft '
                'warm light',
                'Full look, knees up: white chef jacket with rolled sleeves and a dark apron, standing in a warm '
                'restaurant kitchen, tasting from a wooden spoon'),
               ('Selfie portrait, grey t-shirt, cozy home kitchen with fresh herbs and evening light',
                'Full look, knees up: fitted grey t-shirt and jeans, cooking in a cozy home kitchen, looking at '
                'the viewer')]),
    'daniil': dict(
        face='handsome adult man, 32 years old, a surgeon, short dark hair with a few early grey strands at the '
             'temples, calm grey eyes, clean shaven, defined cheekbones, calm serious face',
        body='a tall lean fit build with broad shoulders',
        shots=[('Portrait photo, dark blue surgical scrubs, bright hospital corridor behind him, soft light',
                'Full look, knees up: dark blue scrubs with a stethoscope around his neck, standing in a bright '
                'hospital corridor holding a coffee'),
               ('Portrait photo, black turtleneck, quiet evening apartment with warm lamp light and books',
                'Full look, knees up: black turtleneck and grey trousers, standing by a big window in a quiet '
                'evening apartment')]),
    'timur': dict(
        face='handsome adult man, 34 years old, a business owner, short black hair, dark intense eyes, neat short '
             'beard, sharp masculine features',
        body='a tall powerful muscular build with broad shoulders',
        shots=[('Portrait photo, black shirt with the top buttons open, expensive watch, dark leather car interior '
                'at night with city lights',
                'Full look, knees up: black shirt and black trousers, expensive watch, standing next to a black car '
                'on a night street with city lights'),
               ('Portrait photo, dark charcoal suit with no tie, a high floor office with a night city view',
                'Full look, knees up: dark charcoal suit with no tie, standing by the window of a high floor '
                'office with a night city view')]),
    'leo': dict(
        face='handsome adult man, 26 years old, a photographer, messy dark wavy hair, green eyes, light stubble, a '
             'small silver earring, a cheeky look',
        body='a lean muscular build with tattoos on both forearms',
        shots=[('Selfie portrait, black t-shirt, a vintage film camera on a strap, a graffiti street at sunset',
                'Full look, knees up: black t-shirt, worn black leather jacket open, dark jeans, tattooed forearms, '
                'a film camera in his hand, on a graffiti street at sunset'),
               ('Portrait photo, white t-shirt, his photo studio with prints on the wall and soft window light',
                'Full look, knees up: white t-shirt, dark jeans, tattooed forearms, leaning on a wall of prints '
                'in his photo studio')]),
    'minjun': dict(
        face='handsome adult Korean man, 24 years old, soft black hair with a fringe, gentle dark eyes, clear skin, '
             'soft delicate features, warm shy look, K-drama style',
        body='a slim fit build',
        shots=[('Portrait photo, cream oversized knit sweater, a cozy Seoul cafe with warm light behind him',
                'Full look, knees up: cream oversized knit sweater, light wide trousers, standing on an evening '
                'Seoul street with neon signs'),
               ('Selfie portrait, black hoodie, a Han river bridge with evening lights behind him',
                'Full look, knees up: long camel coat over a black hoodie, standing by the Han river at night '
                'with city lights')]),
}
KEEP = ('The same man as in the reference image: keep his exact face, eyes, nose, lips, hair, facial hair and skin '
        'tone. His build: {body}. ')


def call(method, path, body=None):
    req = urllib.request.Request(
        BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json',
                 'Idempotency-Key': str(uuid.uuid4())})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    if d.get('code') not in (200, 201, 202):
        raise RuntimeError(d)
    return d.get('data', {})


def upload(data: bytes, ctype: str) -> str:
    slot = call('POST', '/common/upload-url', {'contentType': ctype, 'bytes': len(data)})
    put = urllib.request.Request(slot['uploadUrl'], data=data, method='PUT', headers={'Content-Type': ctype})
    urllib.request.urlopen(put, timeout=60).read()
    return call('POST', f"/files/{slot['fileId']}/commit", {})['uri']


def render(model: str, prompt: str, refs=None) -> bytes:
    inp = {'prompt': prompt, 'aspect_ratio': '3:4', 'resolution': '1k', 'output_format': 'png',
           'enable_thinking': True}
    if refs:
        inp['image_urls'] = refs
    tid = call('POST', '/jobs/createTask', {'model': model, 'input': inp})['taskId']
    for _ in range(100):
        time.sleep(3)
        info = call('GET', f'/jobs/recordInfo?taskId={tid}')
        if info.get('state') == 'succeeded':
            url = next(a['url'] for a in info['output']['assets'] if a.get('url'))
            return urllib.request.urlopen(url, timeout=60).read()
        if info.get('state') in ('failed', 'expired', 'canceled'):
            raise RuntimeError(f"{info.get('errorCode')} {info.get('errorMessage')}")
    raise RuntimeError('timeout')


def make_variants() -> None:
    VAR.mkdir(parents=True, exist_ok=True)
    for name, h in HEROES.items():
        for i, (face_scene, look_scene) in enumerate(h['shots'], 1):
            face = VAR / f'{name}_v{i}_face.png'
            look = VAR / f'{name}_v{i}_look.png'
            try:
                if not face.exists():  # text only: nobody real gets cloned
                    face.write_bytes(render(T2I, f"{face_scene}. A {h['face']}." + SOFT + QUALITY))
                    print('ok', face.name, flush=True)
                if not look.exists():
                    uri = upload(face.read_bytes(), 'image/png')
                    look.write_bytes(render(EDIT, KEEP.format(body=h['body']) + look_scene + '.' + SOFT + QUALITY,
                                            [uri]))
                    print('ok', look.name, flush=True)
            except Exception as e:  # keep going with the other heroes
                print('error', name, i, e, flush=True)


def pick(name: str, n: int) -> None:
    out = ROOT / 'data' / 'references' / name
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(VAR / f'{name}_v{n}_face.png', out / f'00_{name}_canonical_face.png')
    shutil.copyfile(VAR / f'{name}_v{n}_look.png', out / f'01_{name}_canonical_look.png')
    print('picked', name, n)


if __name__ == '__main__':
    args = sys.argv[2:]
    if args[:1] == ['pick']:
        pick(args[1], int(args[2]))
    else:
        make_variants()
