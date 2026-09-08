"""
HubSpot funnel data — Colombia Meta Ads downstream metrics.
Queries the HubSpot CRM v3 REST API directly using a private app token.

Lifecycle stage IDs (Docplanner custom):
  MQL         = 62911300
  UNQUALIFIED = 62713234
  RECYCLED UQ = 63037843
"""
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Optional

HS_BASE = "https://api.hubapi.com"

LCS_UNQUALIFIED = "62713234"
LCS_RECYCLED_UQ = "63037843"

# Segments to query for Colombia.
# utm_tokens: all must be present (AND).  utm_exclude: none must be present.
# Mirrors the campaign-name logic in analysis.py classify_product().
CO_SEGMENTS = [
    {
        "key":         "individuals_agenda",
        "label":       "Individuals · Agenda Premium",
        "utm_tokens":  ["co_doc"],
        "utm_exclude": ["co_doc-fac", "noa"],
    },
    {
        "key":         "individuals_noa",
        "label":       "Individuals · NOA",
        "utm_tokens":  ["co_doc", "noa"],
        "utm_exclude": ["co_doc-fac"],
    },
    {
        "key":         "clinics_prs",
        "label":       "Clinics PRS · Clinic Agenda",
        "utm_tokens":  ["co_doc-fac"],
        "utm_exclude": [],
    },
]


def _to_ms(date_str: str) -> str:
    """Convert YYYY-MM-DD to millisecond timestamp string required by HubSpot BETWEEN."""
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return str(int(dt.timestamp() * 1000))


# ── HTTP helpers ───────────────────────────────────────────────────────────────

def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _post(endpoint: str, token: str, payload: dict, _retries: int = 4) -> dict:
    delay = 1.0
    for attempt in range(_retries):
        r = requests.post(
            f"{HS_BASE}{endpoint}",
            headers=_headers(token),
            json=payload,
            timeout=30,
        )
        if r.status_code == 401:
            raise ValueError("HubSpot token invalid or expired")
        if r.status_code == 429:
            if attempt < _retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise ValueError(f"HubSpot {r.status_code} on {endpoint}: {r.text[:400]}")
        if not r.ok:
            raise ValueError(f"HubSpot {r.status_code} on {endpoint}: {r.text[:400]}")
        return r.json()
    raise ValueError(f"HubSpot rate limit not resolved after {_retries} retries")


# ── Contact helpers ────────────────────────────────────────────────────────────

def _contact_ids_and_total(token: str, filter_groups: list, max_ids: int = 600) -> tuple[list, int]:
    """Fetch contact IDs (up to max_ids) and the total count in one pass."""
    ids, after, total = [], None, 0
    while len(ids) < max_ids:
        body = {
            "filterGroups": filter_groups,
            "limit": 200,
            "properties": ["hs_object_id"],
        }
        if after:
            body["after"] = after
        resp = _post("/crm/v3/objects/contacts/search", token, body)
        if not after:
            total = resp.get("total", 0)
        ids.extend(int(r["id"]) for r in resp.get("results", []))
        after = (resp.get("paging") or {}).get("next", {}).get("after")
        if not after:
            break
    return ids, total


def _contact_count(token: str, filter_groups: list) -> int:
    body = {"filterGroups": filter_groups, "limit": 1, "properties": ["hs_object_id"]}
    return _post("/crm/v3/objects/contacts/search", token, body).get("total", 0)


# ── Deal helpers ───────────────────────────────────────────────────────────────

def _associated_deal_ids(token: str, contact_ids: list) -> set:
    """Use the CRM associations API to get all deal IDs linked to these contacts."""
    deal_ids = set()
    for i in range(0, len(contact_ids), 100):
        batch = [{"id": str(cid)} for cid in contact_ids[i : i + 100]]
        try:
            resp = _post(
                "/crm/v4/associations/contacts/deals/batch/read",
                token,
                {"inputs": batch},
            )
            for item in resp.get("results", []):
                for assoc in item.get("to", []):
                    deal_ids.add(str(assoc["toObjectId"]))
        except Exception:
            pass
    return deal_ids


def _deal_ids_for_contacts(
    token: str,
    contact_ids: list,
    extra_filters: Optional[list] = None,
) -> set:
    """Return unique deal IDs associated with the given contacts, filtered by extra_filters."""
    if not contact_ids:
        return set()

    # Step 1: get all deal IDs linked to these contacts via the associations API
    assoc_ids = _associated_deal_ids(token, contact_ids)
    if not assoc_ids:
        return set()
    if not extra_filters:
        return assoc_ids

    # Step 2: filter those deals by extra_filters + hs_object_id IN batch
    filtered: set = set()
    id_list = list(assoc_ids)
    for i in range(0, len(id_list), 100):
        batch = id_list[i : i + 100]
        body = {
            "filterGroups": [{
                "filters": [
                    {"propertyName": "hs_object_id", "operator": "IN", "values": batch},
                    *extra_filters,
                ]
            }],
            "limit": 100,
            "properties": ["hs_object_id"],
        }
        try:
            resp = _post("/crm/v3/objects/deals/search", token, body)
            for r in resp.get("results", []):
                filtered.add(r["id"])
        except Exception:
            pass
    return filtered


