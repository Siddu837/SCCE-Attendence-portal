#!/usr/bin/env python3
"""
Devpost & Devfolio Opportunity Scraper
Extracts live hackathons from Devpost and Devfolio, normalizes them into
the standard SCCE opportunity schema, and saves to data/devpost_devfolio.json.
"""

import os
import re
import json
import logging
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "devpost_devfolio.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,application/json,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

DEFAULT_BANNER = "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=600&q=80"


def scrape_devpost(max_pages: int = 2) -> list:
    """Scrape live hackathons from Devpost API."""
    logging.info("Scraping Devpost opportunities...")
    hackathons = []
    
    for page in range(1, max_pages + 1):
        try:
            url = f"https://devpost.com/api/hackathons?page={page}&status[]=open&status[]=upcoming"
            resp = requests.get(url, headers=HEADERS, timeout=12)
            if resp.status_code != 200:
                logging.warning(f"Devpost page {page} returned status {resp.status_code}")
                # Try general listing without status filters if 0 or error
                fallback_url = f"https://devpost.com/api/hackathons?page={page}"
                resp = requests.get(fallback_url, headers=HEADERS, timeout=12)
                if resp.status_code != 200:
                    continue
            
            data = resp.json()
            items = data.get("hackathons", [])
            logging.info(f"Devpost page {page}: fetched {len(items)} items")
            
            for h in items:
                try:
                    h_id = f"devpost_{h.get('id')}"
                    title = h.get("title", "").strip()
                    if not title:
                        continue
                    
                    loc_info = h.get("displayed_location", {}) or {}
                    loc_text = loc_info.get("location", "Online")
                    is_online = (loc_info.get("icon") == "globe") or ("online" in loc_text.lower())
                    mode = "online" if is_online else "offline"
                    location = loc_text if loc_text else ("Online" if mode == "online" else "In-Person")
                    
                    open_state = h.get("open_state", "open")
                    status = "ongoing" if open_state == "open" else "upcoming"
                    
                    organizer = h.get("organization_name") or "Devpost Community"
                    
                    # Prize pool cleaning
                    raw_prize = h.get("prize_amount", "")
                    clean_prize = re.sub(r"<[^>]+>", "", raw_prize).strip()
                    if not clean_prize or clean_prize == "$0":
                        clean_prize = "$10,000+ Swag & Prizes"
                    
                    # Dates & deadline
                    sub_dates = h.get("submission_period_dates", "")
                    time_left = h.get("time_left_to_submission", "")
                    days_left = time_left if time_left else "Upcoming"
                    
                    # Banner
                    thumb = h.get("thumbnail_url", "")
                    if thumb:
                        if thumb.startswith("//"):
                            thumb = "https:" + thumb
                    else:
                        thumb = DEFAULT_BANNER
                    
                    reg_url = h.get("url")
                    if not reg_url:
                        continue
                    
                    # Tags
                    tags = []
                    for t in h.get("themes", []):
                        if isinstance(t, dict) and t.get("name"):
                            tags.append(t["name"])
                    if not tags:
                        tags = ["Hackathon", "Coding"]
                        
                    norm = {
                        "id": h_id,
                        "title": title,
                        "platform": "Devpost",
                        "category": "hackathon",
                        "mode": mode,
                        "location": location,
                        "isFree": True,
                        "status": status,
                        "organizer": organizer,
                        "prizePool": clean_prize,
                        "startDate": sub_dates,
                        "endDate": sub_dates,
                        "deadline": sub_dates,
                        "daysLeft": days_left,
                        "bannerUrl": thumb,
                        "registrationUrl": reg_url,
                        "tags": tags[:4],
                    }
                    hackathons.append(norm)
                except Exception as ex:
                    logging.warning(f"Error parsing Devpost item: {ex}")
        except Exception as e:
            logging.error(f"Devpost scrape failed for page {page}: {e}")
            
    logging.info(f"Total Devpost hackathons scraped: {len(hackathons)}")
    return hackathons


def fetch_devfolio_details(slug: str) -> dict:
    """Fetch extra details from Devfolio hackathon page."""
    details = {
        "cover_img": None,
        "prize": None,
        "tagline": None,
        "city": None,
        "country": None,
    }
    if not slug:
        return details
    try:
        url = f"https://{slug}.devfolio.co"
        r = requests.get(url, headers=HEADERS, timeout=6)
        if r.status_code == 200:
            m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text, re.DOTALL)
            if m:
                d = json.loads(m.group(1))
                props = d.get("props", {}).get("pageProps", {})
                hack = props.get("hackathon", {})
                if hack:
                    details["cover_img"] = hack.get("cover_img") or hack.get("hero_img") or hack.get("logo")
                    details["tagline"] = hack.get("tagline")
                    details["city"] = hack.get("city")
                    details["country"] = hack.get("country")
                
                pz_val = props.get("aggregatePrizeValue")
                pz_curr = props.get("aggregatePrizeCurrency")
                if pz_val:
                    if pz_curr == "USD":
                        details["prize"] = f"${pz_val:,}"
                    elif pz_curr == "INR":
                        details["prize"] = f"₹{pz_val:,}"
                    else:
                        details["prize"] = f"{pz_curr} {pz_val:,}"
    except Exception:
        pass
    return details


