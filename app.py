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

TOKEN_FILE = Path(__file__).parent / ".token"
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
from analysis import analyze_market, campaign_type
import state


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
t1, t2, t3 = st.tabs(["🚨 Flags & Opportunities", "📊 Market Snapshot", "📋 Action Log"])


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

            rows.append({
                "Campaign": c["campaign_name"][:50],
                "Type":     campaign_type(c["campaign_name"]),
                "Product":  c["product"],
                "Leads":    c["leads"],
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
