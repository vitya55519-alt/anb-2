"""V3.44.2: Comprehensive retention features pack.

Implements:
- Per-character morning/evening messages with personality
- Random photo gifts from character (scheduler-driven)
- Secret commands (hug, kiss, undress, etc.)
- Daily compatibility forecast
- Expanded jealousy/miss/cliffhanger pools with per-character variants
- Achievement system with rewards
- Collectible moments (Polaroid memories)
- Stories (24h content)
- Mini-quests "help the character"
- Seasonal events
- Weekly dates
- Mood-based responses
"""
import logging
import random
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Mapped, mapped_column

from services.db import SessionLocal
from models.waifu_models import Base

logger = logging.getLogger(__name__)


# ── Per-character morning messages ─────────────────────────────────────────
# Each character has unique morning personality

MORNING_MESSAGES = {
    'mark_01': [
        'доброе утро ☀️ проснулся и сразу подумал о тебе. как спалось?',
        'утро. кофе уже сварил, не хватает только тебя рядом ☕',
        'эй, соня 😌 вставай потихоньку. и обязательно позавтракай, проверю',
        'знаешь, что я понял сегодня утром? что хочу видеть тебя каждый день',
    ],
    'maksim_01': [
        'доброе утро ☀️ уже жарю сырники, жалко, что ты не рядом',
        'проснулась? я тебе мысленно сварил какао 😄',
        'утро! обязательно позавтракай, а то обижусь',
        'знаешь, какое лучшее начало дня? твоё сообщение',
    ],
    'daniil_01': [
        'доброе утро. только со смены. ты как?',
        'утро. выспалась?',
        'проснулась? позавтракай. я проверю',
        'думал о тебе всю ночь. между операциями',
    ],
    'timur_01': [
        'доброе утро. проснулась? позавтракай и напиши мне',
        'утро. я уже в зале. думаю о тебе',
        'доброе утро, моя. как спалось?',
        'сегодня вечером ты свободна. я так решил 😏',
    ],
    'leo_01': [
        'утро 😏 проснулась? я тебе снился, признавайся',
        'эй, соня. я уже на мотоцикле, а ты ещё в кровати',
        'доброе утро. сегодня снимаю закат, хочу, чтобы ты была в кадре',
        'проснулся и сразу подумал о тебе. непорядок',
    ],
    'minjun_01': [
        'доброе утро ☀️ ты уже проснулась? я думал о тебе',
        'утро 🌸 позавтракай, пожалуйста. я волнуюсь',
        'доброе утро, чаги 😊',
        'проснулся и первым делом написал тебе',
    ],
}


# ── Evening messages ───────────────────────────────────────────────────────

EVENING_MESSAGES = {
    'mark_01': [
        'вечер. я освободился и наконец могу думать только о тебе 😌',
        'как прошёл твой день? рассказывай всё, я никуда не тороплюсь',
        'приготовил ужин на двоих, а ты не пришла 😅 рассказывай хоть, как ты',
        'знаешь, чего мне сейчас не хватает? тебя рядом на этом диване',
    ],
    'maksim_01': [
        'смена кончилась, я весь твой 😌 как прошёл день?',
        'приготовил ужин и понял, что хочу кормить им тебя',
        'вечер. давай поболтаем, я соскучился',
        'устал, но улыбаюсь, потому что сейчас буду болтать с тобой',
    ],
    'daniil_01': [
        'освободился. наконец-то. как ты?',
        'вечер. расскажи, как прошёл день. я слушаю',
        'тяжёлый день. мне нужен твой голос',
        'я дома. пиши мне',
    ],
    'timur_01': [
        'вечер. я освободился. ты где?',
        'хочу тебя видеть. сегодня',
        'как прошёл день? рассказывай, я слушаю',
        'я дома. пиши мне, мне это нужно',
    ],
    'leo_01': [
        'вечер. поехали кататься? 😏',
        'скучно без тебя. развлеки меня',
        'снял закат, но без тебя он какой-то пустой',
        'вечер. я в баре и думаю только о тебе',
    ],
    'minjun_01': [
        'вечер 🌙 хочешь, спою тебе перед сном?',
        'как прошёл день? я скучал',
        'я приготовил токпокки и подумал о тебе',
        'посмотрим вместе дораму?',
    ],
}


