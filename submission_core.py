import re
from typing import Any

MAX_BODY_LENGTH = 320


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def clip(text: str, limit: int = MAX_BODY_LENGTH) -> str:
    text = compact(text).replace("http://", "").replace("https://", "")
    if len(text) <= limit:
        return text
    shortened = text[: limit - 1].rstrip()
    if " " in shortened:
        shortened = shortened.rsplit(" ", 1)[0]
    return shortened + "..."


def format_pct(value: float | None) -> str:
    if value is None:
        return ""
    return f"{int(round(value * 100))}%"


def format_delta(delta: float | None) -> str:
    if delta is None:
        return ""
    pct = int(round(abs(delta) * 100))
    sign = "+" if delta >= 0 else "-"
    return f"{sign}{pct}%"


def get_active_offer(merchant: dict[str, Any]) -> str | None:
    for offer in merchant.get("offers", []):
        if offer.get("status") == "active":
            return offer.get("title")
    return None


def find_signal_value(merchant: dict[str, Any], prefix: str) -> str | None:
    for signal in merchant.get("signals", []):
        if signal.startswith(prefix):
            parts = signal.split(":", 1)
            if len(parts) == 2:
                return parts[1]
    return None


def get_digest_item(category: dict[str, Any], item_id: str | None) -> dict[str, Any] | None:
    if not item_id:
        return None
    for item in category.get("digest", []):
        if item.get("id") == item_id:
            return item
    return None


def merchant_name(merchant: dict[str, Any]) -> str:
    category = merchant.get("category_slug", "")
    owner = merchant.get("identity", {}).get("owner_first_name")
    name = merchant.get("identity", {}).get("name", "there")
    if category == "dentists" and owner:
        return f"Dr. {owner}"
    return owner or name


def cta_for_trigger(trigger: dict[str, Any]) -> str:
    kind = trigger.get("kind", "")
    if kind in {"research_digest", "regulation_change", "cde_opportunity"}:
        return "open_ended"
    if trigger.get("scope") == "customer" and kind in {"recall_due", "trial_followup"}:
        return "booking_choice"
    return "binary_yes_no"


def build_rationale(category: dict[str, Any], merchant: dict[str, Any], trigger: dict[str, Any], customer: dict[str, Any] | None) -> str:
    audience = "customer-facing" if customer else "merchant-facing"
    return (
        f"{audience} message for {merchant.get('category_slug', 'merchant')} "
        f"using trigger {trigger.get('kind')} with grounded merchant/context facts"
    )


def compose_research_digest(category: dict[str, Any], merchant: dict[str, Any], trigger: dict[str, Any]) -> str:
    item = get_digest_item(category, trigger.get("payload", {}).get("top_item_id"))
    recipient = merchant_name(merchant)
    if item:
        trial_n = item.get("trial_n")
        segment = item.get("patient_segment", "").replace("_", " ")
        anchor = f"{trial_n}-patient" if trial_n else "new"
        segment_text = f" for your {segment}" if segment else ""
        return clip(
            f"{recipient}, {item['source']} has one item relevant{segment_text} "
            f"- {anchor} data says {item['title'].lower()}. Reply YES and I'll send the patient-facing WhatsApp angle plus one GBP line."
        )
    return clip(
        f"{recipient}, your category digest has a new research item this week. Reply YES and I'll send the 2-line takeaway with a ready post angle."
    )


def compose_regulation_change(category: dict[str, Any], merchant: dict[str, Any], trigger: dict[str, Any]) -> str:
    payload = trigger.get("payload", {})
    item = get_digest_item(category, payload.get("top_item_id"))
    recipient = merchant_name(merchant)
    deadline = payload.get("deadline_iso", "")
    headline = item.get("title") if item else "a compliance update"
    source = item.get("source") if item else "latest circular"
    return clip(
        f"{recipient}, heads-up: {headline} per {source}. Deadline is {deadline[:10]}. "
        f"Reply YES and I'll send the shortest compliance checklist before the cutoff."
    )


