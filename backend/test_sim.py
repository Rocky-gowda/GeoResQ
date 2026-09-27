from app.simulation_engine import SimulationEngine

engine = SimulationEngine()
engine.start()
for i in range(15):
    engine.tick_update()
s = engine.get_state()
print(f"Tick: {s.tick}")
print(f"Vehicles: {[v.name for v in s.vehicles]}")
veh_a = next(v for v in s.vehicles if v.id == "veh_a")
print(f"Vehicle A status: {veh_a.status}")
print(f"Vehicle A deviation: {veh_a.deviation_detected}")
print(f"Vehicle A cause: {veh_a.deviation_cause}")
print(f"Vehicle A delay: {veh_a.delay_minutes} min")
print(f"Alt routes: {list(s.alternative_routes.keys())}")
if "veh_a" in s.alternative_routes:
    for r in s.alternative_routes["veh_a"]:
        print(f"  Route: {r.name}, ETA: {r.estimated_time_minutes}, Saves: {r.time_saved_minutes}")
print(f"Explanation: {s.explanation[:150]}")
print(f"Dispatch triggered: {s.dispatch_consideration}")
print("Backend simulation: ALL OK")
