from protocolbuffers import DistributorOps_pb2from distributor.ops import Op
class SetFocusScore(Op):

    def __init__(self, focus_score):
        super().__init__()
        self.op = DistributorOps_pb2.SetFocusScore()
        focus_score.populate_focus_score_msg(self.op)

    def write(self, msg):
        self.serialize_op(msg, self.op, DistributorOps_pb2.Operation.SET_FOCUS_SCORE)
