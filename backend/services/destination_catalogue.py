"""Conservative catalogue cleanup. Preserve raw database records for review."""
import json
import math
from pathlib import Path

ALIASES = json.loads((Path(__file__).resolve().parents[1] / 'data/destination_aliases.json').read_text(encoding='utf-8'))

def key(name, district):
    return (' '.join(str(name or '').split()) + '|' + ' '.join(str(district or '').split())).casefold()

def normalize_destinations(rows):
    alias_map = {key(name, group['district']): group['name'] for group in ALIASES for name in [group['name'], *group['aliases']]}
    groups = {}
    issues = []
    for original in rows:
        row = dict(original)
        row['name'] = ' '.join(str(row.get('name') or '').split())
        row['district'] = ' '.join(str(row.get('district') or '').split())
        if not row['name'] or not row['district']:
            issues.append({'id': row.get('id'), 'issue': 'Missing name or district'})
            continue
        row['category'] = str(row.get('category') or 'other').strip().lower()
        for field, lower, upper in [('rating',0,5), ('entry_fee',0,float('inf')), ('latitude',-90,90), ('longitude',-180,180)]:
            value = row.get(field)
            if value is None or value == '':
                row[field] = None
                continue
            try:
                value = float(value)
                assert math.isfinite(value) and lower <= value <= upper
                row[field] = value
            except (ValueError, TypeError, AssertionError):
                row[field] = None
                issues.append({'id': row.get('id'), 'issue': 'Invalid ' + field})
        canonical = alias_map.get(key(row['name'], row['district']), row['name'])
        groups.setdefault(key(canonical, row['district']), []).append((canonical, row))
    result = []
    for entries in groups.values():
        canonical = entries[0][0]
        records = [row for _, row in entries]
        primary = next((row for row in records if row['name'] == canonical), records[0]).copy()
        primary['name'] = canonical
        primary['aliases'] = sorted({row['name'] for row in records if row['name'] != canonical})
        primary['source_ids'] = [row['id'] for row in records]
        conflicts = [field for field in ['entry_fee','rating','latitude','longitude','category'] if len({row.get(field) for row in records if row.get(field) is not None}) > 1]
        # A conflicting fee or rating must not be silently presented as authoritative.
        for field in ['entry_fee','rating']:
            if field in conflicts:
                primary[field] = None
        primary['data_quality'] = 'needs_review' if conflicts else 'recorded'
        if len(records) > 1:
            issues.append({'name': canonical, 'district': primary['district'], 'source_ids': primary['source_ids'], 'issue': 'Merged duplicate names', 'conflicting_fields': conflicts})
        result.append(primary)
    return result, issues
