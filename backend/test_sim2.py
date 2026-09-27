from app.simulation_engine import SimulationEngine

engine = SimulationEngine()
engine.start()
print("=== Simulating 30 ticks ===")
for i in range(30):
    engine.tick_update()
    s = engine.get_state()
    veh_a = next(v for v in s.vehicles if v.id == "veh_a")
    print(f"Tick {i+1:2d}: pos=({veh_a.current_position.lat:.4f},{veh_a.current_position.lng:.4f}) dev={str(veh_a.deviation_detected):5} dist={veh_a.deviation_distance_meters:.0f}m cause={veh_a.deviation_cause} delay={veh_a.delay_minutes:.1f}")

s = engine.get_state()
veh_a = next(v for v in s.vehicles if v.id == "veh_a")
print(f"\nFinal status: {veh_a.status}")
print(f"Alt routes: {len(s.alternative_routes.get('veh_a', []))}")
print(f"Decision events: {len(s.decision_timeline)}")
print(f"Dispatch: {s.dispatch_consideration.get('triggered', False) if s.dispatch_consideration else False}")
print("Done")
