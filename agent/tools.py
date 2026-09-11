from datetime import datetime, timezone
import math
from typing import Any

# Demo data is intentionally local and deterministic. In production, replace the
# provider functions with GTFS-Realtime/GPS/AVL, ticketing, traffic and dispatch APIs.

ROUTES = {
    "R1": {"name": "North Gate → Main Campus", "stops": ["North Gate", "Library Junction", "Main Campus"]},
    "R2": {"name": "East Hostel → Main Campus", "stops": ["East Hostel", "Science Block", "Main Campus"]},
    "R3": {"name": "South Gate → Main Campus", "stops": ["South Gate", "Market Stop", "Main Campus"]},
    "R4": {"name": "West Apartments → Main Campus", "stops": ["West Apartments", "Stadium", "Main Campus"]},
}

BUSES = {
    "BUS-101": {"route": "R1", "driver": "A", "capacity": 50, "base_occupancy": 38, "progress": 0.62, "speed": 0.006, "delay": 4, "status": "running"},
    "BUS-102": {"route": "R1", "driver": "B", "capacity": 50, "base_occupancy": 46, "progress": 0.34, "speed": 0.007, "delay": 9, "status": "running"},
    "BUS-201": {"route": "R2", "driver": "C", "capacity": 45, "base_occupancy": 31, "progress": 0.73, "speed": 0.005, "delay": 2, "status": "running"},
    "BUS-202": {"route": "R2", "driver": "D", "capacity": 45, "base_occupancy": 43, "progress": 0.28, "speed": 0.004, "delay": 14, "status": "delayed"},
    "BUS-301": {"route": "R3", "driver": "E", "capacity": 55, "base_occupancy": 21, "progress": 0.44, "speed": 0.008, "delay": 0, "status": "running"},
    "BUS-302": {"route": "R3", "driver": "F", "capacity": 55, "base_occupancy": 52, "progress": 0.19, "speed": 0.006, "delay": 18, "status": "delayed"},
    "BUS-401": {"route": "R4", "driver": "G", "capacity": 40, "base_occupancy": 18, "progress": 0.58, "speed": 0.006, "delay": 1, "status": "running"},
    "BUS-402": {"route": "R4", "driver": "H", "capacity": 40, "base_occupancy": 0, "progress": 0.0, "speed": 0, "delay": 0, "status": "maintenance"},
}

STOP_DEMAND = {
    "North Gate": 12,
    "Library Junction": 19,
    "East Hostel": 26,
    "Science Block": 17,
    "South Gate": 9,
    "Market Stop": 33,
    "West Apartments": 8,
    "Stadium": 14,
    "Main Campus": 0,
}

INCIDENTS = [
    {"type": "traffic", "route": "R1", "severity": "medium", "reason": "Heavy traffic near Library Junction", "impact_minutes": 6},
    {"type": "roadblock", "route": "R3", "severity": "high", "reason": "Temporary road work near Market Stop", "impact_minutes": 12},
    {"type": "maintenance", "bus": "BUS-402", "route": "R4", "severity": "medium", "reason": "Scheduled brake inspection", "impact_minutes": None},
    {"type": "safety", "bus": "BUS-302", "route": "R3", "severity": "high", "reason": "Driver reported a warning light; bus is being inspected", "impact_minutes": None},
]

def _freshness():
    return datetime.now(timezone.utc).isoformat()

def _bus_snapshot(bus_id: str, b: dict) -> dict:
    now = datetime.now(timezone.utc)
    # Deterministic movement simulation: progress changes with wall-clock seconds.
    seconds = now.timestamp()
    progress = (b["progress"] + ((seconds % 900) * b["speed"])) % 1.0
    occupancy_wave = int(math.sin(seconds / 180 + b["progress"] * 10) * 2)
    occupancy = max(0, min(b["capacity"], b["base_occupancy"] + occupancy_wave))
    seats = b["capacity"] - occupancy
    stops = ROUTES[b["route"]]["stops"]
    idx = min(len(stops) - 2, int(progress * (len(stops) - 1)))
    current_stop = stops[idx]
    next_stop = stops[idx + 1]
    eta = max(2, round((1 - progress) * 18 + b["delay"]))
    status = b["status"]
    if status == "running" and b["delay"] >= 8:
        status = "delayed"
    return {
        "bus_id": bus_id,
        "route_id": b["route"],
        "route_name": ROUTES[b["route"]]["name"],
        "status": status,
        "capacity": b["capacity"],
        "occupancy": occupancy,
        "available_seats": seats,
        "occupancy_pct": round(occupancy / b["capacity"] * 100),
        "current_stop_or_area": current_stop,
        "next_stop": next_stop,
        "eta_minutes": eta,
        "delay_minutes": b["delay"],
        "last_updated": _freshness(),
    }

