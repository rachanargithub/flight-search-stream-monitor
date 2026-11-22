import json
import random
import uuid
from datetime import datetime, timedelta, timezone

DUP_RATE = 0.05    # 5% of events get sent twice
LATE_RATE = 0.05   # 5% of events arrive 1-10 minutes late


def add_chaos(events: list[tuple[str, dict]], truth: dict) -> list[tuple[str, dict]]:
    """Make events late, duplicate some, shuffle the order, and record what we did."""
    out = []
    for topic, ev in events:
        ev = dict(ev)                                   # copy, so we never change the original

        if random.random() < LATE_RATE:
            delay = random.randint(60, 600)             # 1-10 minutes
            happened = datetime.fromisoformat(ev["event_time"]) - timedelta(seconds=delay)
            ev["event_time"] = happened.isoformat()
            truth["late_sent"] += 1

        out.append((topic, ev))
        truth[f"unique_{topic}"] += 1

        if random.random() < DUP_RATE:
            out.append((topic, dict(ev)))               # exact copy: same event_id
            truth[f"duplicates_{topic}"] += 1

    random.shuffle(out)                                 # out-of-order delivery
    return out

ROUTES = {"LHR-JFK": 420, "LHR-DXB": 380, "ARN-BCN": 140, "LHR-DOH": 400, "LHR-AUH": 390}

def search_event(session_id: str, user_type: str, route: str) -> dict:
    origin, destination = route.split("-")
    return {
        "event_id": str(uuid.uuid4()),          # unique ID, used for dedup later
        "session_id": session_id,
        "true_user_type": user_type,            # ground truth: human or agent
        "route": route,
        "origin": origin,
        "destination": destination,
        "price_eur": round(ROUTES[route] * random.uniform(0.7, 1.6), 2),
        "event_time": datetime.now(timezone.utc).isoformat(),
    }
    
def booking_event(session_id: str, route: str, amount: float,
                  status: str = "confirmed", booking_id: str | None = None) -> dict:
    return {
        "event_id": str(uuid.uuid4()),                          # new for EVERY event
        "booking_id": booking_id or "BK" + uuid.uuid4().hex[:10].upper(),
        "session_id": session_id,
        "route": route,
        "amount_eur": amount,
        "status": status,                                       # "confirmed" or "cancelled"
        "event_time": datetime.now(timezone.utc).isoformat(),
    }

def session(is_agent: bool) -> list[tuple[str, dict]]:
    """One visitor -> list of (topic, event) pairs."""
    user_type = "agent" if is_agent else "human"
    session_id = ("AG-" if is_agent else "HU-") + uuid.uuid4().hex[:12]
    route = random.choice(list(ROUTES))
    n_searches = random.randint(150, 250) if is_agent else random.randint(3, 8)

    events = []
    for _ in range(n_searches):
        if is_agent and random.random() < 0.3:      # agents sweep other routes too
            route = random.choice(list(ROUTES))
        events.append(("searches", search_event(session_id, user_type, route)))

    book_probability = 0.003 if is_agent else 0.2
    if random.random() < book_probability:
        last_search = events[-1][1]
        events.append(("bookings", booking_event(session_id, last_search["route"],
                                                 last_search["price_eur"])))
    return events

if __name__ == "__main__":
    from collections import Counter
    from pathlib import Path

    truth = Counter()
    sent = 0
    out_dir = Path("data")
    out_dir.mkdir(exist_ok=True)

    with open(out_dir / "events.jsonl", "w") as f:
        for _ in range(1000):
            is_agent = random.random() < 0.15
            kind = "agent" if is_agent else "human"
            clean_events = session(is_agent)

            # 1) Count BEFORE the chaos: these are the true business numbers
            for topic, _ in clean_events:
                truth[f"{topic}_{kind}"] += 1

            # 2) Break the data on purpose, then write what "Kafka" would receive
            for topic, ev in add_chaos(clean_events, truth):
                f.write(json.dumps({"topic": topic, **ev}) + "\n")
                sent += 1

    truth["total_sent"] = sent
    (out_dir / "ground_truth.json").write_text(json.dumps(truth, indent=2))
    print(json.dumps(truth, indent=2))

    for kind in ("human", "agent"):
        searches = truth[f"searches_{kind}"]
        bookings = max(truth[f"bookings_{kind}"], 1)
        print(f"{kind}: look-to-book = {searches / bookings:.0f} searches per booking")