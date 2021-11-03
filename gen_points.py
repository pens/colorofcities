import json
import overpy

cities = ['Portland', 'Seattle', 'San Francisco']

def make_name(obj):
    if 'name' in obj.tags:
        tmp = obj.tags['name']
        for c in '<>:"/\\|?*':
            tmp = tmp.replace(c, '_')
        return tmp
    else:
        return '{}'.format(obj.id)

for city in cities:
    data = None
    with open('{}.json'.format(city.lower().replace(' ', '_')), 'r') as f:
        data = f.read()

    api = overpy.Overpass()
    result = api.parse_json(data)

    pois = {}
    visited_nodes = set()

    # Ways are built from multiple nodes, so we must convert to single points
    for way in result.ways:

        # Choose average of child nodes' lat/lon for way's lat/lon
        lat = 0
        lon = 0

        for node in way.nodes:
            lat += float(node.lat)
            lon += float(node.lon)

            # Child nodes of ways aren't their own points of interest
            visited_nodes.add(node.id)
        
        lat /= len(way.nodes)
        lon /= len(way.nodes)

        name = make_name(way)

        pois[name] = {
            'id': way.id,
            'lat': lat,
            'lon': lon
        }

        if way.tags:
            pois[name]['tags'] = way.tags

    # Single points in OSM
    for node in result.nodes:

        # Skip nodes that are children of ways
        if node.id in visited_nodes:
            continue
        
        name = make_name(node)

        pois[name] = {
            'id': node.id,
            'lat': float(node.lat),
            'lon': float(node.lon)
        }

        if node.tags:
            pois[name]['tags'] = node.tags

    # How many points of interest?
    print('{}: {} points of interest'.format(city, len(pois)))

    # JSON sorted & indented for readability / debugging
    with open('{}_points.json'.format(city.lower().replace(' ', '_')), 'w') as f:
        json.dump(pois, f, indent=2, sort_keys=True)