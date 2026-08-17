import requests
from bs4 import BeautifulSoup

url = 'https://pantip.com/topic/43999038'
headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get(url, headers=headers, timeout=30)
text = r.text
soup = BeautifulSoup(text, 'html.parser')

wrappers = soup.select('div.display-post-wrapper')
print('wrapper count', len(wrappers))
for i, w in enumerate(wrappers[:20], 1):
    classes = w.get('class', [])
    print(f'WRAPPER {i}:', classes)
    text_el = w.select_one('.display-post-story')
    txt = text_el.get_text(strip=True) if text_el else None
    print(' text:', repr(txt[:200]) if txt else 'None')
    name = w.select_one('.display-post-name')
    print(' author:', name.get_text(strip=True) if name else 'None')
    title = w.select_one('.display-post-title')
    print(' title:', title.get_text(strip=True) if title else 'None')
    print('---')

# find anything in wrappers with section-comment
comment_wrappers = soup.select('div.section-comment')
print('section-comment count', len(comment_wrappers))
for i, w in enumerate(comment_wrappers[:10], 1):
    print('COMMENT WRAPPER', i, w.get('class'))
    print('HTML snippet:', w.decode_contents()[:400])
    print('---')
