import json
import os
import re
import sys
import logging
from datetime import datetime
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "unstop.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://unstop.com/"
}

CATEGORIES = [
    {"query": "hackathons", "canonical": "hackathon"},
    {"query": "workshops", "canonical": "workshop"},
    {"query": "competitions", "canonical": "competition"}
]

def format_inr(val):
    try:
        n = int(val)
        return f"₹{n:,}"
    except (ValueError, TypeError):
        return str(val)

def extract_prize_pool(item):
    prizes = item.get("prizes") or []
    if not prizes:
        return "N/A"
    
    # Check for summary rank first (e.g. 'Prize Pool', 'Total Prize Pool')
    for p in prizes:
        rank = (p.get("rank") or "").strip().lower()
        if "prize pool" in rank:
            cash = p.get("cash")
            if cash and cash > 0:
                return format_inr(cash)
            others = (p.get("others") or "").strip()
            if others:
                return others

    # Calculate total cash or max cash across prizes
    total_cash = 0
    cash_found = False
    for p in prizes:
        cash = p.get("cash")
        if cash and isinstance(cash, (int, float)) and cash > 0:
            total_cash += cash
            cash_found = True
            
    if cash_found and total_cash > 0:
        return format_inr(total_cash)
        
    for p in prizes:
        others = (p.get("others") or "").strip()
        if others:
            return others
            
    return "N/A"

def extract_banner_url(item, category):
    logo = item.get("logoUrl2") or ""
    if logo and logo.startswith("http"):
        return logo
    
    # Fallback to category defaults
    default_banners = {
        "hackathon": "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=800&q=80",
        "workshop": "https://images.unsplash.com/photo-1531482615713-2afd69097998?auto=format&fit=crop&w=800&q=80",
        "competition": "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?auto=format&fit=crop&w=800&q=80"
    }
    return default_banners.get(category, default_banners["hackathon"])

def extract_mode_and_location(item):
    region = (item.get("region") or "").strip().lower()
    address_obj = item.get("address_with_country_logo") or {}
    city = (address_obj.get("city") or "").strip()
    state = (address_obj.get("state") or "").strip()
    country_name = ((address_obj.get("country") or {}).get("name") or "").strip()
    
    loc_parts = [p for p in [city, state, country_name] if p]
    location = ", ".join(loc_parts) if loc_parts else "Online"
    
    if region == "online":
        mode = "online"
        location = "Online"
    elif region in ["offline", "hybrid"]:
        mode = "offline"
        if not loc_parts:
            location = "In-person / Campus"
    else:
        # Infer mode from address
        if loc_parts:
            mode = "offline"
        else:
            mode = "online"
            location = "Online"
            
    return mode, location

def extract_days_left(item):
    reg = item.get("regnRequirements") or {}
    rem_array = reg.get("remainingDaysArray") or {}
    durations = rem_array.get("durations")
    text = (rem_array.get("text") or "").strip().lower()
    
    if durations is not None:
        try:
            val = int(durations)
            if "month" in text:
                return val * 30
            elif "hour" in text:
                return 1 if val > 0 else 0
            return val
        except (ValueError, TypeError):
            pass
            
    remain_str = (reg.get("remain_days") or "").lower()
    m = re.search(r"(\d+)\s*(day|month|hour)", remain_str)
    if m:
        val = int(m.group(1))
        unit = m.group(2)
        if unit == "month":
            return val * 30
        elif unit == "hour":
            return 1 if val > 0 else 0
        return val
        
    return None

