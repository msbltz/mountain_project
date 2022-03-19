"""
@author: yuan.shao
"""
import re
from copy import deepcopy
from typing import Dict, List, Tuple, Union

import requests

from utils import MP_WEBSITE, replace_special_chars


def read_an_area(
    area_id: str,
    area_name: str,
    location_chain: List[str],
) -> Tuple[
    Dict[str, Union[str, List[str]]],
    List[Tuple[str, str, List[str]]],
    List[Dict[str, Union[str, List[str]]]],
]:
    """
    Read the area page of the given area. Return the parsed information of this
    area, the list of other areas under this area, and the list of routes under
    this area.
    """
    next_areas = []
    routes = []
    
    response = requests.get(f'{MP_WEBSITE}/area/{area_id}/{area_name}')
    html = str(response.content)
    
    display_name = ''
    display_name_read = re.findall(r'<h1>\\n(.*?)\\n', html)
    if display_name_read:
        display_name = replace_special_chars(display_name_read[0].strip())
    
    gps = re.findall(r'maps\?q=([\d\.]+),([\d\.-]+)', html)
    latitude = ''
    longitude = ''
    if gps:
        latitude = gps[0][0]
        longitude = gps[0][1]
    
    this_area = build_area_map(
        area_id, area_name, display_name, latitude, longitude, location_chain,
    )

    # Read routes or areas under this area.
    s = html[html.find('Show all routes'):html.find('Show All Routes')]
    rts = set(re.findall(rf'<a href="{MP_WEBSITE}/route/(\d+)/([\w-]+)">', s))
    rts_no_name = set(re.findall(rf'<a href="{MP_WEBSITE}/route/(\d+)">', s))
    for r in rts_no_name:
        rts.add((r, ''))
    ars = set(re.findall(rf'<a href="{MP_WEBSITE}/area/(\d+)/([\w-]+)">', s))
    if rts:
        for r in rts:
            routes.append(build_route_map(r[0], r[1], location_chain))
    elif ars:
        for a in ars:
            new_chain = deepcopy(location_chain)
            new_chain.append(a[0])
            next_areas.append((a[0], a[1], new_chain))
    return this_area, next_areas, routes


def build_area_map(
    area_id: str,
    area_name: str,
    display_name: str,
    latitude: str,
    longitude: str,
    location_chain: List[str],
) -> Dict[str, Union[str, List[str]]]:
    return {
        'area_id': area_id,
        'area_name': area_name,
        'display_name': display_name,
        'latitude': latitude,
        'longitude': longitude,
        'location_chain': location_chain,
    }


def build_route_map(
    route_id: str,
    route_name: str,
    location_chain: List[str],
) -> Dict[str, Union[str, List[str]]]:
    return {
        'route_id': route_id,
        'route_name': route_name,
        'location_chain': location_chain,
    }
