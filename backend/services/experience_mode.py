# /app/backend/services/experience_mode.py
"""
Experience Mode System - Core Service
Manages user experience tiers: Essential, Plus, Full
"""

from enum import Enum
from typing import Dict, List, Set, Optional
from datetime import datetime, timezone


class ExperienceMode(str, Enum):
    ESSENTIAL = "essential"
    PLUS = "plus"
    FULL = "full"


# ═══════════════════════════════════════════════════════════════════════════════
# MASTER FEATURE REGISTRY
# Central source of truth for all features and their mode availability
# ═══════════════════════════════════════════════════════════════════════════════

FEATURE_REGISTRY: Dict[str, Dict] = {
    # ───────────────────────────────────────────────────────────────────────────
    # DASHBOARD FEATURES
    # ───────────────────────────────────────────────────────────────────────────
    "dashboard_full": {
        "modes": [ExperienceMode.PLUS, ExperienceMode.FULL],
        "essential_alternative": "dashboard_snapshot",
        "description": "Full dashboard with all cards and charts",
        "category": "dashboard"
    },
    "dashboard_snapshot": {
        "modes": [ExperienceMode.ESSENTIAL, ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "3-card financial snapshot (Spent, Safe to Spend, Saved)",
        "category": "dashboard"
    },
    "dashboard_trends": {
        "modes": [ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "Income vs Expense trend charts",
        "category": "dashboard"
    },
    "net_worth_tracker": {
        "modes": [ExperienceMode.FULL],
        "description": "Detailed net worth breakdown",
        "category": "dashboard"
    },
    "financial_health_score": {
        "modes": [ExperienceMode.PLUS, ExperienceMode.FULL],
        "essential_alternative": "ai_health_summary",
        "description": "Numeric health score with detailed breakdown",
        "category": "dashboard"
    },
    "ai_daily_insight": {
        "modes": [ExperienceMode.ESSENTIAL, ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "AI-generated daily financial insight",
        "category": "dashboard"
    },
    
    # ───────────────────────────────────────────────────────────────────────────
    # TRANSACTIONS
    # ───────────────────────────────────────────────────────────────────────────
    "transactions_view": {
        "modes": [ExperienceMode.ESSENTIAL, ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "View transactions list (read-only in Essential)",
        "category": "transactions"
    },
    "transactions_crud": {
        "modes": [ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "Create, edit, delete transactions",
        "category": "transactions"
    },
    "transactions_search": {
        "modes": [ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "Search and advanced filtering",
        "category": "transactions"
    },
    "transactions_categorize": {
        "modes": [ExperienceMode.PLUS, ExperienceMode.FULL],
        "essential_alternative": "ai_categorize",
        "description": "Manual recategorization",
        "category": "transactions"
    },
    "transactions_export": {
        "modes": [ExperienceMode.FULL],
        "description": "Export transactions to CSV/Excel",
        "category": "transactions"
    },
    
    # ───────────────────────────────────────────────────────────────────────────
    # BANK IMPORT
    # ───────────────────────────────────────────────────────────────────────────
    "bank_import_auto": {
        "modes": [ExperienceMode.ESSENTIAL, ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "Automatic bank statement import",
        "category": "banking"
    },
    "bank_import_manual": {
        "modes": [ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "Manual bank account management",
        "category": "banking"
    },
    "bank_accounts_manage": {
        "modes": [ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "Add/edit/delete bank accounts",
        "category": "banking"
    },
    
    # ───────────────────────────────────────────────────────────────────────────
    # INVESTMENTS
    # ───────────────────────────────────────────────────────────────────────────
    "investments_total": {
        "modes": [ExperienceMode.ESSENTIAL, ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "Total portfolio value and P&L summary",
        "category": "investments"
    },
    "investments_holdings": {
        "modes": [ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "Individual holdings breakdown",
        "category": "investments"
    },
    "investments_sip": {
        "modes": [ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "SIP tracker and management",
        "category": "investments"
    },
    "investments_goals": {
        "modes": [ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "Goal mapping to investments",
        "category": "investments"
    },
    "investments_analytics": {
        "modes": [ExperienceMode.FULL],
        "description": "Rebalancing, risk profile, projections, what-if",
        "category": "investments"
    },
    "investments_upload": {
        "modes": [ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "Upload investment statements (Groww, Zerodha, CAS)",
        "category": "investments"
    },
    
    # ───────────────────────────────────────────────────────────────────────────
    # CREDIT CARDS
    # ───────────────────────────────────────────────────────────────────────────
    "creditcards_dues": {
        "modes": [ExperienceMode.ESSENTIAL, ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "Upcoming dues reminder",
        "category": "credit_cards"
    },
    "creditcards_list": {
        "modes": [ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "View all credit cards",
        "category": "credit_cards"
    },
    "creditcards_utilization": {
        "modes": [ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "Utilization tracking per card",
        "category": "credit_cards"
    },
    "creditcards_analytics": {
        "modes": [ExperienceMode.FULL],
        "description": "Full CC analytics, rewards, AI benefits",
        "category": "credit_cards"
    },
    "creditcards_manage": {
        "modes": [ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "Add/edit/delete credit cards",
        "category": "credit_cards"
    },
    
    # ───────────────────────────────────────────────────────────────────────────
    # TAX MODULE
    # ───────────────────────────────────────────────────────────────────────────
    "tax_basic": {
        "modes": [ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "Basic deduction summary and 80C tracker",
        "category": "tax"
    },
    "tax_full": {
        "modes": [ExperienceMode.FULL],
        "description": "Full tax module with regime comparison",
        "category": "tax"
    },
    "tax_capital_gains": {
        "modes": [ExperienceMode.FULL],
        "description": "Capital gains tracking and tax-loss harvesting",
        "category": "tax"
    },
    "tax_documents": {
        "modes": [ExperienceMode.FULL],
        "description": "Form 16, AIS, 26AS upload and parsing",
        "category": "tax"
    },
    "tax_calendar": {
        "modes": [ExperienceMode.FULL],
        "description": "Tax calendar and reminders",
        "category": "tax"
    },
    
    # ───────────────────────────────────────────────────────────────────────────
    # BOOKKEEPING
    # ───────────────────────────────────────────────────────────────────────────
    "bookkeeping_journal": {
        "modes": [ExperienceMode.FULL],
        "description": "Double-entry journal",
        "category": "bookkeeping"
    },
    "bookkeeping_pnl": {
        "modes": [ExperienceMode.FULL],
        "description": "Profit & Loss statement",
        "category": "bookkeeping"
    },
    "bookkeeping_balance_sheet": {
        "modes": [ExperienceMode.FULL],
        "description": "Balance Sheet",
        "category": "bookkeeping"
    },
    "bookkeeping_ledger": {
        "modes": [ExperienceMode.FULL],
        "description": "General Ledger",
        "category": "bookkeeping"
    },
    
    # ───────────────────────────────────────────────────────────────────────────
    # LOANS & EMI
    # ───────────────────────────────────────────────────────────────────────────
    "loans_view": {
        "modes": [ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "View loans list",
        "category": "loans"
    },
    "loans_emi_tracker": {
        "modes": [ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "EMI tracker with upcoming payments",
        "category": "loans"
    },
    "loans_amortization": {
        "modes": [ExperienceMode.FULL],
        "description": "Full amortization schedule",
        "category": "loans"
    },
    "loans_prepayment": {
        "modes": [ExperienceMode.FULL],
        "description": "Prepayment calculator",
        "category": "loans"
    },
    "loans_manage": {
        "modes": [ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "Add/edit/delete loans",
        "category": "loans"
    },
    
    # ───────────────────────────────────────────────────────────────────────────
    # FIXED ASSETS & INSURANCE
    # ───────────────────────────────────────────────────────────────────────────
    "fixed_assets": {
        "modes": [ExperienceMode.FULL],
        "description": "Fixed assets tracker",
        "category": "assets"
    },
    "insurance_policies": {
        "modes": [ExperienceMode.FULL],
        "description": "Insurance policies tracker",
        "category": "assets"
    },
    
    # ───────────────────────────────────────────────────────────────────────────
    # RECURRING TRANSACTIONS
    # ───────────────────────────────────────────────────────────────────────────
    "recurring_view": {
        "modes": [ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "View recurring transactions/SIPs",
        "category": "recurring"
    },
    "recurring_manage": {
        "modes": [ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "Add/edit/delete recurring items",
        "category": "recurring"
    },
    
    # ───────────────────────────────────────────────────────────────────────────
    # EXPORT & REPORTS
    # ───────────────────────────────────────────────────────────────────────────
    "export_pdf": {
        "modes": [ExperienceMode.FULL],
        "description": "PDF export for all reports",
        "category": "export"
    },
    "export_excel": {
        "modes": [ExperienceMode.FULL],
        "description": "Excel export for all reports",
        "category": "export"
    },
    
    # ───────────────────────────────────────────────────────────────────────────
    # AI FEATURES (Available to all, behavior may differ)
    # ───────────────────────────────────────────────────────────────────────────
    "ai_chat": {
        "modes": [ExperienceMode.ESSENTIAL, ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "Full AI chat access",
        "category": "ai"
    },
    "ai_voice": {
        "modes": [ExperienceMode.ESSENTIAL, ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "Voice chat with AI",
        "category": "ai"
    },
    "ai_insights": {
        "modes": [ExperienceMode.ESSENTIAL, ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "AI-generated insights and recommendations",
        "category": "ai"
    },
    "ai_morning_brief": {
        "modes": [ExperienceMode.ESSENTIAL, ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "AI morning brief",
        "category": "ai"
    },
    
    # ───────────────────────────────────────────────────────────────────────────
    # SETTINGS
    # ───────────────────────────────────────────────────────────────────────────
    "settings_profile": {
        "modes": [ExperienceMode.ESSENTIAL, ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "Profile settings",
        "category": "settings"
    },
    "settings_mode": {
        "modes": [ExperienceMode.ESSENTIAL, ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "Experience mode selector",
        "category": "settings"
    },
    "settings_data_management": {
        "modes": [ExperienceMode.PLUS, ExperienceMode.FULL],
        "description": "Data management (clear data, etc.)",
        "category": "settings"
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_user_features(mode: ExperienceMode) -> Set[str]:
    """Get all features available for a given mode"""
    return {
        feature_id 
        for feature_id, config in FEATURE_REGISTRY.items() 
        if mode in config["modes"]
    }


def is_feature_available(feature_id: str, mode: ExperienceMode) -> bool:
    """Check if a specific feature is available in the given mode"""
    if feature_id not in FEATURE_REGISTRY:
        return True  # Unknown features default to available (fail-open)
    return mode in FEATURE_REGISTRY[feature_id]["modes"]


def get_feature_info(feature_id: str) -> Optional[Dict]:
    """Get information about a specific feature"""
    return FEATURE_REGISTRY.get(feature_id)


def get_upgrade_features(current_mode: ExperienceMode, target_mode: ExperienceMode) -> List[str]:
    """Get features that would be unlocked by upgrading"""
    current_features = get_user_features(current_mode)
    target_features = get_user_features(target_mode)
    return list(target_features - current_features)


def get_features_by_category(mode: ExperienceMode, category: str) -> List[str]:
    """Get all features in a category available for a mode"""
    return [
        feature_id
        for feature_id, config in FEATURE_REGISTRY.items()
        if config.get("category") == category and mode in config["modes"]
    ]


def get_hidden_features(mode: ExperienceMode) -> Set[str]:
    """Get features NOT available in the given mode"""
    all_features = set(FEATURE_REGISTRY.keys())
    available = get_user_features(mode)
    return all_features - available


def get_mode_summary(mode: ExperienceMode) -> Dict:
    """Get a summary of what a mode offers"""
    available = get_user_features(mode)
    hidden = get_hidden_features(mode)
    
    # Group by category
    categories = {}
    for feature_id in available:
        cat = FEATURE_REGISTRY[feature_id].get("category", "other")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(feature_id)
    
    return {
        "mode": mode.value,
        "total_features": len(available),
        "hidden_features": len(hidden),
        "categories": categories
    }


# Mode display information
MODE_INFO = {
    ExperienceMode.ESSENTIAL: {
        "title": "Essential",
        "subtitle": "Just keep it simple",
        "description": "AI does the heavy lifting. See only what matters most.",
        "icon": "leaf",
        "color": "#10B981",
        "highlights": [
            "AI chat as your home screen",
            "Monthly spending snapshot",
            "Smart alerts only",
            "Auto bank import"
        ]
    },
    ExperienceMode.PLUS: {
        "title": "Plus",
        "subtitle": "I want more visibility",
        "description": "Full control with context-aware guidance.",
        "icon": "chart-line",
        "color": "#6366F1",
        "highlights": [
            "Everything in Essential",
            "Full transaction management",
            "Holdings & SIP tracking",
            "Financial Health Score"
        ]
    },
    ExperienceMode.FULL: {
        "title": "Full",
        "subtitle": "Give me everything",
        "description": "The entire Visor platform unlocked for power users.",
        "icon": "rocket-launch",
        "color": "#F59E0B",
        "highlights": [
            "Everything in Plus",
            "Double-entry bookkeeping",
            "Full tax module",
            "PDF/Excel exports"
        ]
    }
}
