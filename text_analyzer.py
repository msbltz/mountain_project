"""
@author: yuan.shao
"""
from __future__ import annotations

from copy import deepcopy
from typing import Dict, List, Tuple

import spacy
from spacy.lookups import load_lookups
from spacy.tokens.token import Token

SMALL = 'en_core_web_sm'
MEDIUM = 'en_core_web_md'
LARGE = 'en_core_web_lg'

COLORS = [f'\033[{91 + i}m' for i in range(6)]
ENDC = '\033[0m'

CENTER_POS = {'ADJ', 'NOUN', 'NUM', 'PROPN', 'SYM', 'X'}
DECORATOR_STOP_POS = {'ADP', 'ADV', 'DET', 'PRON', 'PUNCT', 'SCONJ', 'VERB'}


class TextAnalyzer:
    def __init__(self, model: str):
        self.nlp = spacy.load(model)
        self.prob = (
            load_lookups('en', ['lexeme_prob']).get_table('lexeme_prob')
        )
        self.min_prob = min(self.prob.values())

    def generate_keywords(
        self, texts: List[str], print_details: bool = False,
    ) -> Tuple[List[str], Dict[str, int]]:
        counts, weights, probs = dict(), dict(), dict()
        tokens = []
        for text in texts:
            for token in self.nlp(text):
                tokens.append(token)
                if token.is_sent_end:
                    sentence = Sentence(tokens)
                    tokens = []
                    phrases = sentence.extract_phrases()
                    if print_details:
                        sentence.print_parallel()
                        print([phrase.to_string() for phrase in phrases])
                        print('')
                    for phrase in phrases:
                        ps = phrase.to_string()
                        if ps not in counts:
                            counts[ps] = 0
                            weights[ps] = phrase.get_weight()
                            probs[ps] = self.phrase_prob(phrase)
                        counts[ps] += 1
        counts = {p: ct for p, ct in counts.items() if ct > 1}
        keywords = list(counts.keys())
        keywords.sort(
            key=lambda p: (counts[p] * weights[p], -probs[p]), reverse=True,
        )
        return keywords, counts

    def phrase_prob(self, phrase: Phrase) -> float:
        return min(
            [self.prob.get(word, self.min_prob - 1) for word in phrase.words]
        )


class Sentence:
    def __init__(self, tokens: List[Token]):
        mp = dict()
        rd = dict()
        idx = 0
        while idx < len(tokens):
            token = tokens[idx]
            t1 = tokens[idx + 1] if idx + 1 < len(tokens) else None
            t2 = tokens[idx + 2] if idx + 2 < len(tokens) else None
            # Combine '#'(SYM) + NUM.
            if (
                token.lemma_ == '#' and token.pos_ == 'SYM'
                and t1 is not None and t1.pos_ == 'NUM'
            ):
                idx += self.merge_tokens(mp, rd, [token, t1], 1, 1)
            # Combine NUM + '-'(SYM) + NUM.
            elif (
                token.pos_ == 'NUM'
                and t1 is not None and t1.lemma_ == '-' and t1.pos_ == 'SYM'
                and t2 is not None and t2.pos_ == 'NUM'
            ):
                if t2.head == token:
                    idx += self.merge_tokens(mp, rd, [token, t1, t2], 0, 1)
                else:
                    idx += self.merge_tokens(mp, rd, [token, t1, t2], 2, 1)
            # Combine NUM + '%' or '+'(NOUN).
            elif (
                token.pos_ == 'NUM'
                and t1 is not None
                and t1.lemma_ in {'%', '+'} and t1.pos_ == 'NOUN'
            ):
                idx += self.merge_tokens(mp, rd, [token, t1], 0, 1)
            # Combine NUM + 'm'(NOUN).
            elif (
                token.pos_ == 'NUM'
                and t1 is not None
                and t1.lemma_.lower() == 'm' and t1.pos_ == 'NOUN'
            ):
                idx += self.merge_tokens(mp, rd, [token, t1], 1, 1)
            # Combine * + '/' + * + '/' + * + ...
            elif t1 is not None and t1.lemma_ == '/' and t2 is not None:
                to_merge = [token, t1, t2]
                i = 4
                while (
                    idx + i < len(tokens) and tokens[idx + i - 1].lemma_ == '/'
                ):
                    to_merge.append(tokens[idx + i - 1])
                    to_merge.append(tokens[idx + i])
                    i += 2
                head_idx = len(to_merge) - 1
                weight = (len(to_merge) + 1) // 2
                idx += self.merge_tokens(mp, rd, to_merge, head_idx, weight)
            else:
                idx += self.merge_tokens(mp, rd, [token])
        for token in mp:
            mp[token].head = mp[rd[token.head]]
        for i, token in enumerate(tokens):
            if rd[token] != token:
                continue
            res = []
            for t in reversed(tokens[:i]):
                if rd[t] != t:
                    continue
                if mp[t].head == mp[token]:
                    if mp[t].pos in DECORATOR_STOP_POS:
                        break
                    res.append(mp[t])
            mp[token].left_decorators = res
            res = []
            for t in tokens[(i + 1):]:
                if rd[t] != t:
                    continue
                if mp[t].head == mp[token]:
                    if mp[t].pos in DECORATOR_STOP_POS:
                        break
                    res.append(mp[t])
            mp[token].right_decorators = res
        for token in mp:
            if mp[token].center_phrase is None:
                mp[token].compute_center_phrase()
        for token in mp:
            if mp[token].left_phrases is None:
                mp[token].compute_left_phrases()
            if mp[token].right_phrases is None:
                mp[token].compute_right_phrases()
        self.sentence = [
            mp[token] for token in tokens if rd[token] == token
        ]

    @staticmethod
    def merge_tokens(
        mp: Dict[Token, Word],
        rd: Dict[Token, Token],
        tokens: List[Token],
        head_idx: int = 0,
        weight: int = 1,
    ) -> int:
        mp[tokens[head_idx]] = Word(tokens, pos_idx=head_idx, weight=weight)
        for token in tokens:
            rd[token] = tokens[head_idx]
        return len(tokens)

    def extract_phrases(self) -> List[Phrase]:
        res = []
        for word in self.sentence:
            if word.pos in CENTER_POS:
                phrases = [word.center_phrase]
                seen = {word.center_phrase.to_string()}
                for phrase in word.left_phrases:
                    if phrase.to_string() not in seen:
                        phrases.append(phrase)
                        seen.add(phrase.to_string())
                for phrase in word.right_phrases:
                    if phrase.to_string() not in seen:
                        phrases.append(phrase)
                        seen.add(phrase.to_string())
                res.extend(phrases)
        return res

    def print_parallel(self, max_line_len: int = 160) -> None:
        words = (
            [['[TEXT]', '[POS]', '[HEAD]', '[CENTER]', '[LEFT]', '[RIGHT]']]
            + [
                [
                    word.text,
                    word.pos,
                    word.head.text,
                    word.center_phrase.to_string('+'),
                    '|'.join([p.to_string('+') for p in word.left_phrases]),
                    '|'.join([p.to_string('+') for p in word.right_phrases]),
                ]
                for word in self.sentence
            ]
        )
        max_attr_len = [max([len(attr) for attr in word]) for word in words]
        cutoffs = []
        prev_idx, curr_sum = 0, 0
        for idx, length in enumerate(max_attr_len):
            if curr_sum > 0 and curr_sum + length + 1 > max_line_len:
                cutoffs.append((prev_idx, idx))
                prev_idx, curr_sum = idx, length + 1
            else:
                curr_sum += length + 1
        cutoffs.append((prev_idx, len(max_attr_len)))
        print('============')
        for left_idx, right_idx in cutoffs:
            for j in range(len(words[0])):
                print(
                    COLORS[j % len(COLORS)]
                    + ' '.join([
                        word[j].ljust(l)
                        for word, l in zip(
                            words[left_idx:right_idx],
                            max_attr_len[left_idx:right_idx],
                        )
                    ])
                    + ENDC
                )
        print('============')


