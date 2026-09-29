"""Bundle existing photo/guide metadata so direct-file previews also work."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
script = root / 'frontend/js/destination-details.js'
start = '// BEGIN GENERATED DESTINATION MEDIA'
end = '// END GENERATED DESTINATION MEDIA'
photos = json.loads((root / 'frontend/data/destination-photos.json').read_text(encoding='utf-8'))
fields = ['url', 'source', 'author', 'license', 'licenseUrl', 'title']
photos = {key: {field: photo[field] for field in fields} for key, photo in photos.items()}
guide = json.loads((root / 'frontend/data/destination-guide.json').read_text(encoding='utf-8'))
bundle = start + '\nconst destinationAssets = Promise.resolve(' + json.dumps([guide, photos], ensure_ascii=True, separators=(',', ':')) + ');\n' + end + '\n'
content = script.read_text(encoding='utf-8')
if content.startswith(start):
    content = content.split(end, 1)[1].lstrip('\n')
else:
    content = content[content.index('function decorateDestinationCard'):]
script.write_text(bundle + content, encoding='utf-8')
destinations = json.loads((root / 'frontend/data/destinations.json').read_text(encoding='utf-8'))['destinations']
missing = [{'name': d['name'], 'district': d['district']} for d in destinations
           if (d['name'] + '|' + d['district']).lower() not in photos]
(root / 'tools/destination_photo_coverage.json').write_text(json.dumps({
    'matched': len(photos), 'total': len(destinations),
    'note': 'Remaining entries need a verified, reusable photograph. Do not substitute unrelated images.',
    'missing': missing,
}, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Bundled {len(photos)} photo mappings and {len(guide)} destination descriptions')
