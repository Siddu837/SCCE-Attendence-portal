import requests, json

r = requests.get('https://devpost.com/api/hackathons?page=1', headers={'User-Agent': 'Mozilla/5.0'})
hacks = r.json().get('hackathons', [])
for h in hacks:
    thumb = h.get('thumbnail_url', '')
    if thumb.startswith('//'):
        thumb = 'https:' + thumb
    print(h.get('title'), "->", thumb)