class Phrase:
    def __init__(self, words: List[str], weight: int):
        self.words = words
        self.weight = weight

    def add(self, other: Phrase, to_end: bool) -> None:
        if to_end:
            self.words = self.words + other.words
        else:
            self.words = other.words + self.words
        self.weight += other.weight

    @classmethod
    def plus(cls, p1: Phrase, p2: Phrase) -> Phrase:
        res = deepcopy(p1)
        res.add(other=p2, to_end=True)
        return res

    def to_string(self, sep: str = ' ') -> str:
        return sep.join(self.words)

    def get_weight(self) -> int:
        return self.weight


class Word:
    def __init__(self, tokens: List[Token], pos_idx: int = 0, weight: int = 1):
        self.text = ''.join([token.text for token in tokens])
        self.word = ''.join([token.lemma_.lower() for token in tokens])
        self.pos = tokens[pos_idx].pos_
        self.weight = weight
        self.head = None  # Word
        self.left_decorators = []  # List[Word]
        self.right_decorators = []  # List[Word]
        self.center_phrase = None  # Phrase
        self.left_phrases = None  # List[Phrase]
        self.right_phrases = None  # List[Phrase]

    def to_phrase(self) -> Phrase:
        return Phrase([self.word], self.weight)

    def compute_center_phrase(self) -> None:
        self.center_phrase = self.to_phrase()
        if self.pos in CENTER_POS:
            for w in self.left_decorators:
                if w.center_phrase is None:
                    w.compute_center_phrase()
                self.center_phrase.add(other=w.center_phrase, to_end=False)
            for w in self.right_decorators:
                if w.center_phrase is None:
                    w.compute_center_phrase()
                self.center_phrase.add(other=w.center_phrase, to_end=True)

    def compute_left_phrases(self) -> None:
        res = [self.to_phrase()]
        if self.pos in CENTER_POS:
            for w in self.left_decorators:
                if w.left_phrases is None:
                    w.compute_left_phrases()
                res = (
                    [Phrase.plus(w.center_phrase, res[0])]
                    if w.right_decorators
                    else [Phrase.plus(p, res[0]) for p in w.left_phrases]
                ) + res
        self.left_phrases = res

    def compute_right_phrases(self) -> None:
        res = [self.to_phrase()]
        if self.pos in CENTER_POS:
            for w in self.right_decorators:
                if w.right_phrases is None:
                    w.compute_right_phrases()
                res = res + (
                    [Phrase.plus(res[-1], w.center_phrase)]
                    if w.left_decorators
                    else [Phrase.plus(res[-1], p) for p in w.right_phrases]
                )
        self.right_phrases = res
