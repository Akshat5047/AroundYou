"""Find exact-name Commons photo candidates, then download reviewed matches.

Discovery is kept separate from publication so ambiguous names can be reviewed.
"""
import concurrent.futures
import hashlib
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'frontend/data'
AUDIT = ROOT / '.ui-preview/photo-candidates.json'
HEADERS = {'User-Agent': 'AroundYouDestinationPhotos/1.0 (educational tourism catalogue; Wikimedia Commons attribution retained)'}
ALIASES = {
    'Golkonda / Golconda Fort': 'Golconda Fort', 'Qutub Shahi Tombs': 'Qutb Shahi Tombs',
    'Clock Tower (Secunderabad)': 'Secunderabad Clock Tower',
    'High Court of Telangana': 'Telangana High Court',
    'Heritage Jail Museum': 'Sangareddy jail',
    'Sri Neelakanteshwara Temple': 'Neelakanteshwara Temple Nizamabad',
    'Sri Gnana Saraswathi Temple': 'Gnana Saraswati Temple',
    'Birla Planetarium & Science Museum': 'Birla Planetarium Hyderabad',
    'Hussain Sagar & Necklace Road': 'Hussain Sagar',
    'Durgam Cheruvu / Secret Lake': 'Durgam Cheruvu',
    'Osman Sagar Lake / Gandipet': 'Osman Sagar',
    'Buddha Statue': 'Buddha statue Hyderabad',
    'Bhadra Kali Temple': 'Bhadrakali Temple Warangal',
    'Sri Sita Rama Temple': 'Bhadrachalam Temple',
    'Jain Temple - Kolanupaka': 'Kulpakji',
    'Chaya Someshwara Temple (Panagal)': 'Chaya Someswara Temple',
    'Dichpally Ramalayam (Khilla Ramalayam)': 'Dichpally Ramalayam',
    'British Residency (Koti)': 'British Residency Hyderabad',
    'Alampur Jogulamba Temple': 'Jogulamba Temple',
    'Nizam Sagar Reservoir': 'Nizam Sagar', 'Nizam Sagar Dam': 'Nizam Sagar',
    'Sriram Sagar': 'Sriram Sagar', 'Pochampad Dam': 'Sriram Sagar',
    'Kadam Dam': 'Kadam Dam', 'Kaddam Lake': 'Kadam Dam',
    'lower maneru dam': 'Lower Manair Dam',
    'Sanjeeviah Park': 'Sanjeevaiah Park',
    'Purani Haveli': 'Purani Haveli Hyderabad', 'Purana Haveli': 'Purani Haveli Hyderabad',
    'Pillalamarri / Big Banyan Tree': 'Pillalamarri banyan',
    'Pillalamarri Banyan Tree': 'Pillalamarri banyan',
    'Mecca Masjid': 'Mecca Masjid Hyderabad',
    'Medak Church': 'Medak Cathedral',
    'KBR National Park': 'Kasu Brahmananda Reddy National Park',
    'Mrigavani National Park': 'Mrugavani National Park',
    'Kawal WLS/Tiger Reserve': 'Kawal Wildlife Sanctuary',
    'Kawal Tiger Reserve': 'Kawal Wildlife Sanctuary',
    'Pakhal Lake & Wildlife Sanctuary': 'Pakhal Lake',
    'Pocharam Dam & Wildlife Sanctuary': 'Pocharam Dam',
    'Ashok Sagar / Jankampet Lake': 'Ashok Sagar',
    'Maula Ali Dargah': 'Moula Ali Dargah',
    'Public Garden (Hanumakonda)': 'Public Garden Warangal',
    'Public Gardens': 'Public Gardens Hyderabad',
    'Telangana State Museum': 'Telangana State Archaeology Museum',
    'State Art Gallery': 'State Art Gallery Hyderabad',
    'Jalari Gutta': 'Jalari Gutta',
    'Shamir Pet': 'Shamirpet Lake',
    'Anantagiri Hills': 'Ananthagiri Hills Vikarabad',
    'Yadagirigutta': 'Yadadri Temple',
    'Telangana Martyrs Memorial': 'Telangana Martyrs Memorial',
    'Priyadarshini Jurala Dam': 'Jurala Project',
    'Keesara Gutta': 'Keesaragutta',
    'Ramagiri Khilla': 'Ramagiri Fort',
    'Khilla Ghanpur (Ghanpur Fort)': 'Ghanpur Fort',
    'Lalitha Someswara Swamy Temple (Somasila)': 'Somasila Telangana',
    'Sri Rama Chandra Temple - Ammapalli': 'Ammapalli Temple',
    'Jatprole (Jetaprolu)': 'Jetprole',
    'Vemulawada Raja Rajeshwara Swamy Temple': 'Vemulawada Temple',
    'Komuravelli Mallikarjuna Swamy Temple': 'Komuravelli Temple',
    'Edupayala Vana Durga Bhavani Temple': 'Edupayala Temple',
    'Dharmapuri Lakshmi Narasimha Swamy Temple': 'Dharmapuri Telangana Temple',
    'Kondagattu Anjaneya Swamy Temple': 'Kondagattu',
    'St. Joseph\'s Cathedral': 'Saint Joseph Cathedral Hyderabad',
    'Assembly': 'Telangana Legislative Assembly',
    'Botanical Gardens': 'Hyderabad Botanical Garden',
    'Biodiversity Park': 'Biodiversity Park Hyderabad',
    'Railway Museum': 'Rail Museum Kacheguda',
    'Tribal Museum': 'Nehru Centenary Tribal Museum',
}

