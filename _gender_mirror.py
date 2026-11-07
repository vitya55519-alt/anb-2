# -*- coding: utf-8 -*-
"""Stage 2 tool: mirror the gender of people in Russian text.

The original bot is a heroine talking to a man. This bot is a hero talking to
a woman, so every person in the texts swaps gender: «она ждала его» becomes
«он ждал её», «ты пришёл» becomes «ты пришла», «Девушка дня» becomes
«Парень дня». Only string literals are touched (tokenize), never code,
comments or docstrings.

Usage: python _gender_mirror.py FILE...   (needs pymorphy3)
"""
from __future__ import annotations

import io
import re
import sys
import tokenize

import pymorphy3

M = pymorphy3.MorphAnalyzer()
WORD = re.compile(r'[А-Яа-яЁё]+')

PRON = {
    'он': 'она', 'она': 'он', 'его': 'её', 'её': 'его', 'ее': 'его',
    'ему': 'ей', 'ей': 'ему', 'него': 'неё', 'неё': 'него', 'нее': 'него',
    'нему': 'ней', 'ним': 'ней', 'нём': 'ней', 'нем': 'ней', 'ней': 'ним',
}
SHORT = {
    'рад': 'рада', 'готов': 'готова', 'должен': 'должна', 'согласен': 'согласна', 'уверен': 'уверена',
    'свободен': 'свободна', 'занят': 'занята', 'один': 'одна', 'влюблён': 'влюблена', 'влюблен': 'влюблена',
    'счастлив': 'счастлива', 'прав': 'права', 'красив': 'красива', 'смел': 'смела', 'обязан': 'обязана', 'знаком': 'знакома',
}
SHORT.update({v: k for k, v in list(SHORT.items())})
GEN_PREP = {'у', 'от', 'для', 'без', 'из', 'до', 'около', 'возле', 'кроме', 'вместо'}
INSTR_PREP = {'с', 'со', 'над', 'под', 'перед', 'за', 'между'}
LOC_PREP = {'о', 'об', 'обо', 'в', 'во', 'на', 'при'}
DAT_PREP = {'к', 'ко', 'по'}

PERSON = {
    'девушка': 'парень', 'парень': 'девушка', 
    'жена': 'муж', 'муж': 'жена', 'женщина': 'мужчина', 'мужчина': 'женщина',
    'героиня': 'герой', 'герой': 'героиня', 'невеста': 'жених', 'жених': 'невеста',
    'соседка': 'сосед', 'сосед': 'соседка', 'незнакомка': 'незнакомец', 'незнакомец': 'незнакомка',
    'попутчица': 'попутчик', 'попутчик': 'попутчица', 'красавица': 'красавчик', 'красавчик': 'красавица',
    'малышка': 'малыш', 'малыш': 'малышка', 'любовница': 'любовник', 'любовник': 'любовница',
    'девочка': 'мальчик', 'мальчик': 'девочка', 'хозяйка': 'хозяин', 'хозяин': 'хозяйка',
    'королева': 'король', 'король': 'королева', 'принцесса': 'принц', 'принц': 'принцесса',
    'зайка': 'зайка', 'котёнок': 'котёнок',
}
ADDRESS = {'дорогой', 'дорогая', 'родной', 'родная'}
NO_FLIP = {
    'русский', 'английский', 'разговорный', 'встроенный', 'базовый', 'пробный', 'тестовый', 'бессрочный',
    'деплой', 'числовой', 'банковский', 'полицейский', 'мужской', 'женский', 'гардеробный', 'сегодняшний',
    'мелькающий', 'графический', 'приватный', 'разовый', 'одноразовый', 'низкий', 'высокий',
    'обычный', 'новый', 'стильный', 'чёрный', 'белый', 'красный', 'тихий', 'пустой', 'незавершённый',
    'написанный', 'сгенерироваться', 'перезапуститься', 'умереть', 'вернуть', 'отменить', 'отправить',
}
GENDER_SWAP = {'masc': 'femn', 'femn': 'masc'}
CASES = ('nomn', 'gent', 'datv', 'accs', 'ablt', 'loct', 'voct', 'gen2', 'acc2', 'loc2')


def keep_case(src: str, out: str) -> str:
    if src.isupper() and len(src) > 1:
        return out.upper()
    if src[:1].isupper():
        return out[:1].upper() + out[1:]
    return out


