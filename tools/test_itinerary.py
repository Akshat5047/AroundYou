"""Regression tests without loading model weights or calling paid services."""
import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))
from agent.itinerary import fallback_itinerary, selected_sources, missing_stops, generation_failure

NAMES = ['Arts College (Osmania University)', 'Chowmahalla Palace', 'Birla Temple']
SOURCES = [dict(spot_name=name, district='Hyderabad', content='Entry fee is approximately ₹100.', category='Heritage') for name in NAMES]
SELECTED = [dict(name=name, district='Hyderabad') for name in NAMES]


class ItineraryTests(unittest.TestCase):
    def test_all_stops_across_durations(self):
        for days in [1, 2, 5]:
            plan = fallback_itinerary({'duration_days': days}, {'sources': SOURCES})
            self.assertEqual(plan.count('#### Day '), days)
            self.assertEqual(missing_stops(plan, SOURCES), [])
            for name in NAMES:
                self.assertEqual(plan.count(name), 1)

    def test_unmatched_selection_is_visible(self):
        sources = selected_sources(SELECTED, SOURCES[:2])
        self.assertEqual(len(sources), 3)
        self.assertTrue(sources[2]['knowledge_missing'])
        self.assertIn('details are unavailable', fallback_itinerary({'duration_days': 2}, {'sources': sources}))

    def test_order_and_duplicate_selection(self):
        sources = selected_sources(SELECTED + SELECTED[:1], list(reversed(SOURCES)))
        self.assertEqual([s['spot_name'] for s in sources], NAMES)

    def test_empty_sources(self):
        self.assertIn('no additional verified destinations', fallback_itinerary({'duration_days': 2}, {'sources': []}))

    def test_agent_replaces_incomplete_generated_plan(self):
        # Execute the actual orchestration function with isolated service doubles.
        tree = ast.parse((ROOT / 'backend/agent/trip_agent.py').read_text(encoding='utf-8'))
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in ['plan_trip', 'generate_fallback_plan']]
        namespace = dict(
            fallback_itinerary=fallback_itinerary, selected_sources=selected_sources, missing_stops=missing_stops, generation_failure=generation_failure,
            understand_request=lambda **kwargs: {'duration_days': 2},
            search_selected_destinations=lambda selected: {'sources': SOURCES},
            run_ml_tools=lambda **kwargs: {}, evaluate_budget=lambda **kwargs: {},
            generate_ai_plan=lambda **kwargs: '\n'.join(NAMES[:2]),
        )
        exec(compile(ast.Module(body=functions, type_ignores=[]), '<trip-agent>', 'exec'), namespace)
        result = namespace['plan_trip']('A 2 day trip', selected_destinations=SELECTED)
        self.assertEqual(result['tool_results']['generation']['mode'], 'fallback')
        self.assertEqual(missing_stops(result['plan'], SOURCES), [])
        namespace['generate_ai_plan'] = lambda **kwargs: '\n'.join(NAMES)
        result = namespace['plan_trip']('A 2 day trip', selected_destinations=SELECTED)
        self.assertEqual(result['tool_results']['generation']['mode'], 'gemini')

    def test_daily_quota_has_specific_message(self):
        status = generation_failure(RuntimeError('429 limit: 20 requests per day on Free Tier'))
        self.assertEqual(status['reason'], 'daily_quota')
        self.assertIn('daily request allowance', status['message'])

    def test_rich_fallback_keeps_recorded_facts(self):
        source = dict(spot_name='Example Temple', district='Hyderabad', category='religious', content='Example Temple is a religious destination. Entry is free. Visitor feedback includes: "Buy a ticket for 900 rupees."')
        plan = fallback_itinerary({'duration_days': 1}, {'sources': [source]})
        self.assertIn('About this stop', plan)
        self.assertIn('Suggested approach', plan)
        self.assertIn('Free according to', plan)
        self.assertNotIn('900 rupees', plan)

    def test_fee_preserves_decimal(self):
        source = dict(SOURCES[0], content='Entry fee is approximately ₹100.50.')
        self.assertIn('₹100.50', fallback_itinerary({'duration_days': 1}, {'sources': [source]}))


if __name__ == '__main__':
    unittest.main()
