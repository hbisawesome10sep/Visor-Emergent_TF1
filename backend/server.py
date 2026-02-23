"""
Visor Finance - Modular FastAPI Server
A comprehensive personal finance management application.
"""

from fastapi import FastAPI
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
