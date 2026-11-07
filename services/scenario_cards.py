"""V3.75.0: scenario cards — the Come Closer push the owner showed.

Owner (2026-10-23): «смотри, какая в меню нашего конкурента. у него так это
все делают». Come Closer pushes a card every day or two: a 3-second looping
cover of the girl, a one-line role-play setup («лучшая подруга твоей сестры
столкнулась с тобой в дверях»), her quote, a promo code and ONE button that
drops the user straight into that scene.

Ours:

* ``SCENARIOS`` — like Come Closer, every card brings a NEW girl (owner's
  pick, V3.76.0): Лера, Диана, Ника, Лика, Стелла, Аля are full built-in
  heroines (persona, references, voice, pools) whose storefront tile only
  appears for a user once her card reached him (``unlocked``);
* the cover is rendered ONCE per scenario by the admin's «/scenes»: a
  Seedream photo by default (~$0.035; owner: «можем это и фоткой»), or a
  Seedance 2.5 Spicy 4 s silent loop from it (~$0.90) for the best scenes;
  kept as Telegram's ``file_id``, so sending it to everyone costs nothing;
* one card a day at most, in the user's evening, never the same scene twice;
* the button opens the Mini App chat with ``?scene=<key>``: the app starts
  the scene (switches to her, the scene direction rides along with every
  reply for ``ACTIVE_HOURS``) and sends his entrance line, so she answers
  in the scene right away;
* instead of a promo code: +SCENARIO_TAP_PEACHES 🍑 for walking in within a
  day of the card (once per scene).

Safety line: covers come only from our own built-in adult characters' face
references (never a user upload, never a constructor persona), they stay
dressed (lingerie at most — the card lands in the Telegram chat), and every
scene says outright that both are adults.

State lives in DialogStore (no schema change): per user ``{'sent': {key:
iso}, 'last': iso, 'active': {character_id: {'key', 'until'}}}``; covers
under the fixed key 0 of their own store.
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from services import dialog_store

logger = logging.getLogger(__name__)

_state = dialog_store.DialogStore('scenario_cards')
_covers = dialog_store.DialogStore('scenario_covers')
_COVERS_KEY = 0

# The scene direction rides along with her replies this long after the tap.
ACTIVE_HOURS = 24
# The tap bonus is paid when he walks in within this long after the card.
BONUS_WINDOW_HOURS = 24


@dataclass(frozen=True)
class Scenario:
    key: str
    character_id: str
    # the card: setup line (what is going on), her action, her quote, the button
    setup: str
    action: str
    quote: str
    button: str
    # his entrance line, sent for him when he taps (the app shows it as his)
    enter: str
    # who she is and who he is in the scene, for the system direction
    her_role: str
    his_role: str
    place: str
    # cover: the still (outfit, place, framing) and the 4 s motion
    still: str
    motion: str


# Male-heroes bot: scenario cards come back with the heroes' own scenes (later stage).
SCENARIOS: tuple[Scenario, ...] = ()

_BY_KEY = {s.key: s for s in SCENARIOS}
# V3.76.0: the girls who arrive through a card stay out of the storefront
# until that card reached him (owner chose «новые девушки, как у него»).
SCENARIO_GIRLS = frozenset(s.character_id for s in SCENARIOS)


def get(key: str) -> Scenario | None:
    return _BY_KEY.get((key or '').strip())


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse(iso: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(iso) if iso else None
    except (TypeError, ValueError):
        return None


def _user(telegram_id: int) -> dict:
    try:
        raw = _state.get(int(telegram_id)) or {}
        data = dict(raw)
    except Exception:
        data = {}
    data.setdefault('sent', {})
    data.setdefault('active', {})
    return {'sent': dict(data['sent']), 'active': dict(data['active']), 'last': data.get('last')}


def _save(telegram_id: int, data: dict) -> None:
    try:
        _state[int(telegram_id)] = data
    except Exception:
        logger.exception('scenario state save failed user=%s', telegram_id)


# ── covers ──────────────────────────────────────────────────────────────────

def covers() -> dict[str, dict]:
    """key -> {'file_id', 'kind'} (kind: 'animation' | 'video' | 'photo')."""
    try:
        return {str(k): dict(v) for k, v in dict(_covers.get(_COVERS_KEY) or {}).items()}
    except Exception:
        return {}


def cover(key: str) -> dict | None:
    return covers().get(key)


def set_cover(key: str, file_id: str, kind: str = 'animation') -> None:
    data = covers()
    data[key] = {'file_id': file_id, 'kind': kind}
    _covers[_COVERS_KEY] = data


def clear_cover(key: str) -> bool:
    data = covers()
    if data.pop(key, None) is None:
        return False
    _covers[_COVERS_KEY] = data
    return True


def still_prompt(s: Scenario) -> str:
    """The cover's first frame (Seedream edit with her face + look refs)."""
    from services.private_photo_service import _build_visual_identity_lock
    identity = _build_visual_identity_lock(s.character_id)
    prompt = (
        f'{identity}\n'
        f'Photorealistic vertical smartphone photo of the same adult woman from the reference images, {s.still}. '
        'Square-friendly composition: her face and upper body centred in the frame, face fully visible, '
        'sharp focus on the eyes, cinematic natural light, natural skin texture. '
        'She is fully dressed in the described outfit, no nudity, one person only, no text, no watermark.'
    )
    from services.photo_service import apply_art_style
    return apply_art_style(prompt, s.character_id)