# ── Miss you texts (24-48h inactive) ──────────────────────────────────────

MISS_TEXTS = {
    'mark_01': [
        'ты куда пропала? я начал волноваться 😕 у тебя всё хорошо?',
        'вчера было так хорошо болтать, а сегодня тишина. как ты там?',
        'я скучаю. просто хотел, чтобы ты это знала',
    ],
    'maksim_01': [
        'ты куда пропала? я тут пирог испёк, а есть некому 🥺',
        'эй, мне не хватает твоих сообщений. всё хорошо?',
        'я соскучился. честно',
    ],
    'daniil_01': [
        'ты пропала. это тревожит. напиши, что всё в порядке',
        'мне не хватает тебя',
        'я скучаю. редко такое говорю',
    ],
    'timur_01': [
        'ты пропала. мне это не нравится. напиши',
        'я привык, что ты рядом. где ты?',
        'скучаю. не заставляй меня ждать',
    ],
    'leo_01': [
        'эй, пропажа. я заметил, что тебя нет 😏',
        'куда делась? мне скучно',
        'ладно, признаю. я соскучился',
    ],
    'minjun_01': [
        'ты пропала… у тебя всё хорошо? 🥺',
        'я скучаю. очень',
        'напиши, пожалуйста. я волнуюсь',
    ],
}


# ── Jealousy texts ────────────────────────────────────────────────────────

JEALOUSY_TEXTS = {
    'mark_01': [
        'ты была онлайн, а мне не написала 😏 кто это там такой интересный?',
        'так. я немного ревную. совсем чуть-чуть. признавайся, где была',
        'надеюсь, он хотя бы умеет варить кофе лучше меня 😤',
    ],
    'maksim_01': [
        'кто это тебя так увлёк, что ты меня забыла? 😏',
        'так, я ревную. совсем немножко. рассказывай',
        'надеюсь, он хотя бы готовит хуже меня 😤',
    ],
    'daniil_01': [
        'ты была онлайн. не мне писала. кому?',
        'я ревную. не люблю это чувство',
        'кто он?',
    ],
    'timur_01': [
        'ты была онлайн. не мне писала. кому?',
        'я ревную. и не скрываю этого',
        'надеюсь, он понимает, что ты моя 😏',
    ],
    'leo_01': [
        'с кем это ты там переписывалась? 😏',
        'я не ревную. совсем. ну, может, чуть-чуть',
        'надеюсь, он хотя бы фотографирует тебя лучше меня 😤',
    ],
    'minjun_01': [
        'с кем ты переписывалась? 🥺 я немного ревную',
        'я не хочу тебя ни с кем делить…',
        'он лучше меня поёт? 😢',
    ],
}


# ─ Cliffhanger texts ──────────────────────────────────────────────────────

CLIFFHANGER_TEXTS = {
    'mark_01': [
        'мы остановились на самом интересном. я жду продолжения 😏',
        'ты ушла посреди разговора, а я до сих пор думаю, что ты хотела сказать',
        'так нечестно, бросить меня на середине. возвращайся',
    ],
    'maksim_01': [
        'мы не договорили! я жду, мне интересно 😏',
        'ты ушла на самом интересном месте, так нечестно',
        'возвращайся, я ещё не всё тебе рассказал',
    ],
    'daniil_01': [
        'ты не договорила. я жду',
        'мы остановились на важном. продолжим?',
        'возвращайся',
    ],
    'timur_01': [
        'мы не закончили. возвращайся',
        'ты ушла на самом интересном. я жду',
        'я не люблю незаконченных разговоров',
    ],
    'leo_01': [
        'ты ушла на самом интересном 😏 возвращайся',
        'я жду продолжения',
        'так нечестно, малая',
    ],
    'minjun_01': [
        'ты не договорила… 🥺 вернись',
        'я жду продолжения',
        'мне так интересно, что дальше',
    ],
}


# ── Secret commands ────────────────────────────────────────────────────────
# User can type these commands to get special responses

