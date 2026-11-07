from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from models.app_models import CharacterCard
from services.db import SessionLocal


STATUS_LABELS = {
    "active": "активна",
    "soon": "скоро",
    "locked": "закрыта",
    "premium": "Premium",
}

DEFAULT_CARDS = {
    'mark_01': {
        "display_name": 'Марк',
        "gender": "male",
        "age": 29,
        "short_bio": 'Архитектор, спокойный и взрослый. Слушает так, что хочется рассказать всё. Заботится без лишних слов и знает, как сделать вечер особенным.',
        "status": "active",
        "button_emoji": '🏛',
        "is_visible": True,
    },
    'maksim_01': {
        "display_name": 'Максим',
        "gender": "male",
        "age": 27,
        "short_bio": 'Шеф-повар с улыбкой, от которой теплеет. Кормит, балует и смешит. Умеет слушать и делать самый обычный вечер уютным.',
        "status": "active",
        "button_emoji": '👨\u200d🍳',
        "is_visible": True,
    },
    'daniil_01': {
        "display_name": 'Даниил',
        "gender": "male",
        "age": 32,
        "short_bio": 'Хирург. Сдержанный, немногословный, со спокойным взглядом. С тобой оттаивает. Бережёт тех, кто ему дорог, и немного ревнует.',
        "status": "active",
        "button_emoji": '🩺',
        "is_visible": True,
    },
    'timur_01': {
        "display_name": 'Тимур',
        "gender": "male",
        "age": 34,
        "short_bio": 'Владелец бизнеса. Властный, уверенный, привык решать. Рядом с ним спокойно и немного опасно. Знает, чего хочет, и хочет тебя.',
        "status": "active",
        "button_emoji": '🖤',
        "is_visible": True,
    },
    'leo_01': {
        "display_name": 'Лео',
        "gender": "male",
        "age": 26,
        "short_bio": 'Фотограф, загадочный и дерзкий. Плохой парень с мотоциклом, татуировками и неожиданно нежным сердцем. С ним никогда не скучно.',
        "status": "active",
        "button_emoji": '📷',
        "is_visible": True,
    },
    'minjun_01': {
        "display_name": 'Мин Джун',
        "gender": "male",
        "age": 24,
        "short_bio": 'Парень из Сеула, как из дорамы. Нежный, внимательный, немного стеснительный. Поёт тебе по вечерам и учит корейским словам.',
        "status": "active",
        "button_emoji": '🌸',
        "is_visible": True,
    },
}


# V3.19.0: WildGrl-style scenario hooks — a cinematic first message that
# pulls the user into a concrete situation instead of a generic greeting.
# Shown on the character card and sent as her opening line on selection.
SCENARIO_HOOKS = {
    'mark_01': '«Я весь день чертил чужие дома, а думал почему-то о тебе. Расскажешь, как прошёл твой день?»',
    'maksim_01': '«Я приготовил слишком много пасты. Это намёк. Придёшь?»',
    'daniil_01': '«Смена была тяжёлая. Мне нужен один голос, чтобы выдохнуть. Твой.»',
    'timur_01': '«Я заказал столик на двоих. В девять. Не опаздывай.»',
    'leo_01': '«Я снимаю тебя уже третий кадр, а ты даже не заметила. Улыбнись. Нет, не так. Вот так.»',
    'minjun_01': '«Я выучил одну песню на русском. Только для тебя. Можно спою?»',
}


# V3.61.1: «С сюжетом» — the chat opens with a ready scene: what she is doing
# right now (*action*) plus her first line. Everyone in every scene is an adult.
OPENING_SCENES = {
    'mark_01': '*Поздний вечер. Марк стоит у окна своей мастерской, на столе чертежи и остывший кофе. Видит твоё сообщение и улыбается* Наконец-то. Я как раз хотел спросить, как ты. Только честно: ты сегодня хоть раз поела нормально?',
    'maksim_01': '*Максим стоит у плиты в фартуке поверх футболки, на сковородке что-то шипит. Оборачивается на звонок* О, ты как раз вовремя! Разувайся и иди сюда, будешь пробовать соус. Скажешь, что невкусно, обижусь навсегда 😄',
    'daniil_01': '*Даниил выходит из больницы после ночной смены, снимает маску и видит тебя у входа. Устало улыбается* Ты что тут делаешь в такую рань? …Ладно. Я рад. Пойдём, угощу тебя кофе, пока ты не замёрзла.',
    'timur_01': '*Тимур откидывается в кресле своего кабинета, пиджак на спинке, рукава рубашки закатаны. Смотрит на тебя долго и спокойно* Закрой дверь. …Вот так. Я весь день ждал, когда ты придёшь. Садись ближе.',
    'leo_01': '*Лео сидит на мотоцикле у твоего подъезда, шлем на руле, в руке плёночная камера. Щёлкает тебя, как только ты выходишь* Попалась. Садись, прокачу. Или боишься? 😏',
    'minjun_01': '*Мин Джун сидит на подоконнике с гитарой, перебирает струны и смущённо улыбается, когда видит тебя* Ой… ты уже пришла? Я репетировал. Это была песня… для тебя. Только не смейся над моим акцентом, хорошо?',
}


def get_opening_scene(character_id: str) -> str | None:
    """V3.61.1: the «С сюжетом» first message — a full scene, falling back to the hook."""
    return OPENING_SCENES.get(character_id) or SCENARIO_HOOKS.get(character_id)


def get_scenario_hook(character_id: str) -> str | None:
    """Return the cinematic scenario hook for a character, if defined."""
    return SCENARIO_HOOKS.get(character_id)


