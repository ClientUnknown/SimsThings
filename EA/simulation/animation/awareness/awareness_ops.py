from protocolbuffers import Animation_pb2, DistributorOps_pb2from animation.awareness.awareness_tuning import AwarenessTuningfrom distributor.ops import Opfrom distributor.rollback import ProtocolBufferRollbackfrom singletons import UNSET, DEFAULT
class SetAwarenessOp(Op):
    PROXIMITY_INNER_RADIUS = 'pir'
    PROXIMITY_OUTER_RADIUS = 'por'

    def __init__(self, awareness_modifiers):
        super().__init__()
        self.op = Animation_pb2.ConfigureAwarenessActor()
        for (awareness_channel, awareness_options) in awareness_modifiers.items():
            if awareness_channel in (self.PROXIMITY_INNER_RADIUS, self.PROXIMITY_OUTER_RADIUS):
                pass
            else:
                if not awareness_options:
                    awareness_options = DEFAULT
                else:
                    awareness_options = awareness_options[0]
                if awareness_options is UNSET:
                    self.op.channels_to_remove.append(awareness_channel)
                else:
                    awareness_channel_data = AwarenessTuning.AWARENESS_CHANNEL_DATA.get(awareness_channel)
                    with ProtocolBufferRollback(self.op.channels_to_configure) as awareness_options_msg:
                        awareness_options_msg.name = awareness_channel
                        awareness_options_msg.type_name = awareness_channel.get_type_name()
                        if awareness_options is not DEFAULT:
                            awareness_options_msg.gate = awareness_options.gate
                            awareness_options_msg.gain = awareness_options.gain
                            awareness_options_msg.trigger_threshold_delta = awareness_options.threshold
                        if awareness_channel_data is not None:
                            awareness_options_msg.eval_mode = awareness_channel_data.evaluation_type
                            awareness_options_msg.limit = awareness_channel_data.limit
        proximity_inner_radii = awareness_modifiers.get(self.PROXIMITY_INNER_RADIUS, ())
        if proximity_inner_radii:
            self.op.proximity_inner_radius = max(proximity_inner_radii)
        proximity_outer_radii = awareness_modifiers.get(self.PROXIMITY_OUTER_RADIUS, ())
        if proximity_outer_radii:
            self.op.proximity_outer_radius = min(proximity_outer_radii)

    def write(self, msg):
        self.serialize_op(msg, self.op, DistributorOps_pb2.Operation.AWARENESS_CONFIGURE_AWARENESS)

class SetAwarenessSourceOp(Op):

    def __init__(self, awareness_sources):
        super().__init__()
        self.op = Animation_pb2.ConfigureAwarenessSourceObject()
        if awareness_sources is not None:
            for (awareness_channel, awareness_score) in awareness_sources.items():
                if awareness_score:
                    with ProtocolBufferRollback(self.op.gameplay_channel_values) as awareness_score_msg:
                        awareness_score_msg.name = awareness_channel
                        awareness_score_msg.value = awareness_score

    def write(self, msg):
        self.serialize_op(msg, self.op, DistributorOps_pb2.Operation.AWARENESS_CONFIGURE_NOTICEABLE)
