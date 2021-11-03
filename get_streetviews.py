import base64
import hashlib
import hmac
import json
import requests
import os
import time
from io import BytesIO
from PIL import Image

cities = ['Portland', 'Seattle', 'San Francisco']

api_key='API_KEY'
secret = 'SECRET'

assert api_key != 'API_KEY', 'API Key and Secret required.'

img_url='https://maps.googleapis.com/maps/api/streetview'
meta_url='https://maps.googleapis.com/maps/api/streetview/metadata'
req_s = 500

def send_request(url, params):
    req = requests.Request('GET', url, params=params)
    preq = req.prepare()

    dec_key = base64.urlsafe_b64decode(secret)
    sig = hmac.new(dec_key, str.encode(preq.path_url), hashlib.sha1)
    enc_sig = base64.urlsafe_b64encode(sig.digest())
    preq.prepare_url(req.url, params={**params, 'signature': enc_sig})

    s = requests.Session()
    return s.send(preq)

for city in cities:
    points = None
    with open('{}_points.json'.format(city.lower().replace(' ', '_')), 'r') as f:
        points = json.load(f)

    # For deduping streetviews
    panos = {}
    # Streetview & OSM metadata for output
    meta = {}

    # Collect & process metadata for panoramas (free)
    for name, data in points.items():
        params = {
            'location': '{},{}'.format(data['lat'], data['lon']),
            'key': api_key
        }

        r = send_request(meta_url, params)
        j = r.json()

        # Assuming this is always a "can't find", not actually true...
        if j['status'] != 'OK':
            print('Couldn\'t find {}'.format(name))
            continue
        else:
            pano_id = j['pano_id']

            # Dedup repeated streetviews
            if pano_id in panos:
                pano = panos[pano_id]
                pano['dupes'].append(data['id'])

                # If existing name is an id and this name isn't, replace
                if pano['name'] == str(pano['dupes'][0]) and name != str(data['id']):
                    print('Found name {} for {}'.format(name, pano['name']))
                    meta[name] = meta.pop(pano['name'])
                    pano['name'] = name
                else:
                    print('{} duplicates {}'.format(name, pano['name']))

                continue

            else:
                panos[pano_id] = {
                    'name': name,
                    'dupes': [data['id']]
                }
                meta[name] = {
                    'osm_id': data['id'],
                    'osm_lat': data['lat'],
                    'osm_lon': data['lon'],
                    'osm_tags': data['tags'] if 'tags' in data else None,
                    'pano_id': pano_id,
                    'pano_lat': j['location']['lat'],
                    'pano_lon': j['location']['lng'],
                    'pano_date': j['date'] if 'date' in j else None
                }

        time.sleep(1 / req_s)

    with open('{}_meta.json'.format(city.lower().replace(' ', '_')), 'w') as f:
        json.dump(meta, f, indent=2, sort_keys=True)

    out_dir = '{}_images'.format(city.lower().replace(' ', '_'))
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    # Actually collect panoramas ($)
    for name, data in meta.items():

        # Get 4 sides & up, down for cubemap
        for h, p in [('0', '0'), ('90', '0'), ('180', '0'), ('270', '0'), ('0', '-90'), ('0', '90')]:
            params = {
                'pano': data['pano_id'],
                'key': api_key,
                'size': '640x640', # 640x640 is max res
                'heading': h,
                'pitch': p
            }

            r = send_request(img_url, params)

            if r.status_code != 200:
                print('Unexpected error retrieving pano for {}, {}, {}'.format(name, h, p))
                continue

            im = Image.open(BytesIO(r.content))
            im.save('{}/{}_{}_{}.jpg'.format(out_dir, name, h, p))

            time.sleep(1 / req_s)

    print('{} has {} panoramas available'.format(city, len(meta.keys())))