@dataclass(frozen=True)
class CharacterCardView:
    character_id: str
    display_name: str
    gender: str
    age: int
    short_bio: str
    status: str
    button_emoji: str
    is_visible: bool
    card_photo_file_id: str | None

    @property
    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, self.status)

    @property
    def button_text(self) -> str:
        return f"{self.button_emoji} {self.display_name} · {self.status_label}"


def _to_view(row: CharacterCard) -> CharacterCardView:
    return CharacterCardView(
        character_id=row.character_id,
        display_name=row.display_name,
        gender=row.gender or "female",
        age=int(row.age or 18),
        short_bio=row.short_bio or "",
        status=row.status or "soon",
        button_emoji=row.button_emoji or "👩",
        is_visible=bool(row.is_visible),
        card_photo_file_id=row.card_photo_file_id,
    )


def ensure_default_cards() -> None:
    with SessionLocal() as session:
        changed = False
        # Old default bios that should be replaced with updated versions.
        _old_bios = {}
        for character_id, defaults in DEFAULT_CARDS.items():
            row = session.get(CharacterCard, character_id)
            if row is None:
                session.add(CharacterCard(character_id=character_id, **defaults))
                changed = True
                continue
            # One-time backward-compatible public rename. Keep the internal id so existing
            # photo-library and DB references do not break. Do not overwrite a custom name.
            if character_id == "alena_01" and (row.display_name or "").strip() in {"Алёна", "Алена"}:
                row.display_name = "Emily"
                changed = True
            # Update bios that still hold old default text.
            if row.short_bio and row.short_bio == _old_bios.get(character_id):
                row.short_bio = defaults["short_bio"]
                changed = True
            # Emily defaults to active now; sync if still at old "soon" default.
            if character_id == "alena_01" and row.status == "soon":
                row.status = defaults["status"]
                changed = True
            # V3.55.3: Maria is back in the common roster (owner will build the
            # premium lineup himself) — sync the production row the same way.
            # If Maria ever needs to be premium again, REMOVE this line first:
            # it reverts any admin-panel flip on every bot start.
            if character_id == "maria_01" and row.status == "premium":
                row.status = defaults["status"]
                changed = True
            # One-time backfill for rows created before gender/age/short_bio existed
            # in the DB schema. Only fills NULLs, never overwrites admin edits.
            for field in ("gender", "age", "short_bio"):
                if getattr(row, field) is None:
                    setattr(row, field, defaults[field])
                    changed = True
        if changed:
            session.commit()


def list_cards(*, visible_only: bool = False) -> list[CharacterCardView]:
    ensure_default_cards()
    with SessionLocal() as session:
        query = session.query(CharacterCard)
        if visible_only:
            query = query.filter(CharacterCard.is_visible.is_(True))
        rows = query.order_by(CharacterCard.character_id.asc()).all()
        return [_to_view(row) for row in rows]


def get_card(character_id: str) -> CharacterCardView | None:
    ensure_default_cards()
    with SessionLocal() as session:
        row = session.get(CharacterCard, character_id)
        return _to_view(row) if row else None


def update_card(character_id: str, **changes) -> CharacterCardView:
    ensure_default_cards()
    allowed = {
        "display_name", "gender", "age", "short_bio", "status", "button_emoji",
        "is_visible", "card_photo_file_id",
    }
    clean = {k: v for k, v in changes.items() if k in allowed}
    if "status" in clean and clean["status"] not in STATUS_LABELS:
        raise ValueError("unknown card status")
    with SessionLocal() as session:
        row = session.get(CharacterCard, character_id)
        if row is None:
            defaults = DEFAULT_CARDS.get(character_id, {
                "display_name": character_id,
                "gender": "female",
                "age": 18,
                "short_bio": "",
                "status": "soon",
                "button_emoji": "👩",
                "is_visible": True,
            })
            row = CharacterCard(character_id=character_id, **defaults)
            session.add(row)
        for key, value in clean.items():
            setattr(row, key, value)
        session.commit()
        session.refresh(row)
        return _to_view(row)


def reset_card(character_id: str) -> CharacterCardView:
    defaults = DEFAULT_CARDS.get(character_id)
    if not defaults:
        raise ValueError("no defaults for character")
    return update_card(character_id, **defaults, card_photo_file_id=None)


def create_card(character_id: str, display_name: str, age: int, short_bio: str, button_emoji: str = "👩", gender: str = "female") -> CharacterCardView:
    character_id = (character_id or '').strip().lower()
    display_name = (display_name or '').strip()
    gender = (gender or "female").strip().lower()
    if gender not in {"male", "female", "other"}:
        raise ValueError("пол: male, female или other")
    if not character_id or not display_name:
        raise ValueError("id и имя обязательны")
    if not re.match(r'^[a-z0-9_]+$', character_id):
        raise ValueError("id только маленькие латинские буквы, цифры и подчёркивание")
    if not 18 <= age <= 99:
        raise ValueError("возраст 18–99")
    with SessionLocal() as session:
        if session.get(CharacterCard, character_id):
            raise ValueError("такой id уже есть")
        row = CharacterCard(
            character_id=character_id,
            display_name=display_name,
            gender=gender,
            age=age,
            short_bio=short_bio or "",
            status="soon",
            button_emoji=button_emoji or "👩",
            is_visible=True,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _to_view(row)


def delete_card(character_id: str) -> bool:
    if character_id in DEFAULT_CARDS:
        raise ValueError("стандартных персонажей нельзя удалить")
    with SessionLocal() as session:
        row = session.get(CharacterCard, character_id)
        if not row:
            return False
        session.delete(row)
        session.commit()
        return True
