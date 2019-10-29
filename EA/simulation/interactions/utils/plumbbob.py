from protocolbuffers import DistributorOps_pb2 as protocols, Sims_pb2from distributor.ops import Opfrom distributor.system import Distributorfrom element_utils import build_critical_section_with_finallyfrom interactions import ParticipantTypeSinglefrom sims4.tuning.geometric import TunableVector3from sims4.tuning.tunable import Tunable, TunableFactory, TunableEnumEntryimport sims4.hash_utilimport sims4.mathlogger = sims4.log.Logger('Basic')
def unslot_plumbbob(sim):
    reslot_op = ReslotPlumbbob(sim.id, 0, None, sims4.math.Vector3.ZERO(), balloon_offset=sims4.math.Vector3.ZERO())
    Distributor.instance().add_op(sim, reslot_op)

def reslot_plumbbob(sim, reslot_plumbbob):
    reslot_op = ReslotPlumbbob(sim.id, sim.id, reslot_plumbbob.bone_name, reslot_plumbbob.offset, balloon_offset=reslot_plumbbob.balloon_offset)
    Distributor.instance().add_op(sim, reslot_op)

def with_reslot_plumbbob(interaction, bone_name, offset, target, balloon_offset, sequence=None):
    sim = interaction.sim
    subject = interaction.get_participant(target)
    logger.assert_raise(subject is not None, 'Interaction {} has no target {}, but is trying to reslot the plumbbob to {}'.format(interaction, target, bone_name), owner='nbaker')
    subject_suffix = subject.part_suffix
    if subject_suffix is not None:
        bone_name += subject_suffix
    distributor = Distributor.instance()

    def reslot(_):
        reslot_op = ReslotPlumbbob(sim.id, subject.id, bone_name, offset, balloon_offset=balloon_offset)
        distributor.add_op(sim, reslot_op)

    def unslot(_):
        unslot_plumbbob(sim)

    return build_critical_section_with_finally(reslot, sequence, unslot)

class TunableReslotPlumbbob(TunableFactory):
    FACTORY_TYPE = staticmethod(with_reslot_plumbbob)

    def __init__(self, **kwargs):
        super().__init__(bone_name=Tunable(description='\n                The name of the bone to which the plumbbob should be attached.\n                ', tunable_type=str, default=None), offset=TunableVector3(description='\n                The Vector3 offset from the bone to the plumbbob.\n                ', default=TunableVector3.DEFAULT_ZERO), target=TunableEnumEntry(description='\n                Who to reslot the plumbbob on.\n                ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object), balloon_offset=TunableVector3(description='\n                The Vector3 offset from the bone to the thought balloon.\n                ', default=TunableVector3.DEFAULT_ZERO), **kwargs)

class ReslotPlumbbob(Op):

    def __init__(self, sim_id, obj_id, bone_name, offset, balloon_offset=None):
        super().__init__()
        self._sim_id = sim_id
        self._obj_id = obj_id
        self._bone_hash = sims4.hash_util.hash32(bone_name) if bone_name else 0
        self._offset = offset
        self._balloon_offset = balloon_offset

    def write(self, msg):
        reslot_msg = Sims_pb2.ReslotPlumbbob()
        reslot_msg.sim_id = self._sim_id
        reslot_msg.obj_id = self._obj_id
        reslot_msg.bone = self._bone_hash
        reslot_msg.offset.x = self._offset.x
        reslot_msg.offset.y = self._offset.y
        reslot_msg.offset.z = self._offset.z
        if self._balloon_offset is not None:
            reslot_msg.balloon_view_offset.x = self._balloon_offset.x
            reslot_msg.balloon_view_offset.y = self._balloon_offset.y
            reslot_msg.balloon_view_offset.z = self._balloon_offset.z
        self.serialize_op(msg, reslot_msg, protocols.Operation.RESLOT_PLUMBBOB)
