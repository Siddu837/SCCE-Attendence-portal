import requests
import json
import re

headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get('https://devfolio.co/hackathons', headers=headers, timeout=15)
m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text, re.DOTALL)
data = json.loads(m.group(1))
q0 = data['props']['pageProps']['dehydratedState']['queries'][0]['state']['data']

print('open count:', len(q0.get('open_hackathons', [])))
print('upcoming count:', len(q0.get('upcoming_hackathons', [])))
print('featured count:', len(q0.get('featured_hackathons', [])))

if q0.get('open_hackathons'):
    print('Sample open:', json.dumps(q0['open_hackathons'][0], indent=2))
if q0.get('upcoming_hackathons'):
    print('Sample upcoming:', json.dumps(q0['upcoming_hackathons'][0], indent=2))
