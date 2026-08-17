import json
from pathlib import Path
import requests

cfg = json.loads(Path('social_listening/config.json').read_text(encoding='utf-8'))
key = cfg['platforms']['news'].get('api_key')
print('Key present:', bool(key))
q = 'NIDA'
params = {'q': q, 'pageSize': 5, 'apiKey': key, 'language': 'th', 'sortBy': 'relevancy'}
try:
    r = requests.get('https://newsapi.org/v2/everything', params=params, timeout=30)
    print('status', r.status_code)
    try:
        print('json keys', list(r.json().keys()))
        print('totalResults', r.json().get('totalResults'))
    except Exception:
        print('text preview', r.text[:800])
except Exception as e:
    print('request error', e)
