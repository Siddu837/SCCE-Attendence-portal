import requests
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://unstop.com/'
}

def scrape_category(opportunity_type, mapped_category):
    print(f"Scraping Unstop {opportunity_type}...")
    results = []
    url = f"https://unstop.com/api/public/opportunity/search-result?opportunity={opportunity_type}&per_page=15&oppstatus=open"
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            opps = data.get('data', {}).get('data', [])
            for item in opps:
                if not isinstance(item, dict): continue
                title = item.get('title', '').strip()
                if not title: continue
                
                # Image
                banner_obj = item.get('banner_mobile') or {}
                banner_url = banner_obj.get('image_url') if isinstance(banner_obj, dict) else None
                if not banner_url:
                    logo_obj = item.get('logoUrl2') or item.get('organisation', {})
                    banner_url = logo_obj.get('logo_url') if isinstance(logo_obj, dict) else None
                if not banner_url:
                    if mapped_category == 'workshop':
                        banner_url = "https://images.unsplash.com/photo-1531482615713-2afd69097998?auto=format&fit=crop&w=600&q=80"
                    elif mapped_category == 'competition':
                        banner_url = "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?auto=format&fit=crop&w=600&q=80"
                    else:
                        banner_url = "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=600&q=80"
                
                # Organizer
                org = item.get('organisation')
                org_name = org.get('name') if isinstance(org, dict) else "Student Community"
                
                # Prize / Fee
                prizes = item.get('prizes') or []
                prize_str = "Certificates & Goodies"
                if prizes and isinstance(prizes, list):
                    first_p = prizes[0]
                    if isinstance(first_p, dict) and first_p.get('cash'):
                        prize_str = f"₹{first_p.get('cash'):,} Cash"
                        
                is_free = not item.get('isPaid', False)
                
                # Registration URL
                reg_url = item.get('seo_url') or item.get('short_url')
                if reg_url and not reg_url.startswith('http'):
                    reg_url = f"https://unstop.com/{reg_url}"
                elif not reg_url:
                    reg_url = f"https://unstop.com/{opportunity_type}"
                    
                # Deadline & Days left
                reg_req = item.get('regnRequirements') or {}
                remain_days = reg_req.get('remain_days') or "Active"
                
                # Skills / Tags
                skills = [s.get('skill') for s in item.get('required_skills', []) if isinstance(s, dict)]
                if not skills:
                    skills = [f.get('name') for f in item.get('filters', []) if isinstance(f, dict)]
                if not skills:
                    skills = ["Students", "National", "Innovation"]
                    
                results.append({
                    "id": f"unstop_{item.get('id')}",
                    "title": title,
                    "platform": "Unstop",
                    "category": mapped_category,
                    "mode": "online",
                    "location": "Online (National)",
                    "isFree": is_free,
                    "status": "ongoing",
                    "organizer": org_name or "Premier College",
                    "prizePool": prize_str,
                    "startDate": item.get('start_date', '')[:10] if item.get('start_date') else 'Ongoing',
                    "endDate": item.get('end_date', '')[:10] if item.get('end_date') else 'Ongoing',
                    "deadline": remain_days,
                    "daysLeft": remain_days,
                    "bannerUrl": banner_url,
                    "registrationUrl": reg_url,
                    "tags": skills[:4],
                    "featured": True
                })
        print(f"Unstop {opportunity_type}: Extracted {len(results)} items.")
    except Exception as e:
        print(f"Error scraping Unstop {opportunity_type}:", e)
    return results

def main():
    hacks = scrape_category('hackathons', 'hackathon')
    workshops = scrape_category('workshops', 'workshop')
    comps = scrape_category('competitions', 'competition')
    
    all_unstop = hacks + workshops + comps
    out_path = r"C:\Users\keert\.gemini\antigravity\scratch\scce-portal\data\unstop.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_unstop, f, indent=2)
    print(f"SUCCESS: Saved {len(all_unstop)} Unstop opportunities to data/unstop.json")

if __name__ == "__main__":
    main()
