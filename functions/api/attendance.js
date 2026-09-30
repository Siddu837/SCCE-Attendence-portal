// Cloudflare Pages Function: /api/attendance
// Handles requests to /api/attendance?htno=... or /api/attendance?roll=...

const SUBJECT_NAMES = {
  'ES': 'Electronic Sensors',
  'AM': 'Agile Methodology',
  'DDV': 'Design Drawing and Visualization',
  'CC': 'Cloud Computing',
  'CD': 'Compiler Design'
};

const HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  'Referer': 'https://scce.ac.in/parent12/'
};

export async function onRequestGet(context) {
  const url = new URL(context.request.url);
  const htno = (url.searchParams.get('htno') || url.searchParams.get('roll') || '23N01A7405').trim().toUpperCase();
  const forceRefresh = ['true', '1', 'yes'].includes((url.searchParams.get('refresh') || '').toLowerCase());

  try {
    const data = await fetchAttendance(htno);
    return new Response(JSON.stringify(data, null, 2), {
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': forceRefresh ? 'no-cache, no-store' : 'public, max-age=300, s-maxage=300'
      }
    });
  } catch (err) {
    return new Response(JSON.stringify({
      error: true,
      message: err.message || 'Failed to fetch attendance data from college portal',
      hallTicket: htno
    }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Access-Control-Allow-Origin': '*'
      }
    });
  }
}

export async function onRequestOptions() {
  return new Response(null, {
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    }
  });
}

async function fetchAttendance(htno) {
  const loginBody = new URLSearchParams({
    HallticketNo: htno,
    submit: 'Login'
  });

  const loginRes = await fetch('https://scce.ac.in/parent12/', {
    method: 'POST',
    headers: {
      ...HEADERS,
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: loginBody.toString(),
    redirect: 'manual'
  });

  const rawCookies = loginRes.headers.getSetCookie 
    ? loginRes.headers.getSetCookie() 
    : [loginRes.headers.get('set-cookie')];

  let cookieHeader = '';
  if (rawCookies && rawCookies.length > 0) {
    cookieHeader = rawCookies
      .filter(Boolean)
      .map(c => c.split(';')[0])
      .join('; ');
  }

  const authHeaders = {
    ...HEADERS,
    'Cookie': cookieHeader
  };

  const [infoRes, midRes, dwRes] = await Promise.all([
    fetch('https://scce.ac.in/parent12/info.php', { headers: authHeaders }).catch(() => null),
    fetch('https://scce.ac.in/parent12/mid.php', { headers: authHeaders }).catch(() => null),
    fetch('https://scce.ac.in/parent12/Dailywise1.php', {
      method: 'POST',
      headers: {
        ...authHeaders,
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({ HallticketNo: htno, dayatten: 'Submit' }).toString()
    }).catch(() => null)
  ]);

  let studentName = 'STUDENT';
  let fatherName = 'FATHER';
  if (infoRes && infoRes.ok) {
    const infoText = await infoRes.text();
    const nameMatch = infoText.match(/Student Name<\/strong><\/td>\s*<td>:([^<]+)/i);
    const fatherMatch = infoText.match(/Father Name<\/strong><\/td>\s*<td>:([^<]+)/i);
    if (nameMatch) studentName = nameMatch[1].trim();
    if (fatherMatch) fatherName = fatherMatch[1].trim();
  }

  let branch = 'B.Tech';
  let year = '4th Year';
  if (midRes && midRes.ok) {
    const midText = await midRes.text();
    const branchMatch = midText.match(/Branch<\/strong><\/td>\s*<td>:\s*([^<]+)/i);
    const yearMatch = midText.match(/Current Year<\/strong><\/td>\s*<td>:\s*([^<]+)/i);
    if (branchMatch) branch = branchMatch[1].trim();
    if (yearMatch) year = yearMatch[1].trim();
  }

  if (!dwRes || !dwRes.ok) {
    throw new Error('College portal dailywise server did not respond');
  }

  const dwHtml = await dwRes.text();
  const pattern = /<td>(\d+)<\/td>\s*<td>([^<]+)<\/td>\s*<td[^>]*>(\d+)<\/td>\s*<td>(\d+)<\/td>\s*<td>(\d{2}-\d{2}-\d{4})<\/td>/g;
  const matches = [...dwHtml.matchAll(pattern)];

  let totalConducted = 0;
  let totalAttended = 0;
  const subjectStats = {};
  const transactions = [];

  for (const m of matches) {
    const sno = parseInt(m[1], 10);
    const sub = m[2].trim();
    const atnd = parseInt(m[3], 10);
    const cnctd = parseInt(m[4], 10);
    const dt = m[5];

    totalAttended += atnd;
    totalConducted += cnctd;

    const displayName = SUBJECT_NAMES[sub] || sub;

    if (!subjectStats[sub]) {
      subjectStats[sub] = {
        code: sub,
        name: displayName,
        conducted: 0,
        attended: 0
      };
    }
    subjectStats[sub].conducted += cnctd;
    subjectStats[sub].attended += atnd;

    transactions.push({
      sno: sno,
      subject: sub,
      subjectName: displayName,
      attended: atnd,
      conducted: cnctd,
      date: dt,
      present: atnd > 0
    });
  }

  if (matches.length === 0) {
    const totMatch = dwHtml.match(/Total.*?<b>(\d+)\s*<\/td>\s*<td[^>]*><b>(\d+)\s*<\/td>\s*<td[^>]*><b>(\d+)\s*%/s);
    if (totMatch) {
      totalAttended = parseInt(totMatch[1], 10);
      totalConducted = parseInt(totMatch[2], 10);
    }
  }

  const percentage = totalConducted > 0 
    ? Math.round((totalAttended / totalConducted) * 10000) / 100 
    : 0.0;

  transactions.reverse();

  const need75 = totalConducted > 0 
    ? Math.max(0, Math.ceil((0.75 * totalConducted - totalAttended) / 0.25)) 
    : 0;

  const canMiss65 = totalConducted > 0 
    ? Math.max(0, Math.floor((totalAttended - 0.65 * totalConducted) / 0.65)) 
    : 0;

  const latestDate = transactions.length > 0 ? transactions[0].date : new Date().toLocaleDateString('en-GB');

  return {
    hallTicket: htno,
    studentName: studentName,
    fatherName: fatherName,
    branch: branch,
    year: year,
    photoUrl: 'https://scce.ac.in/n0/' + htno + '.jpg',
    totalConducted: totalConducted,
    totalAttended: totalAttended,
    totalAbsent: Math.max(0, totalConducted - totalAttended),
    percentage: percentage,
    need75: need75,
    canMiss65: canMiss65,
    subjectStats: subjectStats,
    transactions: transactions,
    latestClassDate: latestDate,
    fetchedAt: new Date().toLocaleString(),
    fromCache: false,
    autoUpdatePolicy: 'Cloudflare Edge Caching & Real-time Live Sync'
  };
}
