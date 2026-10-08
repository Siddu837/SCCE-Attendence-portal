import requests
import json
import re
import datetime

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

def clean_html(raw_html):
    if not raw_html: return ""
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html).strip()

def scrape_devpost():
    print("Scraping Devpost...")
    results = []
    try:
        url = "https://devpost.com/api/hackathons?page=1"
        res = requests.get(url, headers={'User-Agent': headers['User-Agent'], 'Accept': 'application/json'}, timeout=15)
        if res.status_code == 200:
            data = res.json()
            for item in data.get('hackathons', []):
                title = item.get('title', '').strip()
                if not title: continue
                
                # Image
                thumb = item.get('thumbnail_url', '')
                if thumb and thumb.startswith('//'):
                    thumb = 'https:' + thumb
                elif not thumb:
                    thumb = "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=600&q=80"
                    
                prize = clean_html(item.get('prize_amount', '')) or "Cash & Swag"
                tags = [t.get('name') for t in item.get('themes', []) if isinstance(t, dict)]
                
                # Mode & Location
                is_online = not item.get('displayed_location', {}).get('location', '') or 'online' in item.get('displayed_location', {}).get('location', '').lower()
                location = "Online" if is_online else item.get('displayed_location', {}).get('location', 'Global')
                
                results.append({
                    "id": f"devpost_{item.get('id', title.lower().replace(' ', '_'))}",
                    "title": title,
                    "platform": "Devpost",
                    "category": "hackathon",
                    "mode": "online" if is_online else "offline",
                    "location": location,
                    "isFree": True,
                    "status": "ongoing",
                    "organizer": item.get('organization_name') or "Devpost Community",
                    "prizePool": prize,
                    "startDate": item.get('submission_period_dates', 'Upcoming'),
                    "endDate": item.get('submission_period_dates', 'Upcoming'),
                    "deadline": item.get('submission_period_dates', 'See details'),
                    "daysLeft": item.get('time_left_to_submission', 'Active'),
                    "bannerUrl": thumb,
                    "registrationUrl": item.get('url'),
                    "tags": tags[:4] if tags else ["Software", "Code", "Hackathon"],
                    "featured": True if item.get('featured') else False
                })
        print(f"Devpost: Extracted {len(results)} hackathons.")
    except Exception as e:
        print("Devpost scraping error:", e)
    return results

def scrape_devfolio():
    print("Scraping Devfolio...")
    results = []
    try:
        res = requests.get('https://devfolio.co/hackathons', headers=headers, timeout=15)
        if res.status_code == 200:
            m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', res.text, re.DOTALL)
            if m:
                data = json.loads(m.group(1))
                queries = data.get('props', {}).get('pageProps', {}).get('dehydratedState', {}).get('queries', [])
                for q in queries:
                    state = q.get('state', {})
                    d = state.get('data')
                    items = []
                    if isinstance(d, list):
                        items = d
                    elif isinstance(d, dict):
                        items = d.get('hackathons') or d.get('open_hackathons') or []
                        
                    for item in items:
                        if not isinstance(item, dict): continue
                        name = item.get('name', '').strip()
                        slug = item.get('slug', '').strip()
                        if not name: continue
                        
                        banner = item.get('cover_img') or item.get('hero_img')
                        if not banner:
                            banner = "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=600&q=80"
                            
                        is_online = item.get('is_online', True)
                        loc = "Online" if is_online else (item.get('location') or "In-Person (India)")
                        
                        themes = [t.get('name') for t in item.get('themes', []) if isinstance(t, dict)]
                        if not themes and isinstance(item.get('themes'), list):
                            themes = [str(t) for t in item.get('themes')]
                            
                        reg_url = f"https://{slug}.devfolio.co/" if slug else "https://devfolio.co/hackathons"
                        
                        results.append({
                            "id": f"devfolio_{item.get('uuid') or slug}",
                            "title": name,
                            "platform": "Devfolio",
                            "category": "hackathon",
                            "mode": "online" if is_online else "offline",
                            "location": loc,
                            "isFree": True,
                            "status": "ongoing",
                            "organizer": "Devfolio & Community",
                            "prizePool": "Trophies & Grants",
                            "startDate": item.get('starts_at', '')[:10] if item.get('starts_at') else 'Upcoming',
                            "endDate": item.get('ends_at', '')[:10] if item.get('ends_at') else 'Upcoming',
                            "deadline": item.get('ends_at', '')[:10] if item.get('ends_at') else 'Live',
                            "daysLeft": "Upcoming / Live",
                            "bannerUrl": banner,
                            "registrationUrl": reg_url,
                            "tags": themes[:4] if themes else ["Web3", "Open Source", "Hackathon"],
                            "featured": True
                        })
        print(f"Devfolio: Extracted {len(results)} hackathons.")
    except Exception as e:
        print("Devfolio scraping error:", e)
    return results

def main():
    dp = scrape_devpost()
    df = scrape_devfolio()
    all_items = dp + df
    out_path = r"C:\Users\keert\.gemini\antigravity\scratch\scce-portal\data\devpost_devfolio.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, indent=2)
    print(f"SUCCESS: Saved {len(all_items)} Devpost & Devfolio opportunities to data/devpost_devfolio.json")

if __name__ == "__main__":
    main()
