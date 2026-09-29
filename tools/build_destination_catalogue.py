"""Export public destination fields for fast, same-origin catalogue loading."""
import json
import sqlite3
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
with sqlite3.connect(root / 'backend/data/smart_tourism.db') as connection:
    connection.row_factory = sqlite3.Row
    rows = connection.execute('SELECT id, name, district, category, rating, popularity, entry_fee, lat AS latitude, lon AS longitude FROM other_spots ORDER BY popularity DESC, rating DESC, name ASC').fetchall()
sys.path.insert(0, str(root / 'backend'))
from services.destination_catalogue import normalize_destinations
destinations, issues = normalize_destinations([dict(row) for row in rows])
data = {'count': len(destinations), 'destinations': destinations}
(root / 'tools/destination_data_audit.json').write_text(json.dumps({'raw_count':len(rows), 'clean_count':len(destinations), 'issues':issues}, indent=2), encoding='utf-8')
path = root / 'frontend/data/destinations.json'
path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print(f'Exported {len(rows)} destinations ({path.stat().st_size} bytes)')
start = '// BEGIN GENERATED DESTINATION CATALOGUE'
end = '// END GENERATED DESTINATION CATALOGUE'
loader = (root / 'frontend/js/destination-catalogue.js').read_text(encoding='utf-8')
bundle = start + '\nwindow.BundledDestinations = ' + json.dumps(data, ensure_ascii=True, separators=(',', ':')) + ';\n' + loader + '\n' + end + '\n'
for name in ['home.js', 'destinations.js']:
    script = root / 'frontend/js' / name
    content = script.read_text(encoding='utf-8')
    if content.startswith(start):
        content = content.split(end, 1)[1].lstrip('\n')
    script.write_text(bundle + content, encoding='utf-8')
