"""
Expo QR Code Page - Auto-refreshing QR code for Expo Go (iOS + Android)
Uses cloudflare tunnel for reliable mobile preview access.
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import subprocess
import re

router = APIRouter(prefix="/api/expo", tags=["expo"])


def get_tunnel_hostname():
    """Get the cloudflare tunnel hostname from logs or env"""
    # 1. Try the tunnel URL file (written by start_tunnel.sh)
    try:
        with open("/tmp/tunnel_url.txt", "r") as f:
            url = f.read().strip()
            if url:
                return url.replace("https://", "").replace("http://", "")
    except Exception:
        pass

    # 2. Try cloudflared logs
    for log_file in [
        "/var/log/supervisor/cloudflared.out.log",
        "/var/log/supervisor/cloudflared.err.log",
    ]:
        try:
            result = subprocess.run(
                ["tail", "-n", "200", log_file],
                capture_output=True, text=True, timeout=5,
            )
            urls = re.findall(r"https://([a-z0-9-]+\.trycloudflare\.com)", result.stdout + result.stderr)
            if urls:
                return urls[-1]
        except Exception:
            continue

    # 3. Fallback to frontend .env
    try:
        with open("/app/frontend/.env", "r") as f:
            for line in f:
                if line.startswith("EXPO_PACKAGER_PROXY_URL="):
                    url = line.strip().split("=", 1)[1]
                    m = re.search(r"([a-z0-9-]+\.trycloudflare\.com)", url)
                    if m:
                        return m.group(1)
    except Exception:
        pass

    return None


@router.get("/status")
async def tunnel_status():
    """Get current tunnel status as JSON"""
    hostname = get_tunnel_hostname()
    is_active = False
    if hostname:
        try:
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                 f"https://{hostname}/", "--max-time", "4"],
                capture_output=True, text=True, timeout=8,
            )
            is_active = result.stdout.strip() in ("200", "301", "302", "304")
        except Exception:
            pass

    return {
        "hostname": hostname,
        "exp_url": f"exp://{hostname}" if hostname else None,
        "https_url": f"https://{hostname}" if hostname else None,
        "is_active": is_active,
    }


@router.get("/qr", response_class=HTMLResponse)
async def expo_qr_page():
    """Serve the auto-refreshing Expo Go QR code page"""
    hostname = get_tunnel_hostname()
    exp_url = f"exp://{hostname}" if hostname else ""

    html = f"""<!DOCTYPE html>
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
      max-width:440px;width:100%;text-align:center;
      box-shadow:0 25px 50px -12px rgba(0,0,0,0.6);
      border:1px solid rgba(255,255,255,0.06);
    }}
    .logo{{font-size:30px;font-weight:800;letter-spacing:-0.5px;margin-bottom:2px}}
    .logo span{{color:#10b981}}
    .subtitle{{color:#71717a;font-size:13px;margin-bottom:24px}}

    /* Tabs */
    .tabs{{display:flex;gap:4px;margin-bottom:24px;background:rgba(255,255,255,0.04);border-radius:12px;padding:4px}}
    .tab{{
      flex:1;padding:10px 8px;border-radius:10px;cursor:pointer;font-size:13px;font-weight:600;
      color:#a1a1aa;transition:all .2s;border:none;background:none;
    }}
    .tab.active{{background:rgba(16,185,129,0.15);color:#10b981}}
    .tab:hover:not(.active){{color:#d4d4d8}}

    /* QR */
    .qr-wrap{{
      background:#fff;border-radius:16px;padding:16px;
      display:inline-block;margin-bottom:20px;position:relative;
    }}
    #qr-canvas{{display:block;width:240px;height:240px}}

    .scan-label{{font-size:17px;font-weight:600;margin-bottom:2px}}
    .scan-hint{{color:#a1a1aa;font-size:13px;margin-bottom:18px}}

    /* Buttons */
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
      font-size:12px;font-weight:500;transition:all .15s;margin-bottom:18px;
    }}
    .copy-btn:hover{{background:rgba(255,255,255,0.1)}}

    /* Status */
    .status-row{{
      display:flex;align-items:center;justify-content:center;gap:8px;margin-bottom:18px;
    }}
    .dot{{width:9px;height:9px;border-radius:50%;animation:pulse 2s infinite}}
    .dot.active{{background:#10b981}}
    .dot.inactive{{background:#ef4444}}
    .dot.checking{{background:#f59e0b}}
    @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.4}}}}
    .status-label{{font-size:13px;font-weight:600}}
    .status-label.active{{color:#10b981}}
    .status-label.inactive{{color:#ef4444}}
    .status-label.checking{{color:#f59e0b}}

    /* Steps */
    .steps{{text-align:left;margin-bottom:14px}}
    .step{{display:flex;gap:10px;margin-bottom:10px;align-items:flex-start}}
    .step-num{{
      background:#10b981;color:#fff;width:22px;height:22px;border-radius:50%;
      display:flex;align-items:center;justify-content:center;font-size:11px;
      font-weight:700;flex-shrink:0;
    }}
    .step-text{{color:#a1a1aa;font-size:13px;line-height:1.5}}
    .step-text strong{{color:#e4e4e7}}

    .footer{{color:#52525b;font-size:11px;margin-top:4px}}
    .error-box{{
      background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2);
      border-radius:10px;padding:14px;margin-bottom:16px;color:#ef4444;font-size:13px;
    }}
    .platform-tag{{
      display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:600;
      padding:3px 8px;border-radius:6px;margin:0 3px;
    }}
    .ios{{background:rgba(99,102,241,0.12);color:#818cf8}}
    .android{{background:rgba(16,185,129,0.12);color:#10b981}}
  </style>
</head>
<body>
<div class="card">
  <div class="logo"><span>V</span>isor Finance</div>
  <p class="subtitle">Personal Finance for Indians</p>

  <div class="tabs">
    <button class="tab active" data-tab="expo" onclick="switchTab('expo')">Expo Go (Mobile)</button>
    <button class="tab" data-tab="web" onclick="switchTab('web')">Web Preview</button>
  </div>

  <div id="error-area"></div>

  <!-- Expo Go Tab -->
  <div id="tab-expo">
    <div class="qr-wrap" id="qr-wrap">
      <canvas id="qr-canvas" width="240" height="240"></canvas>
    </div>

    <p class="scan-label">Scan with Expo Go</p>
    <p class="scan-hint">
      Works on <span class="platform-tag ios">iOS</span>
      and <span class="platform-tag android">Android</span>
    </p>

    <div>
      <a id="open-link" class="open-btn" href="{exp_url}">Open in Expo Go</a>
    </div>

    <div class="url-box">
      <p class="url-text" id="url-text">{exp_url or 'Detecting tunnel...'}</p>
    </div>
    <button class="copy-btn" onclick="copyUrl()">Copy URL</button>

    <div class="status-row">
      <div class="dot checking" id="status-dot"></div>
      <span class="status-label checking" id="status-label">Checking...</span>
    </div>

    <div class="steps">
      <div class="step">
        <span class="step-num">1</span>
        <span class="step-text">Install <strong>Expo Go</strong> from App Store / Play Store</span>
      </div>
      <div class="step">
        <span class="step-num">2</span>
        <span class="step-text"><strong>iOS:</strong> Scan QR with Camera app. <strong>Android:</strong> Scan inside Expo Go</span>
      </div>
      <div class="step">
        <span class="step-num">3</span>
        <span class="step-text">Login: <strong>rajesh@visor.demo</strong> / <strong>Demo@123</strong></span>
      </div>
    </div>
  </div>

  <!-- Web Preview Tab -->
  <div id="tab-web" style="display:none">
    <div style="margin-bottom:20px">
      <a id="web-link" class="open-btn" href="/" target="_blank" style="font-size:16px;padding:14px 28px">
        Open Web Preview
      </a>
    </div>
    <div class="url-box">
      <p class="url-text" id="web-url-text"></p>
    </div>
    <button class="copy-btn" onclick="copyWebUrl()">Copy Web URL</button>
    <div class="steps" style="margin-top:12px">
      <div class="step">
        <span class="step-num">1</span>
        <span class="step-text">Click <strong>Open Web Preview</strong> above</span>
      </div>
      <div class="step">
        <span class="step-num">2</span>
        <span class="step-text">Login: <strong>rajesh@visor.demo</strong> / <strong>Demo@123</strong></span>
      </div>
    </div>
  </div>

  <p class="footer">Auto-refreshes every 15s &middot; <span id="countdown"></span></p>
</div>

<script>
const API_BASE = window.location.origin;
const WEB_URL = window.location.origin;
let currentExpUrl = "{exp_url}";
let seconds = 15;

document.getElementById('web-url-text').textContent = WEB_URL;
document.getElementById('web-link').href = WEB_URL;

function switchTab(tab) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelector(`.tab[data-tab="${{tab}}"]`).classList.add('active');
  document.getElementById('tab-expo').style.display = tab === 'expo' ? 'block' : 'none';
  document.getElementById('tab-web').style.display = tab === 'web' ? 'block' : 'none';
}}

function drawQR(data) {{
  if (!data) return;
  const canvas = document.getElementById('qr-canvas');
  const ctx = canvas.getContext('2d');
  const qr = qrcode(0, 'M');
  qr.addData(data);
  qr.make();
  const count = qr.getModuleCount();
  const size = 240;
  const cellSize = size / count;
  ctx.clearRect(0, 0, size, size);
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, size, size);
  ctx.fillStyle = '#09090b';
  for (let r = 0; r < count; r++) {{
    for (let c = 0; c < count; c++) {{
      if (qr.isDark(r, c)) {{
        const x = c * cellSize, y = r * cellSize;
        ctx.beginPath();
        ctx.roundRect(x + 0.5, y + 0.5, cellSize, cellSize, 1);
        ctx.fill();
      }}
    }}
  }}
}}

function updateUI(expUrl, isActive) {{
  document.getElementById('url-text').textContent = expUrl || 'Tunnel not available — will retry...';
  document.getElementById('open-link').href = expUrl || '#';

  const dot = document.getElementById('status-dot');
  const label = document.getElementById('status-label');
  const state = isActive ? 'active' : 'inactive';
  dot.className = 'dot ' + state;
  label.className = 'status-label ' + state;
  label.textContent = isActive ? 'Tunnel Active' : 'Tunnel Inactive';

  const errArea = document.getElementById('error-area');
  errArea.innerHTML = !expUrl
    ? '<div class="error-box">Tunnel not available yet. Will retry automatically...</div>'
    : '';

  if (expUrl) {{
    drawQR(expUrl);
    currentExpUrl = expUrl;
  }}
}}

async function refresh() {{
  const dot = document.getElementById('status-dot');
  const label = document.getElementById('status-label');
  dot.className = 'dot checking';
  label.className = 'status-label checking';
  label.textContent = 'Checking...';
  try {{
    const res = await fetch(API_BASE + '/api/expo/status');
    const data = await res.json();
    updateUI(data.exp_url, data.is_active);
  }} catch(e) {{
    console.error('Refresh failed', e);
  }}
  seconds = 15;
}}

if (currentExpUrl) drawQR(currentExpUrl);

setInterval(() => {{
  seconds--;
  const el = document.getElementById('countdown');
  if (el) el.textContent = 'next check in ' + seconds + 's';
  if (seconds <= 0) refresh();
}}, 1000);

refresh();

function copyUrl() {{
  navigator.clipboard.writeText(currentExpUrl || '').then(() => {{
    const btn = document.querySelector('#tab-expo .copy-btn');
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = 'Copy URL', 1500);
  }});
}}

function copyWebUrl() {{
  navigator.clipboard.writeText(WEB_URL).then(() => {{
    const btn = document.querySelector('#tab-web .copy-btn');
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = 'Copy Web URL', 1500);
  }});
}}
</script>
</body>
</html>"""

    return HTMLResponse(content=html)
