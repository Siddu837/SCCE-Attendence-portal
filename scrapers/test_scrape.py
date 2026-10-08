import requests
import json
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

# Devfolio test
print("--- TESTING DEVFOLIO ---")
try:
    r = requests.get('https://devfolio.co/hackathons', headers=headers, timeout=15)
    print("Devfolio status:", r.status_code, "Length:", len(r.text))
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text, re.DOTALL)
    if m:
        data = json.loads(m.group(1))
        print("NEXT_DATA found!")
        props = data.get('props', {})
        pageProps = props.get('pageProps', {})
        print("pageProps keys:", list(pageProps.keys()))
        dehydrated = pageProps.get('dehydratedState', {})
        queries = dehydrated.get('queries', [])
        print("queries count:", len(queries))
        for idx, q in enumerate(queries):
            q_key = q.get('queryKey')
            state = q.get('state', {})
            d = state.get('data')
            print(f"Query {idx}: key={q_key}, type={type(d)}")
            if isinstance(d, list):
                print(f"  Count: {len(d)}")
                if d and isinstance(d[0], dict):
                    print("  Sample:", d[0].get('name'), d[0].get('slug'), d[0].get('starts_at'), d[0].get('is_online'))
                    print("  All keys:", list(d[0].keys()))
            elif isinstance(d, dict):
                print("  Keys:", list(d.keys()))
    else:
        print("NEXT_DATA not found in HTML")
except Exception as e:
    print("Devfolio error:", e)

# Devpost test
print("\n--- TESTING DEVPOST ---")
try:
    # Test multiple pages or query params
    url = "https://devpost.com/api/hackathons?page=1"
    r2 = requests.get(url, headers={'User-Agent': headers['User-Agent'], 'Accept': 'application/json'}, timeout=15)
    print("Devpost status:", r2.status_code)
    if r2.status_code == 200:
        dp_json = r2.json()
        print("Devpost total hackathons in page 1:", len(dp_json.get('hackathons', [])))
        print("Meta:", dp_json.get('meta'))
        if dp_json.get('hackathons'):
            h = dp_json['hackathons'][0]
            print("Devpost sample:", json.dumps(h, indent=2))
except Exception as e:
    print("Devpost error:", e)
