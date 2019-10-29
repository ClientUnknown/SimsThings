from protocolbuffers.DistributorOps_pb2 import Operationfrom distributor.ops import Op, GenericProtocolBufferOpfrom distributor.system import Distributor
def send_sim_commodity_progress_update_message(sim, msg):
    if sim.is_selectable and sim.valid_for_distribution:
        distributor = Distributor.instance()
        op = GenericProtocolBufferOp(Operation.SIM_COMMODITY_PROGRESS_UPDATE, msg)
        distributor.add_op(sim, op)

def send_sim_commodity_list_update_message(sim, msg):
    if sim.is_selectable and sim.valid_for_distribution:
        distributor = Distributor.instance()
        op = GenericProtocolBufferOp(Operation.SIM_COMMODITY_LIST_UPDATE, msg)
        distributor.add_op(sim, op)

def send_sim_ranked_stat_update_message(sim, msg, allow_npc=False):
    if (allow_npc or sim.is_selectable) and sim.valid_for_distribution:
        distributor = Distributor.instance()
        op = GenericProtocolBufferOp(Operation.RANKED_STATISTIC_PROGRESS, msg)
        distributor.add_op(sim, op)

def send_sim_ranked_stat_change_rank_change_update_message(sim, msg):
    if sim.is_selectable and sim.valid_for_distribution:
        distributor = Distributor.instance()
        op = GenericProtocolBufferOp(Operation.RANKED_STATISTIC_RANK_CHANGED, msg)
        distributor.add_op(sim, op)

def send_sim_life_skill_update_message(sim, msg):
    if sim.is_selectable and sim.valid_for_distribution:
        distributor = Distributor.instance()
        op = GenericProtocolBufferOp(Operation.LIFE_SKILL_UPDATE, msg)
        distributor.add_op(sim, op)

def send_sim_life_skill_delete_message(sim, msg):
    if sim.is_selectable and sim.valid_for_distribution:
        distributor = Distributor.instance()
        op = GenericProtocolBufferOp(Operation.LIFE_SKILL_DELETE, msg)
        distributor.add_op(sim, op)

def send_sim_alert_update_message(sim, msg):
    if sim.is_npc or sim.valid_for_distribution:
        distributor = Distributor.instance()
        op = GenericProtocolBufferOp(Operation.SIM_ALERT_UPDATE, msg)
        distributor.add_op(sim, op)