def best(word: str):
    ps = M.parse(word)
    first = ps[0]
    if word in ADDRESS:
        for q in ps:
            if 'ADJF' in q.tag and q.tag.case == 'nomn':
                return q
    if 'ADJF' in first.tag or 'PRTF' in first.tag:
        for q in ps:
            if ('ADJF' in q.tag or 'PRTF' in q.tag) and q.tag.case == 'nomn' and q.tag.number == 'sing':
                return q
        for q in ps:
            if ('ADJF' in q.tag or 'PRTF' in q.tag) and q.tag.number == 'sing':
                return q
    return first


def flip_gender(p, word, prev=''):
    g = p.tag.gender
    if g not in GENDER_SWAP or p.tag.number == 'plur':
        return None
    feats = {GENDER_SWAP[g]}
    case = p.tag.case
    if g == 'femn' and case in ('gent', 'datv', 'ablt', 'loct') and ('ADJF' in p.tag or 'PRTF' in p.tag):
        # «-ой» is four cases at once; the preposition decides, else instrumental
        # («пишет первой», «стала смелой»)
        if prev in INSTR_PREP:
            case = 'ablt'
        elif prev in LOC_PREP:
            case = 'loct'
        elif prev in DAT_PREP:
            case = 'datv'
        elif prev in GEN_PREP:
            case = 'gent'
        else:
            case = 'ablt'
    if case:
        feats.add(case)
    if 'ADJF' in p.tag or 'PRTF' in p.tag:
        # «первой» (femn ablt) -> «первым»; animacy only matters for accs
        pass
    q = p.inflect(feats)
    return q.word if q else None


def swap_noun(p):
    lemma = p.normal_form
    target = PERSON.get(lemma)
    if not target or target == lemma:
        return None
    tp = None
    for cand in M.parse(target):
        if 'NOUN' in cand.tag:
            tp = cand
            break
    if tp is None:
        return None
    feats = {p.tag.number or 'sing'}
    if p.tag.case:
        feats.add(p.tag.case)
    q = tp.inflect(feats)
    return q.word if q else None


def mirror(text: str) -> str:
    if re.search(r'\[[^\]]*[А-Яа-яЁё][^\]]*\]', text) and ('\\b' in text or '(?' in text or '|' in text):
        parts = re.split(r'(\[[^\]]*\])', text)
        return ''.join(pt if pt.startswith('[') else _mirror(pt) for pt in parts)
    return _mirror(text)