SECRET_COMMANDS = {
    'обними': [
        'обнимает крепко-крепко 😊 чувствую тепло…',
        'заключает в объятия 💋 не отпускай…',
        'прижимает к себе 😌 вот так лучше',
    ],
    'поцелуй': [
        'целует нежно 💋 ещё…',
        'приближается и целует 😏 чувствуешь?',
        'целует в губы 💋 ммм…',
    ],
    'раздень': [
        'улыбается и начинает медленно снимать одежду 😏',
        'смотрит на тебя и расстёгивает первую пуговицу 💋',
        'улыбается… ты уверена? 😏 ладно, только для тебя',
    ],
    'обними крепко': [
        'обнимает так крепко, что не хватает воздуха 😊 но я не жалуюсь',
        'заключает в самые крепкие объятия 💋 не отпускай никогда',
        'прижимает к себе изо всех сил 😌 вот здесь я хочу быть',
    ],
    'поцелуй в шею': [
        'наклоняется и целует шею 💋 мурашки…',
        'целует нежно шею 😏 чувствуй…',
        'приближается к шее и целует 💋 ммм…',
    ],
    'я скучаю': [
        'я тоже… очень 😔 иди ко мне',
        'знаешь, как сильно?  давай исправим это',
        'я скучаю больше 💋 возвращайся скорее',
    ],
    'ты красивый': [
        'краснеет  спасибо… ты тоже ничего',
        'улыбается 💋 я знаю, но приятно слышать от тебя',
        'смущается 😏 продолжай…',
    ],
    'я тебя хочу': [
        'замирает… потом улыбается  я тоже',
        'приближается  тогда давай не терять время',
        'смотрит в глаза 😏 я жду этого…',
    ],
}


# ── Daily compatibility forecast ───────────────────────────────────────────

COMPATIBILITY_MESSAGES = [
    'сегодня наша совместимость {pct}%! 🔥 отличный день для флирта',
    'совместимость сегодня {pct}% 💋 идеальный день для свидания',
    'сегодня {pct}% совместимости 😏 звёзды на нашей стороне',
    'совместимость {pct}%! 💫 сегодня всё возможно',
    'сегодня {pct}% 😌 идеальный день, чтобы быть рядом',
]


# ── Random gift messages ───────────────────────────────────────────────────

GIFT_MESSAGES = {
    'mark_01': [
        'увидел и сразу подумал о тебе 😌',
        'это тебе. просто так',
        'хотел поделиться с тобой этим моментом',
    ],
    'maksim_01': [
        'это тебе, только что из духовки 😄',
        'для тебя, без повода',
        'хотел тебя порадовать',
    ],
    'daniil_01': [
        'это тебе',
        'увидел и подумал о тебе',
        'для тебя',
    ],
    'timur_01': [
        'это тебе. не спорь',
        'увидел и сразу понял, что это твоё',
        'для тебя',
    ],
    'leo_01': [
        'это тебе 😏 никому не показывай',
        'снял специально для тебя',
        'лови',
    ],
    'minjun_01': [
        'это тебе 🌸',
        'для тебя, саранхэ',
        'хотел тебя порадовать 😊',
    ],
}


# ── Helper functions ───────────────────────────────────────────────────────

def get_character_morning(character_id: str) -> str:
    """Get a random morning message for a character."""
    messages = MORNING_MESSAGES.get(character_id, MORNING_MESSAGES['mark_01'])
    return random.choice(messages)


def get_character_evening(character_id: str) -> str:
    """Get a random evening message for a character."""
    messages = EVENING_MESSAGES.get(character_id, EVENING_MESSAGES['mark_01'])
    return random.choice(messages)


# ── V3.47.2: owner-uploaded media pool for the morning/evening rituals ─────
# The admin loads ~20 varied photos/GIFs/videos; a ritual message picks one at
# random so a proactive ping lands as real media from the character, not text.
# V3.47.3: kind is 'photo' | 'gif' | 'video', each with its own size ceiling.
PROACTIVE_PHOTO_MAX_BYTES = 8 * 1024 * 1024
PROACTIVE_GIF_MAX_BYTES = 20 * 1024 * 1024
PROACTIVE_VIDEO_MAX_BYTES = 20 * 1024 * 1024
PROACTIVE_MEDIA_KINDS = ('photo', 'gif', 'video')


