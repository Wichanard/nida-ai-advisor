import json
import re
import requests
from bs4 import BeautifulSoup

url = 'https://pantip.com/topic/43999038'
headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get(url, headers=headers, timeout=30)
text = r.text
soup = BeautifulSoup(text, 'html.parser')

pt_config = soup.select_one('#ptConfig')
print('ptConfig exists', pt_config is not None)
if pt_config:
    try:
        cfg = json.loads(pt_config.string)
        print('service_base_url', cfg.get('service_base_url'))
        print('file_services_base_url', cfg.get('file_services_base_url'))
        print('statistics_service_base_url', cfg.get('statistics_service_base_url'))
    except Exception as e:
        print('ptConfig parse error', e)

print('\nSCRIPT ids containing topic/comment:')
for script in soup.select('script[id]'):
    if 'topic' in script['id'].lower() or 'comment' in script['id'].lower():
        print('  ', script['id'], 'len=', len(script.text))

print('\nFirst lines around api path occurrences:')
for m in re.finditer(r'https?://[^\s"\']*api[^\s"\']*', text):
    start = max(0, m.start() - 100)
    end = min(len(text), m.end() + 100)
    print('---')
    print(text[start:end])

print('\nSearch for keywords:')
for key in ['reply', 'comment', 'topic', 'thread']:
    idx = text.lower().find(key)
    print(key, idx)

print('\nExtracted scripts containing "service_base_url" or "topic"')
for script in soup.find_all('script'):
    if script.string and ('service_base_url' in script.string or 'topic' in script.string.lower() or 'reply' in script.string.lower()):
        s = script.string
        if len(s) > 2000:
            print('SCRIPT len', len(s))
        else:
            print('SCRIPT short', repr(s[:400]))
