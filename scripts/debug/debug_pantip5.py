import requests
from bs4 import BeautifulSoup

url = 'https://pantip.com/topic/43999038'
headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get(url, headers=headers, timeout=30)
text = r.text
soup = BeautifulSoup(text, 'html.parser')

# find wrapper elements and print their structure
wrappers = soup.select('div.display-post-wrapper')
print('wrapper count', len(wrappers))
for i, wrapper in enumerate(wrappers, 1):
    print('\n--- WRAPPER', i, 'classes', wrapper.get('class'))
    print('text len', len(wrapper.get_text(strip=True)))
    child_classes = [c for tag in wrapper.find_all(True) for c in tag.get('class', [])]
    print('child class set', sorted(set(child_classes))[:50])
    if i == 3:
        html = wrapper.decode_contents()
        print('wrapper3 raw HTML sample:')
        print(html[:2000])
        print('...')

# search for content inside script templates that may have comment markup
templates = soup.select('script#topic-renovate-tmpl, script#topic-reply-renovate-tmpl')
for t in templates:
    print('\nTEMPLATE', t.get('id'), 'len', len(t.string or ''))
    snippet = (t.string or '')[:800]
    print(snippet)
    print('...')