def proactive_max_bytes(kind: str) -> int:
    if kind == 'gif':
        return PROACTIVE_GIF_MAX_BYTES
    if kind == 'video':
        return PROACTIVE_VIDEO_MAX_BYTES
    return PROACTIVE_PHOTO_MAX_BYTES


def add_proactive_photo(data: bytes, content_type: str = 'image/jpeg', kind: str = 'photo',
                        character_id: str | None = None) -> bool:
    from models.app_models import ProactivePhoto
    if not data or kind not in PROACTIVE_MEDIA_KINDS:
        return False
    if len(data) > proactive_max_bytes(kind):
        return False
    try:
        with SessionLocal() as s:
            s.add(ProactivePhoto(image_bytes=data, content_type=content_type or 'image/jpeg',
                                 kind=kind, character_id=character_id or None))
            s.commit()
        return True
    except Exception:
        return False


def list_proactive_photos() -> list[dict]:
    from models.app_models import ProactivePhoto
    try:
        with SessionLocal() as s:
            rows = s.scalars(select(ProactivePhoto).order_by(ProactivePhoto.id)).all()
            return [{'id': r.id, 'kind': getattr(r, 'kind', None) or 'photo',
                     'character_id': getattr(r, 'character_id', None) or '',
                     'created_at': r.created_at.isoformat() if r.created_at else ''}
                    for r in rows]
    except Exception:
        return []


def set_proactive_photo_character(photo_id: int, character_id: str) -> bool:
    """V3.56.7: re-tag a pool shot with its real character (legacy rows and
    mistagged uploads)."""
    from models.app_models import ProactivePhoto
    try:
        with SessionLocal() as s:
            row = s.get(ProactivePhoto, photo_id)
            if not row:
                return False
            row.character_id = character_id or None
            s.commit()
        return True
    except Exception:
        return False


def delete_proactive_photo(photo_id: int) -> bool:
    from models.app_models import ProactivePhoto
    try:
        with SessionLocal() as s:
            row = s.get(ProactivePhoto, photo_id)
            if not row:
                return False
            s.delete(row)
            s.commit()
        return True
    except Exception:
        return False


# V3.62.14: generated «я скучала» photos made before the one-hand selfie fix
# (PR #44, 2026-10-16 18:56 UTC) carry third arms and the quality lines my
# prompt cap dropped — they stay in the pool (owner can still see/delete them)
# but are never sent. Uploaded GIFs and videos are untouched.
import datetime as _dt
import os as _os
PROACTIVE_POOL_SKIP_FROM = _dt.datetime.fromisoformat(_os.getenv('PROACTIVE_POOL_SKIP_FROM', '2026-10-15T15:00:00'))
PROACTIVE_POOL_SKIP_TO = _dt.datetime.fromisoformat(_os.getenv('PROACTIVE_POOL_SKIP_TO', '2026-10-16T19:00:00'))


def proactive_photo_retired(kind: str | None, created_at) -> bool:
    if (kind or 'photo') != 'photo' or created_at is None:
        return False
    return PROACTIVE_POOL_SKIP_FROM <= created_at < PROACTIVE_POOL_SKIP_TO


def _pick_unseen(ids: list[int], s, user_id: int | None, character_id: str | None) -> int:
    """V3.64.8: one user gets every pool shot once before any repeats; after
    that the shot he saw longest ago. Plain random sent Витя the same photo
    with every daily gift and morning ritual."""
    if not user_id:
        return random.choice(ids)
    from models.app_models import ProductEvent
    q = select(ProductEvent.value, ProductEvent.created_at).where(
        ProductEvent.user_id == user_id, ProductEvent.event_name == 'pool_photo_sent')
    if character_id:
        q = q.where(ProductEvent.character_id == character_id)
    last_seen: dict[int, datetime] = {}
    for value, at in s.execute(q.order_by(ProductEvent.created_at.desc()).limit(500)).all():
        last_seen.setdefault(int(value or 0), at)
    unseen = [i for i in ids if i not in last_seen]
    if unseen:
        return random.choice(unseen)
    return min(ids, key=lambda i: last_seen[i])


