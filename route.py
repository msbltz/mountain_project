"""
@author: yuan.shao
"""
from __future__ import annotations

import getopt
import re
import sys
from typing import Any, Union
from typing import Dict, List

import requests

from text_analyzer import SMALL, TextAnalyzer
from utils import (
    clean_text, dedupe, flatten, MP_WEBSITE, replace_special_chars,
)


class Route:
    TOP_KEYWORDS = 10
    TRIVIAL_WORDS = {
        '1st', '2nd', 'able', 'anchor', 'area', 'ascent', 'available', 'base',
        'belay', 'belayer', 'big', 'bit', 'book', 'boulder', 'buddy', 'car',
        'climb', 'climber', 'climbing', 'credit', 'day', 'description', 'end',
        'enough', 'experience', 'fa', 'fact', 'few', 'ffa', 'first', 'folk',
        'foot', 'girl', 'good', 'ground', 'guy', 'hand', 'head', 'help',
        'hold', 'idea', 'imho', 'in', 'ish', 'issue', 'key', 'l.', 'large',
        'least', 'left', 'lh', 'lhs', 'line', 'lol', 'lot', 'method', 'middle',
        'more', 'most', 'move', 'name', 'no', 'number', 'one', 'open',
        'opinion', 'option', 'other', 'out', 'own', 'partner', 'people',
        'percentage', 'pitch', 'pitch #', 'place', 'point', 'possible',
        'problem', 'r.', 'reason', 'regard', 'responsible', 'rh', 'rhs',
        'right', 'rock', 'rope', 'route', 'same', 'second', 'section', 'self',
        'set', 'side', 'small', 'source', 'story', 'stuff', 'sure', 'team',
        'thank', 'thing', 'three', 'time', 'today', 'tomorrow', 'top', 'two',
        'up', 'us', 'useful', 'user', 'w/', 'w/o', 'wall', 'way', 'well',
        'worth', 'year', 'yesterday',
    }
    TYPES = {
        'Sport', 'Trad', 'Aid', 'TR', 'Boulder', 'Alpine', 'Ice', 'Snow',
        'Mixed',
    }
    
    def __init__(
        self, route_id: str, route_name: str, display_name: str,
        location_chain: List[str], location_name_chain: List[str],
        grade: List[str], types: List[str], height: int, pitches: int,
        commitment: str, scores: Dict[int, int], comments: List[str],
        descriptions: List[str], keywords: List[str],
        keyword_counts: List[Union[str, int]],
    ) -> None:
        self.id = route_id
        self.name = route_name
        self.link = self.get_link(route_id, route_name)
        self.display_name = display_name
        self.location_chain = location_chain
        self.location_name_chain = location_name_chain
        self.grade = grade
        self.types = types
        self.height = height
        self.pitches = pitches
        self.commitment = commitment
        self.scores = scores
        self.comments = comments
        self.descriptions = descriptions
        self.keywords = keywords
        self.keyword_counts = keyword_counts
    
    def to_map(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'link': self.link,
            'display_name': self.display_name,
            'location_chain': self.location_chain,
            'location_name_chain': self.location_name_chain,
            'grade': self.grade,
            'types': self.types,
            'height': self.height,
            'pitches': self.pitches,
            'commitment': self.commitment,
            'score_0': self.scores[0],
            'score_1': self.scores[1],
            'score_2': self.scores[2],
            'score_3': self.scores[3],
            'score_4': self.scores[4],
            'avg_score': self.avg_score(),
            'votes': self.votes(),
            'keywords': self.keywords,
            'keyword_counts': self.keyword_counts,
        }

    def print(self) -> None:
        print(
            f'display_name = {self.display_name}, '
            f'location_name_chain = {self.location_name_chain}, '
            f'link = {self.link}'
        )
        print(
            f'grade = {self.grade}, types = {self.types}, '
            f'height = {self.height}m, pitches = {self.pitches}'
        )
        print(
            f'score = {self.scores}, '
            f'avg_score = {self.avg_score():.4f}, votes = {self.votes()}'
        )
        print(f'keywords = {self.keywords}')
        if self.keywords:
            kc = ' | '.join([
                f'{self.keyword_counts[2 * i]}: '
                f'{self.keyword_counts[2 * i + 1]}'
                for i in range(len(self.keyword_counts) // 2)
            ])
            print(f"keyword_counts = {kc}")

    @classmethod
    def get_link(cls, route_id: str, route_name: str) -> str:
        return f'{MP_WEBSITE}/route/{route_id}/{route_name}'

    @classmethod
    def read_from_web(
        cls,
        route_id: str,
        route_name: str,
        location_chain: List[str] = None,
        location_name_chain: List[str] = None,
        text_analyzer: TextAnalyzer = None,
        print_details: bool = False,
    ) -> Route:
        """
        Read the details of a route. Construct and return a Route object.
            - Read the route page and parse grade, types, height, number of
            pitches, etc.
            - Read the stats page and parse star ratings.
            - Read the comments page, then analyze the comments together with
            route descriptions on the route page to generate top keywords.
        """
        route_link = cls.get_link(route_id, route_name)
        response = requests.get(route_link)
        html = str(response.content)
        
        display_name = ''
        display_name_read = re.findall(r'<h1>\\n(.*?)\\n', html)
        if len(display_name_read) > 0:
            display_name = replace_special_chars(display_name_read[0].strip())
        
        grade = []
        grade_read = re.findall(
            r'<span class=\\\'rateYDS\\\'>([\w\s\d\.\+\-\/]+)<a href', html,
        )
        if len(grade_read) > 0:
            grade.extend([g.strip() for g in grade_read])
        else:
            other_grade_read = re.findall(
                r'<h2 class="inline-block mr-2">([\w\s\d\.\+\-\/]+)</h2>',
                html,
            )
            if len(other_grade_read) > 0:
                grade.extend([g.strip() for g in other_grade_read])
        
        types_set = set()
        height = 0
        pitches = 1
        commitment = ''
        info = re.findall(
            r'<td>Type:</td>\\n\s*<td>\\n\s*([\w,\s\(\)]+)\\n', html,
        )
        if len(info) > 0:
            for i in info[0].split(','):
                i = i.strip()
                if not i:
                    continue
                if i in cls.TYPES:
                    types_set.add(i)
                    continue
                height_m_read = re.findall(r'\d+ ft \((\d+) m\)', i)
                if len(height_m_read) > 0:
                    height = int(height_m_read[0])
                    continue
                height_ft_read = re.findall(r'(\d+) ft', i)
                if len(height_ft_read) > 0:
                    height = int(0.3048 * float(height_ft_read[0]))
                    continue
                pitches_read = re.findall(r'(\d+) pitch', i)
                if len(pitches_read) > 0:
                    pitches = int(pitches_read[0])
                    continue
                commitment_read = re.findall(r'Grade ([IV]+)', i)
                if len(commitment_read) > 0:
                    commitment = commitment_read[0]
                    continue
                print(f'!!! UNRECOGNIZED INFO: {i}, LINK = {route_link}')
        types = sorted(types_set)
        
        descriptions_read = re.findall(
            r'</h2>\\n\s*?<div class="fr-view">(.*?)</div>\\n', html,
        )
        descriptions = dedupe(
            flatten([clean_text(d) for d in descriptions_read])
        )
        
        stats_link = f'{MP_WEBSITE}/route/stats/{route_id}/{route_name}'
        response = requests.get(stats_link)
        html = str(response.content)
        
        scores = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
        ratings = html.split('!--START-STARS-Climb')
        for r in ratings[1:]:
            s = r.count('/img/stars/starBlue.svg')
            if s > 0:
                scores[s] += 1
                continue
            b = r.count('/img/stars/bombBlue.svg')
            if b > 0:
                scores[0] += 1
        
        comments_link = f'{MP_WEBSITE}/Climb-Route/{route_id}/comments'
        response = requests.get(comments_link)
        html = str(response.content)
        comments_read = re.findall(
            r'<span id="\d+-full".*?>(.*?)</span>', html,
        )
        comments = dedupe(flatten([clean_text(c) for c in comments_read]))

        if location_chain is None:
            location_chain = []
        if location_name_chain is None:
            location_name_chain = []

        keywords, keyword_counts = [], []
        if text_analyzer is not None:
            raw_keywords, counts = text_analyzer.generate_keywords(
                texts=comments + descriptions, print_details=print_details,
            )
            own_name = ' '.join(route_name.split('-'))
            location_names = [
                ' '.join(name.split('-')) for name in location_name_chain
            ]
            raw_keywords = [
                p for p in raw_keywords
                if (
                    p not in cls.TRIVIAL_WORDS
                    and p not in own_name
                    and not any([(p in name) for name in location_names])
                    and len(p) > 1
                )
            ]
            keyword_counts = flatten([[p, counts[p]] for p in raw_keywords])
            for word in raw_keywords:
                if any([(word in w) for w in keywords]):
                    continue
                keywords.append(word)
                if len(keywords) == cls.TOP_KEYWORDS:
                    break

        r = cls(
            route_id, route_name, display_name, location_chain,
            location_name_chain, grade, types, height, pitches, commitment,
            scores, comments, descriptions, keywords, keyword_counts,
        )
        if print_details:
            r.print()
        return r
    
    def votes(self) -> int:
        return sum(self.scores.values())
    
    def avg_score(self) -> float:
        if self.votes() == 0:
            return float('nan')
        return sum([s * n for s, n in self.scores.items()]) / self.votes()


def main():
    short_options = 'l:'
    long_options = ['link=']
    try:
        args, _ = getopt.getopt(sys.argv[1:], short_options, long_options)
    except getopt.error as err:
        print(str(err))
        sys.exit(2)

    text_analyzer = TextAnalyzer(SMALL)
    for a, v in args:
        if a in ('-l', '--link'):
            if v[-1] == '/':
                v = v[:-1]
            s = v.split('/')
            Route.read_from_web(
                route_id=s[-2],
                route_name=s[-1],
                text_analyzer=text_analyzer,
                print_details=True,
            )


if __name__ == '__main__':
    main()
