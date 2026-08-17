import re
import requests
from bs4 import BeautifulSoup

url = 'https://pantip.com/topic/43999038'
headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get(url, headers=headers, timeout=30)
text = r.text
print('status', r.status_code)
print('len', len(text))

for key in ['topic_id', 'topicid', 'topicId', 'comment_id', 'commentid', 'reply_id', 'replyid', 'topic', 'comment', 'reply']:
    idx = text.lower().find(key.lower())
    if idx != -1:
        start = max(0, idx - 200)
        end = min(len(text), idx + 200)
        print('\nKEY', key, 'first idx', idx)
        print(text[start:end])

print('\nSCRIPT IDs with rendered JSON likelihood:')
soup = BeautifulSoup(text, 'html.parser')
for script in soup.find_all('script'):
    if script.string and ('topic' in script.string.lower() or 'comment' in script.string.lower() or 'reply' in script.string.lower()) and len(script.string) < 1000:
        print('SCRIPT short id', script.get('id'), repr(script.string[:400]))

print('\nFind API-like fragments with topic or comment names:')
for match in re.finditer(r'/(?:api|forum|topic|comment|reply)[^"\'>\s]*', text):
    frag = match.group(0)
    if any(x in frag.lower() for x in ['topic', 'comment', 'reply']):
        print(frag)

print('\nCheck for JavaScript object declarations near topic_id:')
for m in re.finditer(r'([A-Za-z0-9_]+\s*[:=]\s*(?:\d+|\"[^\"]*\"|\'[^\']*\'))', text):
    if 'topic' in m.group(1).lower() or 'comment' in m.group(1).lower() or 'reply' in m.group(1).lower():
        print(m.group(1))
        break
