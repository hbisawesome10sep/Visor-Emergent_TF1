"""
Expo QR Code Page - Auto-refreshing QR code for Expo Go
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
import subprocess
import re

router = APIRouter(prefix="/api/expo", tags=["expo"])

def get_cloudflared_url():
    """Get the current cloudflared tunnel URL from logs"""
    try:
        result = subprocess.run(
            ["tail", "-n", "100", "/var/log/supervisor/cloudflared.err.log"],
            capture_output=True, text=True, timeout=5
        )
        # Find the most recent tunnel URL
        urls = re.findall(r'https://([a-z0-9-]+\.trycloudflare\.com)', result.stdout + result.stderr)
        if urls:
            return urls[-1]  # Return the most recent URL
    except Exception as e:
        print(f"Error getting cloudflared URL: {e}")
    
    # Fallback - try to read from .env
    try:
        with open('/app/frontend/.env', 'r') as f:
            content = f.read()
            match = re.search(r'REACT_NATIVE_PACKAGER_HOSTNAME=([a-z0-9-]+\.trycloudflare\.com)', content)
            if match:
                return match.group(1)
    except:
        pass
    
    return None

def check_tunnel_status(url):
    """Check if the tunnel is active"""
    if not url:
        return False
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"https://{url}/", "--max-time", "5"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() == "200"
    except:
        return False

@router.get("/qr", response_class=HTMLResponse)
async def expo_qr_page(request: Request):
    """Serve the Expo Go QR code page"""
    tunnel_url = get_cloudflared_url()
    is_active = check_tunnel_status(tunnel_url) if tunnel_url else False
    
    exp_url = f"exp://{tunnel_url}" if tunnel_url else "Tunnel not available"
    status_color = "#10B981" if is_active else "#EF4444"
    status_text = "Tunnel Active" if is_active else "Tunnel Inactive"
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="25">
    <title>Visor - Expo Go Preview</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0a0a0b 0%, #1a1a2e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .card {{
            background: rgba(30, 30, 40, 0.95);
            border-radius: 24px;
            padding: 40px 32px;
            max-width: 400px;
            width: 100%;
            text-align: center;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }}
        .title {{
            color: #10B981;
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 4px;
        }}
        .subtitle {{
            color: #9CA3AF;
            font-size: 14px;
            margin-bottom: 28px;
        }}
        .qr-container {{
            background: white;
            border-radius: 16px;
            padding: 20px;
            display: inline-block;
            margin-bottom: 20px;
        }}
        .qr-container img {{
            display: block;
            width: 220px;
            height: 220px;
        }}
        .scan-text {{
            color: #F3F4F6;
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 4px;
        }}
        .scan-hint {{
            color: #9CA3AF;
            font-size: 14px;
            margin-bottom: 16px;
        }}
        .scan-hint span {{
            color: #10B981;
        }}
        .url-box {{
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 12px;
            padding: 12px 16px;
            margin-bottom: 16px;
            word-break: break-all;
        }}
        .url-text {{
            color: #10B981;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 13px;
        }}
        .status {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            margin-bottom: 24px;
        }}
        .status-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: {status_color};
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        .status-text {{
            color: {status_color};
            font-size: 14px;
            font-weight: 600;
        }}
        .steps {{
            text-align: left;
            margin-bottom: 20px;
        }}
        .step {{
            display: flex;
            align-items: flex-start;
            gap: 12px;
            margin-bottom: 12px;
        }}
        .step-num {{
            background: #10B981;
            color: white;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 700;
            flex-shrink: 0;
        }}
        .step-text {{
            color: #D1D5DB;
            font-size: 14px;
            line-height: 1.5;
        }}
        .step-text strong {{
            color: #F3F4F6;
        }}
        .refresh-note {{
            color: #6B7280;
            font-size: 12px;
            margin-top: 8px;
        }}
        .copy-btn {{
            background: rgba(16, 185, 129, 0.2);
            border: 1px solid rgba(16, 185, 129, 0.4);
            color: #10B981;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
            margin-top: 8px;
            transition: all 0.2s;
        }}
        .copy-btn:hover {{
            background: rgba(16, 185, 129, 0.3);
        }}
        .error-box {{
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 16px;
        }}
        .error-text {{
            color: #EF4444;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <h1 class="title">Visor Finance</h1>
        <p class="subtitle">Personal Finance for Indians</p>
        
        {"" if tunnel_url else '<div class="error-box"><p class="error-text">⚠️ Tunnel not available. Please wait and refresh.</p></div>'}
        
        <div class="qr-container">
            <img src="https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={exp_url.replace('://', '%3A%2F%2F')}" alt="Expo QR Code" />
        </div>
        
        <p class="scan-text">Scan with Expo Go</p>
        <p class="scan-hint">Open <span>Expo Go</span> → Scan QR Code</p>
        
        <div class="url-box">
            <p class="url-text" id="expUrl">{exp_url}</p>
        </div>
        <button class="copy-btn" onclick="copyUrl()">📋 Copy URL</button>
        
        <div class="status">
            <div class="status-dot"></div>
            <span class="status-text">{status_text}</span>
        </div>
        
        <div class="steps">
            <div class="step">
                <span class="step-num">1</span>
                <span class="step-text">Install <strong>Expo Go</strong> from App Store / Play Store</span>
            </div>
            <div class="step">
                <span class="step-num">2</span>
                <span class="step-text">Open Expo Go → tap <strong>Scan QR Code</strong></span>
            </div>
            <div class="step">
                <span class="step-num">3</span>
                <span class="step-text">Scan the QR above — Visor loads on your phone</span>
            </div>
            <div class="step">
                <span class="step-num">4</span>
                <span class="step-text">Login: <strong>rajesh@visor.demo</strong> / <strong>Demo@123</strong></span>
            </div>
        </div>
        
        <p class="refresh-note">Page auto-refreshes every 25 seconds</p>
    </div>
    
    <script>
        const expUrl = "{exp_url}";
        
        function copyUrl() {{
            navigator.clipboard.writeText(expUrl).then(() => {{
                const btn = document.querySelector('.copy-btn');
                btn.textContent = '✓ Copied!';
                setTimeout(() => btn.textContent = '📋 Copy URL', 2000);
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
    is_active = check_tunnel_status(tunnel_url) if tunnel_url else False
    
    return {
        "tunnel_url": tunnel_url,
        "exp_url": f"exp://{tunnel_url}" if tunnel_url else None,
        "is_active": is_active,
        "web_url": f"https://{tunnel_url}" if tunnel_url else None
    }