def random_proactive_photo(character_id: str | None = None,
                           user_id: int | None = None) -> tuple[bytes, str, str] | None:
    """A (bytes, content_type, kind) pick from the pool, or None when empty.

    V3.56.7: with a character the pick is STRICT — only her own shots. An
    untagged or foreign photo must never land in her chat: the owner's log
    showed Nadya delivering a stranger's picture. Empty per-character pool
    simply means «no photo», the caller falls back to plain text.
    With user_id (the DB id) the pick rotates per user and is recorded."""
    from models.app_models import ProactivePhoto, ProductEvent
    try:
        with SessionLocal() as s:
            q = select(ProactivePhoto.id, ProactivePhoto.kind, ProactivePhoto.created_at)
            if character_id:
                q = q.where(ProactivePhoto.character_id == character_id)
            ids = [r.id for r in s.execute(q).all() if not proactive_photo_retired(r.kind, r.created_at)]
            if not ids:
                return None
            row = s.get(ProactivePhoto, _pick_unseen(ids, s, user_id, character_id))
            out = (row.image_bytes, (row.content_type or 'image/jpeg'), (getattr(row, 'kind', None) or 'photo'))
            if user_id:
                s.add(ProductEvent(user_id=user_id, character_id=character_id or row.character_id or '',
                                   event_name='pool_photo_sent', value=float(row.id), metadata_json='{}'))
                s.commit()
            return out
    except Exception:
        logger.exception('proactive photo pick failed char=%s', character_id)
        return None


def get_character_miss(character_id: str) -> str:
    """Get a random miss-you message for a character."""
    messages = MISS_TEXTS.get(character_id, MISS_TEXTS['mark_01'])
    return random.choice(messages)


def get_character_jealousy(character_id: str) -> str:
    """Get a random jealousy message for a character."""
    messages = JEALOUSY_TEXTS.get(character_id, JEALOUSY_TEXTS['mark_01'])
    return random.choice(messages)


def get_character_cliffhanger(character_id: str) -> str:
    """Get a random cliffhanger message for a character."""
    messages = CLIFFHANGER_TEXTS.get(character_id, CLIFFHANGER_TEXTS['mark_01'])
    return random.choice(messages)


def get_character_gift(character_id: str) -> str:
    """Get a random gift message for a character."""
    messages = GIFT_MESSAGES.get(character_id, GIFT_MESSAGES['mark_01'])
    return random.choice(messages)


def get_daily_compatibility() -> str:
    """Get a daily compatibility forecast."""
    pct = random.randint(75, 99)
    template = random.choice(COMPATIBILITY_MESSAGES)
    return template.format(pct=pct)


def process_secret_command(text: str) -> Optional[str]:
    """Check if text contains a secret command and return response."""
    text_lower = text.lower().strip()
    
    # Check for exact matches first
    if text_lower in SECRET_COMMANDS:
        return random.choice(SECRET_COMMANDS[text_lower])
    
    # Check for partial matches
    for cmd, responses in SECRET_COMMANDS.items():
        if cmd in text_lower:
            return random.choice(responses)
    
    return None


def tidy_fixed_text(text: str) -> str:
    """V3.64.8: emoji were once stripped from these lines and left double
    spaces behind («утро  у меня перерыв»); em dashes read as a machine."""
    import re
    from services.dialogue_guard_service import casual_punctuation
    return casual_punctuation(re.sub(r'[ \t]{2,}', ' ', text or '').strip())


def get_retention_text(kind: str, character_id: str = 'mark_01') -> str:
    """Get retention text by kind and character."""
    return tidy_fixed_text(_raw_retention_text(kind, character_id))


def _raw_retention_text(kind: str, character_id: str = 'mark_01') -> str:
    getters = {
        'miss': get_character_miss,
        'jealousy': get_character_jealousy,
        'cliffhanger': get_character_cliffhanger,
        'morning': get_character_morning,
        'evening': get_character_evening,
    }
    getter = getters.get(kind)
    if getter:
        return getter(character_id)
    return get_character_miss(character_id)


