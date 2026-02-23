"""
Analytics service — computes negotiation depth, carrier objections,
top lanes, and equipment demand/supply from the last 30 days of data.
"""

from collections import Counter, defaultdict

from app.db.repositories.analytics_repo import (
    get_all_calls_last_30_days,
    get_available_loads_by_equipment,
    get_booked_calls_last_30_days,
    get_failed_calls_last_30_days,
    get_recent_calls_by_equipment,
)
from app.models.analytics import (
    AnalyticsResponse,
    CarrierObjection,
    EquipmentDemandSupply,
    NegotiationDepthBucket,
    TopLane,
)

# ── Negotiation depth bucket labels ──────────────────────────────────────────

_DEPTH_LABELS = {
    0: "1st offer",
    1: "1 round",
    2: "2 rounds",
    3: "3 rounds (max)",
}


def _negotiation_depth() -> list[NegotiationDepthBucket]:
    """Distribution of how quickly deals close (booked calls, last 30 days)."""
    booked = get_booked_calls_last_30_days()
    if not booked:
        return []

    buckets: Counter[str] = Counter()
    for call in booked:
        rounds = call.get("negotiation_rounds", 0) or 0
        key = min(rounds, 3)
        buckets[key] += 1

    total = sum(buckets.values())
    result: list[NegotiationDepthBucket] = []
    for key in sorted(buckets):
        label = _DEPTH_LABELS.get(key, f"{key} rounds")
        pct = round(buckets[key] / total * 100)
        result.append(NegotiationDepthBucket(round=label, pct=pct))

    return result


# ── Carrier objections ───────────────────────────────────────────────────────


def _carrier_objections() -> list[CarrierObjection]:
    """Top reasons carriers decline (failed/dropped calls, last 30 days).

    Also includes no_loads_available calls from all calls in the last 30 days.
    """
    failed = get_failed_calls_last_30_days()
    all_calls = get_all_calls_last_30_days()

    reasons: Counter[str] = Counter()

    for call in failed:
        outcome = call.get("outcome", "")
        if outcome == "negotiation_failed":
            reasons["Rate too low"] += 1
        elif outcome == "dropped_call":
            reasons["Call dropped"] += 1

    # Count no_loads_available from all calls
    for call in all_calls:
        if call.get("outcome") == "no_loads_available":
            reasons["No matching loads"] += 1

    if not reasons:
        return []

    total = sum(reasons.values())
    result: list[CarrierObjection] = []
    for reason, count in reasons.most_common():
        pct = round(count / total * 100)
        result.append(CarrierObjection(reason=reason, count=count, pct=pct))

    return result


# ── Top lanes ────────────────────────────────────────────────────────────────


def _top_lanes() -> list[TopLane]:
    """Highest volume lanes (last 30 days, top 5)."""
    all_calls = get_all_calls_last_30_days()

    lane_calls: Counter[str] = Counter()
    lane_bookings: Counter[str] = Counter()
    lane_rates: defaultdict[str, list[float]] = defaultdict(list)

    for call in all_calls:
        origin = call.get("lane_origin")
        dest = call.get("lane_destination")
        if not origin or not dest:
            continue

        lane = f"{origin} \u2192 {dest}"
        lane_calls[lane] += 1

        if call.get("outcome") == "booked":
            lane_bookings[lane] += 1
            # agreed_rate comes from the booked_loads JOIN; fall back to
            # final_rate on the call itself when the JOIN doesn't match.
            agreed = call.get("agreed_rate") or call.get("final_rate")
            if agreed is not None:
                lane_rates[lane].append(float(agreed))

    if not lane_calls:
        return []

    result: list[TopLane] = []
    for lane, calls_count in lane_calls.most_common(5):
        bookings = lane_bookings.get(lane, 0)
        rates = lane_rates.get(lane, [])
        if rates:
            avg = sum(rates) / len(rates)
            avg_rate = f"${avg:,.0f}"
        else:
            avg_rate = "$0"

        result.append(
            TopLane(
                lane=lane,
                calls=calls_count,
                bookings=bookings,
                avg_rate=avg_rate,
            )
        )

    return result


# ── Equipment demand / supply ────────────────────────────────────────────────

_EQUIP_LABELS = {
    "dry_van": "Dry Van",
    "reefer": "Reefer",
    "flatbed": "Flatbed",
    "step_deck": "Step Deck",
    "power_only": "Power Only",
}


def _format_equip(raw: str) -> str:
    return _EQUIP_LABELS.get(raw, raw.replace("_", " ").title())


def _equipment_demand_supply() -> list[EquipmentDemandSupply]:
    """Equipment type balance: demand (available loads) vs supply (recent calls)."""
    demand_raw = get_available_loads_by_equipment()
    supply_raw = get_recent_calls_by_equipment()

    all_types = sorted(set(demand_raw) | set(supply_raw))
    if not all_types:
        return []

    demand_total = sum(demand_raw.values()) or 1
    supply_total = sum(supply_raw.values()) or 1

    result: list[EquipmentDemandSupply] = []
    for eq in all_types:
        demand_pct = round(demand_raw.get(eq, 0) / demand_total * 100)
        supply_pct = round(supply_raw.get(eq, 0) / supply_total * 100)
        result.append(
            EquipmentDemandSupply(
                type=_format_equip(eq),
                demand=demand_pct,
                supply=supply_pct,
            )
        )

    # Sort by demand descending for readability
    result.sort(key=lambda x: x.demand, reverse=True)
    return result


# ── Public entry point ───────────────────────────────────────────────────────


def get_analytics() -> AnalyticsResponse:
    return AnalyticsResponse(
        negotiation_depth=_negotiation_depth(),
        carrier_objections=_carrier_objections(),
        top_lanes=_top_lanes(),
        equipment_demand_supply=_equipment_demand_supply(),
    )
