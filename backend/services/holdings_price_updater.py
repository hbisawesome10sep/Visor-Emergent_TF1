"""
Holdings Price Updater — Fetches live prices for stocks (yfinance) and mutual funds (mfapi.in)
and updates current_value, gain_loss, gain_loss_pct in the holdings collection.
"""
import logging
import requests
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=3)

# ── mfapi.in helpers ─────────────────────────────────────────────────────────

_MFAPI_SEARCH = "https://api.mfapi.in/mf/search?q={query}"
_MFAPI_LATEST = "https://api.mfapi.in/mf/{scheme_code}/latest"

# Cache scheme_code lookups to avoid repeated searches
_scheme_code_cache: dict[str, int | None] = {}


def _search_scheme_code(fund_name: str) -> int | None:
    """Search mfapi.in for a scheme code matching the fund name."""
    if fund_name in _scheme_code_cache:
        return _scheme_code_cache[fund_name]

    # Try progressively shorter search terms
    search_terms = [fund_name]
    words = fund_name.split()
    if len(words) > 3:
        search_terms.append(" ".join(words[:4]))
    if len(words) > 2:
        search_terms.append(" ".join(words[:3]))

    for query in search_terms:
        try:
            resp = requests.get(
                _MFAPI_SEARCH.format(query=requests.utils.quote(query)),
                timeout=8,
            )
            if resp.status_code == 200:
                results = resp.json()
                if isinstance(results, list) and results:
                    # Try exact match first
                    for r in results:
                        if r.get("schemeName", "").strip().lower() == fund_name.strip().lower():
                            code = int(r["schemeCode"])
                            _scheme_code_cache[fund_name] = code
                            return code
                    # Fallback: pick first direct-growth match
                    for r in results:
                        name_lower = r.get("schemeName", "").lower()
                        if "direct" in name_lower and "growth" in name_lower:
                            code = int(r["schemeCode"])
                            _scheme_code_cache[fund_name] = code
                            return code
                    # Fallback: first result
                    code = int(results[0]["schemeCode"])
                    _scheme_code_cache[fund_name] = code
                    return code
        except Exception as e:
            logger.debug(f"mfapi search failed for '{query}': {e}")

    _scheme_code_cache[fund_name] = None
    return None


def _fetch_mf_nav(scheme_code: int) -> float | None:
    """Fetch latest NAV for a mutual fund by scheme code."""
    try:
        resp = requests.get(_MFAPI_LATEST.format(scheme_code=scheme_code), timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            nav_data = data.get("data")
            if isinstance(nav_data, list) and nav_data:
                return float(nav_data[0].get("nav", 0))
            elif isinstance(nav_data, dict):
                return float(nav_data.get("nav", 0))
    except Exception as e:
        logger.debug(f"mfapi NAV fetch failed for {scheme_code}: {e}")
    return None


def fetch_mf_prices(holdings: list[dict]) -> dict[str, float]:
    """Fetch current NAVs for a list of MF holdings. Returns {holding_id: nav}."""
    result = {}
    for h in holdings:
        name = h.get("name", "")
        scheme_code = _search_scheme_code(name)
        if scheme_code:
            nav = _fetch_mf_nav(scheme_code)
            if nav and nav > 0:
                result[h["id"]] = nav
                logger.info(f"MF NAV: {name[:40]} = {nav}")
            else:
                logger.debug(f"MF NAV not found for {name}")
        else:
            logger.debug(f"Scheme code not found for {name}")
    return result


# ── yfinance helpers ─────────────────────────────────────────────────────────

def fetch_stock_prices(holdings: list[dict]) -> dict[str, dict]:
    """Fetch current prices for stock holdings. Returns {holding_id: {price, prev_close}}."""
    result = {}
    ticker_map = {}  # yf_ticker -> holding_id

    for h in holdings:
        ticker = h.get("ticker", "")
        if not ticker:
            continue
        # Ensure .NS suffix for Indian stocks
        yf_ticker = ticker if "." in ticker else f"{ticker}.NS"
        ticker_map[yf_ticker] = h["id"]

    if not ticker_map:
        return result

    try:
        tickers_str = " ".join(ticker_map.keys())
        tickers = yf.Tickers(tickers_str)
        for yf_t, hid in ticker_map.items():
            try:
                t = tickers.tickers[yf_t]
                info = t.fast_info
                price = float(info.last_price) if info.last_price else 0
                prev = float(info.previous_close) if info.previous_close else 0
                if price > 0:
                    result[hid] = {"price": price, "prev_close": prev}
                    logger.info(f"Stock: {yf_t} = {price}")
            except Exception as e:
                logger.debug(f"yfinance error for {yf_t}: {e}")
    except Exception as e:
        logger.error(f"yfinance batch error: {e}")

    return result