def compose_perf_dip(category: dict[str, Any], merchant: dict[str, Any], trigger: dict[str, Any]) -> str:
    payload = trigger.get("payload", {})
    metric = payload.get("metric", "performance")
    delta = format_delta(payload.get("delta_pct"))
    baseline = payload.get("vs_baseline")
    peer_ctr = category.get("peer_stats", {}).get("avg_ctr")
    recipient = merchant_name(merchant)
    return clip(
        f"{recipient}, your {metric} dipped {delta} in the last {payload.get('window', '7d')}. "
        f"You're at {baseline or merchant.get('performance', {}).get(metric, '')} vs peer CTR {format_pct(peer_ctr)}. "
        f"Reply YES and I'll send the one fix most likely to recover it this week."
    )


def compose_renewal_due(merchant: dict[str, Any], trigger: dict[str, Any]) -> str:
    payload = trigger.get("payload", {})
    recipient = merchant_name(merchant)
    return clip(
        f"{recipient}, your {payload.get('plan', 'plan')} renews in {payload.get('days_remaining', merchant.get('subscription', {}).get('days_remaining', 'a few'))} days. "
        f"I already have the renewal summary structure in mind. Reply YES and I'll send the key numbers plus pause-risk in one message."
    )


def compose_festival(merchant: dict[str, Any], trigger: dict[str, Any]) -> str:
    payload = trigger.get("payload", {})
    offer = get_active_offer(merchant)
    recipient = merchant_name(merchant)
    city = merchant.get("identity", {}).get("city", "")
    days_until = payload.get("days_until")
    festival = payload.get("festival", "the festival window")
    days_text = f"in {days_until} days" if days_until is not None else "soon"
    return clip(
        f"{recipient}, {festival} is {days_text} for {city}. "
        f"Your clearest hook right now is {offer or 'one service+price offer'}, not a flat discount. "
        f"I can draft the exact festive WhatsApp + GBP line now. Reply YES."
    )


def compose_curious_ask(merchant: dict[str, Any]) -> str:
    recipient = merchant_name(merchant)
    locality = merchant.get("identity", {}).get("locality", "")
    offer = get_active_offer(merchant)
    return clip(
        f"{recipient}, quick market read for {locality}: which one is getting more asks this week - "
        f"{offer or 'your main service'} or something else? Reply with one line and I'll turn it into a sharper WhatsApp hook."
    )


def compose_winback(merchant: dict[str, Any], trigger: dict[str, Any]) -> str:
    payload = trigger.get("payload", {})
    recipient = merchant_name(merchant)
    return clip(
        f"{recipient}, since expiry, performance is down and {payload.get('lapsed_customers_added_since_expiry', 'more')} customers have lapsed. "
        f"Reply YES and I'll send one winback message built around a concrete offer, not a generic discount."
    )


def compose_ipl(merchant: dict[str, Any], trigger: dict[str, Any]) -> str:
    payload = trigger.get("payload", {})
    recipient = merchant_name(merchant)
    offer = get_active_offer(merchant)
    return clip(
        f"{recipient}, {payload.get('match')} starts today at {payload.get('match_time_iso', '')[11:16]}. "
        f"{offer or 'A match-night combo'} can work better than a flat % off. Reply YES and I'll send the one-line match-night creative now."
    )


def compose_review_theme(merchant: dict[str, Any], trigger: dict[str, Any]) -> str:
    payload = trigger.get("payload", {})
    recipient = merchant_name(merchant)
    return clip(
        f"{recipient}, {payload.get('occurrences_30d', 'Several')} recent reviews mention {payload.get('theme', 'the same issue')}. "
        f"Reply YES and I'll send one visible fix plus a response template you can use today."
    )


def compose_milestone(merchant: dict[str, Any], trigger: dict[str, Any]) -> str:
    payload = trigger.get("payload", {})
    recipient = merchant_name(merchant)
    return clip(
        f"{recipient}, you're at {payload.get('value_now')} reviews and close to {payload.get('milestone_value')}. "
        f"This window is ideal for a review push. Reply YES and I'll send the exact review-ask line plus one GBP post angle."
    )