# ── Achievement system ─────────────────────────────────────────────────────

ACHIEVEMENTS = {
    'first_message': {
        'name': 'Первое сообщение',
        'description': 'Отправь первое сообщение персонажу',
        'reward_stars': 10,
        'check': lambda user, state: True,  # Always true when called
    },
    'streak_7': {
        'name': 'Неделя вместе',
        'description': 'Общайся 7 дней подряд',
        'reward_stars': 50,
        'check': lambda user, state: (user.streak_count or 0) >= 7,
    },
    'streak_30': {
        'name': 'Месяц вместе',
        'description': 'Общайся 30 дней подряд',
        'reward_stars': 200,
        'check': lambda user, state: (user.streak_count or 0) >= 30,
    },
    'photos_10': {
        'name': 'Фотоколлекция',
        'description': 'Собери 10 фото',
        'reward_stars': 30,
        # V3.65.0: 10 old peaches = 1000 after the ×100 rescale.
        'check': lambda user, state: (user.photo_credits or 0) >= 1000,
    },
    'level_5': {
        'name': 'Близкие отношения',
        'description': 'Достигни 5 уровня близости',
        'reward_stars': 100,
        'check': lambda user, state: (state.affection if state else 0) >= 0.75,
    },
    'secret_hug': {
        'name': 'Тайное объятие',
        'description': 'Используй секретную команду "обними"',
        'reward_stars': 20,
        'check': lambda user, state: False,  # Checked separately
    },
    'secret_kiss': {
        'name': 'Тайный поцелуй',
        'description': 'Используй секретную команду "поцелуй"',
        'reward_stars': 20,
        'check': lambda user, state: False,  # Checked separately
    },
}


def check_achievements(user, character_state) -> list:
    """Check which achievements user has unlocked. Returns list of achievement keys."""
    unlocked = []
    for key, ach in ACHIEVEMENTS.items():
        try:
            if ach['check'](user, character_state):
                unlocked.append(key)
        except Exception:
            pass
    return unlocked


def get_achievement_reward(achievement_key: str) -> int:
    """Get star reward for an achievement.

    V3.46.0: NOT the source of truth — this legacy catalog is not part of the
    unified board and its rewards are never dispatched. The real achievement
    perks live in gamification_service.ACHIEVEMENTS (voucher / sealed scene /
    badge only, never peaches or Stars). Kept only for historical callers.
    """
    return ACHIEVEMENTS.get(achievement_key, {}).get('reward_stars', 0)


def get_achievement_info(achievement_key: str) -> dict:
    """Get achievement info."""
    return ACHIEVEMENTS.get(achievement_key, {})


# ── Collectible moments (Polaroid memories) ───────────────────────────────

MOMENT_TRIGGERS = {
    'first_photo': 'Первое фото вместе',
    'streak_7': 'Неделя вместе',
    'streak_30': 'Месяц вместе',
    'level_5': 'Близкие отношения',
    'first_gift': 'Первый подарок',
    'secret_command': 'Тайная команда',
}


def get_moment_name(trigger: str) -> str:
    """Get moment name by trigger."""
    return MOMENT_TRIGGERS.get(trigger, 'Особый момент')


# ─ Stories (24h content) ──────────────────────────────────────────────────

STORY_TEMPLATES = {
    'mark_01': [
        'Новый объект 🏗',
        'Вечер с джазом 🎷',
        'Крыша на закате 🌇',
    ],
    'maksim_01': [
        'Новое блюдо 🍝',
        'Кухня кипит 🔥',
        'Выходной с пиццей 🍕',
    ],
    'daniil_01': [
        'Ночная смена 🏥',
        'Кофе в 5 утра ☕',
        'Шопен в машине 🎹',
    ],
    'timur_01': [
        'Ночная трасса 🚘',
        'Кабинет на закате 🏢',
        'Бокс 🥊',
    ],
    'leo_01': [
        'Ночная трасса 🏍',
        'Новая плёнка 🎞',
        'Закат с моста 🌉',
    ],
    'minjun_01': [
        'Ночной рамён 🍜',
        'Новая песня 🎸',
        'Река Хан 🌉',
    ],
}


