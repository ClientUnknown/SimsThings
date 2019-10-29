from protocolbuffers import Consts_pb2, InteractionOps_pb2from clock import ClockSpeedModeimport distributorimport services
def travel_sim_to_zone(sim_id, zone_id):
    travel_sims_to_zone((sim_id,), zone_id)

def travel_sims_to_zone(sim_ids, zone_id):
    travel_info = InteractionOps_pb2.TravelSimsToZone()
    travel_info.zone_id = zone_id
    travel_info.sim_ids.extend(sim_ids)
    distributor.system.Distributor.instance().add_event(Consts_pb2.MSG_TRAVEL_SIMS_TO_ZONE, travel_info)
    services.game_clock_service().set_clock_speed(ClockSpeedMode.PAUSED)
