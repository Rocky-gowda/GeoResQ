"""
Simulation data: Bengaluru-style fictional coordinates and routes.
All data is SIMULATED for hackathon demonstration purposes.
"""
from app.models import Coordinate, Incident, IncidentType

# Central Bengaluru area coordinates (fictional but realistic)
BENGALURU_CENTER = Coordinate(lat=12.9716, lng=77.5946)

# Destinations
DESTINATIONS = {
    "hospital_a": Coordinate(lat=12.9850, lng=77.5800),  # Manipal Hospital area (fictional)
    "hospital_b": Coordinate(lat=12.9600, lng=77.6100),  # St. John's area (fictional)
    "fire_station": Coordinate(lat=12.9750, lng=77.5950),
}

# Vehicle A (Ambulance) - planned route: south to north through MG Road corridor
VEHICLE_A_START = Coordinate(lat=12.9550, lng=77.6100)
VEHICLE_A_DESTINATION = Coordinate(lat=12.9850, lng=77.5800)

VEHICLE_A_PLANNED_ROUTE = [
    Coordinate(lat=12.9550, lng=77.6100),
    Coordinate(lat=12.9580, lng=77.6080),
    Coordinate(lat=12.9610, lng=77.6050),
    Coordinate(lat=12.9640, lng=77.6020),
    Coordinate(lat=12.9670, lng=77.5990),
    Coordinate(lat=12.9700, lng=77.5960),
    Coordinate(lat=12.9720, lng=77.5930),
    Coordinate(lat=12.9750, lng=77.5900),
    Coordinate(lat=12.9780, lng=77.5870),
    Coordinate(lat=12.9810, lng=77.5840),
    Coordinate(lat=12.9850, lng=77.5800),
]

# Deviation route - Vehicle A detours significantly east due to congestion/accident
VEHICLE_A_DEVIATION_ROUTE = [
    Coordinate(lat=12.9700, lng=77.5960),  # deviation starts here (waypoint 5)
    Coordinate(lat=12.9678, lng=77.6035),  # sharp east turn — clearly off route
    Coordinate(lat=12.9658, lng=77.6090),  # well off-route east
    Coordinate(lat=12.9670, lng=77.6130),  # deepest deviation point
    Coordinate(lat=12.9700, lng=77.6110),
    Coordinate(lat=12.9740, lng=77.6070),
    Coordinate(lat=12.9775, lng=77.6010),
    Coordinate(lat=12.9810, lng=77.5920),
    Coordinate(lat=12.9840, lng=77.5850),
    Coordinate(lat=12.9850, lng=77.5800),
]

# Alternative routes for Vehicle A
VEHICLE_A_ALT_ROUTE_B = [
    Coordinate(lat=12.9700, lng=77.5960),
    Coordinate(lat=12.9720, lng=77.5980),
    Coordinate(lat=12.9745, lng=77.5955),
    Coordinate(lat=12.9768, lng=77.5925),
    Coordinate(lat=12.9800, lng=77.5860),
    Coordinate(lat=12.9835, lng=77.5825),
    Coordinate(lat=12.9850, lng=77.5800),
]

VEHICLE_A_ALT_ROUTE_C = [
    Coordinate(lat=12.9700, lng=77.5960),
    Coordinate(lat=12.9680, lng=77.5940),
    Coordinate(lat=12.9700, lng=77.5910),
    Coordinate(lat=12.9730, lng=77.5880),
    Coordinate(lat=12.9770, lng=77.5845),
    Coordinate(lat=12.9810, lng=77.5818),
    Coordinate(lat=12.9850, lng=77.5800),
]

# Vehicle B (Ambulance) - nearby, on standby / patrolling
VEHICLE_B_START = Coordinate(lat=12.9780, lng=77.5860)
VEHICLE_B_DESTINATION = Coordinate(lat=12.9850, lng=77.5800)

VEHICLE_B_PLANNED_ROUTE = [
    Coordinate(lat=12.9780, lng=77.5860),
    Coordinate(lat=12.9800, lng=77.5840),
    Coordinate(lat=12.9820, lng=77.5820),
    Coordinate(lat=12.9850, lng=77.5800),
]

# Vehicle C (Fire Truck) - separate corridor
VEHICLE_C_START = Coordinate(lat=12.9620, lng=77.5850)
VEHICLE_C_DESTINATION = Coordinate(lat=12.9750, lng=77.5950)

VEHICLE_C_PLANNED_ROUTE = [
    Coordinate(lat=12.9620, lng=77.5850),
    Coordinate(lat=12.9650, lng=77.5870),
    Coordinate(lat=12.9680, lng=77.5900),
    Coordinate(lat=12.9710, lng=77.5920),
    Coordinate(lat=12.9750, lng=77.5950),
]

# Incidents — SIMULATED
INITIAL_INCIDENTS = [
    Incident(
        id="inc_001",
        type=IncidentType.ACCIDENT,
        location=Coordinate(lat=12.9720, lng=77.5930),
        radius_meters=200,
        severity="high",
        description="[SIMULATED] Multi-vehicle collision on main corridor. Lane blockage reported.",
        active=True,
    ),
    Incident(
        id="inc_002",
        type=IncidentType.ROAD_CLOSURE,
        location=Coordinate(lat=12.9750, lng=77.5900),
        radius_meters=150,
        severity="high",
        description="[SIMULATED] Road closure due to utility work. Both lanes blocked.",
        active=True,
    ),
    Incident(
        id="inc_003",
        type=IncidentType.CONGESTION,
        location=Coordinate(lat=12.9670, lng=77.5990),
        radius_meters=300,
        severity="medium",
        description="[SIMULATED] Heavy traffic congestion detected. Average speed < 10 km/h.",
        active=True,
    ),
]
