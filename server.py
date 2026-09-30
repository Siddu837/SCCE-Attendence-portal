import http.server
import socketserver
import json
import os
import urllib.parse
import requests
import re
import time

PORT = 5055
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(DIRECTORY, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Referer': 'https://scce.ac.in/parent12/'
}

SUBJECT_NAMES = {
    'ES': 'Electronic Sensors',
    'AM': 'Agile Methodology',
    'DDV': 'Design Drawing and Visualization',
    'CC': 'Cloud Computing',
    'CD': 'Compiler Design'
}

# Auto-update policy:
# - Cache expires automatically every 5 minutes (300 seconds)
# - Cache expires immediately if date changes (checking tomorrow forces live scrape)
# - Manual 'refresh=true' always forces an immediate live scrape
CACHE_TTL = 300

def fetch_from_scce(htno, force_refresh=False):
    htno = htno.strip().upper()
    cache_path = os.path.join(CACHE_DIR, f"{htno}.json")
    
    # 1. Check if cache is still fresh and from today
    if not force_refresh and os.path.exists(cache_path):
        try:
            mtime = os.path.getmtime(cache_path)
            cache_age = time.time() - mtime
            cache_date = time.strftime("%Y-%m-%d", time.localtime(mtime))
            today_date = time.strftime("%Y-%m-%d")
            
            # If less than 5 minutes old AND recorded today, return cached data
            if cache_age < CACHE_TTL and cache_date == today_date:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    if cached_data.get('totalConducted', 0) > 0:
                        cached_data['fromCache'] = True
                        cached_data['cacheAgeSeconds'] = int(cache_age)
                        return cached_data
        except Exception:
            pass

    # 2. Perform live query directly to SCCE Portal
    try:
        session = requests.Session()
        
        # A. Login
        login_res = session.post(
            'https://scce.ac.in/parent12/',
            data={'HallticketNo': htno, 'submit': 'Login'},
            headers=HEADERS,
            timeout=12
        )

        # B. Student Info
        info_res = session.get('https://scce.ac.in/parent12/info.php', headers=HEADERS, timeout=12)
        name_m = re.search(r'Student Name</strong></td>\s*<td>:([^<]+)', info_res.text, re.IGNORECASE)
        father_m = re.search(r'Father Name</strong></td>\s*<td>:([^<]+)', info_res.text, re.IGNORECASE)
        student_name = name_m.group(1).strip() if name_m else 'STUDENT'
        father_name = father_m.group(1).strip() if father_m else 'FATHER'

        # C. Branch & Year
        mid_res = session.get('https://scce.ac.in/parent12/mid.php', headers=HEADERS, timeout=12)
        branch_m = re.search(r'Branch</strong></td>\s*<td>:\s*([^<]+)', mid_res.text, re.IGNORECASE)
        year_m = re.search(r'Current Year</strong></td>\s*<td>:\s*([^<]+)', mid_res.text, re.IGNORECASE)
        branch = branch_m.group(1).strip() if branch_m else 'B.Tech'
        year = year_m.group(1).strip() if year_m else '4th Year'

        # D. Dailywise1.php — Live transactions table
        dw_res = session.post(
            'https://scce.ac.in/parent12/Dailywise1.php',
            data={'HallticketNo': htno, 'dayatten': 'Submit'},
            headers=HEADERS,
            timeout=15
        )

        pattern = r'<td>(\d+)</td>\s*<td>([^<]+)</td>\s*<td[^>]*>(\d+)</td>\s*<td>(\d+)</td>\s*<td>(\d{2}-\d{2}-\d{4})</td>'
        matches = re.findall(pattern, dw_res.text)

        tot_m = re.search(r'Total.*?<b>(\d+)\s*</td>\s*<td[^>]*><b>(\d+)\s*</td>\s*<td[^>]*><b>(\d+)\s*%', dw_res.text, re.DOTALL)
        
        total_conducted = 0
        total_attended = 0
        
        if matches:
            total_attended = sum(int(m[2]) for m in matches)
            total_conducted = sum(int(m[3]) for m in matches)
        elif tot_m:
            total_attended = int(tot_m.group(1))
            total_conducted = int(tot_m.group(2))

        percentage = round((total_attended / total_conducted * 100), 2) if total_conducted > 0 else 0.0

        subject_stats = {}
        transactions = []
        
        for m in matches:
            sno = m[0]
            sub = m[1].strip()
            atnd = int(m[2])
            cnctd = int(m[3])
            dt = m[4]
            
            display_name = SUBJECT_NAMES.get(sub, sub)
            
            if sub not in subject_stats:
                subject_stats[sub] = {
                    'code': sub,
                    'name': display_name,
                    'conducted': 0,
                    'attended': 0
                }
            subject_stats[sub]['conducted'] += cnctd
            subject_stats[sub]['attended'] += atnd
            
            transactions.append({
                'sno': int(sno),
                'subject': sub,
                'subjectName': display_name,
                'attended': atnd,
                'conducted': cnctd,
                'date': dt,
                'present': atnd > 0
            })

        # Put latest transactions at the top
        transactions.reverse()

        need_75 = max(0, int((0.75 * total_conducted - total_attended) / 0.25 + 0.99)) if total_conducted > 0 else 0
        can_miss_65 = max(0, int((total_attended - 0.65 * total_conducted) / 0.65)) if total_conducted > 0 else 0
        latest_date = transactions[0]['date'] if transactions else time.strftime("%d-%m-%Y")

        result = {
            'hallTicket': htno,
            'studentName': student_name,
            'fatherName': father_name,
            'branch': branch,
            'year': year,
            'photoUrl': f"https://scce.ac.in/n0/{htno}.jpg",
            'totalConducted': total_conducted,
            'totalAttended': total_attended,
            'totalAbsent': total_conducted - total_attended,
            'percentage': percentage,
            'need75': need_75,
            'canMiss65': can_miss_65,
            'subjectStats': subject_stats,
            'transactions': transactions,
            'latestClassDate': latest_date,
            'fetchedAt': time.strftime("%Y-%m-%d %I:%M:%S %p"),
            'fromCache': False,
            'autoUpdatePolicy': 'Daily date-check & 5-minute TTL auto-refresh'
        }

        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)

        return result

    except Exception as e:
        # Graceful fallback to existing cache if college server is momentarily down
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                cached_data['fromCache'] = True
                cached_data['serverWarning'] = f"Live refresh paused ({str(e)}). Showing last verified record."
                return cached_data
        raise e

class PortalHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/attendance':
            params = urllib.parse.parse_qs(parsed.query)
            htno = params.get('htno', ['23N01A7405'])[0].strip().upper()
            force_refresh = params.get('refresh', ['false'])[0].lower() in ('true', '1', 'yes')
            try:
                data = fetch_from_scce(htno, force_refresh=force_refresh)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
        elif parsed.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'online', 'mode': 'live-auto-update', 'ttl_seconds': CACHE_TTL}).encode('utf-8'))
        else:
            super().do_GET()

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

if __name__ == '__main__':
    with ThreadedHTTPServer(("", PORT), PortalHandler) as httpd:
        print(f"SCCE Dynamic Portal Server running at http://localhost:{PORT}")
        httpd.serve_forever()
