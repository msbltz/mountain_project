"""
@author: yuan.shao
"""
import os
import sys
from queue import Queue
from threading import Thread
from time import time

import pandas as pd
from requests.exceptions import RequestException

from area import read_an_area
from route import Route
from text_analyzer import SMALL, TextAnalyzer
from utils import elapsed, remaining, STATES

MAX_RETRY = 3
NUM_OF_THREADS = 100
CHUNK = 1000

TEXT_ANALYZER = TextAnalyzer(SMALL)

SCORE_THRESHOLD = 3.0
VOTES_THRESHOLD = 10

OUTPUT_DIR = 'output'
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

kill_thread = False


# === Read all areas and routes ===============================================
start_time = time()
areas = dict()
routes = []
areas_file = f'{OUTPUT_DIR}/areas.pkl'
routes_file = f'{OUTPUT_DIR}/routes.pkl'
if os.path.exists(areas_file) and os.path.exists(routes_file):
    areas_df = pd.read_pickle(areas_file)
    areas = {row['area_id']: row.to_dict() for _, row in areas_df.iterrows()}
    routes_df = pd.read_pickle(routes_file)
    routes = [row.to_dict() for _, row in routes_df.iterrows()]
    print(f'Areas and routes loaded from {areas_file} and {routes_file}')
else:
    def fetch_areas_and_routes():
        while not kill_thread:
            area_id, area_name, location_chain = q.get()
            retry = 1
            success = False
            while retry <= MAX_RETRY:
                try:
                    this_area, next_areas, rts = read_an_area(
                        area_id=area_id,
                        area_name=area_name,
                        location_chain=location_chain,
                    )
                    areas[area_id] = this_area
                    new_to_read.extend(next_areas)
                    routes.extend(rts)
                    success = True
                    break
                except RequestException:
                    retry += 1
                    continue
            if not success:
                print(f'Fail to read area {area_id}/{area_name}')
            q.task_done()
    to_read = []
    for state in STATES:
        s = state.split('/')
        to_read.append((s[0], s[1], [s[0]]))
    q = Queue()
    for _ in range(NUM_OF_THREADS):
        th = Thread(target=fetch_areas_and_routes)
        th.daemon = True
        th.start()
    while to_read:
        print(
            f'Length of area queue = {len(to_read)}. Reading '
            f'{min(CHUNK, len(to_read))} areas'
        )
        read_start_time = time()
        new_to_read = []
        try:
            for r in to_read[:CHUNK]:
                if r[0] in areas:
                    print(f'!!! REPEATED AREA: {areas[r[0]]}')
                    continue
                q.put(r)
            q.join()
        except KeyboardInterrupt:
            kill_thread = True
            sys.exit(1)
        to_read = to_read[CHUNK:] + new_to_read
        print(
            f'Done in {elapsed(read_start_time)}. {len(new_to_read)} new '
            f'areas added to area queue. Elapsed {elapsed(start_time)}'
        )
    areas_df = pd.DataFrame(list(areas.values())).reset_index(drop=True)
    areas_df.to_pickle(areas_file)
    print(f'Areas written to {areas_file}')
    routes_df = pd.DataFrame(routes).reset_index(drop=True)
    routes_df.to_pickle(routes_file)
    print(f'Routes written to {routes_file}')
print(
    f'Total number of areas = {len(areas)}, number of routes = {len(routes)}'
)


# === Read route details ======================================================
start_time = time()
route_details = []
route_details_file = f'{OUTPUT_DIR}/route_details.pkl'
df = pd.DataFrame()
start_idx = 0
if os.path.exists(route_details_file):
    df = pd.read_pickle(route_details_file)
    route_details = [row.to_dict() for _, row in df.iterrows()]
    start_idx = len(route_details)
    print(f'Load {len(route_details)} route details from {route_details_file}')
