"""
@author: yuan.shao
"""
from typing import Dict, List, Tuple

import spacy
from spacy.lookups import load_lookups

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

    def generate_keywords(self, texts: List[str]) -> List[str]:
        counts = dict()
        for text in texts:
            words = []
            for token in self.nlp(text):
                # Construct a phrase from words.
                if (
                        token.pos_ in {'ADJ', 'PROPN', 'NOUN', 'NUM', 'SYM'}
                        or token.dep_ in {'amod', 'neg', 'nmod', 'nummod'}
                ):
                    words.append(
                        (token.lemma_.lower(), token.pos_, token.dep_)
                    )
                    if token.dep_ in {
                        'amod', 'compound', 'det', 'neg', 'nmod', 'nummod',
                        'prep', 'punct', 'ROOT',
                    }:
                        continue
                # Update phrase counts.
                self.count_phrase(words, counts)
                words = []
            self.count_phrase(words, counts)
        keywords = [p for p, ct in counts.items() if ct > 1]
        keywords.sort(
            key=lambda p: (counts[p], -self.phrase_prob(p)),
            reverse=True,
        )
        return keywords

    @staticmethod
    def count_phrase(
        words: List[Tuple[str, str, str]], counts: Dict[str, int],
    ) -> None:
        if not words:
            return
        if (
            len(words) == 1
            and (words[0][1] in {'NUM', 'SYM'} or words[0][2] in {'neg'})
        ):
            return
        phrase = ' '.join([w for w, _, _ in words])
        if phrase not in counts:
            counts[phrase] = 0
        counts[phrase] += 1

    def phrase_prob(self, phrase: str) -> float:
        return min([
            self.prob.get(word, self.min_prob - 1)
            for word in phrase.split(' ')
        ])
