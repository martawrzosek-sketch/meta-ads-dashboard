import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

st.set_page_config(
    page_title="Meta Ads · Docplanner",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

TOKEN_FILE    = Path(__file__).parent / ".token"
TOKEN_FILE_HS = Path(__file__).parent / ".token_hs"
_LOGO = Path(__file__).parent / "logo.svg"

# ── Brand CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"], .stApp, button, input, textarea, select {
    font-family: 'Figtree', sans-serif !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #F2FAF8;
    border-right: 1px solid #D0EDE8;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stCaption { color: #4A6B66; }

/* Multiselect tags — teal, not red */
[data-baseweb="tag"] {
    background-color: #00A085 !important;
    border-radius: 6px !important;
}
[data-baseweb="tag"] span { color: white !important; }
[data-baseweb="tag"] svg { fill: white !important; }

/* Metric cards — teal left accent */
[data-testid="metric-container"] {
    border: 1px solid #E0F0EC;
    border-left: 4px solid #00A085;
    border-radius: 8px;
    padding: 12px 16px;
    background: #FAFFFE;
}
[data-testid="stMetricValue"] { font-size: 1.2rem; color: #242727; }
[data-testid="stMetricLabel"] { color: #6B8C88; font-size: 0.78rem; }

/* Buttons */
button[kind="primary"] {
    background-color: #00A085 !important;
    border-color: #00A085 !important;
    color: white !important;
}
button[kind="primary"]:hover { background-color: #008572 !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { border-bottom: 2px solid #D0EDE8; gap: 4px; }
.stTabs [data-baseweb="tab"] { border-radius: 6px 6px 0 0; color: #6B8C88; }
.stTabs [aria-selected="true"] { color: #00A085 !important; font-weight: 600; }

/* Bordered containers */
[data-testid="stVerticalBlockBorderWrapper"] > div {
    border-color: #D0EDE8 !important;
    border-radius: 10px !important;
}

/* Section subheaders */
h5 { color: #00A085; letter-spacing: 0.02em; }

/* Expander */
[data-testid="stExpander"] summary { font-weight: 500; color: #242727; }
[data-testid="stExpander"] summary:hover { color: #00A085; }

/* Dividers */
hr { border-color: #D0EDE8; }
</style>
""", unsafe_allow_html=True)

if _LOGO.exists():
    st.logo(str(_LOGO))


def load_token():
    # Streamlit Cloud: read from st.secrets
    try:
        t = st.secrets.get("META_ADS_TOKEN", "")
        if t:
            return t.strip()
    except Exception:
        pass
    # Local: read from .token file
    return TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else ""


def save_token(t: str):
    TOKEN_FILE.write_text(t.strip())


def load_hs_token() -> str:
    try:
        t = st.secrets.get("HUBSPOT_TOKEN", "")
        if t:
            return t.strip()
    except Exception:
        pass
    return TOKEN_FILE_HS.read_text().strip() if TOKEN_FILE_HS.exists() else ""


def save_hs_token(t: str):
    TOKEN_FILE_HS.write_text(t.strip())


# ── Sidebar ────────────────────────────────────────────────────────────────
token = load_token()
selected_markets = []
selected_products = []
selected_types = []
start_date = end_date = prev_start = prev_end = None
refresh = False

with st.sidebar:
    st.caption("Meta Ads · Campaign Dashboard")
    st.divider()

    if not token:
        st.markdown("### ⚙️ Setup")
        t_in = st.text_input(
            "Access Token", type="password",
            help="Meta Business Manager → System Users → Generate Token (ads_read + read_insights)"
        )
        if st.button("Save", type="primary", use_container_width=True):
            if t_in.strip():
                save_token(t_in)
                st.rerun()
            else:
                st.error("Token is required")

    else:
        from meta_api import ACCOUNTS
        all_markets = list(ACCOUNTS.keys())

        selected_markets = st.multiselect(
            "Markets", all_markets, default=all_markets,
        )

        ALL_PRODUCTS = ["NOA", "AGENDA", "FEEGOW", "CLINIC CLOUD", "GIPO", "OTHER"]
        selected_products = st.multiselect(
            "Product", ALL_PRODUCTS, default=ALL_PRODUCTS,
        )

        selected_types = st.multiselect(
            "Type", ["MQL", "MAL"], default=["MQL", "MAL"],
        )

        st.divider()

        period = st.selectbox(
            "Time period",
            ["Last 7 days", "Last 14 days", "Last 30 days", "Custom"],
        )

        today = datetime.now().date()

        if period == "Custom":
            col_a, col_b = st.columns(2)
            with col_a:
                start_date = st.date_input("From", value=today - timedelta(days=7))
            with col_b:
                end_date = st.date_input("To", value=today)
            if start_date >= end_date:
                st.error("Start must be before end")
                st.stop()
        else:
            n = {"Last 7 days": 7, "Last 14 days": 14, "Last 30 days": 30}[period]
            end_date   = today
            start_date = today - timedelta(days=n)

        span      = max((end_date - start_date).days, 1)
        prev_end  = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=span)

        st.caption(f"Current: {start_date.strftime('%b %d')} – {end_date.strftime('%b %d')}")
        st.caption(f"vs prev: {prev_start.strftime('%b %d')} – {prev_end.strftime('%b %d')}")

        st.divider()
        refresh = st.button("🔄 Refresh Data", type="primary", use_container_width=True)

        if st.button("🔑 Change token", use_container_width=True):
            TOKEN_FILE.unlink(missing_ok=True)
            st.rerun()

        st.divider()
        st.caption("HubSpot · Funnel data")
        hs_token = load_hs_token()
        if not hs_token:
            hs_in = st.text_input(
                "HubSpot token", type="password",
                help="HubSpot → Settings → Private Apps → Create app (contacts + deals read scopes)",
                key="hs_token_input",
            )
            if st.button("Save HS token", use_container_width=True):
                if hs_in.strip():
                    save_hs_token(hs_in)
                    st.rerun()
                else:
                    st.error("Token required")
        else:
            st.caption("✅ HubSpot connected")
            if st.button("🔑 Change HS token", use_container_width=True):
                TOKEN_FILE_HS.unlink(missing_ok=True)
                st.rerun()


# ── No-token landing ───────────────────────────────────────────────────────
if not token:
    st.title("Docplanner Meta Ads Dashboard")
    st.info("Enter your Meta Ads access token in the sidebar to get started.")

    with st.expander("How to get a token"):
        st.markdown("""
1. Go to **Meta Business Manager** → **Settings → Users → System Users**
2. Select (or create) a system user
3. Click **Generate New Token** → choose all relevant ad accounts
4. Grant permissions: `ads_read`, `read_insights`
5. Copy the token and paste it in the sidebar
        """)
    st.stop()


# ── Imports (token exists) ─────────────────────────────────────────────────
from meta_api import ACCOUNTS, ACCOUNT_CURRENCIES, get_account_data, get_adset_data, get_fx_rates
from analysis import analyze_market, campaign_type, classify_product
import state
import json, os

# ── DWH MQL lookup (refreshed by running Claude session) ──────────────────
_DWH_MQL_PATH = os.path.join(os.path.dirname(__file__), "dwh_mqls.json")
try:
    with open(_DWH_MQL_PATH) as _f:
        _dwh = json.load(_f)
    DWH_MQLS: dict = _dwh.get("mqls_by_campaign", {})
    DWH_MQL_DATE = _dwh.get("fetched_at", "?")
except Exception:
    DWH_MQLS = {}
    DWH_MQL_DATE = None


# ── Data fetching with caching ─────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def _fetch(market, tok, since, until):
    return get_account_data(market, tok, since, until)

@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_adsets(account_id, campaign_id, tok, since, until):
    return get_adset_data(account_id, campaign_id, tok, since, until)


@st.cache_data(ttl=86400, show_spinner=False)
def _fetch_fx():
    return get_fx_rates()


def _convert_to_eur(items: list, currency: str, fx_rates: dict) -> list:
    if currency == "EUR" or not fx_rates:
        return items
    rate = fx_rates.get(currency, 1.0)
    if rate == 1.0:
        return items
    result = []
    for row in items:
        row2 = dict(row)
        for field in ("spend", "cost_per_result", "cpm"):
            v = row2.get(field)
            if v is not None:
                try:
                    row2[field] = str(float(v) / rate)
                except (ValueError, TypeError):
                    pass
        result.append(row2)
    return result


if refresh:
    st.cache_data.clear()

cache_key = f"{','.join(sorted(selected_markets))}|{start_date}|{end_date}"
needs_fetch = (
    "result_key" not in st.session_state
    or st.session_state["result_key"] != cache_key
    or refresh
)

if needs_fetch:
    all_flags, all_opps, all_stable, errors = [], [], [], []
    pb = st.progress(0, "Fetching campaign data…")
    fx_rates = _fetch_fx()

    for i, market in enumerate(selected_markets):
        pb.progress(i / max(len(selected_markets), 1), f"Fetching {market}…")
        account_id = ACCOUNTS[market]
        currency = ACCOUNT_CURRENCIES.get(market, "EUR")

        curr_raw, e1 = _fetch(market, token, start_date.isoformat(), end_date.isoformat())
        prev_raw, e2 = _fetch(market, token, prev_start.isoformat(), prev_end.isoformat())
        curr = _convert_to_eur(curr_raw, currency, fx_rates)
        prev = _convert_to_eur(prev_raw, currency, fx_rates)

        if e1:
            errors.append(f"{market}: {e1}")
            continue

        f, o, s = analyze_market(market, curr, prev, account_id)
        all_flags  += f
        all_opps   += o
        all_stable += s

    pb.empty()

    st.session_state["result"] = dict(
        flags=all_flags, opps=all_opps, stable=all_stable,
        errors=errors, at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    st.session_state["result_key"] = cache_key

R = st.session_state["result"]
all_campaigns = R["flags"] + R["opps"] + R["stable"]

# ── Apply sidebar filters ──────────────────────────────────────────────────
def _passes(c):
    if selected_products and c["product"] not in selected_products:
        return False
    if selected_types and campaign_type(c["campaign_name"]) not in selected_types:
        return False
    return True

flags_view  = [c for c in R["flags"] if _passes(c)]
opps_view   = [c for c in R["opps"]  if _passes(c)]
stable_view = [c for c in R["stable"] if _passes(c)]
all_view    = flags_view + opps_view + stable_view


# ── Top-line metrics ───────────────────────────────────────────────────────
total_spend = sum(c["spend"] for c in all_view)
total_leads = sum(c["leads"] for c in all_view)
avg_cpl     = total_spend / total_leads if total_leads else 0
n_urgent    = sum(1 for c in flags_view for f in c["flags"] if f["severity"] == "urgent")
n_warning   = sum(1 for c in flags_view for f in c["flags"] if f["severity"] == "warning")
n_opps      = sum(len(c["opportunities"]) for c in opps_view)

st.title("Meta Ads Dashboard")

st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.2rem; }
</style>
""", unsafe_allow_html=True)

cols = st.columns(6)
cols[0].metric("Spend",      f"€{total_spend:,.0f}")
cols[1].metric("Leads",      f"{total_leads:,}")
cols[2].metric("Avg CPL",    f"€{avg_cpl:,.2f}" if avg_cpl else "—")
cols[3].metric("🔴 Urgent",  n_urgent)
cols[4].metric("🟡 Watch",   n_warning)
cols[5].metric("🚀 Opps",    n_opps)

if R["errors"]:
    st.warning("Errors: " + " | ".join(R["errors"]))

st.caption(
    f"Fetched: {R['at']}  ·  {len(selected_markets)} markets  ·  "
    f"{len(all_view)} campaigns (filtered)  ·  all spend in EUR"
)


# ── Action-item card renderer ──────────────────────────────────────────────
def _key(campaign, item) -> str:
    return f"{campaign['market']}|{campaign['campaign_id']}|{item['type']}"


_ADSET_SORT = {
    "frequency_critical":  ("frequency", False),
    "frequency_warning":   ("frequency", False),
    "cpl_spike":           ("cpl",       False),
    "cpl_rise":            ("cpl",       False),
    "ctr_drop_critical":   ("ctr",       True),
    "ctr_drop_warning":    ("ctr",       True),
    "leads_drop_critical": ("leads",     True),
    "leads_drop_warning":  ("leads",     True),
    "scale_improving_cpl": ("cpl",       True),
    "scale_low_frequency": ("frequency", True),
    "zero_leads":          ("spend",     False),
}

_SORT_LABEL = {
    "frequency": "frequency",
    "cpl":       "CPL",
    "ctr":       "CTR",
    "leads":     "leads",
    "spend":     "spend",
}


def render_item(campaign: dict, item: dict, severity: str,
                *, account_id: str = "", tok: str = "", since: str = "", until: str = "", currency: str = "EUR"):
    key      = _key(campaign, item)
    existing = state.get_action(key)
    status   = existing["status"] if existing else "todo"

    if status == "dismissed":
        return

    icon = {"urgent": "🔴", "warning": "🟡", "opportunity": "🚀"}.get(severity, "•")

    with st.container(border=True):
        info_col, btn_col = st.columns([8, 2])

        with info_col:
            msg    = item.get("message", "")
            act    = item.get("action", "")
            uplift = item.get("expected_uplift", "")

            if status == "done":
                st.caption(f"✅ Actioned on {existing['updated_at'][:10]}")
            elif status == "todo" and existing and existing.get("notes", "").strip():
                st.caption(f"💭 Previously skipped: _{existing['notes'].strip()}_")

            st.markdown(
                f"**{campaign['market']}** — `{campaign['product']}`  \n"
                f"{icon} {msg}"
            )
            if act:
                st.markdown(f"**→** {act}")
            cpl_note = item.get("cpl_note")
            if cpl_note:
                st.warning(f"⚠️ CPL impact: {cpl_note}")
            if uplift:
                st.caption(f"Expected: {uplift}")

            # Key metrics line
            parts = [f"€{campaign['spend']:.0f} spent", f"{campaign['leads']} leads"]
            if campaign["cpl"]:
                parts.append(f"CPL €{campaign['cpl']:.2f}")
            if campaign["frequency"]:
                parts.append(f"freq {campaign['frequency']:.1f}×")
            if campaign["prev_cpl"] and campaign["cpl"]:
                d = (campaign["cpl"] - campaign["prev_cpl"]) / campaign["prev_cpl"] * 100
                arrow = "↑" if d > 0 else "↓"
                parts.append(f"WoW {arrow}{abs(d):.0f}%")
            st.caption("  ·  ".join(parts))

            # ── Ad-set breakdown ───────────────────────────────────────────
            if account_id and tok:
                sort_metric, sort_asc = _ADSET_SORT.get(item["type"], ("spend", False))
                sort_label = _SORT_LABEL[sort_metric]
                arrow_label = "↑ best first" if sort_asc else "↓ worst first"
                with st.expander(f"📋 Ad-set breakdown — sorted by {sort_label} {arrow_label}"):
                    from analysis import _leads as _al, _safe as _as
                    adsets_raw, err = _fetch_adsets(account_id, campaign["campaign_id"], tok, since, until)
                    adsets = _convert_to_eur(adsets_raw, currency, _fetch_fx()) if not err else []
                    if err:
                        st.warning(f"Could not load ad sets: {err}")
                    elif not adsets:
                        st.info("No ad-set data for this period.")
                    else:
                        as_rows = []
                        for a in adsets:
                            a_cpl   = _as(a.get("cost_per_result"))
                            a_spend = _as(a.get("spend"))
                            a_leads = _al(a.get("results"), a.get("actions"))
                            a_freq  = _as(a.get("frequency"))
                            a_ctr   = _as(a.get("ctr"))
                            if not a_cpl and a_leads > 0 and a_spend > 0:
                                a_cpl = a_spend / a_leads
                            as_rows.append({
                                "_name":  a.get("adset_name", ""),
                                "_leads": a_leads,
                                "_cpl":   a_cpl,
                                "_freq":  a_freq,
                                "_ctr":   a_ctr,
                                "_spend": a_spend,
                            })
                        sort_key = {"frequency": "_freq", "cpl": "_cpl", "ctr": "_ctr",
                                    "leads": "_leads", "spend": "_spend"}[sort_metric]
                        as_rows.sort(key=lambda r: r[sort_key], reverse=not sort_asc)
                        st.dataframe(pd.DataFrame([{
                            "Ad Set": r["_name"],
                            "Leads":  r["_leads"],
                            "CPL":    f"€{r['_cpl']:.2f}" if r["_cpl"] else "—",
                            "Freq":   f"{r['_freq']:.1f}×" if r["_freq"] else "—",
                            "CTR":    f"{r['_ctr']:.2f}%" if r["_ctr"] else "—",
                            "Spend":  f"€{r['_spend']:.0f}",
                        } for r in as_rows]), hide_index=True, use_container_width=True)

                        # Specific ad-set callout based on flag type
                        itype = item["type"]
                        active = [r for r in as_rows if r["_leads"] > 0 or r["_spend"] > 0]
                        if active:
                            if itype in ("scale_improving_cpl", "scale_low_frequency"):
                                best = min((r for r in active if r["_cpl"] > 0), key=lambda r: r["_cpl"], default=None)
                                if best:
                                    st.success(
                                        f"**👉 Scale specifically:** `{best['_name']}`  "
                                        f"— CPL €{best['_cpl']:.2f}, {best['_leads']} leads, freq {best['_freq']:.1f}×  "
                                        f"(best performer — increase its budget 20–30%)"
                                    )
                            elif itype in ("frequency_critical", "frequency_warning"):
                                worst = max(active, key=lambda r: r["_freq"])
                                cpl_note = f", CPL €{worst['_cpl']:.2f}" if worst["_cpl"] else ""
                                st.warning(
                                    f"**👉 Refresh creatives in:** `{worst['_name']}`  "
                                    f"— freq {worst['_freq']:.1f}×{cpl_note}"
                                )
                            elif itype in ("cpl_spike", "cpl_rise"):
                                worst = max((r for r in active if r["_cpl"] > 0), key=lambda r: r["_cpl"], default=None)
                                if worst:
                                    st.warning(
                                        f"**👉 Investigate first:** `{worst['_name']}`  "
                                        f"— highest CPL €{worst['_cpl']:.2f}, {worst['_leads']} leads"
                                    )
                            elif itype in ("ctr_drop_critical", "ctr_drop_warning"):
                                worst = min((r for r in active if r["_ctr"] > 0), key=lambda r: r["_ctr"], default=None)
                                if worst:
                                    st.warning(
                                        f"**👉 Refresh creatives in:** `{worst['_name']}`  "
                                        f"— lowest CTR {worst['_ctr']:.2f}%"
                                    )
                            elif itype in ("leads_drop_critical", "leads_drop_warning"):
                                worst = min(active, key=lambda r: r["_leads"])
                                st.warning(
                                    f"**👉 Check delivery of:** `{worst['_name']}`  "
                                    f"— {worst['_leads']} leads, €{worst['_spend']:.0f} spend"
                                )

        with btn_col:
            if status != "done":
                if st.button("✅ Done", key=f"d_{key}", use_container_width=True):
                    state.upsert_action(
                        key, campaign["market"], campaign["campaign_name"],
                        item["type"], msg, act, "done",
                    )
                    st.rerun()
                if not st.session_state.get(f"skip_pending_{key}"):
                    if st.button("Skip", key=f"s_{key}", use_container_width=True):
                        st.session_state[f"skip_pending_{key}"] = True
                        st.rerun()
            else:
                if st.button("↩️ Reopen", key=f"r_{key}", use_container_width=True):
                    state.update_status(key, "todo")
                    st.rerun()

        if st.session_state.get(f"skip_pending_{key}"):
            st.divider()
            reason_input = st.text_area(
                "Why are you skipping this? (helps refine future recommendations)",
                key=f"reason_{key}",
                placeholder="e.g. intentional retargeting push, campaign pausing next week, seasonality expected…",
                height=80,
            )
            sc1, sc2, _ = st.columns([1.3, 1, 2])
            if sc1.button("Confirm skip", key=f"cs_{key}", type="primary", use_container_width=True):
                state.upsert_action(
                    key, campaign["market"], campaign["campaign_name"],
                    item["type"], msg, act, "dismissed", notes=reason_input,
                )
                del st.session_state[f"skip_pending_{key}"]
                st.rerun()
            if sc2.button("Cancel", key=f"cc_{key}", use_container_width=True):
                del st.session_state[f"skip_pending_{key}"]
                st.rerun()


# ── Tabs ───────────────────────────────────────────────────────────────────
st.divider()
t1, t2, t3, t4, t5 = st.tabs([
    "🚨 Flags & Opportunities",
    "📊 Market Snapshot",
    "📋 Action Log",
    "🔭 Funnel — Colombia",
    "🎨 Creative Intelligence",
])


# ── Tab 1: Flags & Opportunities ──────────────────────────────────────────
with t1:
    from collections import defaultdict

    urgent_camps = [c for c in flags_view if any(f["severity"] == "urgent" for f in c["flags"])]
    warn_camps   = [c for c in flags_view if any(f["severity"] == "warning" for f in c["flags"])]

    # Cross-market banner: same flag type in 2+ markets
    flag_type_markets = defaultdict(list)
    for c in flags_view:
        for f in c["flags"]:
            flag_type_markets[f["type"]].append(c["market"])

    _FLAG_LABELS = {
        "frequency_critical":  "Critical frequency fatigue",
        "frequency_warning":   "Frequency warning",
        "cpl_spike":           "CPL spike",
        "cpl_rise":            "CPL rising",
        "ctr_drop_critical":   "Critical CTR drop",
        "ctr_drop_warning":    "CTR drop warning",
        "leads_drop_critical": "Critical leads drop",
        "leads_drop_warning":  "Leads drop warning",
    }
    cross_market = {k: v for k, v in flag_type_markets.items() if len(set(v)) >= 2}
    if cross_market:
        for ftype, markets in sorted(cross_market.items(), key=lambda x: -len(x[1])):
            unique_markets = list(dict.fromkeys(markets))  # preserve order, dedupe
            label = _FLAG_LABELS.get(ftype, ftype)
            names = ", ".join(unique_markets)
            st.warning(f"🌍 **{label}** affects {len(unique_markets)} markets: {names}")

    def _ctx(c):
        return dict(
            account_id=ACCOUNTS.get(c["market"], ""),
            tok=token,
            since=start_date.isoformat(),
            until=end_date.isoformat(),
            currency=ACCOUNT_CURRENCIES.get(c["market"], "EUR"),
        )

    if urgent_camps:
        st.subheader("🔴 Urgent — Fix Today")
        for c in urgent_camps:
            for f in [x for x in c["flags"] if x["severity"] == "urgent"]:
                render_item(c, f, "urgent", **_ctx(c))

    if warn_camps:
        st.subheader("🟡 Watch — Act This Week")
        for c in warn_camps:
            for f in [x for x in c["flags"] if x["severity"] == "warning"]:
                render_item(c, f, "warning", **_ctx(c))

    maximize_items  = [(c, o) for c in opps_view for o in c["opportunities"] if o.get("category") == "maximize"]
    reduce_cpl_items = [(c, o) for c in opps_view for o in c["opportunities"] if o.get("category") == "reduce_cpl"]
    other_opp_items  = [(c, o) for c in opps_view for o in c["opportunities"] if not o.get("category")]

    if maximize_items or reduce_cpl_items or other_opp_items:
        st.subheader("🚀 Opportunities")

    if maximize_items:
        st.markdown("##### 📈 Maximize Conversions")
        for c, o in maximize_items:
            render_item(c, o, "opportunity", **_ctx(c))

    if reduce_cpl_items:
        st.markdown("##### 💰 Reduce CPL")
        for c, o in reduce_cpl_items:
            render_item(c, o, "opportunity", **_ctx(c))

    if other_opp_items:
        for c, o in other_opp_items:
            render_item(c, o, "opportunity", **_ctx(c))

    if not urgent_camps and not warn_camps and not opps_view:
        st.success("✅ No flags or opportunities right now. All campaigns healthy.")

    if stable_view:
        with st.expander(f"🟢 Stable — no action needed ({len(stable_view)} campaigns)"):
            rows = []
            for c in stable_view:
                cpl, prev = c["cpl"], c["prev_cpl"]
                wow = ""
                if cpl and prev:
                    d = (cpl - prev) / prev * 100
                    wow = f"{'↑' if d>0 else '↓'}{abs(d):.0f}%"
                rows.append({
                    "Market":   c["market"],
                    "Campaign": c["campaign_name"][:52],
                    "Product":  c["product"],
                    "Leads":    c["leads"],
                    "CPL":      f"€{cpl:.2f}" if cpl else "—",
                    "WoW":      wow,
                    "Freq":     f"{c['frequency']:.1f}×" if c["frequency"] else "—",
                    "Spend":    f"€{c['spend']:.0f}",
                })
            if rows:
                st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    # Collect dismissed flags/opps from current view
    dismissed_items = []
    for c in flags_view + opps_view:
        for it in c.get("flags", []) + c.get("opportunities", []):
            k = _key(c, it)
            ex = state.get_action(k)
            if ex and ex["status"] == "dismissed":
                dismissed_items.append((c, it, ex))

    if dismissed_items:
        with st.expander(f"⏭️ Skipped ({len(dismissed_items)}) — review or reopen"):
            for c, it, ex in dismissed_items:
                reason = ex.get("notes", "").strip()
                sev = it.get("severity", "opportunity")
                icon = {"urgent": "🔴", "warning": "🟡", "opportunity": "🚀"}.get(sev, "•")
                dc1, dc2 = st.columns([8, 2])
                with dc1:
                    st.markdown(
                        f"{icon} **{c['market']}** — `{c['product']}`  \n"
                        f"{it.get('message', '')}"
                    )
                    if reason:
                        st.caption(f"💭 _{reason}_")
                    else:
                        st.caption("No reason recorded.")
                with dc2:
                    k_btn = _key(c, it)
                    if st.button("↩️ Reopen", key=f"rev_{k_btn}", use_container_width=True):
                        state.update_status(k_btn, "todo")
                        st.rerun()
                st.divider()


# ── Tab 2: Market Snapshot ────────────────────────────────────────────────
with t2:
    if DWH_MQL_DATE:
        st.caption(f"MQLs column sourced from DWH · last refreshed {DWH_MQL_DATE} · YTD 2026")
    for market in selected_markets:
        mkt_camps = [c for c in all_view if c["market"] == market]
        if not mkt_camps:
            continue

        st.subheader(market)
        ms = sum(c["spend"] for c in mkt_camps)
        ml = sum(c["leads"] for c in mkt_camps)
        mc = ms / ml if ml else 0

        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Spend", f"€{ms:,.0f}")
        mc2.metric("Leads", str(ml))
        mc3.metric("CPL",   f"€{mc:.2f}" if mc else "—")

        rows = []
        for c in mkt_camps:
            cpl, prev = c["cpl"], c["prev_cpl"]
            wow = ""
            if cpl and prev:
                d = (cpl - prev) / prev * 100
                wow = f"{'+'if d>0 else ''}{d:.0f}%"

            status_str = "🟢 Stable"
            if c["flags"]:
                sevs = [f["severity"] for f in c["flags"]]
                status_str = "🔴 Urgent" if "urgent" in sevs else "🟡 Watch"
            elif c["opportunities"]:
                status_str = "🚀 Opp"

            mqls_dwh = DWH_MQLS.get(c["campaign_name"])
            rows.append({
                "Campaign": c["campaign_name"][:50],
                "Type":     campaign_type(c["campaign_name"]),
                "Product":  c["product"],
                "Leads":    c["leads"],
                "MQLs":     mqls_dwh if mqls_dwh is not None else "—",
                "CPL":      f"€{cpl:.2f}" if cpl else "—",
                "WoW":      wow,
                "Freq":     f"{c['frequency']:.1f}×" if c["frequency"] else "—",
                "CTR":      f"{c['ctr']:.2f}%" if c["ctr"] else "—",
                "Spend":    f"€{c['spend']:.0f}",
                "Status":   status_str,
            })

        if rows:
            sel = st.dataframe(
                pd.DataFrame(rows),
                hide_index=True,
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row",
                key=f"tbl_{market}",
            )

            # Ad-set drill-down when a row is clicked
            if sel.selection.rows:
                idx = sel.selection.rows[0]
                c = mkt_camps[idx]
                st.markdown(f"**Ad sets · {c['campaign_name']}**")

                account_id = ACCOUNTS[market]
                adsets_raw, err = _fetch_adsets(
                    account_id, c["campaign_id"], token,
                    start_date.isoformat(), end_date.isoformat()
                )
                adsets = _convert_to_eur(
                    adsets_raw, ACCOUNT_CURRENCIES.get(market, "EUR"), _fetch_fx()
                ) if not err else []
                if err:
                    st.warning(f"Could not load ad sets: {err}")
                elif not adsets:
                    st.info("No ad-set data for this period.")
                else:
                    from analysis import _leads, _safe
                    as_rows = []
                    for a in adsets:
                        a_cpl   = _safe(a.get("cost_per_result"))
                        a_spend = _safe(a.get("spend"))
                        a_leads = _leads(a.get("results"), a.get("actions"))
                        if not a_cpl and a_leads > 0 and a_spend > 0:
                            a_cpl = a_spend / a_leads
                        as_rows.append({
                            "Ad Set":  a.get("adset_name", ""),
                            "Leads":   a_leads,
                            "CPL":     f"€{a_cpl:.2f}" if a_cpl else "—",
                            "Freq":    f"{_safe(a.get('frequency')):.1f}×" if a.get("frequency") else "—",
                            "CTR":     f"{_safe(a.get('ctr')):.2f}%" if a.get("ctr") else "—",
                            "Spend":   f"€{a_spend:.0f}",
                        })
                    st.dataframe(pd.DataFrame(as_rows), hide_index=True, use_container_width=True)

        st.divider()


# ── Tab 3: Action Log ─────────────────────────────────────────────────────
with t3:
    all_actions = state.get_all_actions()

    f_col, b_col = st.columns([3, 1])
    with f_col:
        sf = st.selectbox(
            "Filter status", ["all", "todo", "done", "dismissed"],
            label_visibility="collapsed",
        )
    with b_col:
        if st.button("Clear done", use_container_width=True):
            state.clear_done()
            st.rerun()

    filtered = all_actions if sf == "all" else [a for a in all_actions if a["status"] == sf]

    status_labels = {"todo": "📋 Todo", "done": "✅ Done", "dismissed": "👋 Skipped"}

    if filtered:
        rows = [{
            "Market":      a["market"],
            "Campaign":    a["campaign_name"][:42],
            "Issue":       a["message"][:68],
            "Status":      status_labels.get(a["status"], a["status"]),
            "Skip reason": (a.get("notes") or "")[:80],
            "Updated":     a["updated_at"][:16],
        } for a in filtered]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.info("No actions tracked yet. Mark flags and opportunities as done to log them here.")

    st.caption(f"{len(all_actions)} total actions in log")


# ── Tab 4: Funnel — Colombia ───────────────────────────────────────────────────
with t4:
    from hubspot_api import get_co_funnel

    CO_MARKET = "🇨🇴 Colombia"
    hs_token  = load_hs_token()

    if not hs_token:
        st.info("Enter your HubSpot token in the sidebar to unlock funnel metrics.")
    elif CO_MARKET not in selected_markets:
        st.warning(f"Select **{CO_MARKET}** in the Markets filter to see funnel data.")
    else:
        # ── Spend by segment from Meta data ───────────────────────────────────
        co_campaigns = [c for c in all_view if c["market"] == CO_MARKET]

        def _co_segment(name: str) -> str:
            n = name.lower()
            if "fac" in n:
                return "clinics_prs"
            if "noa" in n:
                return "individuals_noa"
            return "individuals_agenda"

        spend_by_seg = {"individuals_agenda": 0.0, "individuals_noa": 0.0, "clinics_prs": 0.0}
        leads_by_seg = {"individuals_agenda": 0,   "individuals_noa": 0,   "clinics_prs": 0}
        for c in co_campaigns:
            seg = _co_segment(c["campaign_name"])
            spend_by_seg[seg] += c["spend"]
            leads_by_seg[seg] += c["leads"]

        # ── Fetch HubSpot funnel (cached 1 h) ─────────────────────────────────
        @st.cache_data(ttl=3600, show_spinner=False)
        def _fetch_funnel(tok, d_from, d_to):
            return get_co_funnel(tok, d_from, d_to)

        funnel_cache_key = f"funnel|{hs_token[:8]}|{start_date}|{end_date}"
        if (
            "funnel_result" not in st.session_state
            or st.session_state.get("funnel_key") != funnel_cache_key
            or refresh
        ):
            with st.spinner("Fetching HubSpot funnel data…"):
                funnel_data, funnel_err = _fetch_funnel(
                    hs_token, start_date.isoformat(), end_date.isoformat()
                )
            st.session_state["funnel_result"] = funnel_data
            st.session_state["funnel_err"]    = funnel_err
            st.session_state["funnel_key"]    = funnel_cache_key

        funnel_data = st.session_state["funnel_result"]
        funnel_err  = st.session_state["funnel_err"]

        if funnel_err:
            st.error(f"HubSpot error: {funnel_err}")
        else:
            FUNNEL_SEGS = [
                ("individuals_agenda", "Individuals · Agenda Premium"),
                ("individuals_noa",    "Individuals · NOA"),
                ("clinics_prs",        "Clinics PRS · Clinic Agenda"),
            ]
            SEG_COLORS = {
                "individuals_agenda": "#00A085",
                "individuals_noa":    "#0077B6",
                "clinics_prs":        "#9B59B6",
            }

            st.subheader("Colombia · Meta → HubSpot Funnel")
            st.caption(
                f"Period: {start_date.strftime('%b %d')} – {end_date.strftime('%b %d')}  ·  "
                "30-day cohort  ·  MQL date = lcs_mql_at_test  ·  Spend in EUR  ·  "
                "Deals = closed in period and associated with cohort contacts"
            )

            for seg_key, seg_label in FUNNEL_SEGS:
                d     = funnel_data.get(seg_key, {})
                spend = spend_by_seg.get(seg_key, 0.0)

                mqls        = d.get("mqls", 0)
                unqualified = d.get("unqualified", 0)
                net_qual    = d.get("net_qualified", 0)
                open_deals  = d.get("open_deals", 0)
                wons        = d.get("wons", 0)

                uq_rate      = unqualified / mqls * 100      if mqls      else 0
                raw_cpl      = spend / mqls                  if mqls      else 0
                real_cpl     = spend / net_qual              if net_qual  else 0
                deal_open_rt = open_deals / net_qual * 100   if net_qual  else 0
                won_rt       = wons / net_qual * 100         if net_qual  else 0
                cac          = spend / wons                  if wons      else 0

                color = SEG_COLORS.get(seg_key, "#00A085")
                st.markdown(
                    f"<div style='border-left:4px solid {color};"
                    f"padding-left:12px;margin-bottom:4px'>"
                    f"<strong>{seg_label}</strong></div>",
                    unsafe_allow_html=True,
                )

                c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
                c1.metric("Meta Spend",    f"€{spend:,.0f}")
                c2.metric("Meta Leads",    f"{leads_by_seg.get(seg_key, 0):,}")
                c3.metric("HS MQLs",       f"{mqls:,}")
                c4.metric("Unqualified",   f"{unqualified:,}",
                          delta=f"{uq_rate:.0f}% rate", delta_color="inverse")
                c5.metric("Net Qual MQLs", f"{net_qual:,}")
                c6.metric("Real CPL",
                          f"€{real_cpl:,.0f}" if real_cpl else "—",
                          delta=f"raw €{raw_cpl:,.0f}" if raw_cpl else None,
                          delta_color="inverse")
                c7.metric("Open Deals",    f"{open_deals:,}",
                          delta=f"{deal_open_rt:.0f}% of net MQLs" if deal_open_rt else None,
                          delta_color="off")
                c8.metric("WONs / CAC",
                          f"{wons}  ·  €{cac:,.0f}" if wons else f"{wons}",
                          delta=f"{won_rt:.1f}% CVR" if won_rt else None,
                          delta_color="off")
                st.divider()

            summary_rows = []
            for seg_key, seg_label in FUNNEL_SEGS:
                d     = funnel_data.get(seg_key, {})
                spend = spend_by_seg.get(seg_key, 0.0)
                mqls        = d.get("mqls", 0)
                net_qual    = d.get("net_qualified", 0)
                unqualified = d.get("unqualified", 0)
                open_deals  = d.get("open_deals", 0)
                wons        = d.get("wons", 0)
                summary_rows.append({
                    "Segment":    seg_label,
                    "Spend €":    f"€{spend:,.0f}",
                    "Meta Leads": leads_by_seg.get(seg_key, 0),
                    "HS MQLs":    mqls,
                    "Unqual":     unqualified,
                    "Unqual %":   f"{unqualified/mqls*100:.0f}%" if mqls else "—",
                    "Net Qual":   net_qual,
                    "Raw CPL €":  f"€{spend/mqls:,.0f}" if mqls else "—",
                    "Real CPL €": f"€{spend/net_qual:,.0f}" if net_qual else "—",
                    "Open Deals": open_deals,
                    "Deal Open %":f"{open_deals/net_qual*100:.0f}%" if net_qual else "—",
                    "WONs":       wons,
                    "WON CVR %":  f"{wons/net_qual*100:.1f}%" if net_qual else "—",
                    "CAC €":      f"€{spend/wons:,.0f}" if wons else "—",
                })
            if summary_rows:
                st.dataframe(pd.DataFrame(summary_rows), hide_index=True, use_container_width=True)

            st.caption(
                "⚠️ MQL counts: contacts where utm_campaign = Colombia Meta campaign "
                "AND lcs_mql_at_test in period — precise Meta attribution.  "
                "Deal counts: deals associated with those same contacts, closed in the period "
                "(deduped). Open deals = currently open pipeline deals for those contacts."
            )


# ── Tab 5: Creative Intelligence ───────────────────────────────────────────────
with t5:
    from meta_api import get_ad_creative_data

    @st.cache_data(ttl=3600, show_spinner=False)
    def _fetch_ads(account_id, tok, since, until):
        return get_ad_creative_data(account_id, tok, since, until)

    def _v(arr):
        """Extract float from Meta action-value array."""
        try:
            return float((arr or [{}])[0].get("value", 0)) or None
        except Exception:
            return None

    def _act(actions, atype):
        for a in (actions or []):
            if a.get("action_type") == atype:
                try:
                    return float(a["value"])
                except Exception:
                    return 0.0
        return 0.0

    _RANK = {
        "ABOVE_AVERAGE":    "🟢",
        "BELOW_AVERAGE_35": "🟡",
        "BELOW_AVERAGE_20": "🔴",
        "BELOW_AVERAGE_10": "🔴",
        "UNKNOWN":          "—",
    }

    # ── Fetch ad data for selected markets ─────────────────────────────────────
    all_ads, ad_errors = [], []
    ad_pb = st.progress(0, "Fetching creative data…")
    for i, market in enumerate(selected_markets):
        ad_pb.progress(i / max(len(selected_markets), 1), f"Fetching ads · {market}…")
        account_id = ACCOUNTS[market]
        currency   = ACCOUNT_CURRENCIES.get(market, "EUR")
        raw, err   = _fetch_ads(account_id, token, start_date.isoformat(), end_date.isoformat())
        if err:
            ad_errors.append(f"{market}: {err}")
            continue
        converted = _convert_to_eur(raw, currency, _fetch_fx())
        for ad in converted:
            ad["_market"] = market
        all_ads.extend(converted)
    ad_pb.empty()

    if ad_errors:
        st.warning("Errors: " + " | ".join(ad_errors))

    # ── Parse rows ─────────────────────────────────────────────────────────────
    rows = []
    for ad in all_ads:
        cname = ad.get("campaign_name", "")
        n = cname.lower()
        # Only show actual lead gen campaigns (must contain mql or mal) — filters out boosted posts
        if "mql" not in n and "mal" not in n:
            continue
        if not _passes({"product": classify_product(cname), "campaign_name": cname}):
            continue

        imp      = float(ad.get("impressions", 0) or 0)
        spend    = float(ad.get("spend", 0) or 0)
        if spend <= 0:
            continue
        freq     = float(ad.get("frequency", 0) or 0)
        all_ctr  = float(ad.get("ctr", 0) or 0)

        actions     = ad.get("actions", [])
        leads       = _act(actions, "lead")
        lpv         = _act(actions, "landing_page_view")
        link_clicks = _act(actions, "link_click")

        # 3-second video views come from the actions array, not a separate field
        p3        = _act(actions, "video_view") or None
        p50       = _v(ad.get("video_p50_watched_actions"))
        thruplay  = _v(ad.get("video_thruplay_watched_actions"))
        outbound  = _v(ad.get("outbound_clicks"))

        cpl            = spend / leads     if leads           else None
        hook_rate      = (p3  / imp  * 100)  if p3  and imp  else None
        hold_rate      = (p50 / p3   * 100)  if p50 and p3   else None
        thumb_stop     = (hook_rate * hold_rate / 100) if hook_rate and hold_rate else None
        out_ctr        = (outbound / imp * 100) if outbound and imp else None
        cost_per_tp    = (spend / thruplay) if thruplay else None

        # Instant Form ads have no landing page — LPV events are never fired.
        # Detect by: "instant" in ad/campaign name, OR lpv=0 while leads>0 and clicks>0.
        is_instant_form = (
            "instant" in ad.get("ad_name", "").lower() or
            "instant" in cname.lower() or
            (leads > 0 and link_clicks > 0 and lpv == 0)
        )
        if is_instant_form:
            # Form Completion Rate: what % of form-opens led to a submission
            lpv_rate      = None
            form_fill_rate = (leads / link_clicks * 100) if leads and link_clicks else None
        else:
            lpv_rate       = (lpv / link_clicks * 100) if lpv and link_clicks else None
            form_fill_rate = None

        # Fatigue prediction: days until frequency reaches 5× at current burn rate
        period_days = max((end_date - start_date).days, 1)
        freq_per_day = freq / period_days if freq else 0
        if freq >= 5:
            days_to_fatigue = 0
        elif freq_per_day > 0:
            days_to_fatigue = round((5.0 - freq) / freq_per_day)
        else:
            days_to_fatigue = None

        ad_name_full = ad.get("ad_name", "")
        # Strip the campaign prefix so the Ad column shows only the distinguishing suffix
        # e.g. "de_doc_mql_noa_meta_instant-form_broad_v1" → "instant-form_broad_v1"
        if ad_name_full.lower().startswith(cname.lower()):
            ad_display = ad_name_full[len(cname):].lstrip("_- ") or ad_name_full
        else:
            ad_display = ad_name_full

        rows.append({
            "Market":         ad["_market"],
            "Campaign":       cname,
            "Ad":             ad_display,
            "Ad (full)":      ad_name_full,
            "Format":         "🎬 Video" if p3 is not None else "🖼️ Image",
            "Spend":          spend,
            "Leads":          int(leads),
            "CPL":            cpl,
            "Hook Rate":      hook_rate,
            "Hold Rate":      hold_rate,
            "Thumb-Stop":     thumb_stop,
            "Cost/ThruPlay":  cost_per_tp,
            "LPV Rate":       lpv_rate,
            "Form Fill %":    form_fill_rate,
            "Out CTR":        out_ctr,
            "All CTR":        all_ctr or None,
            "Frequency":      freq or None,
            "Fatigue In":     days_to_fatigue,
            "Quality":        _RANK.get(ad.get("quality_ranking"), "—"),
            "Engagement":     _RANK.get(ad.get("engagement_rate_ranking"), "—"),
            "Conversion":     _RANK.get(ad.get("conversion_rate_ranking"), "—"),
        })

    if not rows:
        st.info("No ad-level data for the selected markets and period.")

    if rows:
        df_ads = pd.DataFrame(rows).sort_values("CPL", ascending=True, na_position="last")

        # ── Summary strip ──────────────────────────────────────────────────────
        n_ads     = len(df_ads)
        n_video   = (df_ads["Format"] == "🎬 Video").sum()
        avg_hook  = df_ads["Hook Rate"].dropna().mean()
        avg_cpl   = df_ads.loc[df_ads["Leads"] > 0, "CPL"].mean()
        tot_spend = df_ads["Spend"].sum()
        tot_leads = df_ads["Leads"].sum()

        sc = st.columns(6)
        sc[0].metric("Active Ads",    n_ads)
        sc[1].metric("Video / Image", f"{n_video} / {n_ads - n_video}")
        sc[2].metric("Avg Hook Rate", f"{avg_hook:.1f}%" if pd.notna(avg_hook) else "—",
                     help="Avg across video ads only")
        sc[3].metric("Avg CPL",       f"€{avg_cpl:,.0f}" if pd.notna(avg_cpl) else "—")
        sc[4].metric("Total Leads",   f"{tot_leads:,}")
        sc[5].metric("Total Spend",   f"€{tot_spend:,.0f}")

        st.divider()

        # ── Insights & recommendations ────────────────────────────────────────
        G = "background-color:#d1f2e5;color:#0a5c36"
        Y = "background-color:#fff8cc;color:#7d5a00"
        R = "background-color:#ffd5d5;color:#8b0000"
        N = "background-color:#f0f0f0;color:#888888"

        has_leads  = df_ads[df_ads["Leads"] > 0].copy()
        video_df   = df_ads[df_ads["Format"] == "🎬 Video"].copy()
        image_df   = df_ads[df_ads["Format"] == "🖼️ Image"].copy()
        avg_cpl_v  = avg_cpl if pd.notna(avg_cpl) else 0

        alerts, recs = [], []

        # Scale signals: CPL ≤80% of avg, freq <3
        # Split: ads with dead hook (<15%) need creative fix first, not budget scale
        if avg_cpl_v:
            scale_candidates = has_leads[
                (has_leads["CPL"] <= avg_cpl_v * 0.80) &
                (has_leads["Frequency"].fillna(0) < 3)
            ]
            for _, r in scale_candidates.head(3).iterrows():
                hook = r.get("Hook Rate")
                has_dead_hook = pd.notna(hook) and hook < 15
                if has_dead_hook:
                    recs.append(
                        f"🛠️ **Fix hook, then scale** — `{r['Ad (full)']}` · CPL €{r['CPL']:.0f} "
                        f"({(1 - r['CPL']/avg_cpl_v)*100:.0f}% below avg) but hook only {hook:.1f}%. "
                        "CPL is good despite a weak hook — replacing the opening frame could make it even cheaper. "
                        "Test a new thumbnail/first 2s first, then scale the winner."
                    )
                else:
                    recs.append(
                        f"🚀 **Scale now** — `{r['Ad (full)']}` · CPL €{r['CPL']:.0f} "
                        f"({(1 - r['CPL']/avg_cpl_v)*100:.0f}% below avg), freq {r['Frequency']:.1f}×. "
                        "Increase budget 20–30% every 48 h while CPL holds."
                    )

        # Creative fatigue: already at/above threshold
        for _, r in df_ads[df_ads["Frequency"].fillna(0) >= 5].iterrows():
            alerts.append(
                f"🔴 **Creative fatigue NOW** — `{r['Ad (full)']}` · freq {r['Frequency']:.1f}×. "
                "Pause and replace immediately."
            )

        # Dead hook: hook <15%
        for _, r in video_df[video_df["Hook Rate"].fillna(100) < 15].head(3).iterrows():
            alerts.append(
                f"🔴 **Dead hook** — `{r['Ad (full)']}` · hook {r['Hook Rate']:.1f}%. "
                "The first frame isn't stopping the scroll — test a new thumbnail or opening shot."
            )

        # Good hook but bad hold: hook ≥25% AND hold <25%
        for _, r in video_df[
            (video_df["Hook Rate"].fillna(0) >= 25) &
            (video_df["Hold Rate"].fillna(100) < 25)
        ].head(2).iterrows():
            alerts.append(
                f"🟡 **Hook ✓ / Script ✗** — `{r['Ad (full)']}` · hook {r['Hook Rate']:.1f}% "
                f"but hold {r['Hold Rate']:.1f}%. "
                "The opening works — tighten or trim the middle of the video."
            )

        # Format CPL comparison
        v_cpl = video_df[video_df["Leads"] > 0]["CPL"].mean() if not video_df.empty else None
        i_cpl = image_df[image_df["Leads"] > 0]["CPL"].mean() if not image_df.empty else None
        if pd.notna(v_cpl) and pd.notna(i_cpl):
            if v_cpl < i_cpl * 0.85:
                recs.append(
                    f"📹 **Shift budget to video** — video CPL €{v_cpl:.0f} vs image €{i_cpl:.0f} "
                    f"({(i_cpl/v_cpl - 1)*100:.0f}% cheaper). Reduce image adset budgets first."
                )
            elif i_cpl < v_cpl * 0.85:
                recs.append(
                    f"🖼️ **Shift budget to image** — image CPL €{i_cpl:.0f} vs video €{v_cpl:.0f} "
                    f"({(v_cpl/i_cpl - 1)*100:.0f}% cheaper). Reduce video adset budgets first."
                )

        # Low LPV rate
        low_lpv = df_ads[df_ads["LPV Rate"].fillna(100) < 50]
        if not low_lpv.empty:
            alerts.append(
                f"🟡 **Landing page friction** — {len(low_lpv)} ad(s) with LPV Rate <50%. "
                "Over half of clickers never reach the page — check load speed, redirects, and mobile UX."
            )

        # Quality/conversion ranking issues
        bad_quality = df_ads[df_ads["Quality"] == "🔴"]
        if not bad_quality.empty:
            alerts.append(
                f"🔴 **Quality ranking below avg** on {len(bad_quality)} ad(s) — "
                "Meta is discounting these in auction. Review post-click experience and reduce negative feedback."
            )
        bad_conv = df_ads[(df_ads["Conversion"] == "🔴") & (df_ads["Leads"] > 0)]
        if not bad_conv.empty:
            alerts.append(
                f"🔴 **Conversion ranking below avg** on {len(bad_conv)} ad(s) — "
                "Good CTR but low conversion. Landing page offer/form friction is the likely culprit."
            )

        # High CPL with spend > €100
        high_cpl = df_ads[
            df_ads["CPL"].fillna(0) > avg_cpl_v * 1.5
        ] if avg_cpl_v else pd.DataFrame()
        if not high_cpl.empty:
            for _, r in high_cpl[high_cpl["Spend"] > 100].head(2).iterrows():
                recs.append(
                    f"⛔ **Kill or test** — `{r['Ad (full)']}` · CPL €{r['CPL']:.0f} "
                    f"({(r['CPL']/avg_cpl_v - 1)*100:.0f}% above avg). "
                    "Pause unless testing — budget is better deployed on performers."
                )

        if alerts or recs:
            ia_col, rec_col = st.columns(2)
            with ia_col:
                st.markdown("##### ⚠️ Alerts")
                for a in alerts:
                    st.markdown(a)
            with rec_col:
                st.markdown("##### 🎯 Recommendations")
                for r in recs:
                    st.markdown(r)
            if not recs:
                rec_col.caption("No scale or kill actions triggered yet.")
            if not alerts:
                ia_col.success("✅ No critical issues detected.")

        # ── Fatigue Forecast ──────────────────────────────────────────────────
        fatigue_df = df_ads[df_ads["Fatigue In"].notna()].copy()
        fatigue_df = fatigue_df.sort_values("Fatigue In")
        urgent   = fatigue_df[fatigue_df["Fatigue In"] <= 7]
        warning  = fatigue_df[(fatigue_df["Fatigue In"] > 7) & (fatigue_df["Fatigue In"] <= 14)]
        healthy  = fatigue_df[fatigue_df["Fatigue In"] > 14]

        if not fatigue_df.empty:
            with st.expander(
                f"⏳ Fatigue Forecast — {len(urgent)} urgent · {len(warning)} watch · {len(healthy)} healthy",
                expanded=bool(len(urgent))
            ):
                st.caption(
                    "Predicts days until frequency hits 5× at the current burn rate. "
                    "🔴 ≤7 days — brief creatives now.  🟡 8–14 days — start briefing.  🟢 >14 days — healthy."
                )
                forecast_rows = []
                for _, r in fatigue_df.iterrows():
                    d = int(r["Fatigue In"])
                    if d <= 0:
                        status, eta = "🔴 Fatigued", "Now"
                    elif d <= 7:
                        status, eta = "🔴 Urgent", f"{d}d"
                    elif d <= 14:
                        status, eta = "🟡 Brief team", f"{d}d"
                    else:
                        status, eta = "🟢 Healthy", f"{d}d"
                    forecast_rows.append({
                        "Ad":           r["Ad (full)"],
                        "Market":       r["Market"],
                        "Freq now":     f"{r['Frequency']:.1f}×" if pd.notna(r.get("Frequency")) else "—",
                        "Days to 5×":   eta,
                        "Status":       status,
                        "Spend":        f"€{r['Spend']:.0f}",
                        "CPL":          f"€{r['CPL']:.0f}" if pd.notna(r.get("CPL")) else "—",
                    })
                st.dataframe(
                    pd.DataFrame(forecast_rows),
                    hide_index=True,
                    use_container_width=True,
                )

        st.divider()

        # ── Color-coded table ─────────────────────────────────────────────────
        # Allow long ad names to wrap inside cells instead of clipping
        st.markdown(
            "<style>"
            ".stDataFrame [data-testid='stDataFrameResizable'] td { white-space: pre-wrap !important; word-break: break-all; }"
            "</style>",
            unsafe_allow_html=True,
        )
        st.caption(
            "🟢 Good  🟡 Watch  🔴 Act  ⬜ N/A  |  "
            "Hover column headers for definitions. "
            "Hook/Hold/LPV only for video ads."
        )

        def _s(val, fn):
            try:
                return fn(val)
            except Exception:
                return ""

        def _hook_color(v):
            if pd.isna(v): return N
            return G if v >= 25 else (Y if v >= 15 else R)

        def _hold_color(v):
            if pd.isna(v): return N
            return G if v >= 40 else (Y if v >= 25 else R)

        def _lpv_color(v):
            if pd.isna(v): return N
            return G if v >= 70 else (Y if v >= 50 else R)

        def _cpl_color(v):
            if pd.isna(v) or not avg_cpl_v: return ""
            return G if v <= avg_cpl_v * 0.80 else (Y if v <= avg_cpl_v * 1.20 else R)

        def _thumb_color(v):
            if pd.isna(v): return N
            return G if v >= 10 else (Y if v >= 5 else R)

        def _tp_color(v):
            if pd.isna(v): return N
            return G if v <= 0.5 else (Y if v <= 1.5 else R)

        def _fatigue_color(v):
            if pd.isna(v): return ""
            return R if v <= 7 else (Y if v <= 14 else G)

        def _freq_color(v):
            if pd.isna(v): return ""
            return G if v < 3 else (Y if v < 5 else R)

        def _rank_color(v):
            return {"🟢": G, "🟡": Y, "🔴": R}.get(v, N)

        _style_map = [
            (_hook_color,   ["Hook Rate"]),
            (_hold_color,   ["Hold Rate"]),
            (_thumb_color,  ["Thumb-Stop"]),
            (_tp_color,     ["Cost/ThruPlay"]),
            (_lpv_color,    ["LPV Rate", "Form Fill %"]),
            (_cpl_color,    ["CPL"]),
            (_freq_color,   ["Frequency"]),
            (_fatigue_color,["Fatigue In"]),
            (_rank_color,   ["Quality", "Engagement", "Conversion"]),
        ]
        try:
            styled = df_ads.style
            for fn, cols in _style_map:
                existing = [c for c in cols if c in df_ads.columns]
                if existing:
                    styled = styled.map(fn, subset=existing)
        except AttributeError:
            styled = df_ads.style
            for fn, cols in _style_map:
                existing = [c for c in cols if c in df_ads.columns]
                if existing:
                    styled = styled.applymap(fn, subset=existing)

        _visible_cols = [c for c in df_ads.columns if c != "Ad (full)"]
        st.dataframe(
            styled,
            hide_index=True,
            use_container_width=True,
            column_order=_visible_cols,
            column_config={
                "Market":   st.column_config.TextColumn("Market", width="small"),
                "Campaign": st.column_config.TextColumn("Campaign", width="medium"),
                "Ad":       st.column_config.TextColumn("Ad variant (campaign prefix stripped)", width="large"),
                "Format":   st.column_config.TextColumn("Format", width="small"),
                "Spend": st.column_config.NumberColumn(
                    "Spend €", format="€%.0f",
                    help="Total spend in the period, converted to EUR.",
                ),
                "Leads": st.column_config.NumberColumn("Leads", width="small"),
                "CPL": st.column_config.NumberColumn(
                    "CPL €", format="€%.0f",
                    help="Cost Per Lead = Spend ÷ Leads. 🟢 ≤80% of avg  🟡 80–120%  🔴 >120%",
                ),
                "Hook Rate": st.column_config.NumberColumn(
                    "Hook Rate %",
                    help="3-second video views ÷ Impressions. Measures if the first frame stops the scroll. "
                         "🟢 ≥25%  🟡 15–25%  🔴 <15%",
                    format="%.1f%%",
                ),
                "Hold Rate": st.column_config.NumberColumn(
                    "Hold Rate %",
                    help="50%-through views ÷ 3-second views. Measures narrative retention after the hook. "
                         "🟢 ≥40%  🟡 25–40%  🔴 <25%",
                    format="%.1f%%",
                ),
                "Thumb-Stop": st.column_config.NumberColumn(
                    "Thumb-Stop",
                    help="Hook Rate × Hold Rate ÷ 100. Compound signal: % of impressions that resulted in "
                         "someone watching at least 50% of the video. Best single number for creative quality. "
                         "🟢 ≥10%  🟡 5–10%  🔴 <5%",
                    format="%.1f%%",
                ),
                "Cost/ThruPlay": st.column_config.NumberColumn(
                    "Cost/ThruPlay",
                    help="Spend ÷ ThruPlays. ThruPlay = watched 15+ seconds or full video (whichever is shorter). "
                         "Upper-funnel video quality signal — high cost = Meta isn't serving this to engaged audiences. "
                         "🟢 ≤€0.50  🟡 €0.50–€1.50  🔴 >€1.50",
                    format="€%.2f",
                ),
                "LPV Rate": st.column_config.NumberColumn(
                    "LPV Rate %",
                    help="Landing Page Views ÷ Link Clicks. Only shown for LP (non-Instant-Form) ads. "
                         "Measures friction between ad click and page load. "
                         "🟢 ≥70%  🟡 50–70%  🔴 <50%  (low = slow page, broken redirect, or mobile UX issue)",
                    format="%.1f%%",
                ),
                "Form Fill %": st.column_config.NumberColumn(
                    "Form Fill %",
                    help="Leads ÷ Link Clicks. Only shown for Instant Form ads (form opens inside Meta — no LP). "
                         "Measures what % of people who opened the form actually submitted it. "
                         "🟢 ≥70%  🟡 50–70%  🔴 <50%  (low = form is too long, too many fields, or poor pre-fill)",
                    format="%.1f%%",
                ),
                "Out CTR": st.column_config.NumberColumn(
                    "Outbound CTR",
                    help="Outbound clicks ÷ Impressions. Real intent signal — excludes reactions/profile visits.",
                    format="%.2f%%",
                ),
                "All CTR": st.column_config.NumberColumn(
                    "All CTR",
                    help="All clicks ÷ Impressions. Compare vs Outbound CTR to spot vanity engagement.",
                    format="%.2f%%",
                ),
                "Frequency": st.column_config.NumberColumn(
                    "Freq",
                    help="Avg times one person saw this ad. 🟢 <3  🟡 3–5  🔴 ≥5 (creative fatigue)",
                    format="%.1f×",
                ),
                "Fatigue In": st.column_config.NumberColumn(
                    "Fatigue In",
                    help="Predicted days until frequency hits 5× at the current burn rate. "
                         "🔴 ≤7 days — brief creatives now  🟡 8–14 days — start briefing  🟢 >14 days — healthy. "
                         "Formula: (5 − current freq) ÷ (freq per day in this period).",
                    format="%d days",
                ),
                "Quality": st.column_config.TextColumn(
                    "Quality",
                    help="Meta's Quality Ranking vs auction competitors. Based on post-click UX & ad feedback. "
                         "🟢 Above avg  🟡 Below 35%  🔴 Bottom 10–20%  ⬜ insufficient data",
                    width="small",
                ),
                "Engagement": st.column_config.TextColumn(
                    "Engage",
                    help="Meta's Engagement Rate Ranking. Expected likes/comments/shares vs similar ads.",
                    width="small",
                ),
                "Conversion": st.column_config.TextColumn(
                    "Conv.",
                    help="Meta's Conversion Rate Ranking. Low here + high CTR = landing page problem.",
                    width="small",
                ),
            },
        )
