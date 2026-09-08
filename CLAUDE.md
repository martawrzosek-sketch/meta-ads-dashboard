# Meta Ads Dashboard — Claude Project Context

## Stack
- **Streamlit** app (`app.py`) — the main dashboard
- **Meta Marketing API** — spend, leads, impressions, CPL via `meta_api.py`
- **HubSpot REST API** — Colombia funnel via `hubspot_api.py` (being replaced with DWH)
- **DWH (Redshift)** — `stage_hubspot.*` tables; accessible via Claude's MCP tools in-session

## Running the app
```bash
streamlit run app.py
```
Already running on port 8501. ngrok tunnel: `ngrok http 8501` (token needed first: `ngrok config add-authtoken <token>`).

## Key files
| File | Purpose |
|------|---------|
| `app.py` | Full Streamlit app — all 5 tabs |
| `meta_api.py` | Meta API client — fetches campaigns, ads, insights |
| `hubspot_api.py` | HubSpot CRM client — Colombia funnel (rate-limit retry added) |
| `analysis.py` | Campaign classification logic (`classify_product`) |

## Tabs
1. **Flags & Opportunities** — cross-market alerts + per-market alerts/recommendations
2. **Market Snapshot** — campaign table per market (Leads, CPL, WoW%, Freq, CTR, Status)
3. **Action Log** — manual actions log
4. **Funnel — Colombia** — HubSpot MQL→deals→WON (TODO: replace with DWH)
5. **Creative Intelligence** — 495+ ads, hook rate, scale/kill recommendations

## Meta API notes
- Always filter `spend > 0` — Brazil/MX have 200+ campaigns and active ones fall off page 1 without it
- Ad names start with the campaign name — stripped in display (`Ad` column), kept in `Ad (full)` for insight text
- Instant Form detection: `"instant"` in ad/campaign name OR `lpv=0` while `leads>0 and clicks>0`
- For Instant Form ads: show **Form Fill Rate** (leads/clicks) instead of LPV Rate

## Campaign naming convention
```
{country}_{segment}_{type}_{product}_{channel}_{variant}
e.g. br_doc_mql_agenda_meta_form
```
Country prefixes: br, mx, co, de, it, pl, es, cl, tr

## HubSpot / DWH funnel — known issues
- `mql_last_touch_channel_wf` is overwritten on re-touch — unreliable for Meta attribution
- `stage_hubspot.deal.hubspot_contact_id` → `stage_hubspot.contact.hubspot_id` join gives ~1 WON per 1,700 MQLs (too low — structural attribution gap)
- DWH association table: `type = 'deal_to_contact'`, `from_obj = deal hs_object_id`, `to_obj = contact hubspot_id`
- WON deals: `hs_deal_stage_probability = 1.0` (no `hs_is_closed_won` column in DWH)
- Best available DWH funnel: **MQLs per utm_campaign** (reliable) — WONs/CAC still unsolved

## Germany CPL target
Germany NOA Meta Ads target CPL = €150

## Sidebar credentials
- **Meta token** — stored in `st.session_state` under `meta_token`
- **HubSpot token** — stored in `st.session_state` under `hs_token`

## Pending work
- [ ] Replace Funnel tab's HubSpot direct API calls with DWH-sourced JSON or Redshift direct connection
- [ ] Fix WON attribution for full funnel (spend → MQLs → WONs → CAC)
- [ ] Italy MioDottore Meta API timeout (add per-market retry/timeout)
