"""Batch exact destination article lookups without using the rate-limited search API."""
import json
import time
import urllib.parse
from expand_destination_photos import ROOT, DATA, AUDIT, ALIASES, get, clean

destinations = json.loads((DATA / 'destinations.json').read_text(encoding='utf-8'))['destinations']
existing = json.loads((DATA / 'destination-photos.json').read_text(encoding='utf-8'))
audit = {item['key']: item for item in json.loads(AUDIT.read_text(encoding='utf-8'))}
overrides = {
 'Golkonda / Golconda Fort': 'Golconda', 'Chilukur Balaji Temple': 'Chilkur Balaji Temple',
 'High Court of Telangana': 'Telangana High Court', 'Hussain Sagar & Necklace Road': 'Hussain Sagar',
 'KBR National Park': 'Kasu Brahmananda Reddy National Park', 'Birla Planetarium & Science Museum': 'B. M. Birla Science Museum',
 'Sri Gnana Saraswathi Temple': 'Gnana Saraswati Temple, Basar', 'Purana Haveli': 'Purani Haveli',
 'Purani Haveli': 'Purani Haveli', 'Mecca Masjid': 'Makkah Masjid, Hyderabad',
 'Buddha Statue': 'Buddha Statue of Hyderabad', 'Medak Church': 'Medak Cathedral',
 'Sri Sita Rama Temple': 'Bhadrachalam Temple', 'St. Joseph\'s Cathedral': 'St. Joseph\'s Cathedral, Hyderabad',
 'Thousand Pillar Temple': 'Thousand Pillar Temple', 'Anantagiri Hills': 'Ananthagiri Hills, Vikarabad district',
 'Yadagirigutta': 'Yadadri Lakshmi Narasimha Temple', 'Public Gardens': 'Public Gardens, Hyderabad',
 'British Residency (Koti)': 'British Residency, Hyderabad',
 'Jain Temple - Kolanupaka': 'Kulpakji', 'Sudha Cars Museum': 'Sudha Cars Museum',
 'Qutub Shahi Tombs': 'Qutb Shahi tombs', 'Qutb Shahi Tombs': 'Qutb Shahi tombs',
 'Chaya Someshwara Temple (Panagal)': 'Chaya Someswara Temple',
 'Alampur Jogulamba Temple': 'Jogulamba Temple', 'Bhadra Kali Temple': 'Bhadrakali Temple',
 'Sri Rama Chandra Temple - Ammapalli': 'Sri Sita Ramachandraswamy temple, Ammapally',
 'Vemulawada Raja Rajeshwara Swamy Temple': 'Raja Rajeswara Temple, Vemulawada',
 'Sanjeeviah Park': 'Sanjeevaiah Park', 'Sanjeevaiah Park': 'Sanjeevaiah Park',
 'Nizam Sagar Reservoir': 'Nizam Sagar', 'Nizam Sagar Dam': 'Nizam Sagar',
 'Sriram Sagar': 'Sriram Sagar Project', 'Pochampad Dam': 'Sriram Sagar Project',
 'lower maneru dam': 'Lower Manair Dam', 'Priyadarshini Jurala Dam': 'Jurala Project',
 'Kadam Dam': 'Kaddam Project', 'Kaddam Lake': 'Kaddam Project',
 'Durgam Cheruvu / Secret Lake': 'Durgam Cheruvu', 'Osman Sagar Lake / Gandipet': 'Osman Sagar',
 'Telangana State Museum': 'Telangana State Archaeology Museum',
 'Komuravelli Mallikarjuna Swamy Temple': 'Komuravelli Mallanna Temple',
 'Edupayala Vana Durga Bhavani Temple': 'Edupayala Vana Durga Bhavani Temple',
 'Shamir Pet': 'Shamirpet Lake', 'Pillalamarri / Big Banyan Tree': 'Pillalamarri',
 'Pillalamarri Banyan Tree': 'Pillalamarri', 'Assembly': 'Telangana Legislative Assembly',
 'Kawal WLS/Tiger Reserve': 'Kawal Tiger Reserve', 'Pakhal Lake & Wildlife Sanctuary': 'Pakhal Lake',
 'Mrigavani National Park': 'Mrugavani National Park', 'Pocharam Dam & Wildlife Sanctuary': 'Pocharam Wildlife Sanctuary',
 'Khilla Ghanpur (Ghanpur Fort)': 'Ghanpur Fort', 'Ramagiri Khilla': 'Ramagiri Fort',
}
todo = [d for d in destinations if (d['name']+'|'+d['district']).lower() not in existing]
found_path = ROOT / '.ui-preview/wiki-photo-articles.json'
found = json.loads(found_path.read_text(encoding='utf-8')) if found_path.exists() else []
for start in ([] if found else range(0, len(todo), 20)):
    batch = todo[start:start+20]
    titles = [overrides.get(d['name'], d['name']) for d in batch]
    params = dict(action='query', format='json', redirects=1, titles='|'.join(titles), prop='pageimages|extracts', piprop='name', exintro=1, explaintext=1, exchars=600, exlimit=20)
    try:
        response = json.loads(get('https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode(params)))['query']
        renames = {x['from']: x['to'] for key in ['normalized', 'redirects'] for x in response.get(key, [])}
        pages = {p['title']:p for p in response.get('pages', {}).values()}
        for d, title in zip(batch, titles):
            for _ in range(5):
                title = renames.get(title, title)
            page = pages.get(title, {})
            if page.get('pageimage'):
                found.append(dict(destination=d, title=page['pageimage'], extract=page.get('extract',''), article=title))
        print(f'Articles {start+len(batch)}/{len(todo)}: {len(found)} photos identified', flush=True)
    except Exception as error:
        print('Article batch failed: ' + str(error), flush=True)
    time.sleep(1)
found_path.write_text(json.dumps(found,ensure_ascii=False,indent=2),encoding='utf-8')

for start in range(0, len(found), 5):
    batch = found[start:start+5]
    params = dict(action='query', format='json', titles='|'.join('File:'+x['title'] for x in batch), prop='imageinfo', iiprop='url|size|extmetadata', iiurlwidth=960)
    response = json.loads(get('https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(params))).get('query', {})
    pages = {p['title'].replace('_', ' ').lower():p for p in response.get('pages', {}).values()}
    for item in batch:
        page = pages.get(('File:'+item['title']).replace('_', ' ').lower(), {})
        info = page.get('imageinfo', [{}])[0]
        meta = info.get('extmetadata', {})
        license = clean(meta.get('LicenseShortName',{}).get('value'))
        if not info.get('url') or not (license.startswith('CC BY') or license in ['CC0', 'Public domain']):
            continue
        if not item['title'].lower().endswith(('.jpg','.jpeg','.png')):
            continue
        d = item['destination']
        key = (d['name']+'|'+d['district']).lower()
        candidate = dict(title='File:'+item['title'], source=info['descriptionurl'], download=info.get('thumburl',info['url']),
            author=clean(meta.get('Artist',{}).get('value')), license=license,
            licenseUrl=meta.get('LicenseUrl',{}).get('value','https://creativecommons.org/publicdomain/mark/1.0/'),
            description=clean(meta.get('ImageDescription',{}).get('value'))[:1400], width=info.get('width'), height=info.get('height'),
            article=item['article'], extract=item['extract'])
        entry = audit.setdefault(key,dict(key=key,name=d['name'],district=d['district'],candidates=[]))
        entry['candidates'].insert(0,candidate)
    AUDIT.write_text(json.dumps(list(audit.values()),ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Commons metadata {start+len(batch)}/{len(found)}',flush=True)
    time.sleep(3)
