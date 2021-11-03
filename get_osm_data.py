import json
import requests

# These id's grabbed manually from Overpass Turbo
cities = {
    'Portland': 3600186579,
    'Seattle': 3600237385,
    'San Francisco': 3600111968
}

# Overpass QL
# Gets OSM nodes (points) and ways (sets of points, e.g. shape of building),
# Matches 'tourism', 'leisure' tags against regex values, in specified area
# (node(w) gets nodes associated with previous way, >; gets children of prev).
#
# This query aims to collect most points of interest for a tourist, as well as
# public places of interest across a city. I'm excluding places like bars/clubs/etc.
# Subjectively, it has good distribution over Portland, OR.
query = '''
[out:json];
(
    node[tourism~"aquarium|artwork|attraction|gallery|museum|viewpoint"](area:{0});
    way[tourism~"aquarium|artwork|attraction|gallery|museum|viewpoint"](area:{0});
    node(w);
    relation[tourism~"aquarium|artwork|attraction|gallery|museum|viewpoint"](area:{0});
    >;

    node[leisure~"garden|nature_reserve|park|stadium"](area:{0});
    way[leisure~"garden|nature_reserve|park|stadium"](area:{0});
    node(w);
    relation[leisure~"garden|nature_reserve|park|stadium"](area:{0});
    >;
);
out;
'''

for city, osm_id in cities.items():
    r = requests.get('https://overpass-api.de/api/interpreter', { 'data': query.format(osm_id) })

    print('{} has {} items'.format(city, len(r.json()['elements'])))

    with open('{}.json'.format(city.lower().replace(' ', '_')), 'w') as f:
        json.dump(r.json(), f, indent=2, sort_keys=True)