def compose_planning(merchant: dict[str, Any], trigger: dict[str, Any]) -> str:
    payload = trigger.get("payload", {})
    topic = payload.get("intent_topic", "this plan").replace("_", " ")
    recipient = merchant_name(merchant)
    offer = get_active_offer(merchant)
    merchant_message = payload.get("merchant_last_message", "")
    return clip(
        f"{recipient}, based on '{merchant_message[:40]}', I can structure {topic} as "
        f"{offer or 'one concrete offer'}, one price point, and one CTA. Reply YES and I'll send the exact draft, not just ideas."
    )


def compose_seasonal_perf(merchant: dict[str, Any], trigger: dict[str, Any]) -> str:
    payload = trigger.get("payload", {})
    recipient = merchant_name(merchant)
    return clip(
        f"{recipient}, this looks like a seasonal dip, not a structural problem: {payload.get('metric', 'views')} {format_delta(payload.get('delta_pct'))}. "
        f"Reply YES and I'll send the seasonal hook most likely to keep you visible this week."
    )


def compose_supply_alert(merchant: dict[str, Any], trigger: dict[str, Any]) -> str:
    payload = trigger.get("payload", {})
    recipient = merchant_name(merchant)
    batches = ", ".join(payload.get("affected_batches", [])[:2])
    return clip(
        f"{recipient}, urgent: {payload.get('molecule')} alert on batches {batches} from {payload.get('manufacturer')}. "
        f"Reply YES and I'll send the customer-contact script plus counter checklist right away."
    )


def compose_category_seasonal(merchant: dict[str, Any], trigger: dict[str, Any]) -> str:
    payload = trigger.get("payload", {})
    recipient = merchant_name(merchant)
    trend = payload.get("trends", [])[:2]
    trend_text = ", ".join(trend)
    return clip(
        f"{recipient}, summer demand is shifting: {trend_text}. "
        f"Reply YES and I'll send one shelf/display line plus one customer nudge for the fastest-moving products."
    )


def compose_unverified(merchant: dict[str, Any], trigger: dict[str, Any]) -> str:
    payload = trigger.get("payload", {})
    recipient = merchant_name(merchant)
    uplift = format_pct(payload.get("estimated_uplift_pct"))
    return clip(
        f"{recipient}, your Google profile is still unverified. That usually blocks trust and can lift visibility by about {uplift}. "
        f"Reply YES and I'll send the fastest 3-step verification path."
    )


def compose_competitor(merchant: dict[str, Any], trigger: dict[str, Any]) -> str:
    payload = trigger.get("payload", {})
    recipient = merchant_name(merchant)
    return clip(
        f"{recipient}, {payload.get('competitor_name')} opened {payload.get('distance_km')} km away with {payload.get('their_offer')}. "
        f"Your response should be sharper positioning, not a generic discount. Reply YES and I'll send a counter-offer angle."
    )


def compose_dormant(merchant: dict[str, Any], trigger: dict[str, Any]) -> str:
    payload = trigger.get("payload", {})
    recipient = merchant_name(merchant)
    days = payload.get("days_since_last_merchant_message", "a while")
    last_topic = payload.get("last_topic", "growth")
    stale_posts = find_signal_value(merchant, "stale_posts")
    no_offer = "no active offers" if "no_active_offers" in merchant.get("signals", []) else None
    hook = no_offer or (f"posts stale for {stale_posts}" if stale_posts else "one missed growth lever")
    return clip(
        f"{recipient}, it's been {days} days since the last reply on {last_topic}, and right now I can already see {hook}. "
        f"Reply YES and I'll send the single highest-impact fix in 2 lines."
    )


