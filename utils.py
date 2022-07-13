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

SPECIAL_CHARS = {
    '\\xc2\\x92': '',
    '\\xc2\\x93': '',
    '\\xc2\\x94': '',
    '\\xc2\\xa1': '¡',
    '\\xc2\\xb0': '°',
    '\\xc3\\x80': 'À',
    '\\xc3\\x81': 'Á',
    '\\xc3\\x82': 'Â',
    '\\xc3\\x83': 'Ã',
    '\\xc3\\x84': 'Ä',
    '\\xc3\\x85': 'Å',
    '\\xc3\\x86': 'Æ',
    '\\xc3\\x87': 'Ç',
    '\\xc3\\x88': 'È',
    '\\xc3\\x89': 'É',
    '\\xc3\\x8a': 'Ê',
    '\\xc3\\x8b': 'Ë',
    '\\xc3\\x8c': 'Ì',
    '\\xc3\\x8d': 'Í',
    '\\xc3\\x8e': 'Î',
    '\\xc3\\x8f': 'Ï',
    '\\xc3\\x91': 'Ñ',
    '\\xc3\\x92': 'Ò',
    '\\xc3\\x93': 'Ó',
    '\\xc3\\x94': 'Ô',
    '\\xc3\\x95': 'Õ',
    '\\xc3\\x96': 'Ö',
    '\\xc3\\x99': 'Ù',
    '\\xc3\\x9a': 'Ú',
    '\\xc3\\x9b': 'Û',
    '\\xc3\\x9c': 'Ü',
    '\\xc3\\xa0': 'à',
    '\\xc3\\xa1': 'á',
    '\\xc3\\xa2': 'â',
    '\\xc3\\xa3': 'ã',
    '\\xc3\\xa4': 'ä',
    '\\xc3\\xa5': 'å',
    '\\xc3\\xa6': 'æ',
    '\\xc3\\xa7': 'ç',
    '\\xc3\\xa8': 'è',
    '\\xc3\\xa9': 'é',
    '\\xc3\\xaa': 'ê',
    '\\xc3\\xab': 'ë',
    '\\xc3\\xac': 'ì',
    '\\xc3\\xad': 'í',
    '\\xc3\\xae': 'î',
    '\\xc3\\xaf': 'ï',
    '\\xc3\\xb1': 'ñ',
    '\\xc3\\xb2': 'ò',
    '\\xc3\\xb3': 'ó',
    '\\xc3\\xb4': 'ô',
    '\\xc3\\xb5': 'õ',
    '\\xc3\\xb6': 'ö',
    '\\xc3\\xb9': 'ù',
    '\\xc3\\xba': 'ú',
    '\\xc3\\xbb': 'û',
    '\\xc3\\xbc': 'ü',
    '\\xc5\\x8d': 'ō',
    '\\xe2\\x80\\x93': '–',
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
        r')<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’]))',
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
    s = list(set(lst))
    idx = set()
    for i, x in enumerate(s):
        for j, y in enumerate(s):
            if i == j:
                continue
            if x in y:
                idx.add(i)
                break
    return [x for i, x in enumerate(s) if i not in idx]


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
