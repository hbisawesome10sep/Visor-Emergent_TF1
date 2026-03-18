"""
Visor Finance - Modular FastAPI Server
A comprehensive personal finance management application.
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from starlette.middleware.cors import CORSMiddleware
import asyncio
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import seed and migration utilities
from seed_data import seed_demo_data, migrate_all_users_encryption
from routes.market_data import seed_market_data, market_data_scheduler

# Import all routers
from routes.auth import router as auth_router
from routes.transactions import router as transactions_router
from routes.goals import router as goals_router
from routes.dashboard import router as dashboard_router
from routes.tax import router as tax_router
from routes.ai_chat import router as ai_chat_router
from routes.ai_advisor import router as ai_advisor_router
from routes.holdings import router as holdings_router
from routes.loans import router as loans_router
from routes.recurring import router as recurring_router
from routes.market_data import router as market_data_router
from routes.portfolio import router as portfolio_router
from routes.risk_profile import router as risk_profile_router
from routes.assets import router as assets_router
from routes.bookkeeping import router as bookkeeping_router
from routes.gmail import router as gmail_router
from routes.bank_accounts import router as bank_accounts_router
from routes.journal import router as journal_router
from routes.bank_statements import router as bank_statements_router
from routes.exports import router as exports_router
from routes.credit_cards import router as credit_cards_router
from routes.cc_statements import router as cc_statements_router
from routes.visor_ai import router as visor_ai_router
from routes.expo_qr import router as expo_qr_router
from routes.dashboard_v2 import router as dashboard_v2_router
from routes.cc_analytics import router as cc_analytics_router

# Create FastAPI app
app = FastAPI(
    title="Visor Finance API",
    description="Personal Finance Management Application",
    version="2.0.0",
)

# Include all routers
app.include_router(auth_router)
app.include_router(transactions_router)
app.include_router(goals_router)
app.include_router(dashboard_router)
app.include_router(tax_router)
app.include_router(ai_chat_router)
app.include_router(ai_advisor_router)
app.include_router(holdings_router)
app.include_router(loans_router)
app.include_router(recurring_router)
app.include_router(market_data_router)
app.include_router(portfolio_router)
app.include_router(risk_profile_router)
app.include_router(assets_router)
app.include_router(bookkeeping_router)
app.include_router(gmail_router)
app.include_router(bank_accounts_router)
app.include_router(journal_router)
app.include_router(bank_statements_router)
app.include_router(exports_router)
app.include_router(credit_cards_router)
app.include_router(cc_statements_router)
app.include_router(visor_ai_router)
app.include_router(expo_qr_router)
app.include_router(dashboard_v2_router)
app.include_router(cc_analytics_router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Initialize application on startup."""
    logger.info("Starting Visor Finance API...")
    
    # Seed demo data
    await seed_demo_data()
    
    # Run encryption migration for existing users
    await migrate_all_users_encryption()
    
    # Seed market data with live prices
    await seed_market_data()
    
    # Start market data refresh scheduler
    asyncio.create_task(market_data_scheduler())
    
    logger.info("Visor Finance API started successfully!")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    from database import client
    client.close()
    logger.info("Visor Finance API shutdown complete.")


# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "visor-finance-api"}


# Tunnel URL endpoint — reads active cloudflared tunnel URL for QR page
@app.get("/api/tunnel-url")
async def get_tunnel_url():
    """Return the current Expo Go tunnel URL."""
    try:
        with open("/tmp/tunnel_url.txt") as f:
            url = f.read().strip()
        if url:
            hostname = url.replace("https://", "")
            return {"url": url, "expo_url": f"exp://{hostname}", "active": True}
    except Exception:
        pass
    return {"url": None, "expo_url": None, "active": False}