def get_fleet_status(route_id: str | None = None, status: str | None = None) -> dict:
    """Return current simulated GPS, occupancy and service status for campus buses."""
    buses = [_bus_snapshot(k, v) for k, v in BUSES.items()]
    if route_id:
        buses = [b for b in buses if b["route_id"].upper() == route_id.upper()]
    if status:
        buses = [b for b in buses if b["status"].lower() == status.lower()]
    return {"timestamp": _freshness(), "buses": buses}

def get_bus_details(bus_id: str) -> dict:
    """Return detailed current information for a specific bus."""
    bus_id = bus_id.upper().strip()
    if bus_id not in BUSES:
        return {"error": f"Bus {bus_id} was not found.", "available_bus_ids": list(BUSES)}
    snapshot = _bus_snapshot(bus_id, BUSES[bus_id])
    related = [x for x in INCIDENTS if x.get("bus") == bus_id or x.get("route") == snapshot["route_id"]]
    return {**snapshot, "incidents": related, "route_stops": ROUTES[snapshot["route_id"]]["stops"]}

def get_route_conditions(route_id: str | None = None) -> dict:
    """Return current traffic, roadblock and diversion conditions."""
    items = INCIDENTS
    if route_id:
        items = [x for x in items if x.get("route", "").upper() == route_id.upper()]
    return {"timestamp": _freshness(), "conditions": items}

def get_stop_demand(stop_name: str | None = None) -> dict:
    """Return current simulated student queue counts by pickup stop."""
    if stop_name:
        key = next((s for s in STOP_DEMAND if s.lower() == stop_name.lower()), None)
        if not key:
            return {"error": f"Stop '{stop_name}' was not found.", "stops": STOP_DEMAND}
        return {"timestamp": _freshness(), "stop": key, "waiting_students": STOP_DEMAND[key]}
    return {
        "timestamp": _freshness(),
        "stops": [{"stop": s, "waiting_students": n} for s, n in STOP_DEMAND.items()]
    }

def get_maintenance_and_incidents(bus_id: str | None = None, route_id: str | None = None) -> dict:
    """Return maintenance, breakdown, cancellation and safety incidents."""
    incidents = INCIDENTS
    if bus_id:
        incidents = [x for x in incidents if x.get("bus", "").upper() == bus_id.upper()]
    if route_id:
        incidents = [x for x in incidents if x.get("route", "").upper() == route_id.upper()]
    return {"timestamp": _freshness(), "incidents": incidents}

def analyze_demand() -> dict:
    """Combine stop demand and live bus capacity to identify pressure and spare capacity."""
    fleet = get_fleet_status()["buses"]
    route_stats = {}
    for route_id, route in ROUTES.items():
        buses = [b for b in fleet if b["route_id"] == route_id and b["status"] != "maintenance"]
        capacity = sum(b["available_seats"] for b in buses)
        waiting = sum(STOP_DEMAND.get(stop, 0) for stop in route["stops"][:-1])
        route_stats[route_id] = {
            "route": route["name"],
            "waiting_students": waiting,
            "available_seats": capacity,
            "pressure": round(waiting / max(capacity, 1), 2),
            "active_buses": len(buses),
        }

    overcrowded = sorted(route_stats.items(), key=lambda x: x[1]["pressure"], reverse=True)
    need_bus = [x for x in overcrowded if x[1]["pressure"] > 0.75]
    spare = [x for x in overcrowded if x[1]["pressure"] < 0.45]

    return {
        "timestamp": _freshness(),
        "routes": route_stats,
        "priority_routes_needing_capacity": need_bus,
        "routes_with_spare_capacity": spare,
    }

def recommend_alternative(origin_stop: str, destination: str = "Main Campus") -> dict:
    """Find a currently operating alternative bus using ETA, seats and route conditions."""
    fleet = get_fleet_status()["buses"]
    candidates = []
    for bus in fleet:
        if bus["status"] not in ("running", "delayed"):
            continue
        if bus["available_seats"] <= 0:
            continue
        route = ROUTES[bus["route_id"]]
        if origin_stop.lower() not in [s.lower() for s in route["stops"]]:
            continue
        condition = get_route_conditions(bus["route_id"])["conditions"]
        extra_delay = sum(i.get("impact_minutes", 0) or 0 for i in condition if i["type"] in ("traffic", "roadblock"))
        score = bus["eta_minutes"] + extra_delay + max(0, 8 - bus["available_seats"])
        candidates.append({
            "bus": bus,
            "extra_route_impact_minutes": extra_delay,
            "score": score,
        })
    candidates.sort(key=lambda x: x["score"])
    return {
        "origin_stop": origin_stop,
        "destination": destination,
        "recommended": candidates[0] if candidates else None,
        "alternatives": candidates[1:4],
        "timestamp": _freshness(),
    }

