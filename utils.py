"""
@author: yuan.shao
"""
import html
import re
from time import time
from typing import Any, List


MP_WEBSITE = 'https://www.mountainproject.com'

STATES = [
    '105905173/alabama', '105909311/alaska', '105708962/arizona',
    '105901027/arkansas', '105708959/california', '105708956/colorado',
    '105806977/connecticut', '106861605/delaware', '111721391/florida',
    '105897947/georgia', '106316122/hawaii', '105708958/idaho',
    '105911816/illinois', '112389571/indiana', '106092653/iowa',
    '107235316/kansas', '105868674/kentucky', '116720343/louisiana',
    '105948977/maine', '106029417/maryland', '105908062/massachusetts',
    '106113246/michigan', '105812481/minnesota', '108307056/mississippi',
    '105899020/missouri', '105907492/montana', '116096758/nebraska',
    '105708961/nevada', '105872225/new-hampshire', '106374428/new-jersey',
    '105708964/new-mexico', '105800424/new-york', '105873282/north-carolina',
    '106598130/north-dakota', '105994953/ohio', '105854466/oklahoma',
    '105708965/oregon', '105913279/pennsylvania', '106842810/rhode-island',
    '107638915/south-carolina', '105708963/south-dakota',
    '105887760/tennessee', '105835804/texas', '105708957/utah',
    '105891603/vermont', '105852400/virginia', '105708966/washington',
    '105855459/west-virginia', '105708968/wisconsin', '105708960/wyoming',
    '105881369/canada', '105910759/mexico',
]

TRIVIAL_KEYWORDS = {
    '1st', '2nd', '3rd', '4th', '5th', 'able', 'anchor', 'appropriate', 'area',
    'ascent', 'available', 'back', 'backside', 'bad', 'base', 'belay',
    'belayer', 'big', 'bit', 'bolt', 'book', 'boulder', 'buddy', 'car',
    'center', 'class', 'climb', 'climber', "climber 's", 'climbing', 'comment',
    'couple', 'crag', 'credit', 'day', 'de', 'de la', 'description',
    'different', 'double', 'du', 'east', 'end', 'enough', 'et', 'experience',
    'fa', 'fact', 'few', 'ffa', 'fifth', 'fine', 'first', 'five', 'folk',
    'foot', 'four', 'fourth', 'front', 'ft', 'full', 'girl', 'good', 'great',
    'ground', 'guy', 'half', 'hand', 'hand side', 'head', 'help', 'hold',
    'hour', 'idea', 'imho', 'in', 'inch', 'info', 'ish', 'issue', 'key', 'l.',
    'la', 'large', 'last', 'le', 'least', 'left', 'less', 'lh', 'lhs', 'line',
    'little', 'lol', 'lot', 'm rope', 'm.', 'main', 'man', 'many', 'medium',
    'meter', 'meter rope', 'method', 'mid', 'middle', 'mile', 'mini', 'minute',
    'more', 'most', 'move', 'much', 'name', 'new', 'next', 'nice', 'no',
    'north', 'not sure', 'number', 'old', 'one', 'only', 'open', 'opinion',
    'option', 'other', 'out', 'own', 'page', 'pair', 'part', 'partner',
    'party', 'path', 'people', 'percentage', 'piece', 'pitch', 'pitch #',
    'place', 'plenty', 'point', 'portion', 'possible', 'pour', 'problem', 'r.',
    'range', 'real', 'reason', 'regard', 'responsible', 'rh', 'rhs', 'right',
    'rock', 'rope', 'route', 'run', 'same', 'second', 'section', 'sector',
    'self', 'series', 'set', 'several', 'side', 'single', 'size', 'sized',
    'small', 'source', 'south', 'star', 'start', 'story', 'stuff', 'sur',
    'sure', 'system', 'team', 'thank', 'thing', 'third', 'three', 'tier',
    'time', 'today', 'tomorrow', 'top', 'two', 'un', 'une', 'up', 'us',
    'useful', 'user', 'voie', 'w/', 'w/o', 'wall', 'way', 'well', 'west',
    'whole', 'work', 'worth', 'year', 'yesterday',
}

