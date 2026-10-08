import requests, json, re

headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get('https://devfolio.co/hackathons', headers=headers, timeout=15)
m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text, re.DOTALL)
data = json.loads(m.group(1))
q0 = data['props']['pageProps']['dehydratedState']['queries'][0]['state']['data']

for h in q0.get('open_hackathons', [])[:5]:
    print("Slug:", h.get('slug'))
    print("Settings keys:", list(h.get('settings', {}).keys()))
    print("featured_cover_img:", h.get('settings', {}).get('featured_cover_img'))
    print("featured_cover_img_v2:", h.get('settings', {}).get('featured_cover_img_v2'))
