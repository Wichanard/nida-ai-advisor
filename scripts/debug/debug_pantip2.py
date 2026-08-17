import re
import requests
from bs4 import BeautifulSoup

url = 'https://pantip.com/topic/43999038'
headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get(url, headers=headers, timeout=30)
text = r.text
print('status', r.status_code)
print('len', len(text))
print('contains display-post-comment?', 'display-post-comment' in text)
print('contains display-post-story?', 'display-post-story' in text)
print('contains topic-data?', 'topic-data' in text)
print('comment string count', text.lower().count('comment'))
print('\nSCRIPT tags with id containing topic/comment:')
for script in BeautifulSoup(text, 'html.parser').select('script[id]'):
    if 'topic' in script['id'].lower() or 'comment' in script['id'].lower():
        print('  ', script['id'], 'len=', len(script.text))

soup = BeautifulSoup(text, 'html.parser')
seen = set()
for el in soup.find_all(class_=re.compile('comment|display-post|post', re.I)):
    for c in el.get('class', []):
        if re.search('comment|display-post|post', c, re.I):
            seen.add(c)
print('\nunique comment/post classes', sorted(seen))

for pat in ['display-post-story', 'display-post-comment', 'display-post-title']:
    idx = text.find(pat)
    print(f'\nPATTERN {pat} idx {idx}')
    if idx != -1:
        start = max(0, idx - 200)
        end = min(len(text), idx + 400)
        print(text[start:end])
