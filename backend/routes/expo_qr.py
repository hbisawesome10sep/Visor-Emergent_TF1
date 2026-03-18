"""
Expo QR Code Page - Auto-refreshing QR code for Expo Go
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
import subprocess
import re
import urllib.parse

router = APIRouter(prefix="/api/expo", tags=["expo"])

def get_cloudflared_url():
    """Get the current cloudflared tunnel URL from logs"""
    # Try out.log first (where tunnel URL usually appears)
    for log_file in [
        "/var/log/supervisor/cloudflared.out.log",
        "/var/log/supervisor/cloudflared.err.log",
    ]:
        try:
            result = subprocess.run(
                ["tail", "-n", "200", log_file],
                capture_output=True, text=True, timeout=5
            )
            output = result.stdout + result.stderr
            urls = re.findall(r'https://([a-z0-9-]+\.trycloudflare\.com)', output)
            if urls:
                return urls[-1]
        except Exception:
            continue

    # Fallback - try EXPO_PACKAGER_PROXY_URL from .env
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('EXPO_PACKAGER_PROXY_URL='):
                    url = line.strip().split('=', 1)[1]
                    match = re.search(r'([a-z0-9-]+\.trycloudflare\.com)', url)
                    if match:
                        return match.group(1)
                if line.startswith('REACT_NATIVE_PACKAGER_HOSTNAME='):
                    hostname = line.strip().split('=', 1)[1]
                    if 'trycloudflare.com' in hostname:
                        return hostname
    except Exception:
        pass

    return None


@router.get("/qr", response_class=HTMLResponse)
async def expo_qr_page(request: Request):
    """Serve the Expo Go QR code page"""
    tunnel_url = get_cloudflared_url()

    exp_url = f"exp://{tunnel_url}" if tunnel_url else ""
    qr_data = urllib.parse.quote(exp_url, safe='') if tunnel_url else ""

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visor Finance — Expo Go Preview</title>
    <script src="https://cdn.jsdelivr.net/npm/qrcode-generator@1.4.4/qrcode.min.js"></script>
    <style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{
            font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
            background:#09090b;min-height:100vh;display:flex;align-items:center;
            justify-content:center;padding:20px;color:#f3f4f6;
        }}
        .card{{
            background:rgba(24,24,27,0.95);border-radius:24px;padding:40px 32px;
            max-width:420px;width:100%;text-align:center;
            box-shadow:0 25px 50px -12px rgba(0,0,0,0.6);
            border:1px solid rgba(255,255,255,0.06);
        }}
        .logo{{font-size:30px;font-weight:800;letter-spacing:-0.5px;margin-bottom:2px}}
        .logo span{{color:#10b981}}
        .subtitle{{color:#71717a;font-size:13px;margin-bottom:28px}}
        .qr-wrap{{
            background:#fff;border-radius:16px;padding:16px;
            display:inline-block;margin-bottom:20px;position:relative;
        }}
        #qr-canvas{{display:block;width:220px;height:220px}}
        .scan-label{{font-size:17px;font-weight:600;margin-bottom:2px}}
        .scan-hint{{color:#a1a1aa;font-size:13px;margin-bottom:18px}}
        .open-btn{{
            display:inline-flex;align-items:center;gap:8px;
            background:linear-gradient(135deg,#10b981 0%,#059669 100%);
            color:#fff;padding:12px 24px;border-radius:12px;text-decoration:none;
            font-weight:600;font-size:14px;margin-bottom:16px;
            transition:transform .15s,box-shadow .15s;
        }}
        .open-btn:hover{{transform:translateY(-1px);box-shadow:0 4px 16px rgba(16,185,129,0.3)}}
        .url-box{{
            background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.2);
            border-radius:10px;padding:10px 14px;margin-bottom:12px;word-break:break-all;
        }}
        .url-text{{color:#10b981;font-family:'SF Mono',Monaco,Consolas,monospace;font-size:12px}}
        .copy-btn{{
            background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);
            color:#d4d4d8;padding:7px 14px;border-radius:8px;cursor:pointer;
            font-size:12px;font-weight:500;transition:all .15s;margin-bottom:20px;
        }}
        .copy-btn:hover{{background:rgba(255,255,255,0.1)}}
        .status-row{{
            display:flex;align-items:center;justify-content:center;gap:8px;margin-bottom:20px;
        }}
        .dot{{
            width:9px;height:9px;border-radius:50%;
            animation:pulse 2s infinite;
        }}
        .dot.active{{background:#10b981}}
        .dot.inactive{{background:#ef4444}}
        @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.4}}}}
        .status-label{{font-size:13px;font-weight:600}}
        .status-label.active{{color:#10b981}}
        .status-label.inactive{{color:#ef4444}}
        .steps{{text-align:left;margin-bottom:16px}}
        .step{{display:flex;gap:10px;margin-bottom:10px;align-items:flex-start}}
        .step-num{{
            background:#10b981;color:#fff;width:22px;height:22px;border-radius:50%;
            display:flex;align-items:center;justify-content:center;font-size:11px;
            font-weight:700;flex-shrink:0;
        }}
        .step-text{{color:#a1a1aa;font-size:13px;line-height:1.5}}
        .step-text strong{{color:#e4e4e7}}
        .refresh-note{{color:#52525b;font-size:11px;margin-top:4px}}
        .error-box{{
            background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2);
            border-radius:10px;padding:14px;margin-bottom:16px;color:#ef4444;font-size:13px;
        }}
        .countdown{{color:#52525b;font-size:11px;margin-top:2px}}
    </style>
</head>
<body>
<div class="card">
    <div class="logo"><span>V</span>isor Finance</div>
    <p class="subtitle">Personal Finance for Indians</p>

    <div id="error-area"></div>

    <div class="qr-wrap" id="qr-wrap">
        <canvas id="qr-canvas" width="220" height="220"></canvas>
    </div>

    <p class="scan-label">Scan with Expo Go</p>
    <p class="scan-hint">or tap the button below on your phone</p>

    <div>
        <a id="open-link" class="open-btn" href="{exp_url}">
            Open in Expo Go
        </a>
    </div>

    <div class="url-box">
        <p class="url-text" id="url-text">{exp_url or 'Loading...'}</p>
    </div>
    <button class="copy-btn" onclick="copyUrl()">Copy URL</button>

    <div class="status-row">
        <div class="dot" id="status-dot"></div>
        <span class="status-label" id="status-label">Checking...</span>
    </div>

    <div class="steps">
        <div class="step">
            <span class="step-num">1</span>
            <span class="step-text">Install <strong>Expo Go</strong> from App Store / Play Store</span>
        </div>
        <div class="step">
            <span class="step-num">2</span>
            <span class="step-text">Tap <strong>"Open in Expo Go"</strong> or scan the QR code</span>
        </div>
        <div class="step">
            <span class="step-num">3</span>
            <span class="step-text">Login: <strong>rajesh@visor.demo</strong> / <strong>Demo@123</strong></span>
        </div>
    </div>

    <p class="refresh-note">Auto-refreshes every 20s</p>
    <p class="countdown" id="countdown"></p>
</div>

<script>
const API_BASE = window.location.origin;
let currentUrl = "{exp_url}";
let seconds = 20;

function drawQR(data) {{
    if (!data) return;
    const canvas = document.getElementById('qr-canvas');
    const ctx = canvas.getContext('2d');
    const qr = qrcode(0, 'M');
    qr.addData(data);
    qr.make();
    const count = qr.getModuleCount();
    const size = 220;
    const cellSize = size / count;
    ctx.clearRect(0, 0, size, size);
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, size, size);
    ctx.fillStyle = '#000';
    for (let r = 0; r < count; r++) {{
        for (let c = 0; c < count; c++) {{
            if (qr.isDark(r, c)) {{
                ctx.fillRect(c * cellSize, r * cellSize, cellSize + 0.5, cellSize + 0.5);
            }}
        }}
    }}
}}

function updateUI(expUrl, isActive) {{
    document.getElementById('url-text').textContent = expUrl || 'Tunnel not available';
    document.getElementById('open-link').href = expUrl || '#';

    const dot = document.getElementById('status-dot');
    const label = document.getElementById('status-label');
    dot.className = 'dot ' + (isActive ? 'active' : 'inactive');
    label.className = 'status-label ' + (isActive ? 'active' : 'inactive');
    label.textContent = isActive ? 'Tunnel Active' : 'Tunnel Inactive';

    const errArea = document.getElementById('error-area');
    if (!expUrl) {{
        errArea.innerHTML = '<div class="error-box">Tunnel not available. Will retry automatically...</div>';
    }} else {{
        errArea.innerHTML = '';
    }}

    if (expUrl) drawQR(expUrl);
    currentUrl = expUrl;
}}

async function refresh() {{
    try {{
        const res = await fetch(API_BASE + '/api/expo/status');
        const data = await res.json();
        updateUI(data.exp_url, data.is_active);
    }} catch(e) {{
        console.error('Refresh failed', e);
    }}
    seconds = 20;
}}

// Initial QR draw
if (currentUrl) drawQR(currentUrl);

// Countdown + auto-refresh
setInterval(() => {{
    seconds--;
    document.getElementById('countdown').textContent = 'Next refresh in ' + seconds + 's';
    if (seconds <= 0) refresh();
}}, 1000);

// Also do an immediate status check
refresh();

function copyUrl() {{
    navigator.clipboard.writeText(currentUrl).then(() => {{
        const btn = document.querySelector('.copy-btn');
        btn.textContent = 'Copied!';
        setTimeout(() => btn.textContent = 'Copy URL', 1500);
    }});
}}
</script>
</body>
</html>'''

    return HTMLResponse(content=html)


@router.get("/status")
async def tunnel_status():
    """Get current tunnel status as JSON"""
    tunnel_url = get_cloudflared_url()
    is_active = False
    if tunnel_url:
        try:
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                 f"https://{tunnel_url}/", "--max-time", "3"],
                capture_output=True, text=True, timeout=6
            )
            is_active = result.stdout.strip() in ("200", "301", "302")
        except Exception:
            pass

    return {
        "tunnel_url": tunnel_url,
        "exp_url": f"exp://{tunnel_url}" if tunnel_url else None,
        "is_active": is_active,
        "web_url": f"https://{tunnel_url}" if tunnel_url else None
    }
