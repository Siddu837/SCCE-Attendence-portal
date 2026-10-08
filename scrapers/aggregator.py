import json, os, datetime

scce_dir = r"C:\Users\keert\.gemini\antigravity\scratch\scce-portal"
data_dir = os.path.join(scce_dir, "data")
public_data_dir = os.path.join(scce_dir, "public", "data")
os.makedirs(public_data_dir, exist_ok=True)

CURATED_MEETUPS = [
    {
        "id": "meetup_gdg_devfest",
        "title": "Google Developer Groups DevFest 2026 - Central India",
        "platform": "Google Developers",
        "category": "meetup",
        "mode": "offline",
        "location": "Hyderabad / Telangana",
        "isFree": True,
        "status": "upcoming",
        "organizer": "Google Developer Community",
        "prizePool": "Swag, Goodies & Certificates",
        "startDate": "2026-11-08",
        "endDate": "2026-11-09",
        "deadline": "RSVP Open",
        "daysLeft": "Upcoming",
        "bannerUrl": "https://images.unsplash.com/photo-1540575467063-178a50c2df87?auto=format&fit=crop&w=600&q=80",
        "registrationUrl": "https://gdg.community.dev/",
        "tags": ["Android", "AI/ML", "Cloud", "Community"],
        "featured": True
    },
    {
        "id": "meetup_aws_community",
        "title": "AWS Community Day & Cloud Architect Meetup",
        "platform": "AWS User Groups",
        "category": "meetup",
        "mode": "offline",
        "location": "HITEC City, Hyderabad",
        "isFree": True,
        "status": "upcoming",
        "organizer": "AWS User Group India",
        "prizePool": "AWS Credits & Vouchers",
        "startDate": "2026-11-20",
        "endDate": "2026-11-20",
        "deadline": "Registration Active",
        "daysLeft": "Limited Seats",
        "bannerUrl": "https://images.unsplash.com/photo-1515187029135-18ee286d815b?auto=format&fit=crop&w=600&q=80",
        "registrationUrl": "https://aws.amazon.com/developer/community/usergroups/",
        "tags": ["AWS", "DevOps", "Serverless", "GenAI"],
        "featured": True
    },
    {
        "id": "meetup_foss_united",
        "title": "FOSS United Hyderabad: Open Source Developers Circle",
        "platform": "FOSS United",
        "category": "meetup",
        "mode": "offline",
        "location": "T-Hub, Hyderabad",
        "isFree": True,
        "status": "ongoing",
        "organizer": "FOSS United Foundation",
        "prizePool": "Grants & Mentorship",
        "startDate": "2026-10-25",
        "endDate": "2026-10-25",
        "deadline": "Open Entry",
        "daysLeft": "17 days left",
        "bannerUrl": "https://images.unsplash.com/photo-1528605248644-14dd04022da1?auto=format&fit=crop&w=600&q=80",
        "registrationUrl": "https://fossunited.org/",
        "tags": ["Open Source", "Linux", "Rust", "Web"],
        "featured": True
    }
]

def merge_and_enrich():
    events = []
    
    # 1. Devpost & Devfolio
    dp_file = os.path.join(data_dir, "devpost_devfolio.json")
    if os.path.exists(dp_file):
        try:
            with open(dp_file, "r", encoding="utf-8") as f:
                dp_data = json.load(f)
                if isinstance(dp_data, list):
                    events.extend(dp_data)
        except Exception as e:
            print("Error loading devpost_devfolio:", e)

    # 2. Unstop
    unstop_file = os.path.join(data_dir, "unstop.json")
    if os.path.exists(unstop_file):
        try:
            with open(unstop_file, "r", encoding="utf-8") as f:
                unstop_data = json.load(f)
                if isinstance(unstop_data, list):
                    events.extend(unstop_data)
        except Exception as e:
            print("Error loading unstop:", e)

    # 3. Add Meetups
    events.extend(CURATED_MEETUPS)

    # 4. Deduplicate
    seen_urls = set()
    seen_titles = set()
    unique_events = []
    
    for ev in events:
        url = ev.get("registrationUrl", "").strip().lower()
        title = ev.get("title", "").strip().lower()
        if url and url in seen_urls: continue
        if title and title in seen_titles: continue
        if url: seen_urls.add(url)
        if title: seen_titles.add(title)
        
        if not ev.get("bannerUrl"):
            cat = ev.get("category", "hackathon")
            if cat == "hackathon":
                ev["bannerUrl"] = "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=600&q=80"
            elif cat == "workshop":
                ev["bannerUrl"] = "https://images.unsplash.com/photo-1531482615713-2afd69097998?auto=format&fit=crop&w=600&q=80"
            elif cat == "competition":
                ev["bannerUrl"] = "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?auto=format&fit=crop&w=600&q=80"
            else:
                ev["bannerUrl"] = "https://images.unsplash.com/photo-1515187029135-18ee286d815b?auto=format&fit=crop&w=600&q=80"
                
        unique_events.append(ev)

    output_payload = {
        "updatedAt": datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "totalCount": len(unique_events),
        "categories": {
            "hackathons": len([e for e in unique_events if e.get("category") == "hackathon"]),
            "workshops": len([e for e in unique_events if e.get("category") == "workshop"]),
            "competitions": len([e for e in unique_events if e.get("category") == "competition"]),
            "meetups": len([e for e in unique_events if e.get("category") == "meetup"])
        },
        "events": unique_events
    }

    for path in [os.path.join(data_dir, "events.json"), os.path.join(public_data_dir, "events.json")]:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, indent=2)
            
    print(f"Total Aggregated: {len(unique_events)} opportunities!")
    print(output_payload["categories"])

if __name__ == "__main__":
    merge_and_enrich()