def scrape_devfolio() -> list:
    """Scrape live hackathons from Devfolio."""
    logging.info("Scraping Devfolio opportunities...")
    hackathons = []
    
    try:
        url = "https://devfolio.co/hackathons"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            logging.error(f"Devfolio HTTP error: {resp.status_code}")
            return hackathons
            
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', resp.text, re.DOTALL)
        if not m:
            logging.error("Devfolio __NEXT_DATA__ script not found")
            return hackathons
            
        data = json.loads(m.group(1))
        queries = (
            data.get("props", {})
            .get("pageProps", {})
            .get("dehydratedState", {})
            .get("queries", [])
        )
        
        raw_items = []
        for q in queries:
            state_data = q.get("state", {}).get("data")
            if isinstance(state_data, dict):
                open_h = state_data.get("open_hackathons", [])
                upc_h = state_data.get("upcoming_hackathons", [])
                feat_h = state_data.get("featured_hackathons", [])
                for item in open_h:
                    item["_status_hint"] = "ongoing"
                    raw_items.append(item)
                for item in upc_h:
                    item["_status_hint"] = "upcoming"
                    raw_items.append(item)
                for item in feat_h:
                    if not any(x.get("slug") == item.get("slug") for x in raw_items):
                        item["_status_hint"] = "ongoing"
                        raw_items.append(item)
                        
        logging.info(f"Devfolio found {len(raw_items)} hackathons in NEXT_DATA")
        
        # Concurrently fetch cover images and prize amounts for each hackathon
        slugs = [h.get("slug") for h in raw_items if h.get("slug")]
        detail_map = {}
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_slug = {executor.submit(fetch_devfolio_details, slug): slug for slug in slugs}
            for future in as_completed(future_to_slug):
                slug = future_to_slug[future]
                try:
                    detail_map[slug] = future.result()
                except Exception:
                    detail_map[slug] = {}
                    
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        
        for h in raw_items:
            try:
                slug = h.get("slug")
                name = h.get("name", "").strip()
                if not name or not slug:
                    continue
                    
                det = detail_map.get(slug, {})
                
                is_online = bool(h.get("is_online"))
                mode = "online" if is_online else "offline"
                
                city = det.get("city") or h.get("city")
                country = det.get("country") or h.get("country")
                if is_online:
                    location = "Online"
                elif city and country:
                    location = f"{city}, {country}"
                elif city:
                    location = f"{city}, India"
                else:
                    location = "In-Person (India)"
                
                starts_at = h.get("starts_at")
                ends_at = h.get("ends_at")
                
                start_str = ""
                end_str = ""
                days_left = "Upcoming / Live"
                status = h.get("_status_hint", "ongoing")
                
                if starts_at:
                    try:
                        s_dt = datetime.datetime.fromisoformat(starts_at.replace("Z", "+00:00"))
                        start_str = s_dt.strftime("%b %d, %Y")
                        if now_utc < s_dt:
                            status = "upcoming"
                    except Exception:
                        start_str = starts_at[:10]
                        
                if ends_at:
                    try:
                        e_dt = datetime.datetime.fromisoformat(ends_at.replace("Z", "+00:00"))
                        end_str = e_dt.strftime("%b %d, %Y")
                        diff = (e_dt - now_utc).days
                        if diff > 1:
                            days_left = f"{diff} days left"
                        elif diff == 1:
                            days_left = "1 day left"
                        elif diff == 0:
                            days_left = "Ending today"
                        elif diff < 0:
                            continue  # Skip already ended hackathons
                    except Exception:
                        end_str = ends_at[:10]
                
                # Banner URL
                banner = det.get("cover_img")
                if not banner:
                    banner = DEFAULT_BANNER
                    
                # Prize
                prize = det.get("prize")
                if not prize:
                    prize = "Cash, Swag & Grants"
                    
                # Tags
                tags = []
                for th in h.get("themes", []):
                    if isinstance(th, dict):
                        t_name = th.get("theme", {}).get("name") or th.get("name")
                        if t_name and t_name != "No Restrictions":
                            tags.append(t_name)
                if not tags:
                    tags = ["Hackathon", "Open Innovation"]
                    
                norm = {
                    "id": f"devfolio_{slug}",
                    "title": name,
                    "platform": "Devfolio",
                    "category": "hackathon",
                    "mode": mode,
                    "location": location,
                    "isFree": True,
                    "status": status,
                    "organizer": "Devfolio & Community",
                    "prizePool": prize,
                    "startDate": start_str or "2026",
                    "endDate": end_str or "2026",
                    "deadline": end_str or "2026",
                    "daysLeft": days_left,
                    "bannerUrl": banner,
                    "registrationUrl": f"https://{slug}.devfolio.co",
                    "tags": tags[:4],
                }
                hackathons.append(norm)
            except Exception as ex:
                logging.warning(f"Error parsing Devfolio item: {ex}")
                
    except Exception as e:
        logging.error(f"Devfolio scrape failed: {e}")
        
    logging.info(f"Total Devfolio hackathons scraped: {len(hackathons)}")
    return hackathons


def run_pipeline():
    """Scrape and save combined Devpost and Devfolio opportunities."""
    os.makedirs(DATA_DIR, exist_ok=True)
    
    devpost_items = scrape_devpost(max_pages=2)
    devfolio_items = scrape_devfolio()
    
    combined = devpost_items + devfolio_items
    
    # Deduplicate by registrationUrl
    seen_urls = set()
    deduped = []
    for item in combined:
        url = item.get("registrationUrl", "").strip().lower()
        if url and url not in seen_urls:
            seen_urls.add(url)
            deduped.append(item)
            
    logging.info(f"Writing {len(deduped)} opportunities to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(deduped, f, indent=2, ensure_ascii=False)
        
    print(f"\n[SUCCESS] Successfully scraped and saved {len(deduped)} opportunities to {OUTPUT_FILE}")
    print(f" - Devpost count: {len([x for x in deduped if x['platform'] == 'Devpost'])}")
    print(f" - Devfolio count: {len([x for x in deduped if x['platform'] == 'Devfolio'])}")
    
    return deduped


if __name__ == "__main__":
    run_pipeline()
