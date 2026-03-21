"""
ISIN → yfinance Ticker Resolver
Resolves Indian equity ISINs (INE*) to NSE/BSE ticker symbols using yfinance.
Results are cached in-memory to avoid repeated network calls.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import yfinance as yf

logger = logging.getLogger(__name__)

# In-memory cache: ISIN → resolved ticker symbol (persists across requests)
_isin_cache: dict[str, str] = {}

_resolver_pool = ThreadPoolExecutor(max_workers=5)


def _resolve_single(isin: str) -> tuple[str, str]:
    """Resolve a single ISIN. Returns (isin, resolved_ticker)."""
    if isin in _isin_cache:
        return isin, _isin_cache[isin]
    try:
        t = yf.Ticker(isin)
        symbol = t.ticker
        if symbol and symbol != isin:
            _isin_cache[isin] = symbol
            logger.info(f"ISIN resolved: {isin} -> {symbol}")
            return isin, symbol
    except Exception as e:
        logger.debug(f"ISIN resolution failed for {isin}: {e}")
    _isin_cache[isin] = ""
    return isin, ""


def resolve_isin(isin: str) -> str:
    """Resolve a single Indian ISIN to a yfinance-compatible ticker."""
    if not isin or len(isin) < 10:
        return ""
    if not (isin.startswith("INE") or isin.startswith("INF")):
        return ""
    _, ticker = _resolve_single(isin)
    return ticker


def resolve_and_fetch_price(isin: str) -> dict | None:
    """Resolve ISIN and fetch live price in a single yfinance call.
    Returns {"symbol": ..., "price": ..., "prev_close": ...} or None."""
    if not isin or not (isin.startswith("INE") or isin.startswith("INF")):
        return None
    try:
        t = yf.Ticker(isin)
        info = t.fast_info
        price = float(info.last_price) if info.last_price else 0
        prev = float(info.previous_close) if info.previous_close else 0
        symbol = t.ticker
        if price > 0 and symbol and symbol != isin:
            _isin_cache[isin] = symbol
            return {"symbol": symbol, "price": price, "prev_close": prev}
    except Exception as e:
        logger.debug(f"ISIN resolve+fetch failed for {isin}: {e}")
    return None


def batch_resolve_and_fetch(holdings: list[dict]) -> dict[str, dict]:
    """Resolve ISINs and fetch prices in parallel for multiple holdings.
    
    Args:
        holdings: list of dicts with 'id' and 'isin' keys
    
    Returns:
        {holding_id: {"price": float, "prev_close": float, "resolved_ticker": str}}
    """
    result = {}
    futures = {}

    for h in holdings:
        isin = h.get("isin", "")
        hid = h.get("id", "")
        if not isin or not hid:
            continue

        # Check cache first
        cached = _isin_cache.get(isin)
        if cached is not None and cached == "":
            continue  # Known unresolvable ISIN

        fut = _resolver_pool.submit(resolve_and_fetch_price, isin)
        futures[fut] = hid

    for fut in as_completed(futures, timeout=90):
        hid = futures[fut]
        try:
            data = fut.result()
            if data:
                result[hid] = {
                    "price": data["price"],
                    "prev_close": data["prev_close"],
                    "resolved_ticker": data["symbol"],
                }
        except Exception as e:
            logger.debug(f"ISIN batch resolution error for {hid}: {e}")

    return result