def motion_prompt(s: Scenario) -> str:
    from services.photo_service import apply_art_style
    return apply_art_style(
        f'{s.motion} Subtle natural movement, gentle breathing, hair moves slightly, camera almost still. '
        'Adult woman, exactly the same face, hair, outfit and body as in the photo, she stays dressed, '
        'one person only, photorealistic, sharp focus, no text.', s.character_id
    )


# ── the card ────────────────────────────────────────────────────────────────

def caption(s: Scenario, bonus: int) -> str:
    """Setup, her action in italics, her quote as a quote block, the bonus."""
    import html
    lines = [
        f'<b>{html.escape(s.setup)}</b>',
        '',
        f'<i>{html.escape(s.action)}</i>',
        f'<blockquote>{html.escape(s.quote)}</blockquote>',
    ]
    if bonus > 0:
        lines += ['', f'🎁 зайдёшь в сцену сегодня — +{bonus}🍑 на счёт']
    return '\n'.join(lines)


def opening_line(s: Scenario) -> str:
    """What lands in her dialog when the card is sent (the app shows it)."""
    return f'*{s.action}*\n{s.quote}'


def unlocked(telegram_id: int, character_id: str) -> bool:
    """A card girl shows in his storefront once her card came (or he
    walked into her scene); every other girl is always there."""
    if character_id not in SCENARIO_GIRLS:
        return True
    data = _user(telegram_id)
    if character_id in data['active']:
        return True
    return any(s.character_id == character_id and s.key in data['sent'] for s in SCENARIOS)


def eligible(available_characters: set[str], *, with_cover: bool = True) -> list[Scenario]:
    have = covers() if with_cover else None
    return [s for s in SCENARIOS
            if s.character_id in available_characters and (have is None or s.key in have)]


def pick_next(telegram_id: int, available_characters: set[str], *, current: str = '') -> Scenario | None:
    """An unsent covered scene; his current girl's scene goes first."""
    sent = _user(telegram_id)['sent']
    fresh = [s for s in eligible(available_characters) if s.key not in sent]
    if not fresh:
        return None
    own = [s for s in fresh if s.character_id == current]
    return own[0] if own else random.choice(fresh)


def last_sent_at(telegram_id: int) -> datetime | None:
    return _parse(_user(telegram_id).get('last'))


def mark_sent(telegram_id: int, key: str) -> None:
    data = _user(telegram_id)
    now = _now().isoformat(timespec='seconds')
    data['sent'][key] = now
    data['last'] = now
    _save(telegram_id, data)


def start(telegram_id: int, key: str) -> dict:
    """He walked into the scene: it stays on for ACTIVE_HOURS with her.
    Returns ``{'sent': bool, 'bonus_due': bool}`` (bonus: the card came
    within BONUS_WINDOW_HOURS)."""
    s = get(key)
    if not s:
        return {'sent': False, 'bonus_due': False}
    data = _user(telegram_id)
    until = _now() + timedelta(hours=ACTIVE_HOURS)
    data['active'][s.character_id] = {'key': s.key, 'until': until.isoformat(timespec='seconds')}
    _save(telegram_id, data)
    sent = _parse(data['sent'].get(s.key))
    return {'sent': bool(sent),
            'bonus_due': bool(sent and _now() - sent <= timedelta(hours=BONUS_WINDOW_HOURS))}