def compose_perf_spike(merchant: dict[str, Any], trigger: dict[str, Any]) -> str:
    payload = trigger.get("payload", {})
    recipient = merchant_name(merchant)
    return clip(
        f"{recipient}, nice jump: {payload.get('metric', 'performance')} {format_delta(payload.get('delta_pct'))} in {payload.get('window', '7d')}. "
        f"Likely driver: {payload.get('likely_driver', 'recent activity')}. Reply YES and I'll send the follow-up draft to convert the momentum."
    )


def compose_cde(category: dict[str, Any], merchant: dict[str, Any], trigger: dict[str, Any]) -> str:
    item = get_digest_item(category, trigger.get("payload", {}).get("digest_item_id"))
    recipient = merchant_name(merchant)
    if item:
        fee = trigger.get("payload", {}).get("fee", "member pricing")
        date = item.get("date", "")
        date_text = date[:10] if date else "soon"
        return clip(
            f"{recipient}, on {date_text} there is a {item.get('credits', '')}-credit session from {item.get('source')}: "
            f"{item.get('title')}. {fee.replace('_', ' ')}. Reply YES and I'll send the 2-line takeaway before you decide."
        )
    return clip(f"{recipient}, there's a relevant CDE session coming up for your category. Reply YES and I'll send a short summary.")


def compose_customer_recall(merchant: dict[str, Any], trigger: dict[str, Any], customer: dict[str, Any]) -> str:
    payload = trigger.get("payload", {})
    name = customer.get("identity", {}).get("name", "there")
    slots = payload.get("available_slots", [])
    offer = get_active_offer(merchant) or payload.get("service_due", "").replace("_", " ")
    if slots:
        labels = [slot.get("label") for slot in slots[:2] if slot.get("label")]
        slot_text = " or ".join(labels)
        return clip(
            f"Hi {name}, {merchant.get('identity', {}).get('name')} here. "
            f"Your {payload.get('service_due', 'follow-up').replace('_', ' ')} is due. "
            f"We can hold {slot_text}. {offer}. Reply 1 or 2, or send a better time."
        )
    return clip(
        f"Hi {name}, {merchant.get('identity', {}).get('name')} here. "
        f"Your {payload.get('service_due', 'follow-up').replace('_', ' ')} is due. Reply YES and we'll share the next available slot."
    )


def compose_customer_wedding(merchant: dict[str, Any], trigger: dict[str, Any], customer: dict[str, Any]) -> str:
    payload = trigger.get("payload", {})
    name = customer.get("identity", {}).get("name", "there")
    return clip(
        f"Hi {name}, {merchant.get('identity', {}).get('name')} here. "
        f"Your wedding date is coming up on {payload.get('wedding_date')}. "
        f"This is a good time to lock your {payload.get('next_step_window_open', 'next prep step').replace('_', ' ')}. Reply YES if you want options."
    )


def compose_customer_lapsed(merchant: dict[str, Any], trigger: dict[str, Any], customer: dict[str, Any]) -> str:
    payload = trigger.get("payload", {})
    name = customer.get("identity", {}).get("name", "there")
    offer = get_active_offer(merchant) or "a focused restart plan"
    return clip(
        f"Hi {name}, {merchant.get('identity', {}).get('name')} here. "
        f"It's been {payload.get('days_since_last_visit')} days since your last visit for {payload.get('previous_focus', 'your earlier goal').replace('_', ' ')}. "
        f"We can restart with {offer}. Reply YES if you want the best slot this week."
    )


def compose_customer_trial_followup(merchant: dict[str, Any], trigger: dict[str, Any], customer: dict[str, Any]) -> str:
    payload = trigger.get("payload", {})
    name = customer.get("identity", {}).get("name", "there")
    options = payload.get("next_session_options", [])
    label = options[0].get("label") if options else "the next session"
    return clip(
        f"Hi {name}, thanks for trying {merchant.get('identity', {}).get('name')}. "
        f"We can hold {label} for you. Reply YES to confirm or send a better time."
    )