# ── Filter builders ────────────────────────────────────────────────────────────

def _base_filters(date_from: str, date_to: str, utm_tokens: list[str], utm_exclude: list[str]) -> list:
    """
    Build contact search filters for Colombia Meta MQLs.

    Segmentation is done entirely via utm_campaign tokens — mirrors the
    campaign-name logic in analysis.py — so we don't rely on product
    recommendation properties that may be set late or from other channels.

    mql_last_touch_channel_wf = "Paid Social [Facebook]" ensures we only
    count contacts whose last MQL touch was Meta, not other channels that
    happen to share the same utm_campaign pattern.
    """
    filters = [
        {
            "propertyName": "mql_last_touch_channel_wf",
            "operator":     "EQ",
            "value":        "Paid Social [Facebook]",
        },
        {
            "propertyName": "lcs_mql_at_test",
            "operator":     "BETWEEN",
            "value":        _to_ms(date_from),
            "highValue":    _to_ms(date_to),
        },
    ]
    for tok in utm_tokens:
        filters.append({
            "propertyName": "utm_campaign",
            "operator":     "CONTAINS_TOKEN",
            "value":        tok,
        })
    for tok in utm_exclude:
        filters.append({
            "propertyName": "utm_campaign",
            "operator":     "NOT_CONTAINS_TOKEN",
            "value":        tok,
        })
    return filters


# ── Per-segment fetcher ────────────────────────────────────────────────────────

def _fetch_segment(token: str, seg: dict, date_from: str, date_to: str) -> dict:
    """
    Fetch all funnel metrics for one segment.
    Runs unqualified count in parallel with contact ID fetch,
    then open-deals and WONs in parallel.
    """
    base    = _base_filters(date_from, date_to, seg["utm_tokens"], seg["utm_exclude"])
    fgs_all = [{"filters": base}]
    fgs_uq  = [{"filters": base + [{
        "propertyName": "lifecyclestage",
        "operator":     "IN",
        "values":       [LCS_UNQUALIFIED, LCS_RECYCLED_UQ],
    }]}]

    # Unqualified count + contact ID fetch run in parallel
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_uq  = ex.submit(_contact_count, token, fgs_uq)
        f_ids = ex.submit(_contact_ids_and_total, token, fgs_all)
        unqualified          = f_uq.result()
        contact_ids, mqls    = f_ids.result()

    net_qual = max(0, mqls - unqualified)

    # Open deals + WONs in parallel
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_open = ex.submit(
            _deal_ids_for_contacts, token, contact_ids,
            [{"propertyName": "hs_is_closed", "operator": "EQ", "value": "false"}],
        )
        f_wons = ex.submit(
            _deal_ids_for_contacts, token, contact_ids,
            [
                {"propertyName": "hs_is_closed_won", "operator": "EQ",      "value": "true"},
                {"propertyName": "closedate",        "operator": "BETWEEN",
                 "value": _to_ms(date_from),         "highValue": _to_ms(date_to)},
            ],
        )
        open_deals = len(f_open.result())
        wons       = len(f_wons.result())

    return {
        "label":         seg["label"],
        "mqls":          mqls,
        "unqualified":   unqualified,
        "net_qualified": net_qual,
        "open_deals":    open_deals,
        "wons":          wons,
    }


# ── Main export ────────────────────────────────────────────────────────────────

def get_co_funnel(token: str, date_from: str, date_to: str) -> tuple[dict, Optional[str]]:
    """
    Return Colombia Meta → HubSpot funnel for the given date range.
    All three segments are fetched in parallel.
    """
    result = {}
    try:
        with ThreadPoolExecutor(max_workers=2) as ex:
            futures = {
                ex.submit(_fetch_segment, token, seg, date_from, date_to): seg["key"]
                for seg in CO_SEGMENTS
            }
            for f in as_completed(futures):
                result[futures[f]] = f.result()
    except ValueError as e:
        return {}, str(e)
    except Exception as e:
        return {}, f"HubSpot API error: {e}"

    return result, None


def validate_token(token: str) -> Optional[str]:
    """Return None if token is valid, else an error message."""
    try:
        r = requests.get(
            f"{HS_BASE}/crm/v3/objects/contacts",
            headers=_headers(token),
            params={"limit": 1},
            timeout=10,
        )
        if r.status_code == 401:
            return "Token invalid or expired"
        r.raise_for_status()
        return None
    except Exception as e:
        return str(e)
