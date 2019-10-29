from protocolbuffers import DistributorOps_pb2from distributor.ops import Opfrom sims4.resources import get_protobuff_for_keyprotocol_constants = DistributorOps_pb2.Operation
def _create_holiday_info(holiday_id, name, icon, time_off_for_work, time_off_for_school, traditions, can_be_modified, lot_decoration_preset):
    distributor_op = DistributorOps_pb2.SendHolidayInfo()
    distributor_op.holiday_type = holiday_id
    distributor_op.name = name
    distributor_op.icon = get_protobuff_for_key(icon)
    distributor_op.time_off_for_work = time_off_for_work
    distributor_op.time_off_for_school = time_off_for_school
    for tradition_type in traditions:
        distributor_op.traditions.append(tradition_type.guid64)
    distributor_op.can_be_modified = can_be_modified
    if lot_decoration_preset is not None:
        distributor_op.lot_decoration_preset = lot_decoration_preset.guid64
    return distributor_op

class SendHolidayInfo(Op):

    def __init__(self, holiday_id, name, icon, time_off_for_work, time_off_for_school, traditions, can_be_modified, lot_decoration_preset):
        super().__init__()
        self.op = _create_holiday_info(holiday_id, name, icon, time_off_for_work, time_off_for_school, traditions, can_be_modified, lot_decoration_preset)

    def write(self, msg):
        msg.type = protocol_constants.HOLIDAY_INFO
        msg.data = self.op.SerializeToString()

class SendActiveHolidayInfo(Op):

    def __init__(self, update_type, holiday_id, name, icon, time_off_for_work, time_off_for_school, traditions, can_be_modified, lot_decoration_preset):
        super().__init__()
        self.op = DistributorOps_pb2.SendActiveHolidayInfo()
        self.op.update_type = update_type
        self.op.holiday_info = _create_holiday_info(holiday_id, name, icon, time_off_for_work, time_off_for_school, traditions, can_be_modified, lot_decoration_preset)

    def write(self, msg):
        msg.type = protocol_constants.ACTIVE_HOLIDAY_INFO
        msg.data = self.op.SerializeToString()