def stop(telegram_id: int, character_id: str) -> bool:
    data = _user(telegram_id)
    if data['active'].pop(character_id, None) is None:
        return False
    _save(telegram_id, data)
    return True


def active(telegram_id: int, character_id: str) -> Scenario | None:
    item = _user(telegram_id)['active'].get(character_id) or {}
    until = _parse(item.get('until'))
    if not until or until < _now():
        return None
    return get(item.get('key', ''))


def direction(s: Scenario, name: str = '') -> str:
    """The system note that keeps her in the scene."""
    who = name or 'он'
    return (
        f'РОЛЕВАЯ СЦЕНА (она сам выбрала его в карточке). Ты, {who}, сейчас играешь роль: {s.her_role}. '
        f'Она в сцене: {s.his_role}. Место и время: {s.place}. Завязка: {s.setup}. '
        f'Ты начала сцену словами: «{s.quote}». '
        'Оба взрослые, всё по обоюдному желанию. Живи ролью: пиши от первого лица, короткие действия '
        'в *звёздочках*, реплики живые и разговорные; сам двигай сцену вперёд, дразни, '
        'создавай напряжение и заканчивай так, чтобы ей хотелось ответить. Не выходи из роли, '
        'не говори, что это игра или сценарий, не пересказывай завязку. Откровенность — '
        'по обычным правилам этого чата. Если она явно хочет закончить сцену — мягко выйди из роли.'
    )


def direction_for(telegram_id: int, character_id: str, name: str = '') -> str:
    try:
        s = active(int(telegram_id), character_id)
    except Exception:
        return ''
    return direction(s, name) if s else ''


# ── cover rendering (admin «/scenes», once per scene) ───────────────────────

class CoverError(RuntimeError):
    pass


async def render_still(s: Scenario) -> bytes:
    """Seedream edit on SpicyAPI from her face + look references (~$0.035)."""
    from config import PUBLIC_BASE_URL, SPICYAPI_IMAGE_MODEL
    from services.private_photo_service import _spicyapi_render, spicyapi_last_error
    refs = [f'{PUBLIC_BASE_URL}/webapp/photo/{s.character_id}?i=0',
            f'{PUBLIC_BASE_URL}/webapp/photo/{s.character_id}?i=1']
    still = await _spicyapi_render(SPICYAPI_IMAGE_MODEL, still_prompt(s), refs,
                                   scene='scenario_cover', breaker=False)
    if not still:
        raise CoverError(f'still: {spicyapi_last_error() or "empty"}')
    return still


async def render_cover(s: Scenario, still: bytes | None = None) -> tuple[bytes, bytes]:
    """(silent square mp4, the still it started from). Raises CoverError."""
    from config import (SCENARIO_COVER_MODEL, SCENARIO_COVER_SECONDS, SCENARIO_COVER_COST_USD,
                        SPICYAPI_HOT_CIRCLE_RESOLUTION)
    from services import spend_service, spicy_jobs
    from services.spicy_video_service import square_frame
    if still is None:
        still = await render_still(s)
    frame = square_frame(still)
    ok = False
    billed = False
    try:
        uri = await spicy_jobs.upload(frame, 'image/jpeg')
        block = {
            'image_url': uri,
            'prompt': motion_prompt(s),
            'resolution': SPICYAPI_HOT_CIRCLE_RESOLUTION,
            'duration_seconds': SCENARIO_COVER_SECONDS,
            'generate_audio': False,
        }
        billed = True
        video, _, _ = await spicy_jobs.run(SCENARIO_COVER_MODEL, block, timeout=900)
        ok = True
    except spicy_jobs.SpicyJobError as exc:
        # refused or failed jobs are not billed; a timeout still is
        billed = billed and str(exc).startswith('timeout')
        raise CoverError(f'video: {exc}') from exc
    finally:
        if billed:
            spend_service.record_image_spend('spicyapi_scenario_cover', 'scenario_cover',
                                             SCENARIO_COVER_COST_USD, billed=True, success=ok)
    try:
        from services.mp4_faststart import faststart_bytes
        video = faststart_bytes(video) or video
    except Exception:
        pass
    return video, still
