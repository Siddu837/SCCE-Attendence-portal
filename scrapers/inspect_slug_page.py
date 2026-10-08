import requests, re, json
r = requests.get('https://wild-bugs.devfolio.co', headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
print('status:', r.status_code)
# check og:image
og = re.findall(r'<meta property="og:image" content="(.*?)"', r.text)
print('og:image:', og)
m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text, re.DOTALL)
if m:
    data = json.loads(m.group(1))
    props = data.get('props', {}).get('pageProps', {})
    print('hackathon keys:', list(props.keys()))
    hackathon = props.get('hackathon', {})
    if hackathon:
        print('hackathon cover:', hackathon.get('cover_img'), hackathon.get('hero_img'), hackathon.get('logo'))
        print('prizes:', hackathon.get('prizes'))
