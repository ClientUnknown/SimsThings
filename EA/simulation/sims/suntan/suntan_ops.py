from protocolbuffers import DistributorOps_pb2from careers.prep_tasks.prep_tasks_tracker import protocol_constantsfrom distributor.ops import Opfrom distributor.rollback import ProtocolBufferRollback
class SetTanLevel(Op):

    def __init__(self, suntan_data):
        super().__init__()
        self._suntan_data = suntan_data

    def write(self, msg):
        tan_level = None
        outfit_part_data_list = None
        force_update = None
        if self._suntan_data:
            tan_level = self._suntan_data.tan_level
            outfit_part_data_list = self._suntan_data.outfit_part_data_list
            force_update = self._suntan_data.force_update
        op = DistributorOps_pb2.SetTanLevel()
        if tan_level is not None:
            op.tan_level = tan_level
        if outfit_part_data_list is not None:
            for (part_id, body_type) in outfit_part_data_list:
                with ProtocolBufferRollback(op.outfit_part_data_list) as entry:
                    entry.id = part_id
                    entry.body_type = body_type
        if force_update is not None:
            op.force_update = force_update
        self.serialize_op(msg, op, protocol_constants.SET_TAN_LEVEL)