def clean(value):
    return html.unescape(re.sub('<[^>]+>', '', value or '')).strip()

def get(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30) as response:
                return response.read()
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 + attempt * 2)

def candidate(destination):
    time.sleep(1)
    name, district = destination['name'], destination['district']
    term = ALIASES.get(name, re.sub(r'\s*\([^)]*\)', '', name).strip())
    query = ' '.join('intitle:' + word for word in re.findall(r'\w+', term))
    params = dict(action='query', format='json', generator='search', gsrsearch=query,
                  gsrnamespace=6, gsrlimit=8, prop='imageinfo', iiprop='url|size|extmetadata', iiurlwidth=960)
    if '--categories' in sys.argv:
        params = dict(action='query', format='json', generator='categorymembers', gcmtitle='Category:' + term,
                      gcmtype='file', gcmlimit=10, prop='imageinfo', iiprop='url|size|extmetadata', iiurlwidth=960)
    try:
        pages = json.loads(get('https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(params))).get('query', {}).get('pages', {})
        results = []
        for page in pages.values():
            info = page.get('imageinfo', [{}])[0]
            title = page.get('title', '')
            if not re.search(r'\.(jpg|jpeg|png)$', title, re.I):
                continue
            if re.search(r'\b(map|logo|portrait|drawing|plan|stamp|painting|flag|chart)\b', title, re.I):
                continue
            meta = info.get('extmetadata', {})
            license = clean(meta.get('LicenseShortName', {}).get('value'))
            if not (license.startswith('CC BY') or license in ['CC0', 'Public domain']):
                continue
            if info.get('width', 0) < 640 or info.get('height', 0) < 360:
                continue
            results.append(dict(title=title, source=info['descriptionurl'],
                download=info.get('thumburl', info['url']), author=clean(meta.get('Artist', {}).get('value')),
                license=license, licenseUrl=meta.get('LicenseUrl', {}).get('value', 'https://creativecommons.org/publicdomain/mark/1.0/'),
                description=clean(meta.get('ImageDescription', {}).get('value'))[:1400],
                width=info['width'], height=info['height'], index=page.get('index', 999)))
        results.sort(key=lambda item: (item['width'] < item['height'], item['index']))
        return {'key': (name + '|' + district).lower(), 'name': name, 'district': district, 'term': term, 'candidates': results}
    except Exception as error:
        return {'key': (name + '|' + district).lower(), 'name': name, 'candidates': [], 'error': str(error)}

def discover():
    existing = json.loads((DATA / 'destination-photos.json').read_text(encoding='utf-8'))
    destinations = json.loads((DATA / 'destinations.json').read_text(encoding='utf-8'))['destinations']
    previous = {item['key']: item for item in json.loads(AUDIT.read_text(encoding='utf-8')) if not item.get('error')} if AUDIT.exists() else {}
    todo = [d for d in destinations if (d['name'] + '|' + d['district']).lower() not in existing and
            (not previous.get((d['name'] + '|' + d['district']).lower(), {}).get('candidates') if '--categories' in sys.argv else (d['name'] + '|' + d['district']).lower() not in previous)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        for item in pool.map(candidate, todo):
            previous[item['key']] = item
            AUDIT.write_text(json.dumps(list(previous.values()), ensure_ascii=False, indent=2), encoding='utf-8')
            print(item['name'] + ': ' + (item['candidates'][0]['title'] if item['candidates'] else item.get('error', 'no exact photo')), flush=True)

def download():
    catalogue_path = DATA / 'destination-photos.json'
    catalogue = json.loads(catalogue_path.read_text(encoding='utf-8'))
    entries = json.loads(AUDIT.read_text(encoding='utf-8'))
    for item in entries:
        if not item.get('approved') or item['key'] in catalogue:
            continue
        photo = item['candidates'][item.get('choice', 0)].copy()
        filename = 'place-' + hashlib.sha256(item['key'].encode()).hexdigest()[:12] + '.jpg'
        path = ROOT / 'frontend/assets/destinations' / filename
        try:
            data = get(photo.pop('download'))
            if not (data.startswith(b'\xff\xd8') or data.startswith(b'\x89PNG')):
                raise ValueError('Not a JPEG or PNG')
            path.write_bytes(data)
            photo['url'] = 'assets/destinations/' + filename
            catalogue[item['key']] = photo
            catalogue_path.write_text(json.dumps(catalogue, ensure_ascii=False, indent=2), encoding='utf-8')
            print('Saved ' + item['name'], flush=True)
        except Exception as error:
            print('FAILED ' + item['name'] + ': ' + str(error), flush=True)
    print(f'{len(catalogue)} destination photo mappings')

if __name__ == '__main__':
    download() if '--download' in sys.argv else discover()
