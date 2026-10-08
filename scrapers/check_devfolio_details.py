import requests, re, json

headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get('https://devfolio.co/hackathons', headers=headers, timeout=15)
m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text, re.DOTALL)
data = json.loads(m.group(1))
q0 = data['props']['pageProps']['dehydratedState']['queries'][0]['state']['data']

hackathons = q0.get('open_hackathons', []) + q0.get('upcoming_hackathons', [])

for h in hackathons[:8]:
    slug = h.get('slug')
    uuid = h.get('uuid')
    print(f"Checking {slug} ({uuid})...")
    try:
        hr = requests.get(f"https://{slug}.devfolio.co", headers=headers, timeout=5)
        hm = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', hr.text, re.DOTALL)
        if hm:
            hdata = json.loads(hm.group(1))
            h_obj = hdata.get('props', {}).get('pageProps', {}).get('hackathon', {})
            print(f"  cover: {h_obj.get('cover_img')}")
            print(f"  hero: {h_obj.get('hero_img')}")
            print(f"  logo: {h_obj.get('logo')}")
            print(f"  tagline: {h_obj.get('tagline')}")
            print(f"  prizes: {h_obj.get('prizes')}")
    except Exception as e:
        print(f"  Error: {e}")
