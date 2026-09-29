"""Build a local destination guide and a small, explicitly matched photo catalogue."""
import csv, json, re, html, urllib.request, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / 'frontend/data'
out.mkdir(exist_ok=True)
guide = {}
for row in csv.DictReader((ROOT / 'ai/rag/vector_store/metadata.csv').open(encoding='utf-8')):
    content = row['content'].split('Visitor feedback includes:')[0]
    sentences = re.split(r'(?<=[.!?])\s+', content)
    description = ' '.join(s for s in sentences if not any(word in s.lower() for word in ['latitude', 'longitude', 'popularity', 'rating', 'entry fee', 'entry is free']))
    guide[(row['spot_name'] + '|' + row['district']).lower()] = description
(out / 'destination-guide.json').write_text(json.dumps(guide, ensure_ascii=False, indent=2), encoding='utf-8')
photos = [
    ('Chowmahalla Palace', 'Hyderabad', 'Chowmahalla Palace 01.jpg'),
    ('Birla Temple', 'Hyderabad', 'Birla Mandir Hyderabad.jpg'),
    ('Arts College (Osmania University)', 'Hyderabad', 'Osmania University Arts College 02.jpg'),
]
catalogue_path = out / 'destination-photos.json'
catalogue = json.loads(catalogue_path.read_text(encoding='utf-8')) if catalogue_path.exists() else {}
asset_dir = ROOT / 'frontend/assets/destinations'
asset_dir.mkdir(parents=True, exist_ok=True)
for index, (name, district, filename) in enumerate(photos, 1):
    params = urllib.parse.urlencode(dict(action='query', format='json', prop='imageinfo', iiprop='url|extmetadata', iiurlwidth=960, titles='File:' + filename))
    request = urllib.request.Request('https://commons.wikimedia.org/w/api.php?' + params, headers={'User-Agent':'AroundYou/1.0 (educational tourism project)'})
    with urllib.request.urlopen(request, timeout=25) as response:
        info = next(iter(json.load(response)['query']['pages'].values()))['imageinfo'][0]
    metadata = info['extmetadata']
    photo_request = urllib.request.Request(info.get('thumburl', info['url']), headers={'User-Agent': 'AroundYou/1.0 (educational tourism project)'})
    with urllib.request.urlopen(photo_request, timeout=25) as response:
        if not response.headers.get('Content-Type', '').startswith('image/'):
            raise ValueError('Expected a photo response')
        (asset_dir / f'destination-{index}.jpg').write_bytes(response.read())
    clean = lambda value: html.unescape(re.sub('<[^>]+>', '', value)).strip()
    catalogue[(name + '|' + district).lower()] = dict(
        url=f'assets/destinations/destination-{index}.jpg', source=info['descriptionurl'],
        author=clean(metadata['Artist']['value']), license=clean(metadata['LicenseShortName']['value']),
        licenseUrl=metadata.get('LicenseUrl', {}).get('value', 'https://creativecommons.org/publicdomain/mark/1.0/' if 'public domain' in metadata['LicenseShortName']['value'].lower() else 'https://creativecommons.org/licenses/by-sa/3.0/'), title=filename,
    )
(out / 'destination-photos.json').write_text(json.dumps(catalogue, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Built {len(guide)} descriptions and {len(catalogue)} credited photos.')
