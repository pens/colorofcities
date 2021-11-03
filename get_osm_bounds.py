import json
import requests

# These id's grabbed manually from Overpass Turbo
cities = {
    'Portland': 186579,
    'Seattle': 237385,
    'San Francisco': 111968
}

# Overpass QL
query = '''
[out:json];
(
    relation({});
    way(r);
    node(w);
);
out;
'''

for city, osm_id in cities.items():
    r = requests.get('https://overpass-api.de/api/interpreter', { 'data': query.format(osm_id) })

    with open('{}_bounds.json'.format(city.lower().replace(' ', '_')), 'w') as f:
        json.dump(r.json()['elements'], f, indent=2, sort_keys=True)
