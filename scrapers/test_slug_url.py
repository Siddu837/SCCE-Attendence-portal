import requests

for slug in ['wild-bugs', 'codearambh']:
    url1 = f"https://{slug}.devfolio.co"
    url2 = f"https://devfolio.co/hackathons/{slug}"
    try:
        r1 = requests.get(url1, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5, allow_redirects=True)
        print(f"{url1} -> {r1.status_code}")
    except Exception as e:
        print(f"{url1} -> err: {e}")
    try:
        r2 = requests.get(url2, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5, allow_redirects=True)
        print(f"{url2} -> {r2.status_code}")
    except Exception as e:
        print(f"{url2} -> err: {e}")
