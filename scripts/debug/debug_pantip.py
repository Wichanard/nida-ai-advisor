import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0'}

# Search page check
search_q = 'NIDA'
search_url = 'https://pantip.com/search'
search_resp = requests.get(search_url, params={'q': search_q}, headers=headers, timeout=30)
print('SEARCH status', search_resp.status_code)
print('SEARCH url', search_resp.url)
search_text = search_resp.text
print('SEARCH len', len(search_text))
search_soup = BeautifulSoup(search_text, 'html.parser')
search_links = [a.get('href') for a in search_soup.select('a[href]') if a.get('href')]
print('SEARCH total links', len(search_links))
print('SEARCH topic count', sum(1 for l in search_links if '/topic/' in l))
print('SEARCH sample topics', [l for l in search_links if '/topic/' in l][:10])

# Thread page check
thread_url = 'https://pantip.com/topic/43999038'
thread_resp = requests.get(thread_url, headers=headers, timeout=30)
print('\nTHREAD status', thread_resp.status_code)
thread_text = thread_resp.text
print('THREAD len', len(thread_text))
thread_soup = BeautifulSoup(thread_text, 'html.parser')
print('THREAD title selectors', [t.get_text(strip=True) for t in thread_soup.select('.display-post-title, h1.title, h1')][:5])
print('THREAD author selectors', [a.get_text(strip=True) for a in thread_soup.select('.display-post__author-name, .display-post-author__name')][:5])
print('THREAD body selectors', [b.get_text(strip=True)[:200] for b in thread_soup.select('.display-post-story, .display-post-body')][:5])
print('THREAD comment selectors raw count', len(thread_soup.select('.display-post-comment, .display-post-story')))
print('THREAD comment sample text', [c.get_text(strip=True)[:200] for c in thread_soup.select('.display-post-comment, .display-post-story')][:5])
print('THREAD display-post classes', sorted({cls for el in thread_soup.select('[class*=display-post]') for cls in el.get('class', [])}))
print('THREAD comment class sample', sorted({cls for el in thread_soup.select('.display-post-comment, .display-post-story') for cls in el.get('class', [])}))
