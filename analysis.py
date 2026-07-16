from typing import Optional


def campaign_type(name: str) -> str:
    return "MAL" if "mal" in name.lower() else "MQL"


def classify_product(name: str, account_id: Optional[str] = None) -> str:
    n = name.lower()
    if "noa" in n:
        return "NOA"
    if "agenda" in n:
        return "AGENDA"
    if "feegow" in n:
        return "FEEGOW"
    if "clinic-cloud" in n or "clinic_cloud" in n:
        return "CLINIC CLOUD"
    if account_id == "1242060572474329" or "gipo" in n:
        return "GIPO"
    return "OTHER"


def _safe(v, default=0.0) -> float:
    try:
        return float(v) if v is not None else default
    except (ValueError, TypeError):
        return default


LEAD_ACTION_TYPES = {
    "lead",
    "leadgen_grouped",
    "offsite_conversion.fb_pixel_lead",
    "onsite_conversion.lead_grouped",
    "contact_total",
}

def _leads(results, actions=None) -> int:
    for arr in (results, actions):
        if not arr:
            continue
        for r in arr:
            if isinstance(r, dict) and r.get("action_type", "") in LEAD_ACTION_TYPES:
                return int(_safe(r.get("value", 0)))
    for r in (results or []):
        if isinstance(r, dict) and r.get("value"):
            return int(_safe(r.get("value", 0)))
    return 0