def _mirror(text: str) -> str:
    toks = list(WORD.finditer(text))
    words = [m.group(0) for m in toks]
    lows = [w.lower() for w in words]
    parses = [best(w) for w in lows]
    out = list(words)
    n = len(words)

    def gap_ok(i, j):
        # tokens i and j are adjacent words (only spaces between them)
        a, b = toks[i].end(), toks[j].start()
        return text[a:b].strip() == ''

    PUNCT_STOP = re.compile(r'[.,!?;:—«»\[\]\n"]')

    def same_clause(a, b):
        lo, hi = (a, b) if a < b else (b, a)
        return not PUNCT_STOP.search(text[toks[lo].end():toks[hi].start()])

    def thing_subject(i, gender):
        # a nominative thing-noun of the same gender in the clause → the word agrees with it
        before = text[max(0, toks[i].start() - 40):toks[i].start()]
        before = re.split(r'[.,!?;:—«»\n]', before)[-1]
        if re.search(r'[A-Za-z]{2,}', before):
            return True  # «Premium кончился», «Stars сразу вернула»
        for j in list(range(i - 1, max(-1, i - 6), -1)) + list(range(i + 1, min(n, i + 3))):
            if not same_clause(i, j):
                continue
            if lows[j] in ('я', 'ты', 'он', 'она', 'сам', 'сама') or j in noun_flipped:
                return False
            for q in M.parse(lows[j]):
                if 'NOUN' in q.tag and q.tag.case == 'nomn' and q.tag.number == 'sing' and q.tag.gender == gender:
                    if q.normal_form in PERSON or 'anim' in q.tag or 'Name' in q.tag:
                        return False
                    return True
        return False

    def target_gender(i):
        # first person is always the hero (masc), second person the user (femn)
        for j in list(range(i - 1, max(-1, i - 7), -1)) + list(range(i + 1, min(n, i + 3))):
            if not same_clause(i, j):
                continue
            lj = lows[j]
            if lj == 'я':
                return 'masc'
            if lj in ('ты', 'пользователь', 'собеседник', 'собеседница'):
                return 'femn'
            if lj == 'он':
                return 'femn'   # the user in the original texts
            if lj == 'она':
                return 'masc'   # the heroine in the original texts
            if j in noun_flipped:
                g = M.parse(out[j].lower())[0].tag.gender
                return g
        return 'masc'

    def antecedent_flipped(i):
        for j in range(i - 1, max(-1, i - 6), -1):
            if 'NOUN' in parses[j].tag or lows[j] in PRON:
                return j in noun_flipped or lows[j] in PRON
        return False

    # 1) person nouns and the adjectives that agree with them
    noun_flipped = set()
    for i, p in enumerate(parses):
        if 'NOUN' in p.tag and p.tag.number != 'plur' and p.normal_form in PERSON and p.normal_form != PERSON[p.normal_form]:
            new = swap_noun(p)
            if new:
                out[i] = keep_case(words[i], new)
                noun_flipped.add(i)
    # 2) everything else, token by token
    for i, (w, lw, p) in enumerate(zip(words, lows, parses)):
        if i in noun_flipped:
            continue
        if lw in ('один', 'одна') and i + 1 < n and (lows[i + 1] == 'из' or 'ADJF' in parses[i + 1].tag):
            continue
        if lw in SHORT and not (lw in ('один', 'одна') and i + 1 < n and gap_ok(i, i + 1)
                                and 'NOUN' in parses[i + 1].tag
                                and any(q.tag.gender == ('femn' if lw == 'одна' else 'masc') for q in M.parse(lows[i + 1]) if 'NOUN' in q.tag)):
            out[i] = keep_case(w, SHORT[lw])
            continue
        if lw in PRON:
            prev = lows[i - 1] if i > 0 and gap_ok(i - 1, i) else ''
            new = PRON[lw]
            if lw in ('ней',):
                pass
            if lw == 'ней' or (lw in ('ним', 'нём', 'нем', 'нему') ):
                pass
            if lw == 'ней':
                if prev in INSTR_PREP:
                    new = 'ним'
                elif prev in LOC_PREP:
                    new = 'нём'
                elif prev in DAT_PREP:
                    new = 'нему'
                else:
                    new = 'ним'
            out[i] = keep_case(w, new)
            continue
        tag = p.tag
        if p.normal_form in NO_FLIP:
            continue
        if 'VERB' in tag and tag.tense == 'past' and tag.number == 'sing' and tag.gender in GENDER_SWAP:
            if lw in ('сек', 'мин', 'час') or len(lw) < 3 or thing_subject(i, tag.gender):
                continue
            want = target_gender(i)
            if want and want != tag.gender:
                new = flip_gender(p, lw)
                if new:
                    out[i] = keep_case(w, new)
            continue
        if 'ADJS' in tag or 'PRTS' in tag:
            near = set(lows[max(0, i - 3):i])
            if any(j in noun_flipped and same_clause(j, i) for j in range(max(0, i - 4), i)):
                near.add('он')
            if tag.number == 'sing' and tag.gender in GENDER_SWAP and not thing_subject(i, tag.gender) and target_gender(i) != tag.gender and near & {'я', 'ты', 'он', 'она', 'сама', 'сам', 'был', 'была', 'будь', 'будешь', 'буду', 'стал', 'стала'}:
                new = flip_gender(p, lw)
                if new:
                    out[i] = keep_case(w, new)
            continue
        if ('ADJF' in tag or 'PRTF' in tag) and tag.number == 'sing' and tag.gender in GENDER_SWAP:
            if p.normal_form == 'который':
                if antecedent_flipped(i):
                    new = flip_gender(p, lw, lows[i - 1] if i > 0 else '')
                    if new:
                        out[i] = keep_case(w, new)
                continue
            # find the head: next non-adjective word (lists like «медицинскую, юридическую … помощь» too)
            j = i + 1
            while j < n and same_clause(j - 1, j) is not None and (
                    ({'ADJF', 'PRTF'} & set(str(parses[j].tag).replace(' ', ',').split(',')))
                    or lows[j] in ('и', 'или', 'а', 'но')) and not re.search(r'[.!?;:—«»]', text[toks[j - 1].end():toks[j].start()]):
                j += 1
            head = parses[j] if j < n and not re.search(r'[.!?;:—«»()\n]', text[toks[j - 1].end():toks[j].start()]) else None
            if head is not None and 'NOUN' in head.tag and (j in noun_flipped or any(
                    q.tag.gender == tag.gender or q.tag.number == 'plur' or 'GNdr' in q.tag
                    for q in M.parse(lows[j]) if 'NOUN' in q.tag)):
                if j in noun_flipped:
                    tp = M.parse(out[j].lower())[0]
                    feats = {tp.tag.gender} if tp.tag.gender else set()
                    if head.tag.case:
                        feats.add(head.tag.case)
                    if head.tag.case == 'accs':
                        feats.add('anim')
                    q = p.inflect(feats) if feats else None
                    if q:
                        out[i] = keep_case(w, q.word)
                continue  # agrees with a thing, not a person
            # an addressed or predicative adjective: «моя хорошая», «сама», «первой»
            if p.normal_form in ('этот', 'тот', 'каждый', 'любой', 'всякий', 'другой', 'иной', 'следующий', 'данный', 'один'):
                continue
            if not any(q.tag.case in ('nomn', 'ablt', 'voct') for q in M.parse(lw) if q.word == lw and ('ADJF' in q.tag or 'PRTF' in q.tag)):
                continue
            if thing_subject(i, tag.gender):
                continue
            cases = {q.tag.case for q in M.parse(lw) if q.word == lw and ('ADJF' in q.tag or 'PRTF' in q.tag)}
            if any(same_clause(i, k) and any('NOUN' in q.tag and q.tag.gender == tag.gender and q.tag.number == 'sing'
                                              and q.tag.case in cases and q.normal_form not in PERSON
                                              for q in M.parse(lows[k]))
                   for k in range(i + 1, min(n, i + 4))):
                continue
            if 'Apro' in tag and lw in ('это', 'эта', 'этот', 'та', 'тот', 'каждая', 'каждый', 'любая', 'любой', 'эту', 'этой', 'этого', 'той', 'того'):
                continue
            prev = lows[i - 1] if i > 0 and gap_ok(i - 1, i) else ''
            new = flip_gender(p, lw, prev)
            if new:
                out[i] = keep_case(w, new)
    res = []
    last = 0
    for m, o in zip(toks, out):
        res.append(text[last:m.start()])
        res.append(o)
        last = m.end()
    res.append(text[last:])
    return ''.join(res)


