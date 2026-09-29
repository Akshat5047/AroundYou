"""Small live probe. Never prints credentials or stores a trip."""
import os
import sys
from pathlib import Path
from importlib.metadata import version
from dotenv import load_dotenv
from google import genai

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
key = os.getenv('GEMINI_API_KEY', '')
print('google-genai:', version('google-genai'))
print('API key configured:', bool(key))
if not key:
    raise SystemExit(1)
try:
    client = genai.Client(api_key=key, http_options={'timeout': 15000, 'retry_options': {'attempts': 1}})
    if '--generate-content' in sys.argv:
        response = client.models.generate_content(model=os.getenv('GEMINI_MODEL', 'gemini-3.6-flash'), contents='Reply with only OK.', config={'automatic_function_calling': {'disable': True}})
        print('Text:', response.text)
        raise SystemExit(0)
    response = client.interactions.create(model='gemini-3.6-flash', input='Reply with only OK.', timeout=15)
    print('Response type:', type(response).__name__)
    print('output_text property present:', hasattr(response, 'output_text'))
    print('Text:', getattr(response, 'output_text', None))
except Exception as error:
    print(type(error).__name__ + ':', str(error).replace(key, '[REDACTED]')[:1800])
    raise SystemExit(1)