def recommend_redistribution() -> dict:
    """Recommend moving available capacity toward the highest current demand."""
    analysis = analyze_demand()
    fleet = get_fleet_status()["buses"]
    high = analysis["priority_routes_needing_capacity"]
    spare = analysis["routes_with_spare_capacity"]

    moves = []
    if high and spare:
        target_id, target = high[0]
        source_id, source = spare[0]
        donor = next((b for b in fleet if b["route_id"] == source_id and b["status"] == "running" and b["available_seats"] >= 10), None)
        if donor:
            moves.append({
                "action": f"Consider redeploying {donor['bus_id']} from {source_id} to {target_id}",
                "from_route": ROUTES[source_id]["name"],
                "to_route": ROUTES[target_id]["name"],
                "reason": f"{target['waiting_students']} waiting students vs {target['available_seats']} seats on target route; donor route has spare capacity.",
                "passenger_disruption": "Low if dispatch confirms another bus covers the donor route."
            })

    if not moves:
        moves.append({
            "action": "No immediate bus redistribution is recommended.",
            "reason": "Current demand/capacity data does not show a safe, clearly beneficial transfer."
        })

    return {"timestamp": _freshness(), "recommendations": moves, "demand_analysis": analysis}

TOOLS = {
    "get_fleet_status": get_fleet_status,
    "get_bus_details": get_bus_details,
    "get_route_conditions": get_route_conditions,
    "get_stop_demand": get_stop_demand,
    "analyze_demand": analyze_demand,
    "recommend_alternative": recommend_alternative,
    "recommend_redistribution": recommend_redistribution,
    "get_maintenance_and_incidents": get_maintenance_and_incidents,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "name": "get_fleet_status",
        "description": "Get current simulated campus fleet status, GPS area, ETA, occupancy and seats. Use for which buses are running, best bus, current buses and capacity.",
        "parameters": {"type": "object", "properties": {
            "route_id": {"type": ["string", "null"], "description": "Optional route such as R1"},
            "status": {"type": ["string", "null"], "description": "Optional status: running, delayed, maintenance"}
        }, "required": ["route_id", "status"], "additionalProperties": False},
        "strict": True
    },
    {
        "type": "function",
        "name": "get_bus_details",
        "description": "Get detailed current information for a specific bus including location, ETA, seats and incidents.",
        "parameters": {"type": "object", "properties": {"bus_id": {"type": "string"}}, "required": ["bus_id"], "additionalProperties": False},
        "strict": True
    },
    {
        "type": "function",
        "name": "get_route_conditions",
        "description": "Get current traffic, roadblocks, diversions and route impacts.",
        "parameters": {"type": "object", "properties": {"route_id": {"type": ["string", "null"]}}, "required": ["route_id"], "additionalProperties": False},
        "strict": True
    },
    {
        "type": "function",
        "name": "get_stop_demand",
        "description": "Get current student waiting counts at one or all pickup stops.",
        "parameters": {"type": "object", "properties": {"stop_name": {"type": ["string", "null"]}}, "required": ["stop_name"], "additionalProperties": False},
        "strict": True
    },
    {
        "type": "function",
        "name": "analyze_demand",
        "description": "Analyze current waiting demand versus available bus seats and identify overcrowded routes and spare capacity.",
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "strict": True
    },
    {
        "type": "function",
        "name": "recommend_alternative",
        "description": "Find the best alternative bus from a pickup stop to the destination using current ETA, seats and route disruptions.",
        "parameters": {"type": "object", "properties": {
            "origin_stop": {"type": "string"},
            "destination": {"type": "string"}
        }, "required": ["origin_stop", "destination"], "additionalProperties": False},
        "strict": True
    },
    {
        "type": "function",
        "name": "recommend_redistribution",
        "description": "Recommend how dispatch should redistribute available buses using current demand, capacity and disruptions.",
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "strict": True
    },
    {
        "type": "function",
        "name": "get_maintenance_and_incidents",
        "description": "Get maintenance, breakdown, cancellation and safety incidents for a bus or route.",
        "parameters": {"type": "object", "properties": {
            "bus_id": {"type": ["string", "null"]},
            "route_id": {"type": ["string", "null"]}
        }, "required": ["bus_id", "route_id"], "additionalProperties": False},
        "strict": True
    },
]