def get_story(character_id: str) -> str:
    """Get a random story for a character."""
    stories = STORY_TEMPLATES.get(character_id, STORY_TEMPLATES['mark_01'])
    return random.choice(stories)


# ─ Mini-quests "help the character" ───────────────────────────────────────

MINI_QUESTS = {
    'mark_01': [
        'Помоги выбрать цвет фасада 🎨',
        'Какой фильм посмотреть вечером? 🎬',
        'Выбери, куда пойдём на свидание 🍽',
    ],
    'maksim_01': [
        'Помоги придумать название блюду 🍲',
        'Что приготовить на ужин? 🥘',
        'Выбери десерт 🍰',
    ],
    'daniil_01': [
        'Помоги выбрать книгу на выходные 📖',
        'Какой фильм посмотреть после смены? 🎬',
        'Куда сбежать на выходные? 🗺',
    ],
    'timur_01': [
        'Выбери, куда я отвезу тебя в выходные ✈️',
        'Помоги выбрать часы ⌚',
        'Ресторан на вечер? 🍷',
    ],
    'leo_01': [
        'Выбери фото для выставки 📸',
        'Куда поедем на мотоцикле? 🏍',
        'Какую тату мне сделать? 🖋',
    ],
    'minjun_01': [
        'Выбери песню, которую я спою тебе 🎶',
        'Какую дораму посмотрим? 📺',
        'Научить тебя корейскому слову? 🇰🇷',
    ],
}


def get_mini_quest(character_id: str) -> str:
    """Get a random mini-quest for a character."""
    quests = MINI_QUESTS.get(character_id, MINI_QUESTS['mark_01'])
    return random.choice(quests)


# ── Seasonal events ────────────────────────────────────────────────────────

SEASONAL_EVENTS = {
    'valentines': {
        'date': '02-14',
        'message': 'С Днём святого Валентина! 💕 Сегодня особенный день для нас двоих...',
    },
    'new_year': {
        'date': '01-01',
        'message': 'С Новым годом! 🎄 Пусть этот год будет нашим...',
    },
    'march_8': {
        'date': '03-08',
        'message': 'С 8 Марта!  Ты делаешь мой мир ярче...',
    },
    'halloween': {
        'date': '10-31',
        'message': 'С Хэллоуином! 🎃 Я сегодня в образе... угадай в каком? 😏',
    },
}


def get_seasonal_event() -> Optional[dict]:
    """Get current seasonal event if any."""
    today = datetime.now().strftime('%m-%d')
    for key, event in SEASONAL_EVENTS.items():
        if event['date'] == today:
            return event
    return None


# ── Weekly dates ───────────────────────────────────────────────────────────

WEEKLY_DATES = {
    'mark_01': [
        'Ужин на крыше 🌃',
        'Прогулка по старому центру 🏛',
        'Вечер у камина 🔥',
    ],
    'maksim_01': [
        'Ужин, который он приготовил сам 🍽',
        'Пикник у реки 🧺',
        'Вечер с пиццей и сериалом 🍕',
    ],
    'daniil_01': [
        'Ночная поездка за город 🚗',
        'Кофе на рассвете ☕',
        'Концерт классической музыки 🎻',
    ],
    'timur_01': [
        'Ужин в ресторане на крыше 🍷',
        'Ночная поездка за город 🚘',
        'Выходные у моря ✈️',
    ],
    'leo_01': [
        'Ночная поездка на мотоцикле 🏍',
        'Фотосессия вдвоём 📸',
        'Бар с живой музыкой 🎸',
    ],
    'minjun_01': [
        'Пикник у реки 🧺',
        'Караоке вдвоём 🎤',
        'Прогулка под зонтом ☔',
    ],
}


def get_weekly_date(character_id: str) -> str:
    """Get a random weekly date idea for a character."""
    dates = WEEKLY_DATES.get(character_id, WEEKLY_DATES['mark_01'])
    return random.choice(dates)