def _is_docstring(prev_sig, nxt):
    return prev_sig in (tokenize.INDENT, tokenize.NEWLINE, tokenize.DEDENT, None) and nxt == tokenize.NEWLINE


def mirror_python(src: str) -> str:
    toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    lines = src.splitlines(keepends=True)
    offs = [0]
    for line in lines:
        offs.append(offs[-1] + len(line))

    def pos(rc):
        return offs[rc[0] - 1] + rc[1]

    edits = []
    prev_sig = None
    for k, t in enumerate(toks):
        if t.type in (tokenize.STRING, getattr(tokenize, 'FSTRING_MIDDLE', -1)):
            nxt = None
            for t2 in toks[k + 1:]:
                if t2.type not in (tokenize.NL, tokenize.COMMENT):
                    nxt = t2.type
                    break
            if t.type == tokenize.STRING and _is_docstring(prev_sig, nxt):
                pass
            elif t.type == tokenize.STRING and re.match(r'^[rR]', t.string) and re.search(r'\\b|\(\?|\|', t.string):
                pass  # a regex: handled by hand
            elif WORD.search(t.string):
                new = mirror(t.string)
                if new != t.string:
                    edits.append((pos(t.start), pos(t.end), new))
        if t.type not in (tokenize.NL, tokenize.COMMENT):
            prev_sig = t.type
    for a, b, new in sorted(edits, reverse=True):
        src = src[:a] + new + src[b:]
    return src


if __name__ == '__main__':
    import ast
    for f in sys.argv[1:]:
        s = open(f, encoding='utf-8').read()
        if f.endswith('.py'):
            n = mirror_python(s)
            ast.parse(n)
        else:
            n = mirror(s)
        if n != s:
            open(f, 'w', encoding='utf-8').write(n)
            print('mirrored', f)
