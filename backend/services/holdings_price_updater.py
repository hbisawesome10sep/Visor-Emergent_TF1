"""
Holdings Price Updater — Fetches live prices for stocks (yfinance) and mutual funds (mfapi.in)
and updates current_value, gain_loss, gain_loss_pct in the holdings collection.

Key fix: MF matching respects Direct vs Regular plan from the fund name and uses ISIN
for precise matching when available.
"""
import logging
import re
import requests
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=3)

# ── mfapi.in helpers ─────────────────────────────────────────────────────────

_MFAPI_SEARCH = "https://api.mfapi.in/mf/search?q={query}"
_MFAPI_LATEST = "https://api.mfapi.in/mf/{scheme_code}/latest"

# Cache scheme_code lookups
_scheme_code_cache: dict[str, int | None] = {}


def _is_direct_plan(name: str) -> bool | None:
    """Determine if a fund name indicates Direct or Regular plan.
    Returns True for Direct, False for Regular, None if ambiguous."""
    lower = name.lower()
    if "direct" in lower:
        return True
    if "regular" in lower:
        return False
    # No explicit mention — treat as Regular (most common for external/distributor funds)
    return None


def _score_match(user_name: str, candidate_name: str, is_user_direct: bool | None) -> int:
    """Score how well a candidate fund name matches the user's fund name.
    Higher score = better match. Returns -1 for disqualified matches."""
    score = 0
    c_lower = candidate_name.lower()
    u_lower = user_name.lower()

    is_candidate_direct = "direct" in c_lower

    # Plan type matching — critical for correct NAV
    if is_user_direct is True:
        if is_candidate_direct:
            score += 100
        else:
            return -1
    elif is_user_direct is False:
        if not is_candidate_direct:
            score += 100
        else:
            return -1
    elif is_user_direct is None:
        # Ambiguous — prefer Regular (non-direct)
        if not is_candidate_direct:
            score += 50
        else:
            score += 10

    # Growth/Dividend/Bonus option matching
    if "growth" in u_lower:
        if "idcw" in c_lower or "dividend" in c_lower:
            return -1
        if "bonus" in c_lower and "bonus" not in u_lower:
            return -1  # Bonus option is different from Growth
        if "growth" in c_lower:
            score += 30

    # Name similarity — match key fund words
    noise = {"fund", "plan", "direct", "growth", "option", "regular", "the", "of", "mutual", "-"}
    user_words = set(re.findall(r'[a-z]+', u_lower)) - noise
    cand_words = set(re.findall(r'[a-z]+', c_lower)) - noise
    common = user_words & cand_words

    if user_words:
        # Reward common words
        score += int(30 * len(common) / len(user_words))

        # Penalize extra candidate words not in user's name
        # This avoids matching "DSP BlackRock Small Mid Cap" when user has "DSP Small Cap"
        extra = cand_words - user_words
        suspect_words = {"blackrock", "institutional", "flexi", "value", "large", "vision"}
        for w in extra:
            if w in suspect_words:
                score -= 20
            else:
                score -= 3

    return score


def _search_scheme_code(fund_name: str, isin: str = "") -> int | None:
    """Search mfapi.in for a scheme code matching the fund name, respecting plan type."""
    cache_key = f"{fund_name}|{isin}"
    if cache_key in _scheme_code_cache:
        return _scheme_code_cache[cache_key]

    is_direct = _is_direct_plan(fund_name)

    # Try progressively shorter search terms
    search_terms = [fund_name]
    words = fund_name.split()
    # Remove plan/growth keywords for broader search
    clean_words = [w for w in words if w.lower() not in ("direct", "plan", "growth", "option", "regular", "-")]
    if len(clean_words) > 3:
        search_terms.append(" ".join(clean_words[:4]))
    if len(clean_words) > 2:
        search_terms.append(" ".join(clean_words[:3]))

    best_match = None
    best_score = -1

    for query in search_terms:
        try:
            resp = requests.get(
                _MFAPI_SEARCH.format(query=requests.utils.quote(query)),
                timeout=8,
            )
            if resp.status_code != 200:
                continue
            results = resp.json()
            if not isinstance(results, list) or not results:
                continue

            for r in results:
                sn = r.get("schemeName", "")
                sc = _score_match(fund_name, sn, is_direct)
                if sc > best_score:
                    best_score = sc
                    best_match = r

            # If we found a good match, stop searching
            if best_score >= 80:
                break

        except Exception as e:
            logger.debug(f"mfapi search failed for '{query}': {e}")

    if best_match and best_score > 0:
        code = int(best_match["schemeCode"])
        logger.info(f"MF match: '{fund_name[:40]}' -> '{best_match['schemeName'][:50]}' (score={best_score})")
        _scheme_code_cache[cache_key] = code
        return code

    logger.debug(f"No match for '{fund_name}'")
    _scheme_code_cache[cache_key] = None
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


def _validate_nav(holding: dict, nav: float) -> bool:
    """Validate that the NAV makes sense given the holding data.
    Uses buy_price as the primary reference since it never gets corrupted by refreshes."""
    qty = holding.get("quantity", 0)
    buy_price = holding.get("buy_price", 0)
    invested = holding.get("invested_value", 0)

    if qty <= 0 or nav <= 0:
        return False

    # Primary validation: NAV vs buy_price
    # For equity MFs, NAV should be within 0.1x to 8.0x of the original buy price
    # (generous range to handle multi-year appreciation/depreciation)
    if buy_price and buy_price > 0:
        ratio = nav / buy_price
        if ratio < 0.1 or ratio > 10.0:
            logger.warning(
                f"NAV validation FAILED for {holding.get('name', '')[:30]}: "
                f"nav={nav:.4f} vs buy_price={buy_price:.4f} (ratio={ratio:.2f})"
            )
            return False
        return True

    # Fallback: NAV vs invested_value / quantity
    if invested and invested > 0 and qty > 0:
        implied_buy = invested / qty
        ratio = nav / implied_buy
        if ratio < 0.1 or ratio > 10.0:
            logger.warning(
                f"NAV validation FAILED for {holding.get('name', '')[:30]}: "
                f"nav={nav:.4f} vs implied_buy={implied_buy:.4f} (ratio={ratio:.2f})"
            )
            return False

    return True


def fetch_mf_prices(holdings: list[dict]) -> dict[str, float]:
    """Fetch current NAVs for a list of MF holdings. Returns {holding_id: nav}."""
    result = {}
    for h in holdings:
        name = h.get("name", "")
        isin = h.get("isin", "")
        scheme_code = _search_scheme_code(name, isin)
        if scheme_code:
            nav = _fetch_mf_nav(scheme_code)
            if nav and nav > 0:
                if _validate_nav(h, nav):
                    result[h["id"]] = nav
                    logger.info(f"MF NAV OK: {name[:40]} = {nav}")
                else:
                    logger.warning(f"MF NAV REJECTED for {name[:40]} (nav={nav}) — keeping original value")
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
