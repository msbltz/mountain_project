"""
@author: yuan.shao
"""
from typing import Dict, List, Tuple

import spacy
from spacy.lookups import load_lookups

from utils import join_around

SMALL = 'en_core_web_sm'
MEDIUM = 'en_core_web_md'
LARGE = 'en_core_web_lg'


class TextAnalyzer:
    def __init__(self, model: str):
        self.nlp = spacy.load(model)
        self.prob = (
            load_lookups('en', ['lexeme_prob']).get_table('lexeme_prob')
        )
        self.min_prob = min(self.prob.values())

    def generate_keywords(
        self, texts: List[str],
    ) -> Tuple[List[str], Dict[str, int]]:
        counts = dict()
        for text in texts:
            phrase_tokens = []
            text_tokens = self.nlp(text)
            for i, token in enumerate(text_tokens):
                lemma, pos, dep = token.lemma_.lower(), token.pos_, token.dep_
                next_lemma = (
                    text_tokens[i + 1].lemma_.lower()
                    if i < len(text_tokens) - 1
                    else ''
                )
                # Construct a phrase from words.
                if (
                    next_lemma in {'/'}
                    or pos in {'ADJ', 'NOUN', 'NUM', 'PROPN', 'SYM', 'X'}
                    or dep in {'amod', 'neg', 'nmod', 'nummod'}
                ):
                    phrase_tokens.append((lemma, pos, dep))
                    if (
                        next_lemma in {'/'}
                        or dep in {
                            'amod', 'compound', 'det', 'neg', 'nmod', 'nummod',
                            'prep', 'punct', 'quantmod', 'ROOT',
                        }
                    ):
                        continue
                # Update phrase counts.
                self.count_phrase(phrase_tokens, counts)
                phrase_tokens = []
            self.count_phrase(phrase_tokens, counts)
        counts = {p: ct for p, ct in counts.items() if ct > 1}
        keywords = list(counts.keys())
        keywords.sort(
            key=lambda p: (counts[p], -self.phrase_prob(p)),
            reverse=True,
        )
        return keywords, counts

    @staticmethod
    def count_phrase(
        phrase_tokens: List[Tuple[str, str, str]], counts: Dict[str, int],
    ) -> None:
        if not phrase_tokens:
            return
        if len(phrase_tokens) == 1:
            _, pos, dep = phrase_tokens[0]
            if pos in {'NUM', 'SYM'} or dep in {'neg'}:
                return
        words = [w for w, _, _ in phrase_tokens]

        # Deal with the dot at the end of the last word.
        # Remove: '60 m.', '5.10r.', 't&t.'.
        # Do not remove: 's.o.s.', 'ph.d.', 'hank jr.'.
        last_word = words[-1]
        dots = []
        for i, c in enumerate(last_word):
            if (
                c == '.'
                and (i == 0 or last_word[i - 1].isalpha())
                and (i <= 1 or (not last_word[i - 2].isalpha()))
            ):
                dots.append(i)
        if len(dots) == 1 and dots[0] == len(last_word) - 1:
            last_word = last_word[:-1]
        words[-1] = last_word

        # Join the words around '/', '+', '#', '.' and '°'.
        # Use cases: ['finger', '/', 'hand'], ['5.9', '+', 'crack'],
        # ['big', '#', '5', 'cam'], ['ft', '.', 'platform'], ['n44', '°'].
        words = join_around(words, '/')
        words = join_around(words, '+', to_right=False)
        words = join_around(words, '#', to_left=False)
        words = join_around(words, '.', to_right=False)
        words = join_around(words, '°', to_right=False)

        phrase = ' '.join(words)
        if phrase not in counts:
            counts[phrase] = 0
        counts[phrase] += 1

    def phrase_prob(self, phrase: str) -> float:
        return min([
            self.prob.get(word, self.min_prob - 1)
            for word in phrase.split(' ')
        ])