# Server-rendered QR page — always shows current Expo Go QR code
@app.get("/api/qr-page", response_class=HTMLResponse)
async def qr_page():
    """Server-rendered QR code page for Expo Go."""
    from fastapi.responses import HTMLResponse
    expo_url = ""
    active = False
    try:
        with open("/tmp/tunnel_url.txt") as f:
            cf_url = f.read().strip()
        if cf_url:
            hostname = cf_url.replace("https://", "")
            expo_url = f"exp://{hostname}"
            active = True
    except Exception:
        pass

    qr_img = "https://api.qrserver.com/v1/create-qr-code/?size=220x220&margin=0&data=" + expo_url if active else ""
    status_color = "#4ade80" if active else "#f59e0b"
    status_text = "Tunnel Active" if active else "Starting up..."
    url_display = expo_url if active else "Tunnel starting, refresh in 15 seconds..."
    qr_block = f'<div class="qr"><img src="{qr_img}" alt="Expo QR Code"/></div>' if active else '<div class="no-qr">Tunnel starting...<br/>Refresh in 15s</div>'

    html = (
        "<!DOCTYPE html><html lang='en'><head>"
        "<meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1.0'>"
        "<meta http-equiv='refresh' content='25'>"
        "<title>Visor Finance - Expo Go</title>"
        "<style>"
        "*{margin:0;padding:0;box-sizing:border-box}"
        "body{background:#0f1117;color:#fff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:24px}"
        ".card{background:#1a1d27;border:1px solid #2a2d3a;border-radius:20px;padding:36px 44px;text-align:center;max-width:400px;width:100%}"
        ".logo{font-size:26px;font-weight:700;color:#10b981;margin-bottom:2px}"
        ".tag{font-size:13px;color:#6b7280;margin-bottom:28px}"
        ".qr{background:#fff;border-radius:14px;padding:16px;display:inline-flex;margin-bottom:20px}"
        ".qr img{width:220px;height:220px;display:block}"
        ".no-qr{background:#fff;border-radius:14px;padding:16px;display:inline-flex;align-items:center;justify-content:center;width:252px;height:252px;margin-bottom:20px;color:#6b7280;font-size:13px;text-align:center}"
        ".label{font-size:15px;color:#d1d5db;font-weight:500;margin-bottom:6px}"
        ".sub{font-size:13px;color:#6b7280;margin-bottom:16px;line-height:1.5}"
        ".url{background:#0f1117;border:1px solid #2a2d3a;border-radius:10px;padding:10px 14px;font-size:11px;color:#10b981;word-break:break-all;font-family:monospace;margin-bottom:16px}"
        ".status{font-size:13px;margin-bottom:24px}"
        ".steps{text-align:left}"
        ".step{display:flex;gap:10px;margin-bottom:12px;align-items:flex-start}"
        ".num{background:#10b981;color:#fff;border-radius:50%;width:20px;height:20px;min-width:20px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;margin-top:1px}"
        ".st{font-size:13px;color:#9ca3af;line-height:1.5}"
        ".st strong{color:#e5e7eb}"
        ".hint{font-size:11px;color:#374151;margin-top:16px}"
        "</style></head><body>"
        "<div class='card'>"
        "<div class='logo'>Visor Finance</div>"
        "<div class='tag'>Personal Finance for Indians</div>"
        f"{qr_block}"
        "<div class='label'>Scan with Expo Go</div>"
        "<div class='sub'>Open <strong>Expo Go</strong> &rarr; <strong>Scan QR Code</strong></div>"
        f"<div class='url'>{url_display}</div>"
        f"<div class='status'><span style='color:{status_color}'>&#9679; {status_text}</span></div>"
        "<div class='steps'>"
        "<div class='step'><div class='num'>1</div><div class='st'>Install <strong>Expo Go</strong> from App Store / Play Store</div></div>"
        "<div class='step'><div class='num'>2</div><div class='st'>Open Expo Go &rarr; tap <strong>Scan QR Code</strong></div></div>"
        "<div class='step'><div class='num'>3</div><div class='st'>Scan the QR above &mdash; Visor loads on your phone</div></div>"
        "<div class='step'><div class='num'>4</div><div class='st'>Login: <strong>rajesh@visor.demo</strong> / <strong>Demo@123</strong></div></div>"
        "</div>"
        "<div class='hint'>Page auto-refreshes every 25 seconds</div>"
        "</div></body></html>"
    )
    return HTMLResponse(content=html)
