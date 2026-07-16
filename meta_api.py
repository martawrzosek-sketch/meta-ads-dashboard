import json
import requests
from typing import Optional

BASE_URL = "https://graph.facebook.com/v21.0"

ACCOUNTS = {
    "🇧🇷 Brazil":            "480280715799901",
    "🇲🇽 Mexico":            "760834031039753",
    "🇨🇴 Colombia":          "2500648553500761",
    "🇩🇪 Germany":           "1386889198496439",
    "🇮🇹 Italy MioDottore": "1896796577198713",
    "🇮🇹 Italy Gipo":        "1242060572474329",
    "🇪🇸 Spain":             "417656883554148",
    "🇨🇱 Chile":             "863553356590233",
    "🇹🇷 Turkey":            "367375651",
}

ACCOUNT_CURRENCIES = {
    "🇧🇷 Brazil":            "BRL",
    "🇲🇽 Mexico":            "MXN",
    "🇨🇴 Colombia":          "COP",
    "🇩🇪 Germany":           "EUR",
    "🇮🇹 Italy MioDottore": "EUR",
    "🇮🇹 Italy Gipo":        "EUR",
    "🇪🇸 Spain":             "EUR",
    "🇨🇱 Chile":             "CLP",
    "🇹🇷 Turkey":            "TRY",
}


def get_fx_rates() -> dict:
    """Fetch EUR-based FX rates from Frankfurter. Returns {currency: units_per_eur}."""
    non_eur = sorted({c for c in ACCOUNT_CURRENCIES.values() if c != "EUR"})
    try:
        r = requests.get(
            "https://api.frankfurter.app/latest",
            params={"base": "EUR", "symbols": ",".join(non_eur)},
            timeout=10,
        )
        rates = r.json().get("rates", {})
        rates["EUR"] = 1.0
        return rates
    except Exception:
        return {"EUR": 1.0}


def _passes_filter(market: str, name: str) -> bool:
    n = name.lower()
    if "mql" not in n and "mal" not in n:
        return False
    if market == "🇩🇪 Germany" and "ebook" in n:
        return False
    return True


def _fetch_insights(account_id: str, token: str, since: str, until: str):
    url = f"{BASE_URL}/act_{account_id}/insights"
    params = {
        "access_token": token,
        "fields": "campaign_id,campaign_name,spend,impressions,frequency,cpm,ctr,cost_per_result,results,actions",
        "level": "campaign",
        "time_range": json.dumps({"since": since, "until": until}),
        "filtering": json.dumps([{"field": "spend", "operator": "GREATER_THAN", "value": "0"}]),
        "limit": 200,
    }
    all_data = []
    try:
        while url:
            r = requests.get(url, params=params, timeout=30)
            body = r.json()
            if "error" in body:
                return [], body["error"].get("message", "API error")
            all_data.extend(body.get("data", []))
            url = body.get("paging", {}).get("next")
            params = {}
        return all_data, None
    except Exception as e:
        return [], str(e)


def get_adset_data(account_id: str, campaign_id: str, token: str, since: str, until: str):
    """Fetch ad-set level insights directly from the campaign node."""
    url = f"{BASE_URL}/{campaign_id}/insights"
    params = {
        "access_token": token,
        "fields": "adset_id,adset_name,spend,impressions,frequency,cpm,ctr,cost_per_result,results,actions",
        "level": "adset",
        "time_range": json.dumps({"since": since, "until": until}),
        "limit": 100,
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        body = r.json()
        if "error" in body:
            return [], body["error"].get("message", "API error")
        return body.get("data", []), None
    except Exception as e:
        return [], str(e)


def get_account_data(market: str, token: str, since: str, until: str):
    account_id = ACCOUNTS[market]
    data, error = _fetch_insights(account_id, token, since, until)
    if error:
        return [], error

    filtered = [
        c for c in data
        if _passes_filter(market, c.get("campaign_name", ""))
        and float(c.get("spend", 0) or 0) > 0
    ]
    return filtered, None
