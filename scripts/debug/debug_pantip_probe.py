import requests

topic_id = '43999038'
base = 'https://pantip.com'
paths = [
    f'/api/topic/{topic_id}',
    f'/api/topic/{topic_id}/comments',
    f'/api/topic/{topic_id}/replies',
    f'/api/topics/{topic_id}',
    f'/api/topics/{topic_id}/comments',
    f'/forum/topic/{topic_id}',
    f'/topic/{topic_id}/story',
    f'/topic/{topic_id}?sc=1J5lBxD',
    f'/api/post?topic_id={topic_id}',
    f'/api/reply?topic_id={topic_id}',
]

headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json, text/plain, */*'}

for p in paths:
    url = base + p
    try:
        r = requests.get(url, headers=headers, timeout=15)
        print('URL:', url)
        print('Status:', r.status_code)
        ctype = r.headers.get('Content-Type','')
        print('Content-Type:', ctype)
        txt = r.text[:800]
        print('Body preview:', txt.replace('\n',' ')[:400])
        print('-'*80)
    except Exception as e:
        print('URL:', url, 'ERROR', e)
        print('-'*80)