def analyze_market(market: str, curr_data: list, prev_data: list, account_id: Optional[str] = None):
    prev_map = {c["campaign_id"]: c for c in (prev_data or [])}

    flags, opps, stable = [], [], []

    for c in (curr_data or []):
        cid  = c.get("campaign_id", "")
        name = c.get("campaign_name", "")
        product = classify_product(name, account_id)

        spend     = _safe(c.get("spend"))
        frequency = _safe(c.get("frequency"))
        cpl       = _safe(c.get("cost_per_result"))
        ctr       = _safe(c.get("ctr"))
        cpm       = _safe(c.get("cpm"))
        leads     = _leads(c.get("results"), c.get("actions"))
        if not cpl and leads > 0 and spend > 0:
            cpl = spend / leads

        pc         = prev_map.get(cid, {})
        prev_cpl   = _safe(pc.get("cost_per_result"))
        prev_leads_raw = _leads(pc.get("results"), pc.get("actions"))
        prev_ctr   = _safe(pc.get("ctr"))
        prev_leads = prev_leads_raw
        if not prev_cpl and prev_leads > 0:
            prev_spend = _safe(pc.get("spend"))
            if prev_spend > 0:
                prev_cpl = prev_spend / prev_leads

        c_flags = []
        c_opps  = []

        # ── Zero leads with spend ────────────────────────────────────────────
        if spend > 0 and leads == 0:
            name_lower = name.lower()
            if "traffic" in name_lower:
                obj_note = (
                    "Campaign objective looks like Traffic (not Lead Generation) — "
                    "it optimises for clicks, not form fills. "
                    "If the goal is leads, duplicate as a Lead objective campaign and pause this one."
                )
            else:
                obj_note = (
                    "Check the Delivery column for errors: rejected ads, audience too small, or wrong conversion event. "
                    "Verify the lead form is live and the conversion event is correctly set."
                )
            c_flags.append({
                "type": "zero_leads",
                "severity": "urgent",
                "message": f"€{spend:.0f} spent, 0 leads — budget burning with no conversions this period",
                "action": obj_note,
            })

        # ── Frequency flags ─────────────────────────────────────────────────
        if frequency > 5:
            c_flags.append({
                "type": "frequency_critical", "severity": "urgent",
                "message": f"Frequency {frequency:.1f}× — audience has seen each ad ~{frequency:.0f} times on avg (critical threshold: 5×)",
                "action": (
                    "Creative is worn out — CPL will keep rising until you refresh. "
                    "In Ads Manager → Ads tab: sort by CTR ↑ and pause the bottom 50% of creatives. "
                    "Duplicate your top ad with a completely new visual and first-line hook. "
                    "If reach has stagnated, also add a fresh audience: 2% lookalike or a new interest group."
                ),
            })
        elif frequency > 3.5:
            c_flags.append({
                "type": "frequency_warning", "severity": "warning",
                "message": f"Frequency {frequency:.1f}× — approaching saturation (warning threshold: 3.5×)",
                "action": (
                    "Above 3.5×, CPL typically starts rising within 1–2 weeks. "
                    "Start preparing 2–3 new creatives now, before it becomes critical. "
                    "In Ads Manager: check whether 'Reach' in the Delivery column has plateaued — "
                    "if yes, it confirms audience saturation and you also need a fresh audience segment."
                ),
            })

        # ── CPL flags ────────────────────────────────────────────────────────
        if prev_cpl > 0 and cpl > 0:
            cpl_pct = (cpl - prev_cpl) / prev_cpl
            if cpl_pct > 0.30:
                if frequency > 3.5:
                    cause = f"frequency at {frequency:.1f}× points to creative fatigue"
                    action = (
                        f"CPL jumped €{prev_cpl:.0f}→€{cpl:.0f} because your audience has seen the ads too many times. "
                        "In Ads Manager → Ad Sets tab: sort by Cost per Result ↓ to find which ad set is the worst offender. "
                        "Pause oldest ads in that set and launch fresh creatives."
                    )
                else:
                    cause = "check budget pacing, auction competition, or creative quality"
                    action = (
                        f"CPL jumped €{prev_cpl:.0f}→€{cpl:.0f}. "
                        "In Ads Manager → Ad Sets: sort by Cost per Result ↓ to find the outlier set. "
                        "Then check: (1) Is daily budget being hit every day? Budget exhaustion raises CPL in the second half of the day. "
                        "(2) Did a competitor start a big campaign? That raises auction CPM."
                    )
                c_flags.append({
                    "type": "cpl_spike", "severity": "urgent",
                    "message": f"CPL +{cpl_pct*100:.0f}% WoW: €{prev_cpl:.0f} → €{cpl:.0f} — {cause}",
                    "action": action,
                })
            elif cpl_pct > 0.15:
                freq_note = f" Frequency at {frequency:.1f}× — start queuing new creatives." if frequency > 2.5 else ""
                c_flags.append({
                    "type": "cpl_rise", "severity": "warning",
                    "message": f"CPL +{cpl_pct*100:.0f}% WoW: €{prev_cpl:.0f} → €{cpl:.0f} — early warning, not yet critical",
                    "action": (
                        f"Monitor for 3–5 more days before acting. "
                        f"If the trend continues: in Ad Sets, sort by Cost per Result ↓ and refresh creatives in the highest-CPL set.{freq_note}"
                    ),
                })

        # ── CTR flags ────────────────────────────────────────────────────────
        if prev_ctr > 0 and ctr > 0:
            ctr_pct = (ctr - prev_ctr) / prev_ctr
            if ctr_pct < -0.20:
                cpc_before = cpm / (10 * prev_ctr) if prev_ctr else 0
                cpc_now    = cpm / (10 * ctr) if ctr else 0
                freq_note  = f" With freq {frequency:.1f}×, the audience is tuning out — they recognize the ad and scroll past." if frequency > 3 else " The ad stopped resonating with the audience."
                c_flags.append({
                    "type": "ctr_drop_critical", "severity": "urgent",
                    "message": f"CTR {ctr_pct*100:.0f}% WoW: {prev_ctr:.2f}% → {ctr:.2f}%{freq_note}",
                    "action": (
                        f"Lower CTR means higher cost per click: was ≈€{cpc_before:.2f}, now ≈€{cpc_now:.2f}. "
                        "In Ads Manager → Ads tab: pause all ads running more than 14 days. "
                        "Create 2–3 new variations — test different opening hooks: a bold question, a specific stat, or a customer outcome."
                    ),
                })
            elif ctr_pct < -0.10:
                c_flags.append({
                    "type": "ctr_drop_warning", "severity": "warning",
                    "message": f"CTR {ctr_pct*100:.0f}% WoW: {prev_ctr:.2f}% → {ctr:.2f}% — early creative decay",
                    "action": (
                        "Test 2 new ad variations this week before the drop accelerates. "
                        "Focus on the opening 3 seconds or first line — that's usually what's losing clicks."
                    ),
                })

        # ── Leads drop flags ─────────────────────────────────────────────────
        if prev_leads > 3 and leads > 0:
            leads_pct = (leads - prev_leads) / prev_leads
            if leads_pct < -0.30:
                cpl_stable = (prev_cpl > 0 and cpl > 0 and abs((cpl - prev_cpl) / prev_cpl) < 0.10)
                if cpl_stable:
                    diagnosis = "CPL is stable → likely a budget or delivery issue, not creative"
                    action = (
                        "In Ads Manager: check the Delivery column for this campaign — look for "
                        "'Budget limited', 'Learning', or 'Off' status on the campaign or its ad sets. "
                        "If budget is the issue, raise the daily budget. If it's in Learning, avoid changing settings for 7 days."
                    )
                else:
                    diagnosis = "CPL also shifted → likely audience or creative issue"
                    action = (
                        "In Ads Manager → Ad Sets: sort by Cost per Result ↓ to find which set is the worst. "
                        "Check its creative freshness (age of active ads) and audience size."
                    )
                c_flags.append({
                    "type": "leads_drop_critical", "severity": "urgent",
                    "message": f"Leads {leads_pct*100:.0f}% WoW: {prev_leads} → {leads} — {diagnosis}",
                    "action": action,
                })
            elif leads_pct < -0.15:
                c_flags.append({
                    "type": "leads_drop_warning", "severity": "warning",
                    "message": f"Leads {leads_pct*100:.0f}% WoW: {prev_leads} → {leads}",
                    "action": (
                        "Monitor for 2–3 more days. "
                        "Quick check in Ads Manager: if spend pace is also down → budget/delivery issue. "
                        "If spend is normal but leads dropped → creative or audience is the problem."
                    ),
                })

        # ── Opportunities ─────────────────────────────────────────────────────
        if prev_cpl > 0 and cpl > 0 and leads > 0:
            cpl_pct = (cpl - prev_cpl) / prev_cpl
            if cpl_pct <= -0.10 and frequency < 3.0:
                c_opps.append({
                    "type": "scale_improving_cpl",
                    "category": "maximize",
                    "cpl_note": None,
                    "message": (
                        f"CPL improved {abs(cpl_pct)*100:.0f}% WoW (€{prev_cpl:.0f}→€{cpl:.0f}) "
                        f"and frequency is only {frequency:.1f}× — efficiency is up, audience has headroom"
                    ),
                    "action": (
                        f"In Ads Manager → Campaign budget: increase daily budget by 20–30%. "
                        f"Don't increase more than 30% at once — larger jumps reset the learning phase "
                        f"(Meta needs 50+ conversions/week to keep optimising). "
                        f"At CPL €{cpl:.0f}, each extra €{cpl:.0f}/day in budget ≈ +1 lead/day."
                    ),
                    "expected_uplift": f"+{max(1, int(leads * 0.25))} leads/week at similar CPL",
                })
            elif -0.10 < cpl_pct <= -0.05:
                c_opps.append({
                    "type": "cpl_momentum",
                    "category": "reduce_cpl",
                    "message": (
                        f"CPL improved {abs(cpl_pct)*100:.0f}% WoW (€{prev_cpl:.0f}→€{cpl:.0f}) "
                        f"— efficiency building, momentum to sustain"
                    ),
                    "action": (
                        f"Don't scale budget yet — let the improvement compound first. "
                        f"In Ads Manager → Ad Sets: sort by Cost per Result ↑ to identify which set is driving this. "
                        f"Shift 10–15% of budget from your most expensive ad set toward the improving one."
                    ),
                    "expected_uplift": f"CPL may drop a further 5–10% over the next 7 days",
                })

        if frequency < 2.0 and cpl > 0 and leads >= 3:
            c_opps.append({
                "type": "scale_low_frequency",
                "category": "maximize",
                "cpl_note": (
                    f"CPL may rise 10–20% temporarily as Meta explores new audience segments at higher volume — "
                    f"normal with scale, expected to stabilise within 1–2 weeks"
                ),
                "message": (
                    f"Frequency only {frequency:.1f}× — audience has plenty of headroom before fatigue "
                    f"(danger zone starts at 3.5×)"
                ),
                "action": (
                    f"Scale budget 20–30% now. "
                    f"At current CPL €{cpl:.0f}, each extra €{cpl:.0f}/day ≈ +1 lead/day. "
                    f"No creative refresh needed yet — the existing ads are under-served."
                ),
                "expected_uplift": f"+{max(1, int(leads * 0.25))} leads/week",
            })

        # Creative efficiency window: freq 2–3.5, CPL stable, no frequency flag yet
        has_freq_flag = any(f["type"] in ("frequency_warning", "frequency_critical") for f in c_flags)
        if not has_freq_flag and 2.0 <= frequency <= 3.5 and leads >= 3 and cpl > 0:
            cpl_stable = (abs((cpl - prev_cpl) / prev_cpl) < 0.05) if prev_cpl > 0 else True
            if cpl_stable:
                c_opps.append({
                    "type": "creative_efficiency_test",
                    "category": "reduce_cpl",
                    "message": (
                        f"Frequency {frequency:.1f}× with stable CPL €{cpl:.0f} — "
                        f"optimal window to A/B test creatives before frequency creep"
                    ),
                    "action": (
                        f"In Ads Manager → Ads tab: duplicate your best-performing ad (highest CTR). "
                        f"Change only the opening hook or main visual — keep CTA and body the same. "
                        f"Run both for 7 days minimum. If the variant beats current CPL, pause the original. "
                        f"Act now — at freq {frequency:.1f}× you have time to find a winner before saturation forces your hand."
                    ),
                    "expected_uplift": "Potential CPL reduction of 10–20% with a winning creative variant",
                })

        entry = {
            "market": market, "campaign_id": cid, "campaign_name": name, "product": product,
            "spend": spend, "leads": leads, "cpl": cpl, "frequency": frequency,
            "ctr": ctr, "cpm": cpm, "prev_cpl": prev_cpl, "prev_leads": prev_leads,
            "flags": c_flags, "opportunities": c_opps,
        }

        if c_flags:
            flags.append(entry)
        elif c_opps:
            opps.append(entry)
        else:
            stable.append(entry)

    return flags, opps, stable