if start_idx < len(routes):
    def fetch_route_details():
        while not kill_thread:
            task = q.get()
            retry = 1
            success = False
            while retry <= MAX_RETRY:
                try:
                    route = Route.read_from_web(
                        route_id=task['route_id'],
                        route_name=task['route_name'],
                        location_chain=task['location_chain'],
                        location_name_chain=[
                            areas.get(a, dict()).get('area_name', '')
                            for a in task['location_chain']
                        ],
                        text_analyzer=TEXT_ANALYZER,
                    )
                    route_details.append(route.to_map())
                    success = True
                    break
                except RequestException:
                    retry += 1
                    continue
            if not success:
                print(
                    f"Fail to read details of route "
                    f"{task['route_id']}/{task['route_name']}"
                )
            q.task_done()
    q = Queue()
    for _ in range(NUM_OF_THREADS):
        th = Thread(target=fetch_route_details)
        th.daemon = True
        th.start()
    for j in range(start_idx, len(routes), CHUNK):
        print(
            f'Reading details of routes {j + 1} to '
            f'{min(j + CHUNK, len(routes))}'
        )
        read_start_time = time()
        try:
            for r in routes[j:(j + CHUNK)]:
                q.put(r)
            q.join()
        except KeyboardInterrupt:
            kill_thread = True
            sys.exit(1)
        dur = elapsed(read_start_time)
        ela = elapsed(start_time)
        rem = remaining(
            start_time=start_time,
            done_tasks=min(j + CHUNK, len(routes)) - start_idx,
            total_tasks=len(routes) - start_idx,
        )
        print(f'Done in {dur}. Elapsed {ela}. Remaining {rem}')
        df = pd.DataFrame(route_details).reset_index(drop=True)
        df.to_pickle(route_details_file)


# === Output good routes ======================================================
df = df[
    df.apply(
        lambda row: (
            row['avg_score'] >= SCORE_THRESHOLD
            and row['votes'] >= VOTES_THRESHOLD
            and set(row['types']).issubset(
                {'Sport', 'Trad', 'Boulder', 'Aid', 'Alpine', 'TR'}
            )
            and len(row['location_chain']) > 0
        ),
        axis=1,
    )
]
print(f'Total {len(df)} good routes found')

output_df = pd.DataFrame()
output_df['name'] = df['display_name']
output_df['location'] = df['location_chain'].map(
    lambda c: ' > '.join(
        [areas.get(a, dict()).get('display_name', '') for a in c]
    )
)
output_df['latitude'] = df['location_chain'].map(
    lambda c: areas.get(c[-1], dict()).get('latitude', '')
)
output_df['longitude'] = df['location_chain'].map(
    lambda c: areas.get(c[-1], dict()).get('longitude', '')
)
output_df['score'] = df['avg_score']
output_df['votes'] = df['votes']
output_df['types'] = df['types'].map(lambda t: ' / '.join(t))
output_df['grade'] = df['grade'].map(lambda g: ' / '.join(g))
output_df['height'] = df['height'].map(lambda h: str(h) if h > 0 else '')
output_df['pitches'] = df['pitches'].map(lambda p: str(p) if p > 1 else '')
output_df['keywords'] = df['keywords'].map(lambda k: ' | '.join(k))
output_df['link'] = df['link']
output_df = output_df.sort_values(
    by=['score', 'votes', 'name'], ascending=[False, False, True],
)

boulder_df = output_df[
    output_df.apply(
        lambda row: 'Boulder' in row['types'] and row['pitches'] == '',
        axis=1,
    )
].reset_index(drop=True)
boulder_df.to_csv(f'{OUTPUT_DIR}/boulder_routes.csv')
rope_df = output_df[output_df['types'] != 'Boulder'].reset_index(drop=True)
rope_df.to_csv(f'{OUTPUT_DIR}/rope_routes.csv')
print(f'Output {len(boulder_df)} boulder routes, {len(rope_df)} rope routes')