def normalize_opportunity(item, category):
    opp_id = f"unstop_{item.get('id')}"
    title = (item.get("title") or "").strip()
    platform = "Unstop"
    
    mode, location = extract_mode_and_location(item)
    
    # Pricing
    is_paid = item.get("isPaid")
    is_free = not bool(is_paid)
    
    # Status
    status_raw = (item.get("status") or "").strip().upper()
    reg = item.get("regnRequirements") or {}
    reg_status = (reg.get("reg_status") or "").strip().upper()
    
    if status_raw == "LIVE" or reg_status == "STARTED":
        status = "ongoing"
    else:
        status = "upcoming"
        
    # Organizer
    org = item.get("organisation") or {}
    organizer = (org.get("name") if isinstance(org, dict) else str(org)) or "Unstop Partner"
    organizer = organizer.strip()
    
    # Prize pool
    prize_pool = extract_prize_pool(item)
    
    # Dates
    start_date = item.get("start_date") or reg.get("start_regn_dt") or None
    end_date = item.get("end_date") or None
    deadline = reg.get("end_regn_dt") or end_date
    
    days_left = extract_days_left(item)
    banner_url = extract_banner_url(item, category)
    registration_url = item.get("seo_url") or item.get("short_url") or f"https://unstop.com/o/{item.get('id')}"
    
    # Tags
    tags_list = []
    for s in (item.get("required_skills") or []):
        if s.get("skill"):
            tags_list.append(s.get("skill").strip())
    for f in (item.get("filters") or []):
        if f.get("name") and f.get("name").strip() != "All":
            tags_list.append(f.get("name").strip())
    for w in (item.get("workfunction") or []):
        if w.get("name"):
            tags_list.append(w.get("name").strip())
            
    seen_tags = set()
    deduped_tags = []
    for t in tags_list:
        if t.lower() not in seen_tags:
            seen_tags.add(t.lower())
            deduped_tags.append(t)
            
    return {
        "id": opp_id,
        "title": title,
        "platform": platform,
        "category": category,
        "mode": mode,
        "location": location,
        "isFree": is_free,
        "status": status,
        "organizer": organizer,
        "prizePool": prize_pool,
        "startDate": start_date,
        "endDate": end_date,
        "deadline": deadline,
        "daysLeft": days_left,
        "bannerUrl": banner_url,
        "registrationUrl": registration_url,
        "tags": deduped_tags[:8]
    }

def scrape_unstop():
    os.makedirs(DATA_DIR, exist_ok=True)
    all_opportunities = []
    seen_ids = set()
    category_counts = {}

    targets = [
        {"query": "hackathons", "canonical": "hackathon", "target": 100},
        {"query": "workshops", "canonical": "workshop", "target": 80},
        {"query": "competitions", "canonical": "competition", "target": 100}
    ]

    for cat_info in targets:
        query_type = cat_info["query"]
        canonical_cat = cat_info["canonical"]
        target_count = cat_info["target"]
        
        cat_count = 0
        page = 1
        per_page = 50
        
        logging.info(f"Fetching {canonical_cat} (target: {target_count})...")
        while cat_count < target_count:
            url = f"https://unstop.com/api/public/opportunity/search-result?opportunity={query_type}&per_page={per_page}&page={page}&oppstatus=open"
            try:
                resp = requests.get(url, headers=HEADERS, timeout=20)
                resp.raise_for_status()
                res_data = resp.json()
                items = res_data.get("data", {}).get("data", [])
                if not items:
                    logging.info(f"No more items returned on page {page} for {query_type}")
                    break
                    
                added_page = 0
                for item in items:
                    record = normalize_opportunity(item, canonical_cat)
                    if record["id"] not in seen_ids:
                        seen_ids.add(record["id"])
                        all_opportunities.append(record)
                        cat_count += 1
                        added_page += 1
                        if cat_count >= target_count:
                            break
                            
                logging.info(f"Page {page} fetched: +{added_page} {canonical_cat}s (Current: {cat_count}/{target_count})")
                if added_page == 0 or len(items) < per_page:
                    break
                page += 1
            except Exception as e:
                logging.error(f"Error fetching page {page} for {query_type}: {e}")
                break
                
        category_counts[canonical_cat] = cat_count

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_opportunities, f, indent=2, ensure_ascii=False)

    logging.info(f"Successfully saved {len(all_opportunities)} normalized opportunities to {OUTPUT_FILE}")
    for cat, count in category_counts.items():
        logging.info(f"  - {cat}: {count} opportunities")

    return all_opportunities, category_counts

if __name__ == "__main__":
    scrape_unstop()