SPECIAL_CHARS = {
    '\\xc2\\x92': '',
    '\\xc2\\x93': '',
    '\\xc2\\x94': '',
    '\\xc2\\xa1': '??',
    '\\xc2\\xb0': '??',
    '\\xc3\\x80': '??',
    '\\xc3\\x81': '??',
    '\\xc3\\x82': '??',
    '\\xc3\\x83': '??',
    '\\xc3\\x84': '??',
    '\\xc3\\x85': '??',
    '\\xc3\\x86': '??',
    '\\xc3\\x87': '??',
    '\\xc3\\x88': '??',
    '\\xc3\\x89': '??',
    '\\xc3\\x8a': '??',
    '\\xc3\\x8b': '??',
    '\\xc3\\x8c': '??',
    '\\xc3\\x8d': '??',
    '\\xc3\\x8e': '??',
    '\\xc3\\x8f': '??',
    '\\xc3\\x91': '??',
    '\\xc3\\x92': '??',
    '\\xc3\\x93': '??',
    '\\xc3\\x94': '??',
    '\\xc3\\x95': '??',
    '\\xc3\\x96': '??',
    '\\xc3\\x99': '??',
    '\\xc3\\x9a': '??',
    '\\xc3\\x9b': '??',
    '\\xc3\\x9c': '??',
    '\\xc3\\xa0': '??',
    '\\xc3\\xa1': '??',
    '\\xc3\\xa2': '??',
    '\\xc3\\xa3': '??',
    '\\xc3\\xa4': '??',
    '\\xc3\\xa5': '??',
    '\\xc3\\xa6': '??',
    '\\xc3\\xa7': '??',
    '\\xc3\\xa8': '??',
    '\\xc3\\xa9': '??',
    '\\xc3\\xaa': '??',
    '\\xc3\\xab': '??',
    '\\xc3\\xac': '??',
    '\\xc3\\xad': '??',
    '\\xc3\\xae': '??',
    '\\xc3\\xaf': '??',
    '\\xc3\\xb1': '??',
    '\\xc3\\xb2': '??',
    '\\xc3\\xb3': '??',
    '\\xc3\\xb4': '??',
    '\\xc3\\xb5': '??',
    '\\xc3\\xb6': '??',
    '\\xc3\\xb9': '??',
    '\\xc3\\xba': '??',
    '\\xc3\\xbb': '??',
    '\\xc3\\xbc': '??',
    '\\xc5\\x8d': '??',
    '\\xe2\\x80\\x93': '???',
    '\\xe2\\x80\\x99': '\'',
    '\\xe2\\x80\\x9c': '"',
    '\\xe2\\x80\\x9d': '"',
}


def replace_special_chars(s: str) -> str:
    s = html.unescape(s)
    for a, b in SPECIAL_CHARS.items():
        s = s.replace(a, b)
    return ' '.join(s.split())


def clean_text(t: str) -> List[str]:
    """
    Clean a html string by replacing the special characters and removing the
    links and html tags in it. Return the list of paragraphs.
    """
    t = replace_special_chars(t)
    return [
        clean_links_and_tags(p.strip()) for p in t.split('<br>') if p.strip()
    ]


def clean_links_and_tags(p: str) -> str:
    links = re.findall(
        r'(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s'
        r'()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s('
        r')<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?????????????????]))',
        p,
    )
    for lk in links:
        p = p.replace(lk[0], ' ')
    tags = re.findall(r'<.*?>', p)
    for a in tags:
        p = p.replace(a, ' ')
    return ' '.join(
        p.replace('\\', '').replace('(', ' (').replace(')', ') ').split()
    )


def dedupe(lst: List[str]) -> List[str]:
    """
    Return strings in a list which are not substrings of any other string in
    the list.
    """
    idx = set()
    for i, x in enumerate(lst):
        for j, y in enumerate(lst):
            if (x == y and i < j) or (x != y and x in y):
                idx.add(i)
                break
    return [x for i, x in enumerate(lst) if i not in idx]


def flatten(lst: List[List[Any]]) -> List[Any]:
    """
    Flatten a list of lists.
    """
    return [x for s in lst for x in s]


def join_around(
    words: List[str], w: str, to_left: bool = True, to_right: bool = True,
) -> List[str]:
    """
    Join a list of words around a certain word w. For example:
    join_around(['a', 'b', '/', 'c', 'd'], '/') == ['a', 'b/c', 'd'].
    join_around(['a', 'b', '/', 'c', 'd'], '/', to_left=False)
        == ['a', 'b', '/c', 'd'].
    join_around(['a', 'b', '/', 'c', 'd'], '/', to_right=False)
        == ['a', 'b/', 'c', 'd'].
    """
    if not (to_left or to_right):
        return words
    res = []
    curr, joining = '', False
    for x in words:
        if (x == w and to_left) or (joining and to_right):
            curr += x
        else:
            if curr:
                res.append(curr)
            curr = x
        joining = (x == w)
    if curr:
        res.append(curr)
    return res


def elapsed(start_time: float) -> str:
    return format_duration_secs(time() - start_time)


def remaining(start_time: float, done_tasks: int, total_tasks: int) -> str:
    return format_duration_secs(
        (time() - start_time) * (total_tasks - done_tasks) / done_tasks
    )


def format_duration_secs(duration: float) -> str:
    if not duration > 0:
        return '0s'
    hour = int(duration / 3600)
    if hour > 0:
        h = f'{hour}h'
    else:
        h = ''
    duration -= 3600 * hour
    minute = int(duration / 60)
    if hour > 0:
        m = f'{str(minute).zfill(2)}m'
    elif minute > 0:
        m = f'{minute}m'
    else:
        m = ''
    duration -= 60 * minute
    second = int(duration)
    if hour > 0 or minute > 0:
        s = f'{str(second).zfill(2)}s'
    else:
        s = f'{second}s'
    return f'{h}{m}{s}'
