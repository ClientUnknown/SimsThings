from protocolbuffers import Sims_pb2import enum
class BalloonTypeEnum(enum.Int):
    THOUGHT = 0
    SPEECH = 1
    DISTRESS = 2
BALLOON_TYPE_LOOKUP = {BalloonTypeEnum.DISTRESS: (Sims_pb2.AddBalloon.DISTRESS_TYPE, Sims_pb2.AddBalloon.MOTIVE_FAILURE_PRIORITY), BalloonTypeEnum.SPEECH: (Sims_pb2.AddBalloon.SPEECH_TYPE, Sims_pb2.AddBalloon.SPEECH_PRIORITY), BalloonTypeEnum.THOUGHT: (Sims_pb2.AddBalloon.THOUGHT_TYPE, Sims_pb2.AddBalloon.THOUGHT_PRIORITY)}