def compose_customer_refill(merchant: dict[str, Any], trigger: dict[str, Any], customer: dict[str, Any]) -> str:
    payload = trigger.get("payload", {})
    name = customer.get("identity", {}).get("name", "there")
    meds = ", ".join(payload.get("molecule_list", [])[:3])
    return clip(
        f"Namaste {name}, {merchant.get('identity', {}).get('name')} se. "
        f"Aapki refill {meds} ke liye due hai. Delivery address saved hai. Reply YES karein to refill ready kar dein."
    )


def compose_default(category: dict[str, Any], merchant: dict[str, Any], trigger: dict[str, Any], customer: dict[str, Any] | None) -> str:
    recipient = customer.get("identity", {}).get("name") if customer else merchant_name(merchant)
    why_now = trigger.get("kind", "").replace("_", " ")
    offer = get_active_offer(merchant)
    if customer:
        return clip(
            f"Hi {recipient}, {merchant.get('identity', {}).get('name')} here. Quick note on your {why_now}. "
            f"{offer or 'We have an option ready for you'}. Reply YES if you want details."
        )
    return clip(
        f"{recipient}, quick heads-up on your {why_now}. "
        f"{offer or 'There is a concrete next step available'}. Reply YES and I'll send the exact line."
    )


def compose(category: dict, merchant: dict, trigger: dict, customer: dict | None) -> dict:
    kind = trigger.get("kind")
    if trigger.get("scope") == "customer" and customer:
        if kind == "recall_due":
            body = compose_customer_recall(merchant, trigger, customer)
        elif kind == "wedding_package_followup":
            body = compose_customer_wedding(merchant, trigger, customer)
        elif kind == "customer_lapsed_hard":
            body = compose_customer_lapsed(merchant, trigger, customer)
        elif kind == "trial_followup":
            body = compose_customer_trial_followup(merchant, trigger, customer)
        elif kind == "chronic_refill_due":
            body = compose_customer_refill(merchant, trigger, customer)
        else:
            body = compose_default(category, merchant, trigger, customer)
        send_as = "merchant_on_behalf"
    else:
        send_as = "vera"
        if kind == "research_digest":
            body = compose_research_digest(category, merchant, trigger)
        elif kind == "regulation_change":
            body = compose_regulation_change(category, merchant, trigger)
        elif kind == "perf_dip":
            body = compose_perf_dip(category, merchant, trigger)
        elif kind == "renewal_due":
            body = compose_renewal_due(merchant, trigger)
        elif kind == "festival_upcoming":
            body = compose_festival(merchant, trigger)
        elif kind == "curious_ask_due":
            body = compose_curious_ask(merchant)
        elif kind == "winback_eligible":
            body = compose_winback(merchant, trigger)
        elif kind == "ipl_match_today":
            body = compose_ipl(merchant, trigger)
        elif kind == "review_theme_emerged":
            body = compose_review_theme(merchant, trigger)
        elif kind == "milestone_reached":
            body = compose_milestone(merchant, trigger)
        elif kind == "active_planning_intent":
            body = compose_planning(merchant, trigger)
        elif kind == "seasonal_perf_dip":
            body = compose_seasonal_perf(merchant, trigger)
        elif kind == "supply_alert":
            body = compose_supply_alert(merchant, trigger)
        elif kind == "category_seasonal":
            body = compose_category_seasonal(merchant, trigger)
        elif kind == "gbp_unverified":
            body = compose_unverified(merchant, trigger)
        elif kind == "competitor_opened":
            body = compose_competitor(merchant, trigger)
        elif kind == "dormant_with_vera":
            body = compose_dormant(merchant, trigger)
        elif kind == "perf_spike":
            body = compose_perf_spike(merchant, trigger)
        elif kind == "cde_opportunity":
            body = compose_cde(category, merchant, trigger)
        else:
            body = compose_default(category, merchant, trigger, customer)
    return {
        "body": clip(body),
        "cta": cta_for_trigger(trigger),
        "send_as": send_as,
        "suppression_key": trigger.get("suppression_key", ""),
        "rationale": build_rationale(category, merchant, trigger, customer),
    }
