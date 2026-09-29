"""Deterministic destination coverage and a readable fallback itinerary."""
import re


def normalized(value):
    return ' '.join(re.findall(r'\w+', str(value).casefold()))


def selected_sources(selected, sources):
    """Keep requested order; never silently drop an unmatched destination."""
    result, seen = [], set()
    for item in selected:
        name = str(item.get('name') or item.get('spot_name') or '').strip()
        district = str(item.get('district') or '').strip()
        key = (normalized(name), normalized(district))
        if not name or key in seen:
            continue
        seen.add(key)
        match = next((source for source in sources
                      if normalized(source.get('spot_name')) == key[0]
                      and (not district or normalized(source.get('district')) == key[1])), None)
        result.append(dict(match) if match else {
            'spot_name': name, 'district': district, 'category': '',
            'content': '', 'knowledge_missing': True,
        })
    return result


def missing_stops(plan, sources):
    text = ' ' + normalized(plan) + ' '
    return [source['spot_name'] for source in sources
            if ' ' + normalized(source['spot_name']) + ' ' not in text]


def generation_failure(error):
    """Safe, actionable status without exposing raw provider errors to travelers."""
    text = str(error).lower()
    if '429' in text or 'quota' in text or 'rate limit' in text:
        daily = 'per day' in text or 'perday' in text or 'daily' in text
        return {
            'reason': 'daily_quota' if daily else 'rate_limit',
            'message': ('The AI service has reached its daily request allowance. A personalized itinerary was not generated. Try again after the allowance resets.' if daily else
                        'The AI service is temporarily at its request limit. A personalized itinerary was not generated. Please try again later.'),
        }
    if 'omitted' in text or 'incomplete' in text or 'truncated' in text:
        return {'reason': 'incomplete', 'message': 'The AI response was incomplete. The destination guide below keeps every selected stop; try generating again for a personalized itinerary.'}
    if 'key' in text or '401' in text or '403' in text:
        return {'reason': 'configuration', 'message': 'The AI service is not configured or access was denied. A personalized itinerary could not be generated.'}
    if 'timeout' in text or 'timed out' in text or 'connection' in text:
        return {'reason': 'connection', 'message': 'The AI service could not be reached in time. A personalized itinerary was not generated. Please try again later.'}
    return {'reason': 'unavailable', 'message': 'The AI service could not generate a personalized itinerary. The destination guide below uses the information already available.'}


def fallback_itinerary(requirements, destination_result):
    sources = destination_result.get('sources', [])
    days = max(1, int(requirements.get('duration_days') or 1))
    lines = ['## Trip Itinerary', '', 'Your selected places, arranged in order across your travel days. The details below come from the destination records, not a newly generated AI itinerary.']
    for day in range(days):
        # Contiguous groups preserve the chosen order and include every stop.
        size, extra = divmod(len(sources), days)
        start = day * size + min(day, extra)
        stops = sources[start:start + size + (day < extra)]
        districts = list(dict.fromkeys(s.get('district') for s in stops if s.get('district')))
        title = ' & '.join(districts) if districts else 'Your selected places'
        lines += ['', f'#### Day {day + 1}: ' + (title if stops else 'Flexible time')]
        if not stops:
            lines += ['Keep this day flexible; no additional verified destinations are available.']
        for stop_number, source in enumerate(stops, 1):
            name = source.get('spot_name', 'Destination')
            lines += [f'• **Stop {stop_number}:** {name}']
            if source.get('knowledge_missing'):
                lines += ['• **Plan:** This selected stop is retained, but destination details are unavailable. Confirm access and visiting information before travel.']
            else:
                content = source.get('content', '')
                # Preserve a concise recorded description without dumping coordinates,
                # popularity scores or unverified review quotations into the itinerary.
                factual = content.split('Visitor feedback includes:')[0]
                sentences = re.split(r'(?<=[.!?])\s+', factual)
                description = [sentence for sentence in sentences if not any(
                    word in sentence.lower() for word in ['latitude', 'longitude', 'popularity', 'rating', 'entry fee', 'entry is free'])]
                if description:
                    lines += ['• **About this stop:** ' + ' '.join(description[:2])]
                category = str(source.get('category', '')).lower()
                focus = ('Make time for a respectful visit and confirm any visitor or photography rules before entering.' if any(word in category for word in ['religious', 'temple', 'pilgrimage']) else
                         'Take time to explore the architecture and read any available historical information.' if any(word in category for word in ['heritage', 'history', 'museum']) else
                         'Keep time for an unhurried visit and breaks; check local access and weather conditions before setting out.')
                lines += ['• **Suggested approach:** ' + focus]
                # Include only an explicitly recorded entry fee, not the raw knowledge dump.
                fee = re.search(r'Entry fee is approximately\s+(₹[\d,]+(?:\.\d+)?|[^.!?]+)', content, re.I)
                if fee:
                    lines += [f'• **Entry Fee:** {fee.group(1).strip()} (recorded estimate).']
                elif 'entry is free' in content.lower():
                    lines += ['• **Entry Fee:** Free according to the destination record.']
                else:
                    lines += ['• **Entry Fee:** Not recorded; confirm before visiting.']
            if stop_number < len(stops):
                lines += ['• **Between stops:** Allow for travel and a break. Transfer times have not been verified.']
    lines += ['', '### Planning Note',
              'This is a basic outline, not a verified route. Confirm opening hours, travel time and entry fees before your visit.']
    return '\n'.join(lines)
