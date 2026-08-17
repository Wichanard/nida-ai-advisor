import re
import requests
from bs4 import BeautifulSoup

url = 'https://pantip.com/topic/43999038'
headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get(url, headers=headers, timeout=30)
text = r.text

print('status', r.status_code)
print('contains /api/', '/api/' in text)
print('contains "topic" in /api', 'topic' in text)

# print some candidate API URLs and JSON structures
for match in re.finditer(r'https?://[^\s"\']*/api/[^\s"\']*', text):
    url_match = match.group(0)
    print('API URL', url_match)

for match in re.finditer(r'/api/[^\s"\']*', text):
    fragment = match.group(0)
    if 'topic' in fragment or 'comment' in fragment or 'reply' in fragment or 'reply' in fragment:
        print('API fragment', fragment)

# print some template content for reply or comment templates
soup = BeautifulSoup(text, 'html.parser')
for script in soup.select('script#topic-reply-renovate-tmpl, script#count-comment-tmpl, script#comment-count-tmpl, script#topic-renovate-tmpl'):
    print('SCRIPT', script['id'], 'len', len(script.string or ''))
    snippet = (script.string or '')[:1200]
    print(snippet)
    print('---')

print('\nsearch for "data-topic" or "topic-id" strings')
for key in ['data-topic', 'topic-id', 'topic_id', 'comment_id', 'reply_id', 'comment-count', 'reply_count']:
    idx = text.find(key)
    print(key, idx)

print('\ncount comment-template occurrences', text.count('topic-reply-renovate-tmpl'), text.count('topic-renovate-tmpl'))
